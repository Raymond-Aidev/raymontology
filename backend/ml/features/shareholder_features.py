"""
대주주 피처 추출 (S01-S04)

최대주주 지분율, 지분변동, 특수관계인 분석
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class ShareholderFeatureExtractor:
    """대주주 피처 추출기 (4개 피처)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str) -> Dict[str, Optional[float]]:
        """기업의 대주주 피처 4개 추출"""
        features = {}

        # S01: largest_shareholder_ratio - 최대주주 지분율
        features['largest_shareholder_ratio'] = self._largest_shareholder_ratio(company_id)

        # S02: shareholder_change_1y - 지분 변동폭 (1년)
        features['shareholder_change_1y'] = self._shareholder_change_1y(company_id)

        # S03: related_party_ratio - 특수관계인 지분율
        features['related_party_ratio'] = self._related_party_ratio(company_id)

        # S04: shareholder_count - 주요주주 수 (5%+)
        features['shareholder_count'] = self._shareholder_count(company_id)

        return features

    def _largest_shareholder_ratio(self, company_id: str) -> Optional[float]:
        """S01: 최대주주 지분율 (%)"""
        result = self.conn.execute(text("""
            SELECT share_ratio
            FROM major_shareholders
            WHERE company_id = :cid
              AND is_largest_shareholder = TRUE
            ORDER BY report_date DESC NULLS LAST
            LIMIT 1
        """), {'cid': company_id}).scalar()
        return round(float(result), 2) if result else None

    def _shareholder_change_1y(self, company_id: str) -> Optional[float]:
        """S02: 최대주주 지분 변동폭 (current - previous, %p)

        이전 보고서에서 직접 조회하여 계산 (previous_share_ratio 컬럼 미사용)
        """
        result = self.conn.execute(text("""
            WITH ranked_reports AS (
                SELECT
                    share_ratio,
                    report_date,
                    ROW_NUMBER() OVER (ORDER BY report_date DESC) as rn
                FROM major_shareholders
                WHERE company_id = :cid
                  AND is_largest_shareholder = TRUE
                  AND share_ratio IS NOT NULL
            )
            SELECT
                curr.share_ratio - prev.share_ratio as change_1y
            FROM ranked_reports curr
            JOIN ranked_reports prev ON prev.rn = 2
            WHERE curr.rn = 1
        """), {'cid': company_id}).scalar()
        return round(float(result), 2) if result else None

    def _related_party_ratio(self, company_id: str) -> Optional[float]:
        """S03: 특수관계인 전체 지분율 합계 (is_related_party 컬럼 기반)"""
        result = self.conn.execute(text("""
            SELECT SUM(share_ratio)
            FROM major_shareholders
            WHERE company_id = :cid
              AND is_related_party = TRUE
              AND report_date = (
                  SELECT MAX(report_date) FROM major_shareholders WHERE company_id = :cid
              )
        """), {'cid': company_id}).scalar()
        return round(float(result), 2) if result else None

    def _shareholder_count(self, company_id: str) -> Optional[int]:
        """S04: 5% 이상 지분 보유 주요주주 수"""
        result = self.conn.execute(text("""
            SELECT COUNT(DISTINCT shareholder_name)
            FROM major_shareholders
            WHERE company_id = :cid
              AND share_ratio >= 5
              AND report_date = (
                  SELECT MAX(report_date) FROM major_shareholders WHERE company_id = :cid
              )
        """), {'cid': company_id}).scalar()
        return result or 0
