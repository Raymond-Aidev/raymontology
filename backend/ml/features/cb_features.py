"""
CB 투자자 피처 추출 (C01-C08)

전환사채 발행 및 투자자 네트워크 분석
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class CBFeatureExtractor:
    """CB 투자자 피처 추출기 (8개 피처)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str, reference_date: str = '2024-12-31') -> Dict[str, Optional[float]]:
        """기업의 CB 투자자 피처 8개 추출"""
        features = {}

        # C01: cb_count_1y - CB 발행 횟수 (최근 1년)
        features['cb_count_1y'] = self._cb_count_1y(company_id, reference_date)

        # C02: cb_total_amount_1y - CB 발행 총액 (최근 1년)
        features['cb_total_amount_1y'] = self._cb_total_amount_1y(company_id, reference_date)

        # C03: cb_subscriber_count - CB 참여자 수 (전체 기간)
        features['cb_subscriber_count'] = self._cb_subscriber_count(company_id)

        # C04: cb_high_risk_subscriber_ratio - 고위험 투자자 비율
        features['cb_high_risk_subscriber_ratio'] = self._cb_high_risk_subscriber_ratio(company_id)

        # C05: cb_subscriber_avg_investments - 투자자 평균 투자 건수
        features['cb_subscriber_avg_investments'] = self._cb_subscriber_avg_investments(company_id)

        # C06: cb_loss_company_connections - 적자기업 연결 수
        features['cb_loss_company_connections'] = self._cb_loss_company_connections(company_id)

        # C07: cb_delisted_connections - 상장폐지/거래정지 연결 수
        features['cb_delisted_connections'] = self._cb_delisted_connections(company_id)

        # C08: cb_repeat_subscriber_ratio - 반복 투자자 비율
        features['cb_repeat_subscriber_ratio'] = self._cb_repeat_subscriber_ratio(company_id)

        return features

    def _cb_count_1y(self, company_id: str, reference_date: str) -> Optional[int]:
        """C01: 최근 1년 CB 발행 횟수"""
        result = self.conn.execute(text("""
            SELECT COUNT(*)
            FROM convertible_bonds
            WHERE company_id = :cid
              AND issue_date >= (CAST(:ref_date AS date) - INTERVAL '1 year')
              AND issue_date <= CAST(:ref_date AS date)
        """), {'cid': company_id, 'ref_date': reference_date}).scalar()
        return result or 0

    def _cb_total_amount_1y(self, company_id: str, reference_date: str) -> Optional[int]:
        """C02: 최근 1년 CB 발행 총액 (원)"""
        result = self.conn.execute(text("""
            SELECT COALESCE(SUM(issue_amount), 0)
            FROM convertible_bonds
            WHERE company_id = :cid
              AND issue_date >= (CAST(:ref_date AS date) - INTERVAL '1 year')
              AND issue_date <= CAST(:ref_date AS date)
        """), {'cid': company_id, 'ref_date': reference_date}).scalar()
        return int(result) if result else 0

    def _cb_subscriber_count(self, company_id: str) -> Optional[int]:
        """C03: CB 참여자 수 (전체 기간, 중복 제거)"""
        result = self.conn.execute(text("""
            SELECT COUNT(DISTINCT s.subscriber_name)
            FROM cb_subscribers s
            JOIN convertible_bonds cb ON cb.id = s.cb_id
            WHERE cb.company_id = :cid
        """), {'cid': company_id}).scalar()
        return result or 0

    def _cb_high_risk_subscriber_ratio(self, company_id: str) -> Optional[float]:
        """C04: 고위험 투자자 비율 (적자기업 투자비율 50%+ 투자자 / 전체)"""
        # 해당 기업의 CB 투자자들을 찾고, 그 투자자들이 투자한 다른 기업 중 적자기업 비율이 50%+ 인 투자자
        result = self.conn.execute(text("""
            WITH company_subscribers AS (
                SELECT DISTINCT s.subscriber_name
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON cb.id = s.cb_id
                WHERE cb.company_id = :cid
            ),
            subscriber_portfolios AS (
                SELECT
                    cs.subscriber_name,
                    COUNT(DISTINCT cb2.company_id) as total_investments,
                    COUNT(DISTINCT CASE
                        WHEN fs.net_income < 0 THEN cb2.company_id
                    END) as loss_investments
                FROM company_subscribers cs
                JOIN cb_subscribers s2 ON s2.subscriber_name = cs.subscriber_name
                JOIN convertible_bonds cb2 ON cb2.id = s2.cb_id
                LEFT JOIN financial_statements fs ON fs.company_id = cb2.company_id
                    AND fs.fiscal_year = 2024
                GROUP BY cs.subscriber_name
            )
            SELECT
                COUNT(CASE WHEN total_investments > 0
                    AND loss_investments::float / total_investments >= 0.5
                    THEN 1 END)::float /
                NULLIF(COUNT(*), 0)
            FROM subscriber_portfolios
        """), {'cid': company_id}).scalar()
        return round(float(result or 0), 4)

    def _cb_subscriber_avg_investments(self, company_id: str) -> Optional[float]:
        """C05: CB 참여자들의 평균 타사 투자 건수"""
        result = self.conn.execute(text("""
            WITH company_subscribers AS (
                SELECT DISTINCT s.subscriber_name
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON cb.id = s.cb_id
                WHERE cb.company_id = :cid
            )
            SELECT AVG(sub_count)
            FROM (
                SELECT cs.subscriber_name,
                       COUNT(DISTINCT cb2.company_id) - 1 as sub_count
                FROM company_subscribers cs
                JOIN cb_subscribers s2 ON s2.subscriber_name = cs.subscriber_name
                JOIN convertible_bonds cb2 ON cb2.id = s2.cb_id
                GROUP BY cs.subscriber_name
            ) t
        """), {'cid': company_id}).scalar()
        return round(float(result), 2) if result else 0.0

    def _cb_loss_company_connections(self, company_id: str) -> Optional[int]:
        """C06: CB 투자자들이 투자한 적자기업 수 (중복 제거)"""
        result = self.conn.execute(text("""
            WITH company_subscribers AS (
                SELECT DISTINCT s.subscriber_name
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON cb.id = s.cb_id
                WHERE cb.company_id = :cid
            )
            SELECT COUNT(DISTINCT cb2.company_id)
            FROM company_subscribers cs
            JOIN cb_subscribers s2 ON s2.subscriber_name = cs.subscriber_name
            JOIN convertible_bonds cb2 ON cb2.id = s2.cb_id
            JOIN financial_statements fs ON fs.company_id = cb2.company_id
                AND fs.fiscal_year = 2024
            WHERE fs.net_income < 0
              AND cb2.company_id != :cid
        """), {'cid': company_id}).scalar()
        return result or 0

    def _cb_delisted_connections(self, company_id: str) -> Optional[int]:
        """C07: CB 투자자들이 투자한 상장폐지/거래정지 기업 수"""
        result = self.conn.execute(text("""
            WITH company_subscribers AS (
                SELECT DISTINCT s.subscriber_name
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON cb.id = s.cb_id
                WHERE cb.company_id = :cid
            )
            SELECT COUNT(DISTINCT c.id)
            FROM company_subscribers cs
            JOIN cb_subscribers s2 ON s2.subscriber_name = cs.subscriber_name
            JOIN convertible_bonds cb2 ON cb2.id = s2.cb_id
            JOIN companies c ON c.id = cb2.company_id
            WHERE c.id != :cid
              AND (c.trading_status = 'SUSPENDED' OR c.listing_status = 'DELISTED')
        """), {'cid': company_id}).scalar()
        return result or 0

    def _cb_repeat_subscriber_ratio(self, company_id: str) -> Optional[float]:
        """C08: 반복 투자자 비율 (2회 이상 참여 / 전체)"""
        result = self.conn.execute(text("""
            WITH subscriber_counts AS (
                SELECT s.subscriber_name, COUNT(*) as cb_count
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON cb.id = s.cb_id
                WHERE cb.company_id = :cid
                GROUP BY s.subscriber_name
            )
            SELECT
                COUNT(CASE WHEN cb_count >= 2 THEN 1 END)::float /
                NULLIF(COUNT(*), 0)
            FROM subscriber_counts
        """), {'cid': company_id}).scalar()
        return round(float(result or 0), 4)
