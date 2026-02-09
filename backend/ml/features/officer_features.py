"""
임원 네트워크 피처 추출 (E01-E10)

PostgreSQL 기반 구현 (Neo4j fallback 대신 직접 쿼리)
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class OfficerFeatureExtractor:
    """임원 네트워크 피처 추출기 (10개 피처)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str) -> Dict[str, Optional[float]]:
        """기업의 임원 네트워크 피처 10개 추출"""
        features = {}

        # E01: exec_count - 임원 수
        features['exec_count'] = self._exec_count(company_id)

        # E02: exec_turnover_rate - 임원 이직률 (proxy)
        features['exec_turnover_rate'] = self._exec_turnover_rate(company_id)

        # E03: exec_avg_tenure - 평균 재직 기간(월)
        features['exec_avg_tenure'] = self._exec_avg_tenure(company_id)

        # E04-E05: 타사 재직 관련
        e04, e05 = self._exec_other_companies(company_id)
        features['exec_other_company_count'] = e04  # E04: 타사 재직 건수 합계
        features['exec_avg_other_companies'] = e05  # E05: 임원당 평균 타사 재직

        # E06: exec_delisted_connection - 상장폐지/거래정지 기업 연결 수
        features['exec_delisted_connection'] = self._exec_delisted_connection(company_id)

        # E07: exec_managed_connection - 관리종목 기업 연결 수
        features['exec_managed_connection'] = self._exec_managed_connection(company_id)

        # E08: exec_concurrent_positions - 겸직 임원 수
        features['exec_concurrent_positions'] = self._exec_concurrent_positions(company_id)

        # E09: exec_network_density - 네트워크 밀도
        features['exec_network_density'] = self._exec_network_density(company_id)

        # E10: exec_high_risk_ratio - 고위험 임원 비율
        features['exec_high_risk_ratio'] = self._exec_high_risk_ratio(company_id)

        return features

    def _exec_count(self, company_id: str) -> Optional[int]:
        """E01: 현재 재직 중인 임원 수"""
        result = self.conn.execute(text("""
            SELECT COUNT(DISTINCT officer_id)
            FROM officer_positions
            WHERE company_id = :cid AND is_current = TRUE
        """), {'cid': company_id}).scalar()
        return result

    def _exec_turnover_rate(self, company_id: str) -> Optional[float]:
        """E02: 임원 이직률 (퇴임 임원 / 전체 임원) proxy"""
        # term_end_date가 48%만 존재하므로, is_current=FALSE 비율로 proxy
        result = self.conn.execute(text("""
            SELECT
                COUNT(CASE WHEN is_current = FALSE THEN 1 END)::float /
                NULLIF(COUNT(*), 0)
            FROM officer_positions
            WHERE company_id = :cid
        """), {'cid': company_id}).scalar()
        return round(float(result), 4) if result else 0.0

    def _exec_avg_tenure(self, company_id: str) -> Optional[float]:
        """E03: 평균 재직 기간(월)

        1순위: term_start_date가 있는 경우 직접 계산
        2순위: term_start_date가 없으면 earliest disclosure date를 proxy로 사용
        """
        # 1순위: term_start_date 기반 계산
        result = self.conn.execute(text("""
            SELECT AVG(
                (COALESCE(term_end_date, CURRENT_DATE) - term_start_date) / 30.44
            )
            FROM officer_positions
            WHERE company_id = :cid
              AND term_start_date IS NOT NULL
              AND is_current = TRUE
        """), {'cid': company_id}).scalar()

        if result:
            return round(float(result), 2)

        # 2순위: Fallback - 가장 오래된 공시일 기반 추정
        # officer_positions의 created_at 또는 source_rcept_no 기반 추정
        result = self.conn.execute(text("""
            WITH officer_earliest AS (
                SELECT
                    officer_id,
                    MIN(created_at) as earliest_seen
                FROM officer_positions
                WHERE company_id = :cid
                  AND is_current = TRUE
                GROUP BY officer_id
            )
            SELECT AVG(
                (CURRENT_DATE - earliest_seen::date) / 30.44
            )
            FROM officer_earliest
            WHERE earliest_seen IS NOT NULL
        """), {'cid': company_id}).scalar()

        return round(float(result), 2) if result else None

    def _exec_other_companies(self, company_id: str) -> tuple:
        """E04, E05: 타사 재직 건수 (PostgreSQL fallback)"""
        # 해당 기업 임원들이 다른 기업에서 재직한 건수
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            )
            SELECT
                COUNT(DISTINCT op2.company_id) - 1 as total_other,  -- 자기 기업 제외
                COUNT(DISTINCT co.officer_id) as officer_count
            FROM company_officers co
            JOIN officer_positions op2 ON op2.officer_id = co.officer_id
        """), {'cid': company_id}).fetchone()

        if result and result.officer_count and result.officer_count > 0:
            total_other = max(0, result.total_other or 0)
            avg_other = round(total_other / result.officer_count, 2)
            return total_other, avg_other
        return 0, 0.0

    def _exec_delisted_connection(self, company_id: str) -> Optional[int]:
        """E06: 임원이 재직했던 상장폐지/거래정지 기업 수"""
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            )
            SELECT COUNT(DISTINCT c.id)
            FROM company_officers co
            JOIN officer_positions op2 ON op2.officer_id = co.officer_id
            JOIN companies c ON c.id = op2.company_id
            WHERE c.id != :cid
              AND (c.trading_status = 'SUSPENDED' OR c.listing_status = 'DELISTED')
        """), {'cid': company_id}).scalar()
        return result

    def _exec_managed_connection(self, company_id: str) -> Optional[int]:
        """E07: 임원이 재직했던 관리종목 기업 수"""
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            )
            SELECT COUNT(DISTINCT c.id)
            FROM company_officers co
            JOIN officer_positions op2 ON op2.officer_id = co.officer_id
            JOIN companies c ON c.id = op2.company_id
            WHERE c.id != :cid
              AND c.is_managed = 'Y'
        """), {'cid': company_id}).scalar()
        return result

    def _exec_concurrent_positions(self, company_id: str) -> Optional[int]:
        """E08: 현재 타사 겸직 중인 임원 수"""
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            )
            SELECT COUNT(DISTINCT co.officer_id)
            FROM company_officers co
            WHERE EXISTS (
                SELECT 1 FROM officer_positions op2
                WHERE op2.officer_id = co.officer_id
                  AND op2.company_id != :cid
                  AND op2.is_current = TRUE
            )
        """), {'cid': company_id}).scalar()
        return result

    def _exec_network_density(self, company_id: str) -> Optional[float]:
        """E09: 네트워크 밀도 (근사치) = 연결된 고유 기업 수 / 가능한 최대 연결"""
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            ),
            connections AS (
                SELECT COUNT(DISTINCT op2.company_id) - 1 as connected_companies,
                       COUNT(DISTINCT co.officer_id) as officer_count
                FROM company_officers co
                JOIN officer_positions op2 ON op2.officer_id = co.officer_id
            )
            SELECT
                CASE WHEN officer_count > 0
                    THEN connected_companies::float / (officer_count * 10)  -- 정규화 (max ~10 companies per officer)
                    ELSE 0
                END
            FROM connections
        """), {'cid': company_id}).scalar()
        return round(min(float(result or 0), 1.0), 4)

    def _exec_high_risk_ratio(self, company_id: str) -> Optional[float]:
        """E10: 고위험 임원 비율 (타사 5개사+ 재직)"""
        result = self.conn.execute(text("""
            WITH company_officers AS (
                SELECT DISTINCT officer_id
                FROM officer_positions
                WHERE company_id = :cid AND is_current = TRUE
            ),
            officer_company_counts AS (
                SELECT co.officer_id,
                       COUNT(DISTINCT op2.company_id) - 1 as other_companies
                FROM company_officers co
                JOIN officer_positions op2 ON op2.officer_id = co.officer_id
                GROUP BY co.officer_id
            )
            SELECT
                COUNT(CASE WHEN other_companies >= 5 THEN 1 END)::float /
                NULLIF(COUNT(*), 0)
            FROM officer_company_counts
        """), {'cid': company_id}).scalar()
        return round(float(result or 0), 4)
