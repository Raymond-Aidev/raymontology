#!/usr/bin/env python3
"""
회차 정보가 없는 CB bond_name 수정 스크립트

원본 공시에서 SEQ_NO, PL_KND를 다시 파싱하여 bond_name 업데이트
"""
import asyncio
import aiohttp
import asyncpg
import logging
import re
import zipfile
import io
import os
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = "postgresql://postgres:dev_password@localhost:5432/raymontology_dev"


def extract_acode(content: str, acode: str) -> Optional[str]:
    """ACODE 속성으로 값 추출 (중첩 태그 처리)"""
    # 1차 시도: 중첩 태그 없는 단순 패턴
    pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
    match = re.search(pattern, content)
    if match and match.group(1).strip():
        return match.group(1).strip()

    # 2차 시도: 중첩 태그(SPAN 등) 포함 패턴
    pattern2 = rf'<TE[^>]*ACODE="{acode}"[^>]*>(.*?)</TE>'
    match2 = re.search(pattern2, content, re.DOTALL)
    if match2:
        text = re.sub(r'<[^>]+>', '', match2.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            return text

    return None


def parse_bond_name(content: str) -> Optional[str]:
    """공시 내용에서 bond_name 추출"""
    seq_no = extract_acode(content, 'SEQ_NO')
    pl_knd = extract_acode(content, 'PL_KND')

    # DEB_KND (사채의 명칭)에서 직접 추출 시도
    deb_knd = extract_acode(content, 'DEB_KND')

    # 1. DEB_KND에서 회차 정보 있으면 사용
    if deb_knd:
        match = re.search(r'제(\d+)회', deb_knd)
        if match:
            return deb_knd[:200]

    # 2. SEQ_NO + PL_KND 조합
    if seq_no and seq_no != '-':
        if pl_knd and pl_knd != '-':
            return f"제{seq_no}회 {pl_knd}"[:200]
        else:
            return f"제{seq_no}회 전환사채"

    # 3. XML 텍스트에서 회차 패턴 직접 검색
    patterns = [
        r'(제\d+회[^\s<]*전환사채)',
        r'(제\d+회[^\s<]*사채)',
        r'(\d+회차[^\s<]*전환사채)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)[:200]

    return None


async def download_disclosure(session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
    """공시 문서 다운로드"""
    try:
        params = {'crtfc_key': DART_API_KEY, 'rcept_no': rcept_no}
        async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
            if response.status != 200:
                return None
            raw_content = await response.read()

            # ZIP 또는 XML 디코딩
            encodings = ['euc-kr', 'utf-8', 'cp949']
            try:
                with zipfile.ZipFile(io.BytesIO(raw_content)) as zf:
                    xml_bytes = zf.read(zf.namelist()[0])
                    for enc in encodings:
                        try:
                            return xml_bytes.decode(enc)
                        except UnicodeDecodeError:
                            continue
            except zipfile.BadZipFile:
                for enc in encodings:
                    try:
                        return raw_content.decode(enc)
                    except UnicodeDecodeError:
                        continue
    except Exception as e:
        logger.error(f"다운로드 실패 {rcept_no}: {e}")
    return None


async def main():
    if not DART_API_KEY:
        logger.error("DART_API_KEY 환경변수가 설정되지 않았습니다")
        return

    logger.info("=" * 60)
    logger.info("CB bond_name 수정 시작 (회차 정보 추출)")
    logger.info("=" * 60)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 회차 정보 없는 CB 조회
        cbs = await conn.fetch("""
            SELECT cb.id, cb.bond_name, cb.source_disclosure_id, c.name as company_name
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            WHERE cb.bond_name NOT LIKE '%제%회%'
            ORDER BY c.name
        """)

        logger.info(f"수정 대상: {len(cbs)}건")

        updated = 0
        failed = 0

        async with aiohttp.ClientSession() as session:
            for i, cb in enumerate(cbs):
                rcept_no = cb['source_disclosure_id']
                if not rcept_no:
                    logger.warning(f"  [{cb['company_name']}] source_disclosure_id 없음")
                    failed += 1
                    continue

                # 공시 다운로드
                content = await download_disclosure(session, rcept_no)
                if not content:
                    logger.warning(f"  [{cb['company_name']}] 다운로드 실패: {rcept_no}")
                    failed += 1
                    continue

                # bond_name 파싱
                new_bond_name = parse_bond_name(content)
                if not new_bond_name:
                    logger.warning(f"  [{cb['company_name']}] 회차 추출 실패: {rcept_no}")
                    failed += 1
                    continue

                # 기존과 동일하면 스킵
                if new_bond_name == cb['bond_name']:
                    continue

                # 중복 체크: 같은 회사에 이미 같은 bond_name이 있는지 확인
                existing = await conn.fetchval("""
                    SELECT id FROM convertible_bonds
                    WHERE company_id = (SELECT company_id FROM convertible_bonds WHERE id = $1)
                    AND bond_name = $2
                    AND id != $1
                """, cb['id'], new_bond_name)

                if existing:
                    # 중복인 경우: 이 CB의 인수자 이전 후 삭제
                    logger.info(f"  [{cb['company_name']}] 중복 발견 - 삭제: '{cb['bond_name']}' (이미 '{new_bond_name}' 존재)")

                    # 인수자 이전 (중복 아닌 것만)
                    await conn.execute("""
                        UPDATE cb_subscribers SET cb_id = $1
                        WHERE cb_id = $2
                        AND subscriber_name NOT IN (
                            SELECT subscriber_name FROM cb_subscribers WHERE cb_id = $1
                        )
                    """, existing, cb['id'])

                    # 남은 중복 인수자 삭제
                    await conn.execute("DELETE FROM cb_subscribers WHERE cb_id = $1", cb['id'])

                    # CB 삭제
                    await conn.execute("DELETE FROM convertible_bonds WHERE id = $1", cb['id'])
                    updated += 1
                    continue

                # DB 업데이트
                await conn.execute("""
                    UPDATE convertible_bonds SET bond_name = $1, updated_at = NOW()
                    WHERE id = $2
                """, new_bond_name, cb['id'])

                logger.info(f"  [{cb['company_name']}] '{cb['bond_name']}' → '{new_bond_name}'")
                updated += 1

                # API 호출 간격
                await asyncio.sleep(0.5)

                if (i + 1) % 20 == 0:
                    logger.info(f"진행: {i + 1}/{len(cbs)} (업데이트: {updated}, 실패: {failed})")

        # 결과 확인
        logger.info("=" * 60)
        logger.info(f"완료: 업데이트 {updated}건, 실패 {failed}건")

        # 남은 문제 확인
        remaining = await conn.fetchval("""
            SELECT COUNT(*) FROM convertible_bonds
            WHERE bond_name NOT LIKE '%제%회%'
        """)
        logger.info(f"남은 회차 없는 CB: {remaining}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
