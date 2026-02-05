#!/usr/bin/env python3
"""
EGM 공시 ZIP 파일 다운로드 스크립트

egm_disclosures 테이블에 있는 레코드에 대해
로컬에 ZIP 파일이 없으면 DART API에서 다운로드합니다.

사용법:
    python -m scripts.collection.download_egm_zips --limit 100

환경 변수:
    DATABASE_URL: PostgreSQL 연결 문자열
    DART_API_KEY: DART OpenAPI 키
"""

import argparse
import asyncio
import logging
import os
import zipfile
from pathlib import Path
from typing import Optional

import aiohttp
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '')
DART_API_BASE = 'https://opendart.fss.or.kr/api'
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'egm'
REQUESTS_PER_MINUTE = 900
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE


async def download_zip(
    session: aiohttp.ClientSession,
    api_key: str,
    rcept_no: str,
    output_dir: Path
) -> Optional[Path]:
    """DART API에서 공시 ZIP 다운로드"""
    zip_path = output_dir / f"{rcept_no}.zip"

    # 이미 존재하면 스킵
    if zip_path.exists():
        return zip_path

    url = f"{DART_API_BASE}/document.xml"
    params = {
        'crtfc_key': api_key,
        'rcept_no': rcept_no,
    }

    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.warning(f"다운로드 실패 ({resp.status}): {rcept_no}")
                return None

            content_type = resp.headers.get('Content-Type', '')

            # XML 에러 응답 체크
            if 'xml' in content_type or 'text' in content_type:
                text = await resp.text()
                if '<status>' in text:
                    # 에러 메시지 추출
                    if '<message>' in text:
                        import re
                        match = re.search(r'<message>([^<]+)</message>', text)
                        if match:
                            logger.warning(f"API 오류 ({rcept_no}): {match.group(1)}")
                    else:
                        logger.warning(f"API 오류 응답: {rcept_no}")
                    return None

            content = await resp.read()

            if len(content) < 100:
                logger.warning(f"파일이 너무 작음: {rcept_no}")
                return None

            output_dir.mkdir(parents=True, exist_ok=True)

            with open(zip_path, 'wb') as f:
                f.write(content)

            # ZIP 검증
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    xml_count = sum(1 for n in zf.namelist() if n.endswith('.xml'))
                    if xml_count == 0:
                        logger.warning(f"XML 파일 없음: {rcept_no}")
                        zip_path.unlink()
                        return None
            except zipfile.BadZipFile:
                logger.warning(f"잘못된 ZIP 파일: {rcept_no}")
                zip_path.unlink()
                return None

            return zip_path

    except Exception as e:
        logger.error(f"다운로드 오류 {rcept_no}: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description='EGM 공시 ZIP 다운로드')
    parser.add_argument('--limit', type=int, help='최대 다운로드 개수')
    parser.add_argument('--year', type=int, help='특정 연도만')
    parser.add_argument('--dry-run', action='store_true', help='실제 다운로드 없이 테스트')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    api_key = os.getenv('DART_API_KEY')

    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 필요합니다")
    if not api_key:
        raise ValueError("DART_API_KEY 환경 변수가 필요합니다")

    pool = await asyncpg.create_pool(database_url)

    try:
        async with pool.acquire() as conn:
            # egm_disclosures에서 다운로드 필요한 레코드 조회
            query = """
                SELECT
                    disclosure_id,
                    corp_code,
                    corp_name,
                    disclosure_date
                FROM egm_disclosures
                WHERE parse_status = 'PENDING'
            """

            if args.year:
                query += f" AND EXTRACT(YEAR FROM disclosure_date) = {args.year}"

            query += " ORDER BY disclosure_date DESC"

            if args.limit:
                query += f" LIMIT {args.limit}"

            rows = await conn.fetch(query)

            logger.info(f"다운로드 대상: {len(rows)}건")

            if args.dry_run:
                logger.info("Dry run 모드 - 다운로드 건너뜀")
                for row in rows[:10]:
                    year = row['disclosure_date'].year if row['disclosure_date'] else 'N/A'
                    logger.info(f"  - [{year}] {row['corp_name']}: {row['disclosure_id']}")
                return

        # 다운로드 실행
        stats = {
            'total': len(rows),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
        }

        async with aiohttp.ClientSession() as session:
            for i, row in enumerate(rows):
                if (i + 1) % 20 == 0:
                    logger.info(f"진행: {i+1}/{len(rows)} ({(i+1)/len(rows)*100:.1f}%)")

                disclosure_id = row['disclosure_id']
                year = str(row['disclosure_date'].year) if row['disclosure_date'] else '2024'
                output_dir = DATA_DIR / year

                zip_path = output_dir / f"{disclosure_id}.zip"

                # 이미 존재하면 스킵
                if zip_path.exists():
                    stats['skipped'] += 1
                    continue

                # 다운로드
                result = await download_zip(session, api_key, disclosure_id, output_dir)

                if result:
                    stats['downloaded'] += 1
                    logger.info(f"다운로드 완료: {disclosure_id} ({row['corp_name']})")
                else:
                    stats['failed'] += 1

                await asyncio.sleep(REQUEST_DELAY)

        # 결과 출력
        logger.info(f"\n=== 다운로드 완료 ===")
        logger.info(f"총 대상: {stats['total']}")
        logger.info(f"다운로드: {stats['downloaded']}")
        logger.info(f"스킵 (이미 존재): {stats['skipped']}")
        logger.info(f"실패: {stats['failed']}")

    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
