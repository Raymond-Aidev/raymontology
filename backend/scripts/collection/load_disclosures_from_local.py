#!/usr/bin/env python3
"""
로컬 DART ZIP 메타데이터에서 disclosures 테이블 적재

소스: backend/data/dart/batch_XXX/{corp_code}/{year}/*_meta.json
"""
import asyncio
import asyncpg
import json
import logging
import os
from pathlib import Path
from datetime import datetime
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')


async def load_disclosures():
    """로컬 메타데이터 파일에서 disclosures 적재"""

    conn = await asyncpg.connect(DB_URL)

    try:
        # 시작 전 카운트
        before_count = await conn.fetchval("SELECT COUNT(*) FROM disclosures")
        logger.info(f"작업 전 disclosures: {before_count:,}건")

        # companies 테이블의 corp_code 목록 가져오기 (FK 제약)
        corp_codes = await conn.fetch("SELECT corp_code FROM companies WHERE corp_code IS NOT NULL")
        valid_corp_codes = {row['corp_code'] for row in corp_codes}
        logger.info(f"유효한 corp_code: {len(valid_corp_codes):,}개")

        # 기존 rcept_no 목록 가져오기 (중복 방지)
        existing = await conn.fetch("SELECT rcept_no FROM disclosures")
        existing_rcept_nos = {row['rcept_no'] for row in existing}
        logger.info(f"기존 disclosures: {len(existing_rcept_nos):,}건")

        stats = {
            'scanned': 0,
            'inserted': 0,
            'skipped_no_company': 0,
            'skipped_duplicate': 0,
            'errors': 0
        }

        # 배치 폴더 순회
        batch_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith('batch_')])
        logger.info(f"배치 폴더: {len(batch_dirs)}개")

        batch_data = []

        for batch_dir in batch_dirs:
            batch_num = batch_dir.name

            # meta.json 파일들 찾기
            meta_files = list(batch_dir.rglob('*_meta.json'))

            for meta_file in meta_files:
                stats['scanned'] += 1

                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    rcept_no = meta.get('rcept_no')
                    corp_code = meta.get('corp_code')

                    # 중복 체크
                    if rcept_no in existing_rcept_nos:
                        stats['skipped_duplicate'] += 1
                        continue

                    # FK 체크
                    if corp_code not in valid_corp_codes:
                        stats['skipped_no_company'] += 1
                        continue

                    # 배치 데이터에 추가
                    batch_data.append((
                        str(uuid.uuid4()),      # id
                        rcept_no,               # rcept_no
                        corp_code,              # corp_code
                        meta.get('corp_name'),  # corp_name
                        meta.get('stock_code') if meta.get('stock_code') and meta.get('stock_code').strip() else None,  # stock_code
                        meta.get('report_nm'),  # report_nm
                        meta.get('rcept_dt'),   # rcept_dt
                        meta.get('flr_nm'),     # flr_nm
                        meta.get('rm'),         # rm
                        datetime.now()          # crawled_at
                    ))

                    existing_rcept_nos.add(rcept_no)  # 중복 방지

                    # 1000건마다 배치 삽입
                    if len(batch_data) >= 1000:
                        await insert_batch(conn, batch_data)
                        stats['inserted'] += len(batch_data)
                        logger.info(f"  {stats['inserted']:,}건 삽입 완료 (스캔: {stats['scanned']:,})")
                        batch_data = []

                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 5:
                        logger.error(f"파일 처리 오류 {meta_file}: {e}")

            logger.info(f"배치 {batch_num} 완료 - 스캔: {stats['scanned']:,}")

        # 남은 데이터 삽입
        if batch_data:
            await insert_batch(conn, batch_data)
            stats['inserted'] += len(batch_data)

        # 최종 결과
        after_count = await conn.fetchval("SELECT COUNT(*) FROM disclosures")

        logger.info("\n" + "=" * 60)
        logger.info("disclosures 적재 완료")
        logger.info("=" * 60)
        logger.info(f"스캔된 파일: {stats['scanned']:,}개")
        logger.info(f"삽입: {stats['inserted']:,}건")
        logger.info(f"스킵 (회사 없음): {stats['skipped_no_company']:,}건")
        logger.info(f"스킵 (중복): {stats['skipped_duplicate']:,}건")
        logger.info(f"오류: {stats['errors']:,}건")
        logger.info("-" * 60)
        logger.info(f"disclosures: {before_count:,}건 → {after_count:,}건 (+{after_count - before_count:,}건)")
        logger.info("=" * 60)

    finally:
        await conn.close()


async def insert_batch(conn, batch_data):
    """배치 삽입"""
    await conn.executemany("""
        INSERT INTO disclosures (
            id, rcept_no, corp_code, corp_name, stock_code,
            report_nm, rcept_dt, flr_nm, rm, crawled_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (rcept_no) DO NOTHING
    """, batch_data)


if __name__ == "__main__":
    asyncio.run(load_disclosures())
