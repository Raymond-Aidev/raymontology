"""
4대 인덱스 피처 추출 (I01-I04)

RaymondsIndex 테이블에서 CEI, CGI, RII, MAI 점수 조회
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class IndexFeatureExtractor:
    """4대 인덱스 피처 추출기 (4개 피처)"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def extract(self, company_id: str, year: int = 2024) -> Dict[str, Optional[float]]:
        """기업의 4대 인덱스 피처 4개 추출"""
        result = self.conn.execute(text("""
            SELECT cei_score, cgi_score, rii_score, mai_score
            FROM raymonds_index
            WHERE company_id = :cid
              AND fiscal_year = :year
            LIMIT 1
        """), {'cid': company_id, 'year': year}).fetchone()

        if result:
            return {
                'cei_score': round(float(result.cei_score), 2) if result.cei_score else None,
                'cgi_score': round(float(result.cgi_score), 2) if result.cgi_score else None,
                'rii_score': round(float(result.rii_score), 2) if result.rii_score else None,
                'mai_score': round(float(result.mai_score), 2) if result.mai_score else None,
            }

        return {
            'cei_score': None,
            'cgi_score': None,
            'rii_score': None,
            'mai_score': None,
        }
