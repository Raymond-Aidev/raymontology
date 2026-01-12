#!/usr/bin/env python3
"""
포지션 데이터 빠른 적재 (배치 방식)
"""
import asyncio
import asyncpg
import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime, date
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(line_buffering=True)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
PARSED_DATA_FILE = Path(__file__).parent / 'parsed_officers_426.json'


async def main():
    conn = await asyncpg.connect(DB_URL, timeout=60, command_timeout=600)

    try:
        # 회사 정보 로드
        rows = await conn.fetch("SELECT id, corp_code, market FROM companies WHERE corp_code IS NOT NULL")
        company_cache = {r['corp_code']: str(r['id']) for r in rows}
        company_market = {r['corp_code']: r['market'] for r in rows}
        logger.info(f"회사 캐시 로드: {len(company_cache)}개")

        # 기존 임원 로드
        logger.info("임원 캐시 로드 시작...")
        officer_cache = {}
        officer_rows = await conn.fetch("SELECT id, name, birth_date FROM officers")
        for r in officer_rows:
            key = f"{r['name']}_{r['birth_date'] or ''}"
            officer_cache[key] = str(r['id'])
        logger.info(f"임원 캐시 로드: {len(officer_cache)}개")

        # 기존 포지션 로드 (중복 방지)
        logger.info("기존 포지션 로드 시작...")
        existing_positions = set()
        pos_rows = await conn.fetch(
            "SELECT officer_id, company_id, term_start_date FROM officer_positions"
        )
        for r in pos_rows:
            key = f"{r['officer_id']}_{r['company_id']}_{r['term_start_date'] or ''}"
            existing_positions.add(key)
        logger.info(f"기존 포지션 로드: {len(existing_positions)}개")

        # 파싱 데이터 로드
        with open(PARSED_DATA_FILE, 'r') as f:
            parsed_data = json.load(f)
        logger.info(f"파싱 데이터 로드: {len(parsed_data)} 기업")

        # 포지션 수집
        positions_to_insert = []
        skipped = 0

        for corp_code, corp_data in parsed_data.items():
            company_id = company_cache.get(corp_code)
            if not company_id:
                continue

            is_listed = company_market.get(corp_code) in ('KOSPI', 'KOSDAQ', 'KONEX')

            for officer_data in corp_data['officers']:
                name = officer_data.get('name')
                birth_date = officer_data.get('birth_date')
                key = f"{name}_{birth_date or ''}"

                officer_id = officer_cache.get(key)
                if not officer_id:
                    skipped += 1
                    continue

                # 포지션 정보
                position = officer_data.get('position', '임원')
                term_start = None
                term_end = None

                if is_listed and officer_data.get('term_end_date'):
                    try:
                        term_end = datetime.strptime(officer_data['term_end_date'], '%Y%m%d').date()
                        term_start = date(term_end.year - 3, term_end.month, term_end.day)
                    except:
                        pass

                report_date = None
                if officer_data.get('base_date'):
                    try:
                        report_date = datetime.strptime(officer_data['base_date'], '%Y%m%d').date()
                    except:
                        pass

                # 중복 체크
                pos_key = f"{officer_id}_{company_id}_{term_start or ''}"
                if pos_key in existing_positions:
                    skipped += 1
                    continue

                existing_positions.add(pos_key)
                positions_to_insert.append((
                    str(uuid.uuid4()),
                    officer_id,
                    company_id,
                    position,
                    term_start,
                    term_end,
                    True,  # is_current
                    officer_data.get('rcept_no'),
                    report_date,
                    datetime.now()
                ))

        logger.info(f"새 포지션: {len(positions_to_insert)}개, 스킵: {skipped}개")

        # 배치 삽입 (executemany 대신 copy_records_to_table 사용 시도)
        if positions_to_insert:
            logger.info(f"포지션 {len(positions_to_insert)}개 삽입 시작...")

            batch_size = 1000
            total_batches = (len(positions_to_insert) + batch_size - 1) // batch_size
            inserted = 0

            for i in range(total_batches):
                start = i * batch_size
                end = min(start + batch_size, len(positions_to_insert))
                batch = positions_to_insert[start:end]

                try:
                    await conn.executemany("""
                        INSERT INTO officer_positions
                        (id, officer_id, company_id, position, term_start_date, term_end_date,
                         is_current, source_disclosure_id, source_report_date, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """, batch)
                    inserted += len(batch)
                except Exception as e:
                    logger.warning(f"배치 {i+1} 실패: {e}, 개별 삽입 시도...")
                    for pos in batch:
                        try:
                            await conn.execute("""
                                INSERT INTO officer_positions
                                (id, officer_id, company_id, position, term_start_date, term_end_date,
                                 is_current, source_disclosure_id, source_report_date, created_at)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                            """, *pos)
                            inserted += 1
                        except:
                            pass

                if (i + 1) % 10 == 0 or (i + 1) == total_batches:
                    logger.info(f"진행: {i+1}/{total_batches} 배치 ({inserted}/{len(positions_to_insert)} 삽입)")

            logger.info(f"삽입 완료: {inserted}개")

        # 최종 통계
        officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
        positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
