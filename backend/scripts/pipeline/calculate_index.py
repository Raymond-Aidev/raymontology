#!/usr/bin/env python3
"""
RaymondsIndex 계산 (v2.1 통합)

분기별 데이터 업데이트 후 RaymondsIndex를 재계산합니다.
정상 계산기(RaymondsIndexCalculator)를 사용하여 Sub-Index를 포함한
완전한 점수를 계산합니다.

⚠️ 변경 이력:
    2026-01-27: 단순화된 계산 로직 제거, 정상 계산기 통합
               Sub-Index (CEI, RII, CGI, MAI) 저장 추가

사용법:
    python -m scripts.pipeline.calculate_index --year 2025
    python -m scripts.pipeline.calculate_index --year 2025 --sample 100
    python -m scripts.pipeline.calculate_index --year 2025 --version 3.0
    python -m scripts.pipeline.calculate_index --stats

옵션:
    --year: 대상 연도 (해당 연도 재무 데이터 기준)
    --sample: 샘플 개수 (테스트용)
    --version: 알고리즘 버전 (2.1 또는 3.0, 기본값: 2.1)
    --stats: 계산 없이 현재 통계만 출력
"""

import argparse
import asyncio
import logging
import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

import asyncpg

# 프로젝트 루트 경로 추가 (app 모듈 import를 위해)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.raymonds_index_calculator import RaymondsIndexCalculator as ProperCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RaymondsIndexPipelineCalculator:
    """RaymondsIndex 파이프라인 계산기

    v2.1 (기본): 정상 계산기(ProperCalculator) 사용 - Sub-Index 포함
    v3.0: HDI 방식 기하평균 + 클램핑 + V-Score (별도 테이블)

    ⚠️ 2026-01-27 수정: 단순화된 계산 로직 제거, 정상 계산기 통합
    """

    def __init__(self, database_url: Optional[str] = None, version: str = '2.1'):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        # asyncpg용 URL로 변환 (SQLAlchemy 형식 → 순수 PostgreSQL 형식)
        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

        self.version = version
        self._v3_calculator = None

        # v2.1: 정상 계산기 인스턴스
        self._proper_calculator = ProperCalculator()

        # v3.0 사용 시 v3 모듈 로드
        if version == '3.0':
            try:
                from app.services.raymonds_index_v3.engine import RaymondsIndexCalculatorV3
                self._v3_calculator = RaymondsIndexCalculatorV3()
                logger.info("RaymondsIndex v3.0 계산기 로드 완료")
            except ImportError as e:
                logger.error(f"v3.0 모듈 로드 실패: {e}")
                logger.info("v2.1 모드로 폴백합니다")
                self.version = '2.1'

    async def calculate(
        self,
        year: Optional[int] = None,
        sample: Optional[int] = None
    ) -> Dict[str, Any]:
        """RaymondsIndex 계산

        기존 calculate_raymonds_index.py 로직을 호출합니다.

        Args:
            year: 대상 연도
            sample: 샘플 개수

        Returns:
            계산 결과 통계
        """
        logger.info(f"=== RaymondsIndex 계산 시작 (v{self.version}) ===")

        conn = await asyncpg.connect(self.database_url)

        try:
            # 계산 대상 회사 조회 (SPAC/REIT/ETF 제외)
            query = """
                SELECT DISTINCT c.id, c.name, c.ticker
                FROM companies c
                JOIN financial_details fd ON c.id = fd.company_id
                WHERE c.listing_status = 'LISTED'
                  AND (c.company_type IS NULL OR c.company_type NOT IN ('SPAC', 'REIT', 'ETF'))
            """
            params = []

            if year:
                query += " AND fd.fiscal_year = $1"
                params.append(year)

            query += " ORDER BY c.name"

            if sample:
                query += f" LIMIT {sample}"

            companies = await conn.fetch(query, *params)
            logger.info(f"계산 대상: {len(companies)}개 회사")

            stats = {
                'started_at': datetime.now(),
                'total': len(companies),
                'calculated': 0,
                'skipped': 0,
                'errors': 0,
                'grade_distribution': {},
            }

            for i, company in enumerate(companies):
                if (i + 1) % 100 == 0:
                    logger.info(f"진행: {i+1}/{len(companies)}")

                try:
                    # company_id를 문자열로 변환 (asyncpg UUID 호환)
                    company_id_str = str(company['id'])

                    # 버전에 따라 다른 계산기 사용
                    if self.version == '3.0' and self._v3_calculator:
                        result = await self._calculate_v3(
                            conn, company_id_str, company['name'], year
                        )
                    else:
                        result = await self._calculate_for_company(
                            conn, company_id_str, company['name'], year
                        )

                    if result:
                        stats['calculated'] += 1
                        grade = result.get('grade', 'N/A')
                        stats['grade_distribution'][grade] = \
                            stats['grade_distribution'].get(grade, 0) + 1
                    else:
                        stats['skipped'] += 1

                except Exception as e:
                    logger.error(f"계산 오류 {company['name']}: {e}")
                    stats['errors'] += 1

            stats['finished_at'] = datetime.now()
            stats['duration'] = (stats['finished_at'] - stats['started_at']).total_seconds()

            logger.info(f"\n{'=' * 50}")
            logger.info("RaymondsIndex 계산 완료")
            logger.info(f"  - 소요 시간: {stats['duration']:.1f}초")
            logger.info(f"  - 계산: {stats['calculated']}개")
            logger.info(f"  - 스킵: {stats['skipped']}개")
            logger.info(f"  - 오류: {stats['errors']}개")
            logger.info(f"\n등급 분포:")
            for grade, count in sorted(stats['grade_distribution'].items()):
                logger.info(f"  {grade}: {count}")

            return stats

        finally:
            await conn.close()

    async def _get_financial_data(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        target_year: Optional[int] = None
    ) -> List[Dict]:
        """회사의 재무 데이터 조회 (3년치)"""
        if target_year:
            years = [target_year - 2, target_year - 1, target_year]
        else:
            years = None

        query = """
            SELECT DISTINCT ON (fiscal_year)
                fiscal_year, fiscal_quarter, fs_type,
                -- 재무상태표
                cash_and_equivalents, short_term_investments, trade_and_other_receivables,
                inventories, tangible_assets, intangible_assets,
                total_assets, current_liabilities, non_current_liabilities,
                total_liabilities, total_equity,
                -- 재무상태표 (투자괴리율 v2용)
                right_of_use_assets, investments_in_associates,
                fvpl_financial_assets, other_financial_assets_non_current,
                -- 손익계산서
                revenue, cost_of_sales, selling_admin_expenses,
                operating_income, net_income,
                -- 현금흐름표
                operating_cash_flow, investing_cash_flow, financing_cash_flow,
                capex, intangible_acquisition, dividend_paid,
                treasury_stock_acquisition, stock_issuance, bond_issuance
            FROM financial_details
            WHERE company_id = $1
        """
        params = [uuid.UUID(company_id)]

        if years:
            query += f" AND fiscal_year IN ({', '.join(map(str, years))})"

        query += " ORDER BY fiscal_year, fiscal_quarter NULLS FIRST"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """값을 범위 내로 제한 (DB overflow 방지)"""
        if value is None:
            return None
        return max(min_val, min(max_val, value))

    async def _save_result(self, conn: asyncpg.Connection, result_dict: Dict) -> bool:
        """계산 결과 저장 (v2.1 - Sub-Index 포함)"""
        try:
            await conn.execute("""
                INSERT INTO raymonds_index (
                    id, company_id, calculation_date, fiscal_year,
                    total_score, grade,
                    cei_score, rii_score, cgi_score, mai_score,
                    investment_gap, cash_cagr, capex_growth, idle_cash_ratio,
                    asset_turnover, reinvestment_rate, shareholder_return,
                    cash_tangible_ratio, fundraising_utilization, short_term_ratio,
                    capex_trend, roic, capex_cv, violation_count,
                    investment_gap_v2, investment_gap_v21, investment_gap_v21_flag,
                    cash_utilization, industry_sector, weight_adjustment,
                    tangible_efficiency, cash_yield, debt_to_ebitda, growth_investment_ratio,
                    red_flags, yellow_flags,
                    verdict, key_risk, recommendation, watch_trigger,
                    data_quality_score, created_at
                )
                VALUES (
                    gen_random_uuid(), $1, $2, $3,
                    $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12, $13,
                    $14, $15, $16,
                    $17, $18, $19,
                    $20, $21, $22, $23,
                    $24, $25, $26,
                    $27, $28, $29,
                    $30, $31, $32, $33,
                    $34, $35,
                    $36, $37, $38, $39,
                    $40, NOW()
                )
                ON CONFLICT (company_id, fiscal_year)
                DO UPDATE SET
                    calculation_date = EXCLUDED.calculation_date,
                    total_score = EXCLUDED.total_score,
                    grade = EXCLUDED.grade,
                    cei_score = EXCLUDED.cei_score,
                    rii_score = EXCLUDED.rii_score,
                    cgi_score = EXCLUDED.cgi_score,
                    mai_score = EXCLUDED.mai_score,
                    investment_gap = EXCLUDED.investment_gap,
                    cash_cagr = EXCLUDED.cash_cagr,
                    capex_growth = EXCLUDED.capex_growth,
                    idle_cash_ratio = EXCLUDED.idle_cash_ratio,
                    asset_turnover = EXCLUDED.asset_turnover,
                    reinvestment_rate = EXCLUDED.reinvestment_rate,
                    shareholder_return = EXCLUDED.shareholder_return,
                    cash_tangible_ratio = EXCLUDED.cash_tangible_ratio,
                    fundraising_utilization = EXCLUDED.fundraising_utilization,
                    short_term_ratio = EXCLUDED.short_term_ratio,
                    capex_trend = EXCLUDED.capex_trend,
                    roic = EXCLUDED.roic,
                    capex_cv = EXCLUDED.capex_cv,
                    violation_count = EXCLUDED.violation_count,
                    investment_gap_v2 = EXCLUDED.investment_gap_v2,
                    investment_gap_v21 = EXCLUDED.investment_gap_v21,
                    investment_gap_v21_flag = EXCLUDED.investment_gap_v21_flag,
                    cash_utilization = EXCLUDED.cash_utilization,
                    industry_sector = EXCLUDED.industry_sector,
                    weight_adjustment = EXCLUDED.weight_adjustment,
                    tangible_efficiency = EXCLUDED.tangible_efficiency,
                    cash_yield = EXCLUDED.cash_yield,
                    debt_to_ebitda = EXCLUDED.debt_to_ebitda,
                    growth_investment_ratio = EXCLUDED.growth_investment_ratio,
                    red_flags = EXCLUDED.red_flags,
                    yellow_flags = EXCLUDED.yellow_flags,
                    verdict = EXCLUDED.verdict,
                    key_risk = EXCLUDED.key_risk,
                    recommendation = EXCLUDED.recommendation,
                    watch_trigger = EXCLUDED.watch_trigger,
                    data_quality_score = EXCLUDED.data_quality_score
            """,
                uuid.UUID(result_dict['company_id']),
                date.today(),
                result_dict['fiscal_year'],
                result_dict['total_score'],
                result_dict['grade'],
                self._clamp(result_dict.get('cei_score'), 0, 100),
                self._clamp(result_dict.get('rii_score'), 0, 100),
                self._clamp(result_dict.get('cgi_score'), 0, 100),
                self._clamp(result_dict.get('mai_score'), 0, 100),
                self._clamp(result_dict.get('investment_gap'), -999, 999),
                self._clamp(result_dict.get('cash_cagr'), -999, 999),
                self._clamp(result_dict.get('capex_growth'), -999, 999),
                self._clamp(result_dict.get('idle_cash_ratio'), 0, 100),
                self._clamp(result_dict.get('asset_turnover'), 0, 99.999),
                self._clamp(result_dict.get('reinvestment_rate'), 0, 100),
                self._clamp(result_dict.get('shareholder_return'), 0, 100),
                self._clamp(result_dict.get('cash_tangible_ratio', 0), 0, 9999999.99),
                self._clamp(result_dict.get('fundraising_utilization', -1), -1, 999),
                self._clamp(result_dict.get('short_term_ratio', 0), 0, 100),
                result_dict.get('capex_trend', 'stable'),
                self._clamp(result_dict.get('roic', 0), -999, 999),
                self._clamp(result_dict.get('capex_cv', 0), 0, 9.999),
                result_dict.get('violation_count', 0),
                self._clamp(result_dict.get('investment_gap_v2', 0), -100, 100),
                self._clamp(result_dict.get('investment_gap_v21', 0), -50, 50),
                result_dict.get('investment_gap_v21_flag', 'ok'),
                self._clamp(result_dict.get('cash_utilization', 0), 0, 999),
                result_dict.get('industry_sector', ''),
                json.dumps(result_dict.get('weight_adjustment', {}), ensure_ascii=False),
                self._clamp(result_dict.get('tangible_efficiency', 0), 0, 999.999),
                self._clamp(result_dict.get('cash_yield', 0), -999, 999),
                self._clamp(result_dict.get('debt_to_ebitda', 0), 0, 999),
                self._clamp(result_dict.get('growth_investment_ratio', 0), 0, 100),
                json.dumps(result_dict.get('red_flags', []), ensure_ascii=False),
                json.dumps(result_dict.get('yellow_flags', []), ensure_ascii=False),
                result_dict.get('verdict', ''),
                result_dict.get('key_risk', ''),
                result_dict.get('recommendation', ''),
                result_dict.get('watch_trigger', ''),
                result_dict.get('data_quality_score', 0)
            )
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    async def _calculate_for_company(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        company_name: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """개별 회사 RaymondsIndex 계산 (v2.1 정상 계산기 사용)

        ⚠️ 2026-01-27 수정: 단순화된 계산 로직 제거
        → 정상 계산기(ProperCalculator)를 사용하여 Sub-Index 포함 완전한 점수 계산
        """
        # 재무 데이터 조회 (3년치)
        financial_data = await self._get_financial_data(conn, company_id, year)

        if len(financial_data) < 2:  # 최소 2년 데이터 필요
            return None

        # 정상 계산기로 계산 (Sub-Index 포함)
        result = self._proper_calculator.calculate(
            company_id=company_id,
            financial_data=financial_data,
            target_year=year
        )

        if result is None:
            return None

        # 결과 저장 (Sub-Index 포함)
        result_dict = self._proper_calculator.to_dict(result)
        success = await self._save_result(conn, result_dict)

        if not success:
            return None

        return {'score': result.total_score, 'grade': result.grade}

    async def _calculate_v3(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        company_name: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """v3.0 알고리즘으로 개별 회사 RaymondsIndex 계산

        HDI 방식 기하평균 + 클램핑 + V-Score 적용
        ⚠️ 옵션 A: 별도 테이블 (raymonds_index_v3)에 저장
           → 기존 raymonds_index 테이블 영향 없음
        """
        # 재무 데이터 조회 (5년치)
        query = """
            SELECT fiscal_year, revenue, operating_income, net_income,
                   total_assets, total_liabilities, total_equity,
                   operating_cash_flow, investing_cash_flow, financing_cash_flow,
                   capex, r_and_d_expense, dividend_paid,
                   cash_and_equivalents, short_term_investments, tangible_assets
            FROM financial_details
            WHERE company_id = $1
        """
        params = [company_id]

        if year:
            query += " AND fiscal_year <= $2"
            params.append(year)

        query += " ORDER BY fiscal_year DESC LIMIT 5"

        financials = await conn.fetch(query, *params)

        if len(financials) < 2:  # 최소 2년 데이터 필요
            return None

        # 리스트 형태로 변환 (오래된 순서로 정렬)
        financial_data = [dict(row) for row in reversed(financials)]

        # v3.0 계산기로 계산
        try:
            result = self._v3_calculator.calculate(str(company_id), financial_data)

            # ⭐ 별도 테이블 (raymonds_index_v3)에 저장
            # 기존 raymonds_index 테이블은 변경하지 않음
            await conn.execute("""
                INSERT INTO raymonds_index_v3 (
                    id, company_id, fiscal_year, total_score, grade,
                    cei_score, rii_score, cgi_score, mai_score,
                    investment_gap, cash_cagr, capex_growth,
                    asset_turnover, reinvestment_rate,
                    algorithm_version, data_quality_score, calculation_date
                )
                VALUES (
                    gen_random_uuid(), $1, $2, $3, $4,
                    $5, $6, $7, $8,
                    $9, $10, $11,
                    $12, $13,
                    $14, $15, CURRENT_DATE
                )
                ON CONFLICT (company_id, fiscal_year)
                DO UPDATE SET
                    total_score = $3, grade = $4,
                    cei_score = $5, rii_score = $6, cgi_score = $7, mai_score = $8,
                    investment_gap = $9, cash_cagr = $10, capex_growth = $11,
                    asset_turnover = $12, reinvestment_rate = $13,
                    algorithm_version = $14, data_quality_score = $15,
                    calculation_date = CURRENT_DATE
            """,
                company_id,
                result.fiscal_year,
                result.total_score,
                result.grade,
                result.cei_score,
                result.rii_score,
                result.cgi_score,
                result.mai_score,
                result.investment_gap,
                result.raw_metrics.get('cash_cagr') if result.raw_metrics else None,
                result.raw_metrics.get('capex_growth') if result.raw_metrics else None,
                result.raw_metrics.get('asset_turnover') if result.raw_metrics else None,
                result.raw_metrics.get('reinvestment_rate') if result.raw_metrics else None,
                '3.0',
                result.data_quality_score,
            )

            return {'score': result.total_score, 'grade': result.grade}

        except Exception as e:
            logger.error(f"v3.0 계산 오류 {company_name}: {e}")
            return None

    def _get_grade(self, score: float) -> str:
        """점수 → 등급 변환"""
        if score >= 95:
            return 'A++'
        elif score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 70:
            return 'B+'
        elif score >= 60:
            return 'B'
        elif score >= 50:
            return 'B-'
        elif score >= 40:
            return 'C+'
        else:
            return 'C'

    async def get_stats(self) -> Dict[str, Any]:
        """현재 통계 조회"""
        conn = await asyncpg.connect(self.database_url)

        try:
            # 총 개수
            total = await conn.fetchval("SELECT COUNT(*) FROM raymonds_index")

            # 등급별 분포
            distribution = await conn.fetch("""
                SELECT grade, COUNT(*) as count
                FROM raymonds_index
                GROUP BY grade
                ORDER BY grade
            """)

            # 연도별 분포
            yearly = await conn.fetch("""
                SELECT fiscal_year, COUNT(*) as count
                FROM raymonds_index
                GROUP BY fiscal_year
                ORDER BY fiscal_year DESC
            """)

            return {
                'total': total,
                'grade_distribution': {r['grade']: r['count'] for r in distribution},
                'yearly_distribution': {r['fiscal_year']: r['count'] for r in yearly},
            }

        finally:
            await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='RaymondsIndex 계산')
    parser.add_argument('--year', type=int, help='대상 연도')
    parser.add_argument('--sample', type=int, help='샘플 개수 (테스트용)')
    parser.add_argument('--version', type=str, default='2.1', choices=['2.1', '3.0'],
                        help='알고리즘 버전 (2.1 또는 3.0, 기본값: 2.1)')
    parser.add_argument('--stats', action='store_true', help='현재 통계만 출력')

    args = parser.parse_args()

    calculator = RaymondsIndexPipelineCalculator(version=args.version)

    if args.stats:
        stats = await calculator.get_stats()
        print("\n=== RaymondsIndex 현황 ===")
        print(f"총 개수: {stats['total']:,}")
        print("\n등급 분포:")
        for grade, count in sorted(stats['grade_distribution'].items()):
            print(f"  {grade}: {count}")
        print("\n연도별 분포:")
        for year, count in stats['yearly_distribution'].items():
            print(f"  {year}: {count}")
    else:
        await calculator.calculate(year=args.year, sample=args.sample)


if __name__ == '__main__':
    asyncio.run(main())
