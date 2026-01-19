#!/usr/bin/env python3
"""
426개 대상 기업 임원 정보 파싱 (최적화 버전)

기존 parse_officers_from_local.py의 OfficerParser를 재사용하되,
대상 기업 폴더만 직접 찾아서 처리합니다.
"""
import asyncio
import asyncpg
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_officers_from_local import OfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = Path("/Users/jaejoonpark/raymontology/backend/data/dart")


def find_corp_dirs(corp_code: str) -> list:
    """corp_code에 해당하는 모든 폴더 찾기 (여러 batch에 있을 수 있음)"""
    dirs = []
    for batch_dir in DART_DATA_DIR.glob("batch_*"):
        corp_dir = batch_dir / corp_code
        if corp_dir.exists() and corp_dir.is_dir():
            dirs.append(corp_dir)
    return dirs


async def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="426개 대상 기업 임원 파싱")
    arg_parser.add_argument("--corp-list", required=True, help="대상 기업 목록 파일")
    arg_parser.add_argument("--years", default="2022,2023,2024", help="파싱할 연도")
    arg_parser.add_argument("--limit", type=int, help="처리할 기업 수 제한")

    args = arg_parser.parse_args()
    years = args.years.split(',')

    # 대상 기업 로드
    target_corps = []
    with open(args.corp_list, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if parts:
                target_corps.append((parts[0], parts[1] if len(parts) > 1 else ''))

    logger.info(f"대상 기업: {len(target_corps)}개")
    logger.info(f"대상 연도: {years}")

    # 파서 초기화
    parser = OfficerParser()
    conn = await asyncpg.connect(DB_URL)

    try:
        await parser.load_companies(conn)

        processed = 0
        skipped = 0

        for i, (corp_code, corp_name) in enumerate(target_corps):
            if args.limit and processed >= args.limit:
                break

            # 해당 기업 폴더 찾기
            corp_dirs = find_corp_dirs(corp_code)
            if not corp_dirs:
                skipped += 1
                continue

            corp_processed = False
            for corp_dir in corp_dirs:
                for year in years:
                    year_dir = corp_dir / year
                    if not year_dir.exists():
                        continue

                    for zip_file in year_dir.glob("*.zip"):
                        await parser.process_zip_file(conn, zip_file, corp_code, year)
                        corp_processed = True

            if corp_processed:
                processed += 1

                if processed % 50 == 0:
                    logger.info(
                        f"진행: {processed}/{len(target_corps)} 기업 - "
                        f"임원: {parser.stats['officers_inserted']}, "
                        f"포지션: {parser.stats['positions_inserted']}"
                    )

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("임원 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {processed}개")
        logger.info(f"스킵된 기업 (폴더 없음): {skipped}개")
        logger.info(f"처리된 파일: {parser.stats['files_processed']}개")
        logger.info(f"발견된 임원: {parser.stats['officers_found']}명")
        logger.info(f"생성된 임원: {parser.stats['officers_inserted']}명")
        logger.info(f"생성된 포지션: {parser.stats['positions_inserted']}개")

        # 현재 상태 확인
        officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
        positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
