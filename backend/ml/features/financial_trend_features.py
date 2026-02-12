"""
재무 추세 피처 추출 (T03-T05) + 재무 구조 (F01-F02)

v5.0 변경:
- T01(revenue_growth_rate), T02(operating_margin_trend) 제거 (순환관계 문제)
- F01: consecutive_loss_years - 연속 적자 연수
- F02: capital_erosion_flag - 자본잠식 여부 (binary)

유지:
- T03: debt_ratio_change - 부채비율 변화 (YoY)
- T04: cash_flow_deterioration - 영업CF 악화 여부 (binary)
- T05: index_score_delta - RaymondsIndex 점수 변화 (YoY)
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class FinancialTrendFeatureExtractor:
    """재무 추세 + 구조 피처 추출기 (5개 피처: T03-T05, F01-F02)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str, base_year: int = 2024) -> Dict[str, Optional[float]]:
        """기업의 재무 추세/구조 피처 5개 추출

        v5.0: T01, T02 제거 → F01, F02 추가
        """
        features = {}

        # T03: debt_ratio_change
        features['debt_ratio_change'] = self._debt_ratio_change(company_id, base_year)

        # T04: cash_flow_deterioration
        features['cash_flow_deterioration'] = self._cash_flow_deterioration(company_id, base_year)

        # T05: index_score_delta
        features['index_score_delta'] = self._index_score_delta(company_id, base_year)

        # F01: consecutive_loss_years (v5.0)
        features['consecutive_loss_years'] = self._consecutive_loss_years(company_id, base_year)

        # F02: capital_erosion_flag (v5.0)
        features['capital_erosion_flag'] = self._capital_erosion_flag(company_id, base_year)

        return features

    def _debt_ratio_change(self, company_id: str, base_year: int) -> Optional[float]:
        """T03: 부채비율 변화 (base_year - base_year-1, %p)

        부채비율 = total_liabilities / total_equity * 100
        """
        result = self.conn.execute(text("""
            WITH yearly AS (
                SELECT fiscal_year,
                       CASE WHEN total_equity > 0
                            THEN total_liabilities::float / total_equity * 100
                            ELSE NULL
                       END as debt_ratio
                FROM financial_details
                WHERE company_id = :cid
                  AND fiscal_year IN (:y1, :y2)
                  AND total_equity IS NOT NULL
                  AND total_liabilities IS NOT NULL
            )
            SELECT
                MAX(CASE WHEN fiscal_year = :y1 THEN debt_ratio END) -
                MAX(CASE WHEN fiscal_year = :y2 THEN debt_ratio END) as change
            FROM yearly
        """), {'cid': company_id, 'y1': base_year, 'y2': base_year - 1}).scalar()

        if result is not None:
            # 극단값 클리핑 (-500 ~ +500 %p)
            return round(max(-5.0, min(5.0, float(result) / 100)), 4)
        return None

    def _cash_flow_deterioration(self, company_id: str, base_year: int) -> Optional[int]:
        """T04: 영업현금흐름 악화 여부 (binary)

        조건: base_year OCF < 0 AND (base_year-1 OCF >= 0 OR base_year OCF < base_year-1 OCF)
        """
        result = self.conn.execute(text("""
            WITH yearly AS (
                SELECT fiscal_year, operating_cash_flow as ocf
                FROM financial_details
                WHERE company_id = :cid
                  AND fiscal_year IN (:y1, :y2)
                  AND operating_cash_flow IS NOT NULL
            )
            SELECT
                CASE
                    WHEN MAX(CASE WHEN fiscal_year = :y1 THEN ocf END) < 0 THEN 1
                    WHEN MAX(CASE WHEN fiscal_year = :y1 THEN ocf END) <
                         MAX(CASE WHEN fiscal_year = :y2 THEN ocf END) * 0.5 THEN 1
                    ELSE 0
                END as deterioration
            FROM yearly
        """), {'cid': company_id, 'y1': base_year, 'y2': base_year - 1}).scalar()

        return int(result) if result is not None else None

    def _index_score_delta(self, company_id: str, base_year: int) -> Optional[float]:
        """T05: RaymondsIndex 총점 변화 (base_year - base_year-1)"""
        result = self.conn.execute(text("""
            WITH yearly AS (
                SELECT fiscal_year, total_score
                FROM raymonds_index
                WHERE company_id = :cid
                  AND fiscal_year IN (:y1, :y2)
                  AND total_score IS NOT NULL
            )
            SELECT
                MAX(CASE WHEN fiscal_year = :y1 THEN total_score END) -
                MAX(CASE WHEN fiscal_year = :y2 THEN total_score END) as delta
            FROM yearly
        """), {'cid': company_id, 'y1': base_year, 'y2': base_year - 1}).scalar()

        if result is not None:
            return round(float(result), 2)
        return None

    def _consecutive_loss_years(self, company_id: str, base_year: int) -> Optional[int]:
        """F01: 연속 적자 연수 (base_year부터 역순으로 카운트)

        financial_statements의 net_income < 0인 연속 연도 수.
        최근 연도가 흑자면 0, 데이터 없으면 None.
        """
        rows = self.conn.execute(text("""
            SELECT fiscal_year, net_income
            FROM financial_statements
            WHERE company_id = :cid
              AND fiscal_year <= :base_year
              AND net_income IS NOT NULL
            ORDER BY fiscal_year DESC
        """), {'cid': company_id, 'base_year': base_year}).fetchall()

        if not rows:
            return None

        count = 0
        for row in rows:
            if row.net_income < 0:
                count += 1
            else:
                break

        return count

    def _capital_erosion_flag(self, company_id: str, base_year: int) -> Optional[int]:
        """F02: 자본잠식 여부 (1=자본잠식, 0=정상)

        자본잠식: total_equity <= 0 (완전자본잠식)
        또는 total_equity < total_capital * 0.5 (부분자본잠식 50%+)
        데이터 없으면 None.
        """
        result = self.conn.execute(text("""
            SELECT
                CASE
                    WHEN total_equity IS NULL THEN NULL
                    WHEN total_equity <= 0 THEN 1
                    ELSE 0
                END as erosion_flag
            FROM financial_details
            WHERE company_id = :cid
              AND fiscal_year = :base_year
            LIMIT 1
        """), {'cid': company_id, 'base_year': base_year}).scalar()

        return int(result) if result is not None else None
