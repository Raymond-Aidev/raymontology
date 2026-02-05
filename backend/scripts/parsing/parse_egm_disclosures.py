#!/usr/bin/env python3
"""
EGM 공시 파싱 스크립트

다운로드된 ZIP 파일에서 경영분쟁 여부와 임원 정보를 추출합니다.

사용법:
    python -m scripts.parsing.parse_egm_disclosures --limit 100
    python -m scripts.parsing.parse_egm_disclosures --year 2025

환경 변수:
    DATABASE_URL: PostgreSQL 연결 문자열
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'egm'


async def main():
    parser = argparse.ArgumentParser(description='EGM 공시 파싱')
    parser.add_argument('--limit', type=int, help='최대 파싱 개수')
    parser.add_argument('--year', type=int, help='특정 연도만')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 테스트')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 필요합니다")

    # EGM 파서 import
    from scripts.parsers.egm_officer import EGMOfficerParser

    pool = await asyncpg.create_pool(database_url)
    egm_parser = EGMOfficerParser()

    stats = {
        'total': 0,
        'parsed': 0,
        'disputes': 0,
        'officers_found': 0,
        'skipped': 0,
        'failed': 0,
    }

    try:
        async with pool.acquire() as conn:
            # 파싱 대상 조회 (PENDING 상태)
            query = """
                SELECT
                    disclosure_id,
                    company_id,
                    corp_code,
                    corp_name,
                    disclosure_date,
                    egm_type
                FROM egm_disclosures
                WHERE parse_status = 'PENDING'
            """

            if args.year:
                query += f" AND EXTRACT(YEAR FROM disclosure_date) = {args.year}"

            query += " ORDER BY disclosure_date DESC"

            if args.limit:
                query += f" LIMIT {args.limit}"

            rows = await conn.fetch(query)

            stats['total'] = len(rows)
            logger.info(f"파싱 대상: {len(rows)}건")

            if args.dry_run:
                logger.info("Dry run 모드 - 파싱 건너뜀")
                for row in rows[:10]:
                    year = row['disclosure_date'].year if row['disclosure_date'] else 'N/A'
                    logger.info(f"  - [{year}] {row['corp_name']}: {row['disclosure_id']}")
                return

            # 파싱 실행
            for i, row in enumerate(rows):
                if (i + 1) % 50 == 0:
                    logger.info(f"진행: {i+1}/{len(rows)} ({(i+1)/len(rows)*100:.1f}%)")

                disclosure_id = row['disclosure_id']
                year = str(row['disclosure_date'].year) if row['disclosure_date'] else '2024'
                zip_path = DATA_DIR / year / f"{disclosure_id}.zip"

                # ZIP 파일 확인
                if not zip_path.exists():
                    logger.warning(f"ZIP 없음: {disclosure_id}")
                    stats['skipped'] += 1
                    continue

                # 메타 정보 구성
                meta = {
                    'disclosure_id': disclosure_id,
                    'company_id': str(row['company_id']) if row['company_id'] else None,
                    'corp_code': row['corp_code'],
                    'corp_name': row['corp_name'],
                }

                try:
                    # 파싱 실행
                    result = await egm_parser.parse(zip_path, meta)

                    if result.get('success'):
                        # DB 저장
                        saved = await egm_parser.save_to_db(conn, result)
                        if saved:
                            stats['parsed'] += 1
                            if result.get('is_dispute'):
                                stats['disputes'] += 1
                                logger.info(f"분쟁 발견: {row['corp_name']} ({disclosure_id})")
                            stats['officers_found'] += result.get('officers_appointed', 0)
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                        # 파싱 실패 상태 업데이트
                        await conn.execute("""
                            UPDATE egm_disclosures
                            SET parse_status = 'FAILED',
                                parse_errors = $2,
                                updated_at = NOW()
                            WHERE disclosure_id = $1
                        """, disclosure_id, str(result.get('parse_errors', [])))

                except Exception as e:
                    logger.error(f"파싱 오류 {disclosure_id}: {e}")
                    stats['failed'] += 1

        # 결과 출력
        logger.info(f"\n=== 파싱 완료 ===")
        logger.info(f"총 대상: {stats['total']}")
        logger.info(f"파싱 완료: {stats['parsed']}")
        logger.info(f"분쟁 관련: {stats['disputes']}")
        logger.info(f"임원 추출: {stats['officers_found']}명")
        logger.info(f"스킵 (ZIP 없음): {stats['skipped']}")
        logger.info(f"실패: {stats['failed']}")

        # 파서 통계 출력
        parser_stats = egm_parser.get_stats()
        logger.info(f"\n파서 통계:")
        logger.info(f"  - 파일 처리: {parser_stats.get('files_processed', 0)}")
        logger.info(f"  - 레코드 생성: {parser_stats.get('records_created', 0)}")
        logger.info(f"  - 오류: {parser_stats.get('errors', 0)}")

    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
