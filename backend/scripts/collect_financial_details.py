#!/usr/bin/env python3
"""
상세 재무 데이터 수집 스크립트 - RaymondsIndex용

DART API를 통해 financial_details 테이블에 데이터 적재
현금흐름표 상세 항목 (CAPEX, 배당금 등) 포함

사용법:
    python scripts/collect_financial_details.py --limit 100  # 100개 회사만
    python scripts/collect_financial_details.py              # 전체 회사
    python scripts/collect_financial_details.py --year 2024  # 특정 연도만
"""
import asyncio
import asyncpg
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import uuid

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.dart_financial_parser import DARTFinancialParser

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/collect_financial_details_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수
DART_API_KEY = os.getenv('DART_API_KEY')
if not DART_API_KEY:
    raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다")
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


class FinancialDetailsCollector:
    """상세 재무 데이터 수집기"""

    def __init__(self, api_key: str, db_url: str):
        self.api_key = api_key
        self.db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.stats = {
            'total': 0,
            'processed': 0,
            'saved': 0,
            'updated': 0,
            'skipped': 0,
            'no_data': 0,
            'errors': 0
        }

    async def get_companies(self, conn, limit: Optional[int] = None) -> List[Dict]:
        """상장사 목록 조회"""
        query = """
            SELECT id, corp_code, name, ticker, market
            FROM companies
            WHERE corp_code IS NOT NULL
              AND market IS NOT NULL
              AND market NOT IN ('ETF', '기타')
            ORDER BY name
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def check_existing(self, conn, company_id: str, year: int) -> bool:
        """기존 데이터 존재 여부 확인"""
        result = await conn.fetchval("""
            SELECT 1 FROM financial_details
            WHERE company_id = $1 AND fiscal_year = $2
        """, uuid.UUID(company_id), year)
        return result is not None

    async def save_financial_details(self, conn, company_id: str, data: Dict) -> bool:
        """재무 데이터 저장 (upsert)"""
        try:
            await conn.execute("""
                INSERT INTO financial_details (
                    id, company_id, fiscal_year, fiscal_quarter, report_type,
                    -- 재무상태표
                    cash_and_equivalents, short_term_investments,
                    inventories, tangible_assets, intangible_assets,
                    total_assets, current_liabilities, non_current_liabilities,
                    total_liabilities, total_equity,
                    -- 손익계산서
                    revenue, cost_of_sales, selling_admin_expenses,
                    operating_income, net_income,
                    -- 현금흐름표
                    operating_cash_flow, investing_cash_flow, financing_cash_flow,
                    capex, intangible_acquisition, dividend_paid,
                    treasury_stock_acquisition, stock_issuance, bond_issuance,
                    -- 메타데이터
                    fs_type, data_source, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), $1, $2, $3, $4,
                    $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19,
                    $20, $21, $22, $23, $24, $25, $26, $27, $28,
                    $29, $30, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, fiscal_quarter, fs_type)
                DO UPDATE SET
                    cash_and_equivalents = EXCLUDED.cash_and_equivalents,
                    short_term_investments = EXCLUDED.short_term_investments,
                    inventories = EXCLUDED.inventories,
                    tangible_assets = EXCLUDED.tangible_assets,
                    intangible_assets = EXCLUDED.intangible_assets,
                    total_assets = EXCLUDED.total_assets,
                    current_liabilities = EXCLUDED.current_liabilities,
                    non_current_liabilities = EXCLUDED.non_current_liabilities,
                    total_liabilities = EXCLUDED.total_liabilities,
                    total_equity = EXCLUDED.total_equity,
                    revenue = EXCLUDED.revenue,
                    cost_of_sales = EXCLUDED.cost_of_sales,
                    selling_admin_expenses = EXCLUDED.selling_admin_expenses,
                    operating_income = EXCLUDED.operating_income,
                    net_income = EXCLUDED.net_income,
                    operating_cash_flow = EXCLUDED.operating_cash_flow,
                    investing_cash_flow = EXCLUDED.investing_cash_flow,
                    financing_cash_flow = EXCLUDED.financing_cash_flow,
                    capex = EXCLUDED.capex,
                    intangible_acquisition = EXCLUDED.intangible_acquisition,
                    dividend_paid = EXCLUDED.dividend_paid,
                    treasury_stock_acquisition = EXCLUDED.treasury_stock_acquisition,
                    stock_issuance = EXCLUDED.stock_issuance,
                    bond_issuance = EXCLUDED.bond_issuance,
                    fs_type = EXCLUDED.fs_type,
                    updated_at = NOW()
            """,
                uuid.UUID(company_id),
                data.get('fiscal_year'),
                data.get('fiscal_quarter'),
                data.get('report_type', 'annual'),
                # 재무상태표
                data.get('cash_and_equivalents'),
                data.get('short_term_investments'),
                data.get('inventories'),
                data.get('tangible_assets'),
                data.get('intangible_assets'),
                data.get('total_assets'),
                data.get('current_liabilities'),
                data.get('non_current_liabilities'),
                data.get('total_liabilities'),
                data.get('total_equity'),
                # 손익계산서
                data.get('revenue'),
                data.get('cost_of_sales'),
                data.get('selling_admin_expenses'),
                data.get('operating_income'),
                data.get('net_income'),
                # 현금흐름표
                data.get('operating_cash_flow'),
                data.get('investing_cash_flow'),
                data.get('financing_cash_flow'),
                data.get('capex'),
                data.get('intangible_acquisition'),
                data.get('dividend_paid'),
                data.get('treasury_stock_acquisition'),
                data.get('stock_issuance'),
                data.get('bond_issuance'),
                # 메타데이터
                data.get('fs_type', 'CFS'),
                data.get('data_source', 'DART')
            )
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    async def collect_batch(
        self,
        companies: List[Dict],
        years: List[int],
        batch_size: int = 5,
        quarter: Optional[int] = None
    ):
        """배치 단위로 재무 데이터 수집"""
        conn = await asyncpg.connect(self.db_url)

        try:
            async with DARTFinancialParser(self.api_key) as parser:
                total = len(companies)

                for i in range(0, total, batch_size):
                    batch = companies[i:i + batch_size]

                    for company in batch:
                        self.stats['processed'] += 1

                        try:
                            results = await parser.collect_company_financials(
                                corp_code=company['corp_code'],
                                years=years,
                                prefer_consolidated=True,
                                quarter=quarter
                            )

                            if not results:
                                self.stats['no_data'] += 1
                                logger.debug(f"No data: {company['name']} ({company['corp_code']})")
                                continue

                            for data in results:
                                quality = parser.validate_data_quality(data)
                                if quality < 0.3:  # 최소 품질 기준
                                    self.stats['skipped'] += 1
                                    continue

                                success = await self.save_financial_details(
                                    conn, str(company['id']), data
                                )
                                if success:
                                    self.stats['saved'] += 1

                        except Exception as e:
                            self.stats['errors'] += 1
                            logger.error(f"Error processing {company['name']}: {e}")

                    # 진행 상황 로깅
                    if self.stats['processed'] % 50 == 0:
                        logger.info(
                            f"Progress: {self.stats['processed']}/{total} "
                            f"(Saved: {self.stats['saved']}, No data: {self.stats['no_data']}, "
                            f"Errors: {self.stats['errors']})"
                        )

                    # Rate limiting
                    await asyncio.sleep(2)

        finally:
            await conn.close()

    async def run(
        self,
        limit: Optional[int] = None,
        years: Optional[List[int]] = None,
        batch_size: int = 5,
        quarter: Optional[int] = None
    ):
        """수집 실행"""
        if years is None:
            years = [2022, 2023, 2024]

        conn = await asyncpg.connect(self.db_url)

        try:
            # 1. 회사 목록 조회
            companies = await self.get_companies(conn, limit)
            self.stats['total'] = len(companies)

            quarter_str = f"{quarter}분기" if quarter else "연간"
            logger.info("=" * 80)
            logger.info("상세 재무 데이터 수집 시작 (financial_details)")
            logger.info("=" * 80)
            logger.info(f"대상 회사: {self.stats['total']}개")
            logger.info(f"수집 연도: {years}")
            logger.info(f"보고서 유형: {quarter_str}")
            logger.info(f"배치 크기: {batch_size}")
            logger.info("=" * 80)

        finally:
            await conn.close()

        # 2. 배치 수집 실행
        await self.collect_batch(companies, years, batch_size, quarter)

        # 3. 결과 출력
        logger.info("=" * 80)
        logger.info("수집 완료")
        logger.info("=" * 80)
        logger.info(f"처리: {self.stats['processed']}/{self.stats['total']}")
        logger.info(f"저장: {self.stats['saved']}건")
        logger.info(f"데이터 없음: {self.stats['no_data']}건")
        logger.info(f"품질 미달: {self.stats['skipped']}건")
        logger.info(f"오류: {self.stats['errors']}건")
        logger.info("=" * 80)


async def verify_results():
    """수집 결과 검증"""
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 연도별 COUNT
        yearly = await conn.fetch("""
            SELECT fiscal_year, COUNT(*) as cnt
            FROM financial_details
            GROUP BY fiscal_year
            ORDER BY fiscal_year
        """)

        logger.info("\n[수집 결과 검증]")
        logger.info("연도별 레코드 수:")
        for row in yearly:
            logger.info(f"  {row['fiscal_year']}년: {row['cnt']:,}건")

        # 핵심 필드 채움률
        total = await conn.fetchval("SELECT COUNT(*) FROM financial_details")
        capex_filled = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_details WHERE capex IS NOT NULL"
        )
        ocf_filled = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_details WHERE operating_cash_flow IS NOT NULL"
        )
        dividend_filled = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_details WHERE dividend_paid IS NOT NULL"
        )

        logger.info("\n핵심 필드 채움률:")
        if total > 0:
            logger.info(f"  CAPEX: {capex_filled}/{total} ({capex_filled/total*100:.1f}%)")
            logger.info(f"  영업CF: {ocf_filled}/{total} ({ocf_filled/total*100:.1f}%)")
            logger.info(f"  배당금: {dividend_filled}/{total} ({dividend_filled/total*100:.1f}%)")

    finally:
        await conn.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='상세 재무 데이터 수집')
    parser.add_argument('--limit', type=int, help='수집할 회사 수 제한')
    parser.add_argument('--year', type=int, help='특정 연도만 수집')
    parser.add_argument('--years', type=str, help='수집 연도 (예: 2022,2023,2024)')
    parser.add_argument('--quarter', type=int, choices=[1, 2, 3], help='분기 (1=1분기, 2=반기, 3=3분기)')
    parser.add_argument('--batch-size', type=int, default=5, help='배치 크기 (기본: 5)')
    parser.add_argument('--verify-only', action='store_true', help='결과 검증만 실행')

    args = parser.parse_args()

    # 로그 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)

    if args.verify_only:
        asyncio.run(verify_results())
        return

    # 연도 파싱
    if args.year:
        years = [args.year]
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(',')]
    else:
        years = [2022, 2023, 2024]

    # 수집 실행
    collector = FinancialDetailsCollector(DART_API_KEY, DATABASE_URL)
    asyncio.run(collector.run(
        limit=args.limit,
        years=years,
        batch_size=args.batch_size,
        quarter=args.quarter
    ))

    # 결과 검증
    asyncio.run(verify_results())


if __name__ == "__main__":
    main()
