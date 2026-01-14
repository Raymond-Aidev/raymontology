#!/usr/bin/env python3
"""
426개 대상 기업 임원 정보 파싱 (배치 버전)

50개씩 나눠서 처리하고 중간 진행 상황 저장
"""
import asyncio
import asyncpg
import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from parse_officers_from_local import OfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(line_buffering=True)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
PROGRESS_FILE = Path(__file__).parent / 'parse_426_progress.json'


def load_progress() -> dict:
    """진행 상황 로드"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed_corps': [], 'stats': {}}


def save_progress(progress: dict):
    """진행 상황 저장"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


async def process_batch(conn, parser, corps_batch: list, corp_map: dict, years: set, progress: dict):
    """배치 처리"""
    batch_files = 0
    batch_positions = 0

    for corp_code, corp_name in corps_batch:
        if corp_code in progress['processed_corps']:
            continue

        corp_dirs = corp_map.get(corp_code, [])
        if not corp_dirs:
            progress['processed_corps'].append(corp_code)
            continue

        corp_processed = False
        for corp_dir_str in corp_dirs:
            corp_dir = Path(corp_dir_str)
            if not corp_dir.exists():
                continue

            for year_dir in corp_dir.iterdir():
                if not year_dir.is_dir() or year_dir.name not in years:
                    continue

                for zip_file in year_dir.glob("*.zip"):
                    try:
                        await parser.process_zip_file(conn, zip_file, corp_code, year_dir.name)
                        corp_processed = True
                        batch_files += 1
                    except Exception as e:
                        logger.warning(f"파일 처리 오류 {zip_file.name}: {e}")

        progress['processed_corps'].append(corp_code)

        if corp_processed:
            batch_positions += parser.stats['positions_inserted'] - progress['stats'].get('positions_inserted', 0)
            progress['stats'] = dict(parser.stats)

    return batch_files, batch_positions


async def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="426개 대상 기업 임원 파싱 (배치 버전)")
    arg_parser.add_argument("--corp-list", required=True, help="대상 기업 목록 파일")
    arg_parser.add_argument("--corp-map", default="scripts/corp_dir_map.json", help="기업 폴더 맵 JSON")
    arg_parser.add_argument("--years", default="2022,2023,2024", help="파싱할 연도")
    arg_parser.add_argument("--batch-size", type=int, default=50, help="배치 크기")
    arg_parser.add_argument("--reset", action='store_true', help="진행 상황 초기화")

    args = arg_parser.parse_args()
    years = set(args.years.split(','))

    # 진행 상황 로드
    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    progress = load_progress()

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

    already_processed = len(progress['processed_corps'])
    remaining = [c for c in target_corps if c[0] not in progress['processed_corps']]

    logger.info(f"대상 기업: {len(target_corps)}개")
    logger.info(f"이미 처리됨: {already_processed}개")
    logger.info(f"남은 기업: {len(remaining)}개")
    logger.info(f"대상 연도: {years}")

    if not remaining:
        logger.info("모든 기업이 이미 처리되었습니다.")
        return

    # 파서 초기화
    parser = OfficerParser()
    # 이전 통계 복원
    if progress['stats']:
        parser.stats = dict(progress['stats'])

    conn = await asyncpg.connect(DB_URL)

    try:
        await parser.load_companies(conn)

        # 배치 단위로 처리
        total_batches = (len(remaining) + args.batch_size - 1) // args.batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * args.batch_size
            end_idx = min(start_idx + args.batch_size, len(remaining))
            batch = remaining[start_idx:end_idx]

            logger.info(f"\n--- 배치 {batch_idx + 1}/{total_batches} ({len(batch)}개 기업) ---")

            batch_files, batch_positions = await process_batch(
                conn, parser, batch, corp_map, years, progress
            )

            # 진행 상황 저장
            save_progress(progress)

            logger.info(
                f"배치 완료: {len(progress['processed_corps'])}/{len(target_corps)} 기업 완료 - "
                f"이번 배치: {batch_files} 파일, 누적: {parser.stats['positions_inserted']} 포지션"
            )

            # DB 연결 확인 (간단한 쿼리로 연결 유지)
            await conn.fetchval("SELECT 1")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("임원 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {len(progress['processed_corps'])}개")
        logger.info(f"처리된 파일: {parser.stats['files_processed']}개")
        logger.info(f"발견된 임원: {parser.stats['officers_found']}명")
        logger.info(f"생성된 임원: {parser.stats['officers_inserted']}명")
        logger.info(f"생성된 포지션: {parser.stats['positions_inserted']}개")

        # 현재 상태 확인
        officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
        positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

        # 완료 후 진행 파일 삭제
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
            logger.info("진행 파일 삭제됨")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
