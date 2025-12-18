#!/usr/bin/env python3
"""
CB 공시 메타데이터 임포트
cb_disclosures_by_company_full.json → PostgreSQL disclosures 테이블
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def import_cb_disclosures():
    """CB 공시 메타데이터를 PostgreSQL에 임포트"""

    # JSON 파일 로드
    json_path = Path(__file__).parent.parent / 'data' / 'cb_disclosures_by_company_full.json'

    logger.info(f"Loading CB disclosure data from {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        disclosures_data = json.load(f)

    logger.info(f"Loaded {len(disclosures_data)} disclosure records")

    # PostgreSQL 연결 (Docker 컨테이너 또는 로컬)
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    logger.info(f"Connecting to database: {db_url.replace('dev_password', '***')}")
    conn = await asyncpg.connect(db_url)

    try:
        # 기존 데이터 확인
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM disclosures")
        logger.info(f"Existing disclosures in database: {existing_count}")

        # Batch insert
        inserted = 0
        skipped = 0
        errors = 0

        for disclosure in disclosures_data:
            try:
                # UUID 생성
                disclosure_id = str(uuid.uuid4())

                # rcept_no 중복 체크
                existing = await conn.fetchval(
                    "SELECT id FROM disclosures WHERE rcept_no = $1",
                    disclosure['rcept_no']
                )

                if existing:
                    skipped += 1
                    continue

                # Insert
                await conn.execute("""
                    INSERT INTO disclosures (
                        id, rcept_no, corp_code, corp_name, stock_code,
                        report_nm, rcept_dt, flr_nm, rm,
                        crawled_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10
                    )
                """,
                    disclosure_id,
                    disclosure['rcept_no'],
                    disclosure['corp_code'],
                    disclosure['corp_name'],
                    disclosure.get('stock_code'),
                    disclosure['report_nm'],
                    disclosure['rcept_dt'],
                    disclosure.get('flr_nm'),
                    disclosure.get('rm', ''),
                    datetime.now(),
                )

                inserted += 1

                if inserted % 100 == 0:
                    logger.info(f"Progress: {inserted} inserted, {skipped} skipped")

            except Exception as e:
                logger.error(f"Error inserting disclosure {disclosure.get('rcept_no')}: {e}")
                errors += 1

        # 결과 출력
        logger.info("=" * 80)
        logger.info("CB Disclosure Import Complete")
        logger.info("=" * 80)
        logger.info(f"Total records in JSON: {len(disclosures_data)}")
        logger.info(f"Inserted: {inserted}")
        logger.info(f"Skipped (duplicates): {skipped}")
        logger.info(f"Errors: {errors}")

        # 최종 카운트
        final_count = await conn.fetchval("SELECT COUNT(*) FROM disclosures")
        logger.info(f"Total disclosures in database: {final_count}")

        # 샘플 데이터 확인
        sample = await conn.fetch("""
            SELECT rcept_no, corp_name, report_nm, rcept_dt
            FROM disclosures
            ORDER BY rcept_dt DESC
            LIMIT 5
        """)

        logger.info("\nSample records:")
        for row in sample:
            logger.info(f"  {row['rcept_dt']} - {row['corp_name']} - {row['report_nm']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(import_cb_disclosures())
