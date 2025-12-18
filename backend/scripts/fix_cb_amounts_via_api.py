#!/usr/bin/env python3
"""
CB 인수자 인수금액 수정 - DART API를 통해 공시 다운로드

로컬 파일이 없는 경우 DART API를 통해 직접 공시를 다운로드하여
인수금액을 추출하고 업데이트
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import re
import zipfile
import io
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_API_KEY = os.getenv('DART_API_KEY')
DART_BASE_URL = "https://opendart.fss.or.kr/api"


def _parse_amount(amount_str):
    """금액 파싱"""
    if not amount_str or amount_str == '-':
        return None
    try:
        cleaned = re.sub(r'[^\d]', '', amount_str)
        if cleaned:
            return int(cleaned)
    except ValueError:
        pass
    return None


def extract_subscribers_from_xml(content: str) -> dict:
    """XML에서 인수자별 금액 추출"""
    subscribers = {}

    # TR 단위로 ISSU_NM과 ISSU_AMT 찾기
    tr_pattern = r'<TR[^>]*>(.*?)</TR>'
    tr_matches = re.findall(tr_pattern, content, re.DOTALL | re.IGNORECASE)

    for tr_content in tr_matches:
        # ISSU_NM 찾기
        name_match = re.search(r'<TE[^>]*ACODE="ISSU_NM"[^>]*>(.*?)</TE>', tr_content, re.DOTALL | re.IGNORECASE)
        if not name_match:
            continue

        # 이름 정리
        name_raw = name_match.group(1)
        name = re.sub(r'<[^>]+>', '', name_raw)
        name = re.sub(r'&[^;]+;', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if not name or name == '-' or len(name) < 2:
            continue

        # 금액 추출
        amt_match = re.search(r'<TE[^>]*ACODE="ISSU_AMT"[^>]*>([^<]*)</TE>', tr_content, re.IGNORECASE)
        if amt_match:
            amount = _parse_amount(amt_match.group(1))
            if amount:
                subscribers[name] = amount

    return subscribers


async def download_disclosure(session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
    """DART API로 공시 다운로드"""
    try:
        params = {
            'crtfc_key': DART_API_KEY,
            'rcept_no': rcept_no
        }

        async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
            if response.status != 200:
                return None

            raw_content = await response.read()

            # ZIP 또는 XML 디코딩
            encodings = ['euc-kr', 'utf-8', 'cp949']

            try:
                with zipfile.ZipFile(io.BytesIO(raw_content)) as zf:
                    xml_filename = zf.namelist()[0]
                    xml_bytes = zf.read(xml_filename)

                    for encoding in encodings:
                        try:
                            return xml_bytes.decode(encoding)
                        except UnicodeDecodeError:
                            continue
            except zipfile.BadZipFile:
                for encoding in encodings:
                    try:
                        return raw_content.decode(encoding)
                    except UnicodeDecodeError:
                        continue

    except Exception as e:
        logger.debug(f"다운로드 실패 {rcept_no}: {e}")
    return None


async def main():
    if not DART_API_KEY:
        logger.error("DART_API_KEY 환경변수가 설정되지 않았습니다")
        return

    logger.info("=" * 80)
    logger.info("CB 인수자 인수금액 수정 (API 다운로드)")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 1. 인수금액이 NULL이고 source_disclosure_id가 있는 인수자 목록
        rows = await conn.fetch("""
            SELECT
                cs.id,
                cs.subscriber_name,
                cs.source_disclosure_id
            FROM cb_subscribers cs
            WHERE (cs.subscription_amount IS NULL OR cs.subscription_amount = 0)
              AND cs.source_disclosure_id IS NOT NULL
              AND cs.source_disclosure_id != ''
        """)

        logger.info(f"수정 대상 인수자: {len(rows)}건")

        if not rows:
            logger.info("수정할 인수자가 없습니다")
            return

        # 2. 공시별로 그룹화
        disclosure_map = {}
        for row in rows:
            rcept_no = row['source_disclosure_id']
            if rcept_no not in disclosure_map:
                disclosure_map[rcept_no] = []
            disclosure_map[rcept_no].append({
                'id': row['id'],
                'name': row['subscriber_name']
            })

        logger.info(f"관련 공시: {len(disclosure_map)}건")

        # 3. API로 공시 다운로드 및 업데이트
        stats = {'updated': 0, 'not_found': 0, 'download_failed': 0}

        async with aiohttp.ClientSession() as session:
            for i, (rcept_no, subscribers) in enumerate(disclosure_map.items()):
                # API 호출
                xml_content = await download_disclosure(session, rcept_no)

                if not xml_content:
                    stats['download_failed'] += len(subscribers)
                    continue

                # 인수자별 금액 추출
                extracted = extract_subscribers_from_xml(xml_content)

                # 각 인수자 업데이트
                for sub in subscribers:
                    sub_name = sub['name']
                    sub_id = sub['id']

                    # 이름으로 금액 찾기
                    amount = extracted.get(sub_name)

                    if not amount:
                        # 부분 일치 시도
                        for ext_name, ext_amt in extracted.items():
                            if sub_name in ext_name or ext_name in sub_name:
                                amount = ext_amt
                                break

                    if amount:
                        await conn.execute("""
                            UPDATE cb_subscribers
                            SET subscription_amount = $1, updated_at = NOW()
                            WHERE id = $2
                        """, float(amount), sub_id)
                        stats['updated'] += 1
                    else:
                        stats['not_found'] += 1

                # 진행 상황
                if (i + 1) % 50 == 0:
                    logger.info(f"진행: {i+1}/{len(disclosure_map)} - 업데이트: {stats['updated']}")

                # API 호출 간격
                await asyncio.sleep(0.5)

        # 4. 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("수정 완료")
        logger.info("=" * 80)
        logger.info(f"업데이트: {stats['updated']}건")
        logger.info(f"금액 못 찾음: {stats['not_found']}건")
        logger.info(f"다운로드 실패: {stats['download_failed']}건")

        # 최종 현황
        zero_count = await conn.fetchval("""
            SELECT COUNT(*) FROM cb_subscribers
            WHERE subscription_amount IS NULL OR subscription_amount = 0
        """)
        total_count = await conn.fetchval("SELECT COUNT(*) FROM cb_subscribers")
        logger.info(f"\n현재 인수금액 NULL/0원: {zero_count}건 / 전체 {total_count}건 ({zero_count*100/total_count:.1f}%)")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
