"""
재무비율 배치 계산 스크립트

financial_details 데이터를 기반으로 financial_ratios 테이블에
모든 기업의 재무비율을 계산하여 저장합니다.

사용법:
    # 테스트 (샘플 10개)
    python -m scripts.pipeline.calculate_financial_ratios --sample 10 --dry-run

    # 특정 연도만
    python -m scripts.pipeline.calculate_financial_ratios --year 2024

    # 전체 실행
    python -m scripts.pipeline.calculate_financial_ratios
"""
import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

import asyncpg

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.financial_ratios_calculator import FinancialRatiosCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinancialRatiosBatchCalculator:
    """재무비율 배치 계산기"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.calculator = FinancialRatiosCalculator()
        self.stats = {
            'total_processed': 0,
            'success': 0,
            'skipped': 0,
            'errors': 0,
        }

    async def run(
        self,
        year: Optional[int] = None,
        sample: Optional[int] = None,
        dry_run: bool = False,
    ):
        """배치 계산 실행"""
        logger.info("=" * 60)
        logger.info("재무비율 배치 계산 시작")
        logger.info(f"연도: {year or '전체'}, 샘플: {sample or '전체'}, Dry-run: {dry_run}")
        logger.info("=" * 60)

        pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)

        try:
            # 1. 대상 데이터 조회
            records = await self._fetch_financial_details(pool, year, sample)
            logger.info(f"처리 대상: {len(records)}건")

            if not records:
                logger.warning("처리할 데이터가 없습니다.")
                return

            # 2. 회사별, 연도별 그룹화
            grouped = self._group_by_company_year(records)
            logger.info(f"회사-연도 조합: {len(grouped)}건")

            # 3. 배치 계산
            for idx, ((company_id, fiscal_year), current_data) in enumerate(grouped.items(), 1):
                try:
                    # 전년도 데이터 조회 (성장성 계산용)
                    previous_data = await self._fetch_previous_year(
                        pool, company_id, fiscal_year
                    )

                    # 계산
                    result = self.calculator.calculate(
                        current_data=current_data,
                        previous_data=previous_data,
                        company_id=str(company_id),
                        fiscal_year=fiscal_year,
                    )

                    # 저장
                    if not dry_run:
                        await self._save_result(pool, result)

                    self.stats['success'] += 1

                    if idx % 100 == 0:
                        logger.info(f"진행: {idx}/{len(grouped)} ({idx/len(grouped)*100:.1f}%)")

                except Exception as e:
                    logger.error(f"Error for {company_id}/{fiscal_year}: {e}")
                    self.stats['errors'] += 1

                self.stats['total_processed'] += 1

            # 4. 결과 보고
            self._print_summary()

        finally:
            await pool.close()

    async def _fetch_financial_details(
        self,
        pool: asyncpg.Pool,
        year: Optional[int],
        sample: Optional[int],
    ) -> List[Dict]:
        """financial_details 데이터 조회"""
        query = """
            SELECT
                fd.company_id,
                fd.fiscal_year,
                fd.fiscal_quarter,
                -- 재무상태표
                fd.current_assets,
                fd.cash_and_equivalents,
                fd.short_term_investments,
                fd.trade_and_other_receivables,
                fd.inventories,
                fd.non_current_assets,
                fd.tangible_assets,
                fd.intangible_assets,
                fd.total_assets,
                fd.current_liabilities,
                fd.trade_payables,
                fd.short_term_borrowings,
                fd.non_current_liabilities,
                fd.long_term_borrowings,
                fd.bonds_payable,
                fd.total_liabilities,
                fd.total_equity,
                fd.capital_stock,
                fd.capital_surplus,
                fd.retained_earnings,
                fd.treasury_stock,
                -- 손익계산서
                fd.revenue,
                fd.cost_of_sales,
                fd.gross_profit,
                fd.operating_income,
                fd.net_income,
                fd.depreciation_expense,
                fd.interest_expense,
                fd.interest_income,
                fd.income_before_tax,
                fd.tax_expense,
                fd.amortization,
                -- 현금흐름표
                fd.operating_cash_flow,
                fd.investing_cash_flow,
                fd.financing_cash_flow,
                fd.capex,
                fd.intangible_acquisition,
                fd.dividend_paid
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE 1=1
                AND (c.company_type IS NULL OR c.company_type NOT IN ('ETF', 'SPAC', 'REIT'))
        """

        params = []
        if year:
            query += f" AND fd.fiscal_year = ${len(params) + 1}"
            params.append(year)

        query += " ORDER BY fd.company_id, fd.fiscal_year"

        if sample:
            query += f" LIMIT ${len(params) + 1}"
            params.append(sample)

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    def _group_by_company_year(self, records: List[Dict]) -> Dict:
        """회사-연도별 그룹화"""
        grouped = {}
        for r in records:
            key = (r['company_id'], r['fiscal_year'])
            grouped[key] = r
        return grouped

    async def _fetch_previous_year(
        self,
        pool: asyncpg.Pool,
        company_id: UUID,
        fiscal_year: int,
    ) -> Optional[Dict]:
        """전년도 데이터 조회"""
        query = """
            SELECT
                company_id, fiscal_year,
                revenue, operating_income, net_income, total_assets
            FROM financial_details
            WHERE company_id = $1 AND fiscal_year = $2
        """

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, company_id, fiscal_year - 1)
            return dict(row) if row else None

    async def _save_result(self, pool: asyncpg.Pool, result):
        """계산 결과 저장 (UPSERT)"""
        data = self.calculator.result_to_dict(result)

        query = """
            INSERT INTO financial_ratios (
                id, company_id, fiscal_year, fiscal_quarter, calculation_date,
                -- 안정성
                current_ratio, quick_ratio, debt_ratio, equity_ratio,
                debt_dependency, non_current_ratio,
                -- 수익성
                operating_margin, net_profit_margin, roa, roe,
                gross_margin, ebitda_margin, ebitda,
                -- 성장성
                revenue_growth, operating_income_growth, net_income_growth,
                total_assets_growth, growth_data_available,
                -- 활동성
                asset_turnover, receivables_turnover, inventory_turnover,
                payables_turnover, receivables_days, inventory_days,
                payables_days, cash_conversion_cycle,
                -- 현금흐름
                ocf_ratio, ocf_interest_coverage, free_cash_flow, fcf_margin,
                -- 레버리지
                interest_coverage, ebitda_interest_coverage, net_debt_to_ebitda,
                financial_expense_ratio, total_borrowings, net_debt,
                -- 연속 적자/흑자
                consecutive_loss_quarters, consecutive_profit_quarters, is_loss_making,
                -- 카테고리 점수
                stability_score, profitability_score, growth_score,
                activity_score, cashflow_score, leverage_score,
                -- 종합
                financial_health_score, financial_health_grade, financial_risk_level,
                -- 메타
                data_completeness, calculation_notes, created_at
            ) VALUES (
                gen_random_uuid(), $1, $2, $3, NOW(),
                $4, $5, $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15, $16,
                $17, $18, $19, $20, $21,
                $22, $23, $24, $25, $26, $27, $28, $29,
                $30, $31, $32, $33,
                $34, $35, $36, $37, $38, $39,
                $40, $41, $42,
                $43, $44, $45, $46, $47, $48,
                $49, $50, $51,
                $52, $53, NOW()
            )
            ON CONFLICT (company_id, fiscal_year, fiscal_quarter)
            DO UPDATE SET
                calculation_date = NOW(),
                current_ratio = EXCLUDED.current_ratio,
                quick_ratio = EXCLUDED.quick_ratio,
                debt_ratio = EXCLUDED.debt_ratio,
                equity_ratio = EXCLUDED.equity_ratio,
                debt_dependency = EXCLUDED.debt_dependency,
                non_current_ratio = EXCLUDED.non_current_ratio,
                operating_margin = EXCLUDED.operating_margin,
                net_profit_margin = EXCLUDED.net_profit_margin,
                roa = EXCLUDED.roa,
                roe = EXCLUDED.roe,
                gross_margin = EXCLUDED.gross_margin,
                ebitda_margin = EXCLUDED.ebitda_margin,
                ebitda = EXCLUDED.ebitda,
                revenue_growth = EXCLUDED.revenue_growth,
                operating_income_growth = EXCLUDED.operating_income_growth,
                net_income_growth = EXCLUDED.net_income_growth,
                total_assets_growth = EXCLUDED.total_assets_growth,
                growth_data_available = EXCLUDED.growth_data_available,
                asset_turnover = EXCLUDED.asset_turnover,
                receivables_turnover = EXCLUDED.receivables_turnover,
                inventory_turnover = EXCLUDED.inventory_turnover,
                payables_turnover = EXCLUDED.payables_turnover,
                receivables_days = EXCLUDED.receivables_days,
                inventory_days = EXCLUDED.inventory_days,
                payables_days = EXCLUDED.payables_days,
                cash_conversion_cycle = EXCLUDED.cash_conversion_cycle,
                ocf_ratio = EXCLUDED.ocf_ratio,
                ocf_interest_coverage = EXCLUDED.ocf_interest_coverage,
                free_cash_flow = EXCLUDED.free_cash_flow,
                fcf_margin = EXCLUDED.fcf_margin,
                interest_coverage = EXCLUDED.interest_coverage,
                ebitda_interest_coverage = EXCLUDED.ebitda_interest_coverage,
                net_debt_to_ebitda = EXCLUDED.net_debt_to_ebitda,
                financial_expense_ratio = EXCLUDED.financial_expense_ratio,
                total_borrowings = EXCLUDED.total_borrowings,
                net_debt = EXCLUDED.net_debt,
                consecutive_loss_quarters = EXCLUDED.consecutive_loss_quarters,
                consecutive_profit_quarters = EXCLUDED.consecutive_profit_quarters,
                is_loss_making = EXCLUDED.is_loss_making,
                stability_score = EXCLUDED.stability_score,
                profitability_score = EXCLUDED.profitability_score,
                growth_score = EXCLUDED.growth_score,
                activity_score = EXCLUDED.activity_score,
                cashflow_score = EXCLUDED.cashflow_score,
                leverage_score = EXCLUDED.leverage_score,
                financial_health_score = EXCLUDED.financial_health_score,
                financial_health_grade = EXCLUDED.financial_health_grade,
                financial_risk_level = EXCLUDED.financial_risk_level,
                data_completeness = EXCLUDED.data_completeness,
                calculation_notes = EXCLUDED.calculation_notes
        """

        async with pool.acquire() as conn:
            await conn.execute(
                query,
                data['company_id'],
                data['fiscal_year'],
                data['fiscal_quarter'],
                # 안정성
                data['current_ratio'],
                data['quick_ratio'],
                data['debt_ratio'],
                data['equity_ratio'],
                data['debt_dependency'],
                data['non_current_ratio'],
                # 수익성
                data['operating_margin'],
                data['net_profit_margin'],
                data['roa'],
                data['roe'],
                data['gross_margin'],
                data['ebitda_margin'],
                data['ebitda'],
                # 성장성
                data['revenue_growth'],
                data['operating_income_growth'],
                data['net_income_growth'],
                data['total_assets_growth'],
                data['growth_data_available'],
                # 활동성
                data['asset_turnover'],
                data['receivables_turnover'],
                data['inventory_turnover'],
                data['payables_turnover'],
                data['receivables_days'],
                data['inventory_days'],
                data['payables_days'],
                data['cash_conversion_cycle'],
                # 현금흐름
                data['ocf_ratio'],
                data['ocf_interest_coverage'],
                data['free_cash_flow'],
                data['fcf_margin'],
                # 레버리지
                data['interest_coverage'],
                data['ebitda_interest_coverage'],
                data['net_debt_to_ebitda'],
                data['financial_expense_ratio'],
                data['total_borrowings'],
                data['net_debt'],
                # 연속
                data['consecutive_loss_quarters'],
                data['consecutive_profit_quarters'],
                data['is_loss_making'],
                # 카테고리 점수
                data['stability_score'],
                data['profitability_score'],
                data['growth_score'],
                data['activity_score'],
                data['cashflow_score'],
                data['leverage_score'],
                # 종합
                data['financial_health_score'],
                data['financial_health_grade'],
                data['financial_risk_level'],
                # 메타
                data['data_completeness'],
                data['calculation_notes'],
            )

    def _print_summary(self):
        """결과 요약 출력"""
        logger.info("=" * 60)
        logger.info("배치 계산 완료")
        logger.info("=" * 60)
        logger.info(f"총 처리: {self.stats['total_processed']}")
        logger.info(f"성공: {self.stats['success']}")
        logger.info(f"스킵: {self.stats['skipped']}")
        logger.info(f"오류: {self.stats['errors']}")
        success_rate = (
            self.stats['success'] / self.stats['total_processed'] * 100
            if self.stats['total_processed'] > 0 else 0
        )
        logger.info(f"성공률: {success_rate:.1f}%")


async def main():
    parser = argparse.ArgumentParser(description='재무비율 배치 계산')
    parser.add_argument('--year', type=int, help='특정 연도만 계산')
    parser.add_argument('--sample', type=int, help='샘플 수 (테스트용)')
    parser.add_argument('--dry-run', action='store_true', help='저장 없이 테스트만')
    args = parser.parse_args()

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Railway 프로덕션 DB
        database_url = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"

    calculator = FinancialRatiosBatchCalculator(database_url)
    await calculator.run(
        year=args.year,
        sample=args.sample,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    asyncio.run(main())
