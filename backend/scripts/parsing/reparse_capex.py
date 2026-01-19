#!/usr/bin/env python3
"""
CAPEX 재파싱 스크립트 (v3.1)

CAPEX가 NULL인 레코드를 대상으로 개선된 파서로 재파싱하여 업데이트.
개별 유형자산 취득(토지, 건물, 기계장치 등)을 합산하는 로직 적용.

사용법:
    # 테스트 (dry-run)
    DATABASE_URL="..." python scripts/reparse_capex.py --sample 10 --dry-run

    # 전체 실행
    DATABASE_URL="..." python scripts/reparse_capex.py

    # 특정 연도만
    DATABASE_URL="..." python scripts/reparse_capex.py --year 2024
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.parsers.financial import FinancialParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def find_capex_null_companies(conn: asyncpg.Connection, year: Optional[int] = None) -> List[Dict]:
    """CAPEX가 NULL인 레코드 조회"""
    query = """
        SELECT
            fd.id, fd.company_id, fd.fiscal_year,
            c.corp_code, c.name as company_name,
            fd.source_rcept_no
        FROM financial_details fd
        JOIN companies c ON c.id = fd.company_id
        WHERE fd.capex IS NULL
          AND fd.operating_cash_flow IS NOT NULL
    """
    if year:
        query += f" AND fd.fiscal_year = {year}"
    query += " ORDER BY fd.fiscal_year DESC, c.name"

    rows = await conn.fetch(query)
    return [dict(r) for r in rows]


async def find_zip_file(corp_code: str, rcept_no: str, base_dir: Path) -> Optional[Path]:
    """접수번호로 ZIP 파일 찾기"""
    # batch 디렉토리들에서 검색
    for batch_dir in sorted(base_dir.glob('batch_*')):
        corp_dir = batch_dir / corp_code
        if not corp_dir.exists():
            continue

        for year_dir in corp_dir.iterdir():
            if not year_dir.is_dir():
                continue

            zip_file = year_dir / f"{rcept_no}.zip"
            if zip_file.exists():
                return zip_file

    return None


async def reparse_capex(
    database_url: str,
    year: Optional[int] = None,
    sample: int = 0,
    dry_run: bool = False
):
    """CAPEX 재파싱 메인 함수"""

    pool = await asyncpg.create_pool(database_url)
    parser = FinancialParser(database_url, enable_xbrl=True)

    base_dir = Path(__file__).parent.parent / 'data' / 'dart'

    async with pool.acquire() as conn:
        # CAPEX NULL 레코드 조회
        null_records = await find_capex_null_companies(conn, year)
        logger.info(f"CAPEX NULL 레코드: {len(null_records)}건")

        if sample > 0:
            null_records = null_records[:sample]
            logger.info(f"샘플 모드: {sample}건만 처리")

        # 통계
        stats = {
            'total': len(null_records),
            'updated': 0,
            'not_found': 0,
            'parse_failed': 0,
            'no_capex': 0
        }

        for i, record in enumerate(null_records, 1):
            corp_code = record['corp_code']
            rcept_no = record['source_rcept_no']
            company_name = record['company_name']
            fiscal_year = record['fiscal_year']

            if not rcept_no:
                logger.debug(f"[{i}/{stats['total']}] {company_name}: rcept_no 없음")
                stats['not_found'] += 1
                continue

            # ZIP 파일 찾기
            zip_file = await find_zip_file(corp_code, rcept_no, base_dir)
            if not zip_file:
                logger.debug(f"[{i}/{stats['total']}] {company_name}: ZIP 파일 없음")
                stats['not_found'] += 1
                continue

            # 파싱
            meta = {
                'corp_code': corp_code,
                'rcept_no': rcept_no,
                'report_nm': f'사업보고서 ({fiscal_year}.12)'
            }

            try:
                result = await parser.parse(zip_file, meta)

                if not result.get('success'):
                    logger.debug(f"[{i}/{stats['total']}] {company_name}: 파싱 실패")
                    stats['parse_failed'] += 1
                    continue

                capex = result['data'].get('capex')
                if capex is None:
                    logger.debug(f"[{i}/{stats['total']}] {company_name}: CAPEX 추출 실패")
                    stats['no_capex'] += 1
                    continue

                # DB 업데이트
                if not dry_run:
                    await conn.execute(
                        "UPDATE financial_details SET capex = $1, updated_at = NOW() WHERE id = $2",
                        capex, record['id']
                    )

                logger.info(f"[{i}/{stats['total']}] {company_name} ({fiscal_year}): CAPEX = {capex:,}원")
                stats['updated'] += 1

            except Exception as e:
                logger.error(f"[{i}/{stats['total']}] {company_name}: 에러 - {e}")
                stats['parse_failed'] += 1

        # 결과 출력
        print("\n" + "="*60)
        print("CAPEX 재파싱 결과")
        print("="*60)
        print(f"총 대상:     {stats['total']}건")
        print(f"업데이트:    {stats['updated']}건")
        print(f"파일 없음:   {stats['not_found']}건")
        print(f"파싱 실패:   {stats['parse_failed']}건")
        print(f"CAPEX 없음:  {stats['no_capex']}건")
        if dry_run:
            print("\n[DRY-RUN] 실제 DB 업데이트 없음")
        print("="*60)

    await pool.close()


def main():
    parser = argparse.ArgumentParser(description='CAPEX 재파싱 스크립트')
    parser.add_argument('--year', type=int, help='특정 연도만 처리')
    parser.add_argument('--sample', type=int, default=0, help='샘플 수 (0=전체)')
    parser.add_argument('--dry-run', action='store_true', help='테스트 모드 (DB 업데이트 안함)')
    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경 변수 필요")
        sys.exit(1)

    asyncio.run(reparse_capex(
        database_url=database_url,
        year=args.year,
        sample=args.sample,
        dry_run=args.dry_run
    ))


if __name__ == '__main__':
    main()
