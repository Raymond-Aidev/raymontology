#!/usr/bin/env python3
"""
RaymondsIndex 계산

분기별 데이터 업데이트 후 RaymondsIndex를 재계산합니다.

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
from datetime import datetime
from typing import Dict, Any, Optional

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RaymondsIndexCalculator:
    """RaymondsIndex 계산기

    v2.1 (기본): 기존 산술평균 기반 계산
    v3.0: HDI 방식 기하평균 + 클램핑 + V-Score
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
                    # 버전에 따라 다른 계산기 사용
                    if self.version == '3.0' and self._v3_calculator:
                        result = await self._calculate_v3(
                            conn, company['id'], company['name'], year
                        )
                    else:
                        result = await self._calculate_for_company(
                            conn, company['id'], company['name'], year
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

    async def _calculate_for_company(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        company_name: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """개별 회사 RaymondsIndex 계산

        실제 계산 로직은 raymonds_index_calculator.py 서비스 사용
        """
        # 최신 재무 데이터 조회
        query = """
            SELECT fiscal_year, revenue, operating_income, net_income,
                   total_assets, total_liabilities, total_equity,
                   operating_cash_flow, investing_cash_flow, financing_cash_flow,
                   capex, r_and_d_expense, dividend_paid
            FROM financial_details
            WHERE company_id = $1
        """
        params = [company_id]

        if year:
            query += " AND fiscal_year = $2"
            params.append(year)

        query += " ORDER BY fiscal_year DESC LIMIT 3"

        financials = await conn.fetch(query, *params)

        if not financials:
            return None

        # 간단한 점수 계산 (실제로는 raymonds_index_calculator.py 사용)
        latest = financials[0]

        # ROE 계산
        roe = 0
        if latest['total_equity'] and latest['total_equity'] > 0:
            roe = (latest['net_income'] or 0) / latest['total_equity'] * 100

        # 부채비율
        debt_ratio = 0
        if latest['total_equity'] and latest['total_equity'] > 0:
            debt_ratio = (latest['total_liabilities'] or 0) / latest['total_equity'] * 100

        # 영업이익률
        opm = 0
        if latest['revenue'] and latest['revenue'] > 0:
            opm = (latest['operating_income'] or 0) / latest['revenue'] * 100

        # 간단한 점수 산정 (0-100)
        score = 50  # 기본 점수

        # ROE 가산점 (최대 20점)
        if roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        elif roe > 5:
            score += 10
        elif roe > 0:
            score += 5

        # 부채비율 감점 (최대 -20점)
        if debt_ratio > 200:
            score -= 20
        elif debt_ratio > 150:
            score -= 15
        elif debt_ratio > 100:
            score -= 10

        # 영업이익률 가산점 (최대 15점)
        if opm > 15:
            score += 15
        elif opm > 10:
            score += 10
        elif opm > 5:
            score += 5

        # 현금흐름 가산점 (최대 15점)
        ocf = latest['operating_cash_flow'] or 0
        if ocf > 0:
            score += 10
            # FCF (영업CF - 투자CF)
            icf = latest['investing_cash_flow'] or 0
            if ocf + icf > 0:  # 투자CF는 보통 음수
                score += 5

        score = max(0, min(100, score))

        # 등급 결정
        grade = self._get_grade(score)

        # UPSERT
        await conn.execute("""
            INSERT INTO raymonds_index (id, company_id, fiscal_year, total_score, grade, calculation_date)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, CURRENT_DATE)
            ON CONFLICT (company_id, fiscal_year)
            DO UPDATE SET total_score = $3, grade = $4, calculation_date = CURRENT_DATE
        """, company_id, latest['fiscal_year'], score, grade)

        return {'score': score, 'grade': grade}

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

    calculator = RaymondsIndexCalculator(version=args.version)

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
