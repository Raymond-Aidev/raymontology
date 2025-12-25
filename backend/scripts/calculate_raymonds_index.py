#!/usr/bin/env python3
"""
RaymondsIndex 배치 계산 스크립트

financial_details 테이블의 데이터를 기반으로
raymonds_index 테이블에 계산 결과를 저장합니다.

사용법:
    python scripts/calculate_raymonds_index.py --limit 100  # 100개 회사만
    python scripts/calculate_raymonds_index.py              # 전체 회사
    python scripts/calculate_raymonds_index.py --company "삼성전자"  # 특정 회사
    python scripts/calculate_raymonds_index.py --year 2024  # 특정 연도
"""
import asyncio
import asyncpg
import argparse
import logging
import sys
import os
import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional
import uuid

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.raymonds_index_calculator import RaymondsIndexCalculator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/calculate_raymonds_index_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)


class RaymondsIndexBatchCalculator:
    """RaymondsIndex 배치 계산기"""

    def __init__(self, db_url: str):
        self.db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.calculator = RaymondsIndexCalculator()
        self.stats = {
            'total': 0,
            'processed': 0,
            'calculated': 0,
            'saved': 0,
            'skipped': 0,
            'errors': 0
        }

    async def get_companies_with_data(
        self,
        conn,
        limit: Optional[int] = None,
        company_name: Optional[str] = None
    ) -> List[Dict]:
        """재무 데이터가 있는 회사 목록 조회"""
        query = """
            SELECT DISTINCT
                c.id,
                c.name,
                c.ticker,
                c.market
            FROM companies c
            INNER JOIN financial_details fd ON fd.company_id = c.id
            WHERE 1=1
        """
        params = []

        if company_name:
            query += f" AND c.name LIKE $1"
            params.append(f"%{company_name}%")

        query += " ORDER BY c.name"

        if limit:
            query += f" LIMIT {limit}"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def get_financial_data(
        self,
        conn,
        company_id: str,
        target_year: Optional[int] = None
    ) -> List[Dict]:
        """회사의 재무 데이터 조회 (최근 3년)"""
        if target_year:
            years = [target_year - 2, target_year - 1, target_year]
        else:
            years = None

        query = """
            SELECT
                fiscal_year, fiscal_quarter, fs_type,
                -- 재무상태표
                cash_and_equivalents, short_term_investments, trade_and_other_receivables,
                inventories, tangible_assets, intangible_assets,
                total_assets, current_liabilities, non_current_liabilities,
                total_liabilities, total_equity,
                -- 손익계산서
                revenue, cost_of_sales, selling_admin_expenses,
                operating_income, net_income,
                -- 현금흐름표
                operating_cash_flow, investing_cash_flow, financing_cash_flow,
                capex, intangible_acquisition, dividend_paid,
                treasury_stock_acquisition, stock_issuance, bond_issuance
            FROM financial_details
            WHERE company_id = $1
              AND fiscal_quarter IS NULL  -- 연간 데이터만
        """
        params = [uuid.UUID(company_id)]

        if years:
            query += f" AND fiscal_year IN ({', '.join(map(str, years))})"

        query += " ORDER BY fiscal_year"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """값을 범위 내로 제한 (DB overflow 방지)"""
        if value is None:
            return None
        return max(min_val, min(max_val, value))

    async def save_raymonds_index(self, conn, result_dict: Dict) -> bool:
        """계산 결과 저장"""
        try:
            await conn.execute("""
                INSERT INTO raymonds_index (
                    id, company_id, calculation_date, fiscal_year,
                    total_score, grade,
                    cei_score, rii_score, cgi_score, mai_score,
                    investment_gap, cash_cagr, capex_growth, idle_cash_ratio,
                    asset_turnover, reinvestment_rate, shareholder_return,
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
                    $17, $18,
                    $19, $20, $21, $22,
                    $23, NOW()
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
                self._clamp(result_dict['cei_score'], 0, 100),
                self._clamp(result_dict['rii_score'], 0, 100),
                self._clamp(result_dict['cgi_score'], 0, 100),
                self._clamp(result_dict['mai_score'], 0, 100),
                self._clamp(result_dict['investment_gap'], -999, 999),  # DECIMAL(6,2)
                self._clamp(result_dict['cash_cagr'], -999, 999),
                self._clamp(result_dict['capex_growth'], -999, 999),
                self._clamp(result_dict['idle_cash_ratio'], 0, 100),
                self._clamp(result_dict['asset_turnover'], 0, 99.999),  # DECIMAL(5,3)
                self._clamp(result_dict['reinvestment_rate'], 0, 100),
                self._clamp(result_dict['shareholder_return'], 0, 100),
                json.dumps(result_dict['red_flags'], ensure_ascii=False),
                json.dumps(result_dict['yellow_flags'], ensure_ascii=False),
                result_dict['verdict'],
                result_dict['key_risk'],
                result_dict['recommendation'],
                result_dict['watch_trigger'],
                result_dict['data_quality_score']
            )
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    async def run(
        self,
        limit: Optional[int] = None,
        company_name: Optional[str] = None,
        target_year: Optional[int] = None
    ):
        """배치 계산 실행"""
        conn = await asyncpg.connect(self.db_url)

        try:
            # 1. 대상 회사 목록 조회
            companies = await self.get_companies_with_data(conn, limit, company_name)
            self.stats['total'] = len(companies)

            logger.info("=" * 80)
            logger.info("RaymondsIndex 배치 계산 시작")
            logger.info("=" * 80)
            logger.info(f"대상 회사: {self.stats['total']}개")
            if target_year:
                logger.info(f"계산 연도: {target_year}")
            logger.info("=" * 80)

            # 2. 회사별 계산
            for company in companies:
                self.stats['processed'] += 1
                company_id = str(company['id'])

                try:
                    # 재무 데이터 조회
                    financial_data = await self.get_financial_data(
                        conn, company_id, target_year
                    )

                    if len(financial_data) < 2:
                        self.stats['skipped'] += 1
                        logger.debug(f"Skipped (insufficient data): {company['name']}")
                        continue

                    # RaymondsIndex 계산
                    result = self.calculator.calculate(
                        company_id=company_id,
                        financial_data=financial_data,
                        target_year=target_year
                    )

                    if result is None:
                        self.stats['skipped'] += 1
                        continue

                    self.stats['calculated'] += 1

                    # 결과 저장
                    result_dict = self.calculator.to_dict(result)
                    success = await self.save_raymonds_index(conn, result_dict)

                    if success:
                        self.stats['saved'] += 1
                        logger.info(
                            f"[{self.stats['processed']}/{self.stats['total']}] "
                            f"{company['name']}: {result.grade} ({result.total_score:.1f}점) "
                            f"투자괴리율: {result.core_metrics.investment_gap:.1f}%"
                        )

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing {company['name']}: {e}")

                # 진행 상황 로깅
                if self.stats['processed'] % 100 == 0:
                    logger.info(
                        f"Progress: {self.stats['processed']}/{self.stats['total']} "
                        f"(Saved: {self.stats['saved']}, Errors: {self.stats['errors']})"
                    )

            # 3. 결과 출력
            logger.info("=" * 80)
            logger.info("계산 완료")
            logger.info("=" * 80)
            logger.info(f"처리: {self.stats['processed']}/{self.stats['total']}")
            logger.info(f"계산: {self.stats['calculated']}건")
            logger.info(f"저장: {self.stats['saved']}건")
            logger.info(f"건너뜀: {self.stats['skipped']}건")
            logger.info(f"오류: {self.stats['errors']}건")
            logger.info("=" * 80)

        finally:
            await conn.close()


async def show_statistics():
    """통계 조회"""
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 등급별 분포
        grade_dist = await conn.fetch("""
            SELECT grade, COUNT(*) as cnt
            FROM raymonds_index
            GROUP BY grade
            ORDER BY grade
        """)

        logger.info("\n[RaymondsIndex 등급 분포]")
        for row in grade_dist:
            logger.info(f"  {row['grade']}: {row['cnt']:,}건")

        # 점수 통계
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                ROUND(AVG(total_score)::numeric, 2) as avg_score,
                ROUND(MIN(total_score)::numeric, 2) as min_score,
                ROUND(MAX(total_score)::numeric, 2) as max_score,
                ROUND(AVG(investment_gap)::numeric, 2) as avg_gap
            FROM raymonds_index
        """)

        if stats:
            logger.info("\n[점수 통계]")
            logger.info(f"  총 레코드: {stats['total']:,}건")
            logger.info(f"  평균 점수: {stats['avg_score']}")
            logger.info(f"  점수 범위: {stats['min_score']} ~ {stats['max_score']}")
            logger.info(f"  평균 투자괴리율: {stats['avg_gap']}%")

        # Top 10
        top10 = await conn.fetch("""
            SELECT
                ri.total_score, ri.grade, ri.investment_gap,
                c.name, c.market
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            ORDER BY ri.total_score DESC
            LIMIT 10
        """)

        logger.info("\n[Top 10 기업]")
        for i, row in enumerate(top10, 1):
            logger.info(
                f"  {i}. {row['name']} ({row['market']}): "
                f"{row['grade']} ({row['total_score']:.1f}점) "
                f"투자괴리: {row['investment_gap']:.1f}%"
            )

    finally:
        await conn.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='RaymondsIndex 배치 계산')
    parser.add_argument('--limit', type=int, help='계산할 회사 수 제한')
    parser.add_argument('--company', type=str, help='특정 회사명 (부분 일치)')
    parser.add_argument('--year', type=int, help='계산 대상 연도')
    parser.add_argument('--stats-only', action='store_true', help='통계만 조회')

    args = parser.parse_args()

    # 로그 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)

    if args.stats_only:
        asyncio.run(show_statistics())
        return

    # 계산 실행
    calculator = RaymondsIndexBatchCalculator(DATABASE_URL)
    asyncio.run(calculator.run(
        limit=args.limit,
        company_name=args.company,
        target_year=args.year
    ))

    # 통계 조회
    asyncio.run(show_statistics())


if __name__ == "__main__":
    main()
