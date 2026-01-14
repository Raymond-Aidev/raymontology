#!/usr/bin/env python3
"""
426개 대상 기업 임원 정보 파싱 (빠른 버전)

미리 생성된 corp_dir_map.json을 사용하여 폴더 검색 시간 최소화
"""
import asyncio
import asyncpg
import logging
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_officers_from_local import OfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # stdout으로 출력
)
logger = logging.getLogger(__name__)

# 버퍼링 비활성화
sys.stdout.reconfigure(line_buffering=True)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


async def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="426개 대상 기업 임원 파싱 (빠른 버전)")
    arg_parser.add_argument("--corp-list", required=True, help="대상 기업 목록 파일")
    arg_parser.add_argument("--corp-map", default="scripts/corp_dir_map.json", help="기업 폴더 맵 JSON")
    arg_parser.add_argument("--years", default="2022,2023,2024", help="파싱할 연도")
    arg_parser.add_argument("--limit", type=int, help="처리할 기업 수 제한")

    args = arg_parser.parse_args()
    years = set(args.years.split(','))

    # 폴더 맵 로드
    with open(args.corp_map, 'r') as f:
        corp_map = json.load(f)
    logger.info(f"폴더 맵 로드: {len(corp_map)}개 기업")

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
        skipped_no_folder = 0
        total_files = 0

        for i, (corp_code, corp_name) in enumerate(target_corps):
            if args.limit and processed >= args.limit:
                break

            # 폴더 맵에서 직접 조회
            corp_dirs = corp_map.get(corp_code, [])
            if not corp_dirs:
                skipped_no_folder += 1
                continue

            corp_processed = False
            for corp_dir_str in corp_dirs:
                corp_dir = Path(corp_dir_str)

                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir():
                        continue
                    if year_dir.name not in years:
                        continue

                    for zip_file in year_dir.glob("*.zip"):
                        await parser.process_zip_file(conn, zip_file, corp_code, year_dir.name)
                        corp_processed = True
                        total_files += 1

            if corp_processed:
                processed += 1

                if processed % 10 == 0 or processed == 1:
                    logger.info(
                        f"진행: {processed}/{len(target_corps)} 기업 ({total_files} 파일) - "
                        f"임원: {parser.stats['officers_inserted']}, "
                        f"포지션: {parser.stats['positions_inserted']}"
                    )
            else:
                # 폴더는 있지만 연도 데이터가 없는 경우
                if (i + 1) % 20 == 0:
                    logger.info(f"스캔 중: {i+1}/{len(target_corps)} ({corp_name})")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("임원 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {processed}개")
        logger.info(f"스킵된 기업 (폴더 없음): {skipped_no_folder}개")
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
