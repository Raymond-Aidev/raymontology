#!/usr/bin/env python3
"""
426개 대상 기업 임원 정보 파싱 (v3 - 배치 INSERT)

로컬에서 파싱된 JSON 데이터를 COPY 방식으로 빠르게 DB에 적재
"""
import asyncio
import asyncpg
import logging
import os
import sys
import json
import io
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


async def get_connection():
    """연결 생성 (재시도 포함)"""
    for attempt in range(3):
        try:
            conn = await asyncpg.connect(DB_URL, timeout=60, command_timeout=300)
            return conn
        except Exception as e:
            logger.warning(f"연결 시도 {attempt + 1}/3 실패: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2)


async def load_with_copy(parsed_data: dict):
    """배치 방식으로 DB 적재"""
    conn = await get_connection()

    try:
        # 회사 정보 로드 (작은 쿼리)
        rows = await conn.fetch("SELECT id, corp_code, market FROM companies WHERE corp_code IS NOT NULL")
        company_cache = {r['corp_code']: str(r['id']) for r in rows}
        company_market = {r['corp_code']: r['market'] for r in rows}
        logger.info(f"회사 캐시 로드: {len(company_cache)}개")

        # 기존 임원 로드 - 배치로 로드
        logger.info("임원 캐시 로드 시작 (배치)...")
        officer_cache = {}
        offset = 0
        batch_size = 10000
        while True:
            officer_rows = await conn.fetch(
                "SELECT id, name, birth_date FROM officers ORDER BY id LIMIT $1 OFFSET $2",
                batch_size, offset
            )
            if not officer_rows:
                break
            for r in officer_rows:
                key = f"{r['name']}_{r['birth_date'] or ''}"
                officer_cache[key] = str(r['id'])
            offset += batch_size
            logger.info(f"  임원 로드: {len(officer_cache)}명...")
        logger.info(f"임원 캐시 로드: {len(officer_cache)}개")

        # 새로운 임원 수집
        new_officers = []  # (id, name, birth_date, gender)
        positions_to_insert = []  # (id, officer_id, company_id, position, ...)

        stats = {'new_officers': 0, 'new_positions': 0, 'companies': 0}

        for corp_code, corp_data in parsed_data.items():
            company_id = company_cache.get(corp_code)
            if not company_id:
                continue

            is_listed = company_market.get(corp_code) in ('KOSPI', 'KOSDAQ', 'KONEX')

            for officer_data in corp_data['officers']:
                name = officer_data.get('name')
                birth_date = officer_data.get('birth_date')
                key = f"{name}_{birth_date or ''}"

                # 임원 ID 확인 또는 생성
                if key in officer_cache:
                    officer_id = officer_cache[key]
                else:
                    officer_id = str(uuid.uuid4())
                    officer_cache[key] = officer_id
                    new_officers.append((
                        officer_id,
                        name,
                        birth_date,
                        officer_data.get('gender'),
                        datetime.now()
                    ))
                    stats['new_officers'] += 1

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
                stats['new_positions'] += 1

            stats['companies'] += 1

            if stats['companies'] % 100 == 0:
                logger.info(f"데이터 준비: {stats['companies']}/{len(parsed_data)} 기업")

        logger.info(f"데이터 준비 완료: 새 임원 {stats['new_officers']}명, 새 포지션 {stats['new_positions']}개")

        # 새 임원 배치 삽입 (중복 캐시에서 이미 제외됨)
        if new_officers:
            logger.info(f"임원 {len(new_officers)}명 배치 삽입 시작...")
            batch_size = 500
            total_batches = (len(new_officers) + batch_size - 1) // batch_size

            for i in range(total_batches):
                start = i * batch_size
                end = min(start + batch_size, len(new_officers))
                batch = new_officers[start:end]

                try:
                    await conn.executemany("""
                        INSERT INTO officers (id, name, birth_date, gender, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                    """, batch)
                except Exception as e:
                    # 개별 삽입으로 폴백
                    for officer in batch:
                        try:
                            await conn.execute("""
                                INSERT INTO officers (id, name, birth_date, gender, created_at)
                                VALUES ($1, $2, $3, $4, $5)
                            """, *officer)
                        except:
                            pass  # 중복 무시

                if (i + 1) % 5 == 0:
                    logger.info(f"임원 배치 삽입: {i+1}/{total_batches} ({end}/{len(new_officers)})")

            logger.info("임원 배치 삽입 완료")

        # 포지션 배치 삽입
        if positions_to_insert:
            logger.info(f"포지션 {len(positions_to_insert)}개 배치 삽입 시작...")
            batch_size = 500
            total_batches = (len(positions_to_insert) + batch_size - 1) // batch_size
            inserted = 0
            skipped = 0

            for i in range(total_batches):
                start = i * batch_size
                end = min(start + batch_size, len(positions_to_insert))
                batch = positions_to_insert[start:end]

                for pos in batch:
                    try:
                        await conn.execute("""
                            INSERT INTO officer_positions
                            (id, officer_id, company_id, position, term_start_date, term_end_date,
                             is_current, source_disclosure_id, report_date, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                            ON CONFLICT (officer_id, company_id, term_start_date)
                            DO UPDATE SET
                                position = EXCLUDED.position,
                                term_end_date = EXCLUDED.term_end_date,
                                is_current = EXCLUDED.is_current
                        """, *pos)
                        inserted += 1
                    except Exception as e:
                        skipped += 1

                if (i + 1) % 10 == 0:
                    logger.info(f"포지션 배치 삽입: {i+1}/{total_batches} ({end}/{len(positions_to_insert)}) - 성공: {inserted}, 스킵: {skipped}")

            logger.info(f"포지션 배치 삽입 완료 - 성공: {inserted}, 스킵: {skipped}")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("DB 적재 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {stats['companies']}개")
        logger.info(f"삽입된 임원: {stats['new_officers']}명")
        logger.info(f"삽입된 포지션: {stats['new_positions']}개")

        officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
        positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

    finally:
        await conn.close()


async def main():
    if not PARSED_DATA_FILE.exists():
        logger.error(f"파싱 파일 없음: {PARSED_DATA_FILE}")
        logger.info("먼저 parse_426_officers_v2.py --parse-only 실행 필요")
        return

    with open(PARSED_DATA_FILE, 'r') as f:
        parsed_data = json.load(f)

    logger.info(f"파싱 데이터 로드: {len(parsed_data)} 기업")

    await load_with_copy(parsed_data)


if __name__ == "__main__":
    asyncio.run(main())
