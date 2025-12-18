#!/usr/bin/env python3
"""
CB 인수자 인수금액 0원/NULL 문제 수정

기존 데이터에서 인수금액이 0이거나 NULL인 인수자들의 금액을
원본 공시 문서에서 다시 추출하여 업데이트
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import glob
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'


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


def normalize_name(name: str) -> str:
    """이름 정규화 - 모든 공백과 특수문자 제거하여 키로 사용"""
    if not name:
        return ""
    name = re.sub(r'&[^;]+;', '', name)  # &cr; 등 제거
    name = re.sub(r'\s+', '', name)  # 공백 제거
    return name.strip()


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

        # 이름 정리 (HTML 태그, &cr; 제거)
        name_raw = name_match.group(1)
        name = re.sub(r'<[^>]+>', '', name_raw)
        name = re.sub(r'&[^;]+;', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if not name or name == '-' or len(name) < 2:
            continue

        # 정규화된 키로 저장
        name_key = normalize_name(name)

        # 금액 추출
        amt_match = re.search(r'<TE[^>]*ACODE="ISSU_AMT"[^>]*>([^<]*)</TE>', tr_content, re.IGNORECASE)
        if amt_match:
            amount = _parse_amount(amt_match.group(1))
            if amount:
                subscribers[name_key] = amount

    return subscribers


def load_xml_from_zip(zip_path: str) -> str:
    """ZIP 파일에서 XML 내용 로드"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.xml'):
                    content = zf.read(name)
                    try:
                        return content.decode('utf-8')
                    except:
                        return content.decode('euc-kr', errors='ignore')
    except Exception as e:
        logger.debug(f"ZIP 로드 실패 {zip_path}: {e}")
    return None


async def main():
    logger.info("=" * 80)
    logger.info("CB 인수자 인수금액 수정 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 1. 인수금액이 NULL인 인수자 목록 조회
        rows = await conn.fetch("""
            SELECT
                cs.id,
                cs.subscriber_name,
                cs.source_disclosure_id,
                c.corp_code
            FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE cs.subscription_amount IS NULL OR cs.subscription_amount = 0
        """)

        logger.info(f"수정 대상 인수자: {len(rows)}건")

        if not rows:
            logger.info("수정할 인수자가 없습니다")
            return

        # 2. 공시별로 그룹화
        disclosure_map = {}  # rcept_no -> [(id, name, corp_code), ...]
        for row in rows:
            rcept_no = row['source_disclosure_id']
            if rcept_no:
                if rcept_no not in disclosure_map:
                    disclosure_map[rcept_no] = []
                disclosure_map[rcept_no].append({
                    'id': row['id'],
                    'name': row['subscriber_name'],
                    'corp_code': row['corp_code']
                })

        logger.info(f"관련 공시: {len(disclosure_map)}건")

        # 3. 각 공시별로 처리
        stats = {'updated': 0, 'not_found': 0, 'file_not_found': 0}

        for rcept_no, subscribers in disclosure_map.items():
            if not rcept_no:
                continue

            corp_code = subscribers[0]['corp_code']

            # ZIP 파일 찾기
            zip_pattern = f"{DART_DATA_DIR}/**/{corp_code}/*/{rcept_no}.zip"
            zip_files = glob.glob(zip_pattern, recursive=True)

            if not zip_files:
                stats['file_not_found'] += len(subscribers)
                continue

            zip_path = zip_files[0]
            xml_content = load_xml_from_zip(zip_path)
            if not xml_content:
                stats['file_not_found'] += len(subscribers)
                continue

            # XML에서 인수자별 금액 추출
            extracted = extract_subscribers_from_xml(xml_content)

            # 각 인수자 업데이트
            for sub in subscribers:
                sub_name = sub['name']
                sub_id = sub['id']

                # 정규화된 키로 금액 찾기
                sub_key = normalize_name(sub_name)
                amount = extracted.get(sub_key)

                if not amount:
                    # 부분 일치 시도 (이름이 잘린 경우)
                    for ext_key, ext_amt in extracted.items():
                        if sub_key in ext_key or ext_key in sub_key:
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

        # 4. 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("수정 완료")
        logger.info("=" * 80)
        logger.info(f"업데이트: {stats['updated']}건")
        logger.info(f"금액 못 찾음: {stats['not_found']}건")
        logger.info(f"파일 없음: {stats['file_not_found']}건")

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
