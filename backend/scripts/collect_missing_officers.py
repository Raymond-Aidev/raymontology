#!/usr/bin/env python3
"""
결손 기업 임원 데이터 수집 스크립트

임원 데이터가 없는 기업(67개)의 공시를 분석하여 임원 정보 수집.
SPAC, 리츠, 증권사 등 특수 형태 기업도 처리.

사용법:
    # 분석 (dry-run)
    DATABASE_URL="..." python scripts/collect_missing_officers.py --analyze

    # 수집 실행
    DATABASE_URL="..." python scripts/collect_missing_officers.py --collect

    # 특정 기업만
    DATABASE_URL="..." python scripts/collect_missing_officers.py --corp-code 01156795
"""

import asyncio
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.parsers.officer import OfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_missing_companies(conn: asyncpg.Connection) -> List[Dict]:
    """임원 데이터 없는 기업 조회"""
    query = """
        SELECT
            c.id, c.corp_code, c.name, c.ticker, c.market
        FROM companies c
        WHERE c.listing_status = 'LISTED'
          AND NOT EXISTS (SELECT 1 FROM officer_positions op WHERE op.company_id = c.id)
        ORDER BY c.market, c.name
    """
    rows = await conn.fetch(query)
    return [dict(r) for r in rows]


async def find_latest_annual_report(conn: asyncpg.Connection, corp_code: str) -> Optional[str]:
    """최근 사업보고서 접수번호 조회"""
    query = """
        SELECT rcept_no, rcept_dt
        FROM disclosures
        WHERE corp_code = $1
          AND report_nm LIKE '%사업보고서%'
        ORDER BY rcept_dt DESC
        LIMIT 1
    """
    row = await conn.fetchrow(query, corp_code)
    if row:
        return row['rcept_no']
    return None


async def analyze_missing_companies(database_url: str):
    """결손 기업 분석"""
    pool = await asyncpg.create_pool(database_url)

    async with pool.acquire() as conn:
        missing = await get_missing_companies(conn)
        logger.info(f"결손 기업: {len(missing)}개")

        # 유형별 분류
        spac_count = sum(1 for c in missing if '스팩' in c['name'] or 'SPAC' in c['name'].upper())
        reit_count = sum(1 for c in missing if '리츠' in c['name'] or '인프라' in c['name'])
        securities_count = sum(1 for c in missing if '증권' in c['name'])
        other_count = len(missing) - spac_count - reit_count - securities_count

        print("\n" + "="*60)
        print("결손 기업 분석")
        print("="*60)
        print(f"총 결손 기업: {len(missing)}개")
        print(f"  - SPAC: {spac_count}개")
        print(f"  - 리츠/인프라: {reit_count}개")
        print(f"  - 증권사: {securities_count}개")
        print(f"  - 기타: {other_count}개")
        print()

        # 기타 기업 목록 (수집 가능성 높음)
        print("수집 가능 기타 기업:")
        for c in missing:
            if '스팩' not in c['name'] and 'SPAC' not in c['name'].upper() \
               and '리츠' not in c['name'] and '인프라' not in c['name'] \
               and '증권' not in c['name']:
                rcept_no = await find_latest_annual_report(conn, c['corp_code'])
                print(f"  - {c['name']} ({c['ticker']}, {c['market']}) - 최근 사업보고서: {rcept_no or 'N/A'}")

        print("="*60)

    await pool.close()


async def collect_missing_officers(
    database_url: str,
    corp_code: Optional[str] = None,
    dry_run: bool = False
):
    """결손 기업 임원 수집"""
    pool = await asyncpg.create_pool(database_url)
    parser = OfficerParser(database_url)
    base_dir = Path(__file__).parent.parent / 'data' / 'dart'

    async with pool.acquire() as conn:
        await parser.load_companies(conn)

        if corp_code:
            missing = [{'corp_code': corp_code}]
        else:
            missing = await get_missing_companies(conn)
            # SPAC, 리츠, 증권사 제외 (일반 기업만)
            missing = [c for c in missing
                      if '스팩' not in c.get('name', '')
                      and 'SPAC' not in c.get('name', '').upper()
                      and '리츠' not in c.get('name', '')
                      and '인프라' not in c.get('name', '')
                      and '증권' not in c.get('name', '')]

        logger.info(f"수집 대상: {len(missing)}개 기업")

        stats = {'total': len(missing), 'success': 0, 'no_file': 0, 'parse_failed': 0}

        for i, company in enumerate(missing, 1):
            corp_code = company['corp_code']
            company_name = company.get('name', corp_code)

            # 최근 사업보고서 찾기
            rcept_no = await find_latest_annual_report(conn, corp_code)
            if not rcept_no:
                logger.debug(f"[{i}/{stats['total']}] {company_name}: 사업보고서 없음")
                stats['no_file'] += 1
                continue

            # ZIP 파일 찾기
            zip_file = None
            for batch_dir in sorted(base_dir.glob('batch_*')):
                corp_dir = batch_dir / corp_code
                if not corp_dir.exists():
                    continue
                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir():
                        continue
                    candidate = year_dir / f"{rcept_no}.zip"
                    if candidate.exists():
                        zip_file = candidate
                        break
                if zip_file:
                    break

            if not zip_file:
                logger.debug(f"[{i}/{stats['total']}] {company_name}: ZIP 파일 없음")
                stats['no_file'] += 1
                continue

            # 파싱
            meta = {'corp_code': corp_code, 'rcept_no': rcept_no}
            try:
                result = await parser.parse(zip_file, meta)

                if not result.get('success') or not result.get('officers'):
                    logger.debug(f"[{i}/{stats['total']}] {company_name}: 임원 정보 없음")
                    stats['parse_failed'] += 1
                    continue

                if not dry_run:
                    await parser.save_to_db(conn, result)

                logger.info(f"[{i}/{stats['total']}] {company_name}: {len(result['officers'])}명 수집")
                stats['success'] += 1

            except Exception as e:
                logger.error(f"[{i}/{stats['total']}] {company_name}: 에러 - {e}")
                stats['parse_failed'] += 1

        # 결과
        print("\n" + "="*60)
        print("결손 기업 임원 수집 결과")
        print("="*60)
        print(f"총 대상:    {stats['total']}개")
        print(f"수집 성공:  {stats['success']}개")
        print(f"파일 없음:  {stats['no_file']}개")
        print(f"파싱 실패:  {stats['parse_failed']}개")
        if dry_run:
            print("\n[DRY-RUN] 실제 DB 저장 없음")
        print("="*60)

    await pool.close()


def main():
    parser = argparse.ArgumentParser(description='결손 기업 임원 수집')
    parser.add_argument('--analyze', action='store_true', help='결손 기업 분석')
    parser.add_argument('--collect', action='store_true', help='임원 수집 실행')
    parser.add_argument('--corp-code', type=str, help='특정 기업 코드')
    parser.add_argument('--dry-run', action='store_true', help='테스트 모드')
    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경 변수 필요")
        sys.exit(1)

    if args.analyze:
        asyncio.run(analyze_missing_companies(database_url))
    elif args.collect or args.corp_code:
        asyncio.run(collect_missing_officers(
            database_url=database_url,
            corp_code=args.corp_code,
            dry_run=args.dry_run
        ))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
