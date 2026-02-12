"""
거버넌스 피처 추출 (G01-G03) + 확장 (G04-G05)

v5.0: 거버넌스 확장 2개 추가
- G04: disclosure_decline_flag - 공시 빈도 30%+ 감소 여부 (binary)
- G05: cb_to_equity_ratio - CB 발행총액 / 자기자본 비율

기존:
- G01: disclosure_frequency - 최근 1년 공시 빈도
- G02: egm_flag - 임시주주총회 개최 여부 (binary)
- G03: dispute_officer_flag - 경영분쟁 참여 임원 유무 (binary)
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class GovernanceFeatureExtractor:
    """거버넌스 피처 추출기 (5개 피처: G01-G05)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str, base_year: int = 2024) -> Dict[str, Optional[int]]:
        """기업의 거버넌스 피처 5개 추출

        Args:
            company_id: 기업 ID
            base_year: 기준 연도 (G04 공시 비교, G05 자기자본 기준)
        """
        features = {}

        # G01: disclosure_frequency
        features['disclosure_frequency'] = self._disclosure_frequency(company_id, base_year)

        # G02: egm_flag
        features['egm_flag'] = self._egm_flag(company_id)

        # G03: dispute_officer_flag
        features['dispute_officer_flag'] = self._dispute_officer_flag(company_id)

        # G04: disclosure_decline_flag (v5.0)
        features['disclosure_decline_flag'] = self._disclosure_decline_flag(company_id, base_year)

        # G05: cb_to_equity_ratio (v5.0)
        features['cb_to_equity_ratio'] = self._cb_to_equity_ratio(company_id, base_year)

        return features

    def _disclosure_frequency(self, company_id: str, base_year: int = 2024) -> Optional[int]:
        """G01: 기준연도 공시 횟수

        disclosures 테이블은 corp_code로 연결되므로 companies.dart_code 사용
        """
        y_start = f'{base_year}0101'
        y_end = f'{base_year}1231'

        result = self.conn.execute(text("""
            SELECT COUNT(*) as cnt
            FROM disclosures d
            JOIN companies c ON d.corp_code = c.corp_code
            WHERE c.id = :cid
              AND d.rcept_dt >= :y_start
              AND d.rcept_dt <= :y_end
        """), {'cid': company_id, 'y_start': y_start, 'y_end': y_end}).scalar()

        return int(result) if result is not None else 0

    def _egm_flag(self, company_id: str) -> Optional[int]:
        """G02: 임시주주총회 개최 여부 (1=있음, 0=없음)"""
        result = self.conn.execute(text("""
            SELECT 1
            FROM egm_disclosures
            WHERE company_id = :cid
            LIMIT 1
        """), {'cid': company_id}).fetchone()

        return 1 if result else 0

    def _dispute_officer_flag(self, company_id: str) -> Optional[int]:
        """G03: 경영분쟁 참여 임원 유무 (1=있음, 0=없음)"""
        result = self.conn.execute(text("""
            SELECT 1
            FROM dispute_officers
            WHERE company_id = :cid
            LIMIT 1
        """), {'cid': company_id}).fetchone()

        return 1 if result else 0

    def _disclosure_decline_flag(self, company_id: str, base_year: int) -> Optional[int]:
        """G04: 공시 빈도 30%+ 감소 여부 (1=감소, 0=유지/증가)

        base_year vs base_year-1 공시 건수 비교
        이전 연도 공시가 0건이면 None (비교 불가)
        """
        result = self.conn.execute(text("""
            WITH yearly AS (
                SELECT
                    COUNT(CASE WHEN d.rcept_dt >= :curr_start AND d.rcept_dt <= :curr_end
                               THEN 1 END) as curr_count,
                    COUNT(CASE WHEN d.rcept_dt >= :prev_start AND d.rcept_dt <= :prev_end
                               THEN 1 END) as prev_count
                FROM disclosures d
                JOIN companies c ON d.corp_code = c.corp_code
                WHERE c.id = :cid
                  AND d.rcept_dt >= :prev_start
            )
            SELECT
                CASE
                    WHEN prev_count = 0 THEN NULL
                    WHEN curr_count < prev_count * 0.7 THEN 1
                    ELSE 0
                END as decline_flag
            FROM yearly
        """), {
            'cid': company_id,
            'curr_start': f'{base_year}0101',
            'curr_end': f'{base_year}1231',
            'prev_start': f'{base_year - 1}0101',
            'prev_end': f'{base_year - 1}1231',
        }).scalar()

        return int(result) if result is not None else None

    def _cb_to_equity_ratio(self, company_id: str, base_year: int) -> Optional[float]:
        """G05: CB 발행총액 / 자기자본 비율

        최근 2년 CB 발행 총액을 기준연도 자기자본으로 나눈 비율.
        CB 발행이 없으면 0, 자기자본이 0 이하면 None.
        """
        result = self.conn.execute(text("""
            WITH cb_total AS (
                SELECT COALESCE(SUM(issue_amount), 0) as total_cb
                FROM convertible_bonds
                WHERE company_id = :cid
                  AND issue_date >= :cutoff
            ),
            equity AS (
                SELECT total_equity
                FROM financial_details
                WHERE company_id = :cid
                  AND fiscal_year = :base_year
                  AND total_equity IS NOT NULL
                LIMIT 1
            )
            SELECT
                CASE
                    WHEN e.total_equity IS NULL OR e.total_equity <= 0 THEN NULL
                    WHEN ct.total_cb = 0 THEN 0
                    ELSE ct.total_cb::float / e.total_equity
                END as ratio
            FROM cb_total ct
            CROSS JOIN (SELECT total_equity FROM equity UNION ALL SELECT NULL WHERE NOT EXISTS (SELECT 1 FROM equity)) e
            LIMIT 1
        """), {
            'cid': company_id,
            'base_year': base_year,
            'cutoff': f'{base_year - 1}-01-01',
        }).scalar()

        if result is not None:
            return round(float(result), 4)
        return None
