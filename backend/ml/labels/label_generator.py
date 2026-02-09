"""
라벨 생성 모듈 (Phase 3)

Temporal Split: 2024년 피처 → 2025년 라벨
악화 이벤트를 식별하여 이진 라벨(Y=0/1) 생성

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.labels.label_generator
    DATABASE_URL="postgresql://..." python -m ml.labels.label_generator --dry-run
"""

import argparse
import logging
import os
import sys
from typing import Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ml.config import DEFAULT_LABEL_CONFIG, LabelConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LabelGenerator:
    """
    악화 이벤트 기반 이진 라벨 생성기
    
    라벨 유형 (v2.0):
    1. suspension_type_a: 거래정지 (재무악화) - weight 1.0
    2. index_drop: RaymondsIndex 20%+ 하락 - weight 0.4
    3. consecutive_loss: 연속 적자 (2년+) - weight 0.3
    
    이진 라벨: 가중합 >= 0.5 → Y=1 (양성)
    """

    def __init__(self, conn, config: LabelConfig = None):
        self.conn = conn
        self.config = config or DEFAULT_LABEL_CONFIG

    def generate_label(self, company_id: str) -> Dict:
        """
        단일 기업의 라벨 생성
        
        Returns:
            {
                'label': 0 or 1,
                'label_score': float (0.0~1.0),
                'events': {'suspension': bool, 'index_drop': bool, 'consecutive_loss': bool},
                'event_weights': {event_name: weight},
            }
        """
        events = {}
        weights = {}
        
        # 1. 거래정지 (TYPE_A: 재무악화)
        is_suspended = self._check_suspension_type_a(company_id)
        events['suspension'] = is_suspended
        if is_suspended:
            weights['suspension'] = self.config.event_weights.get('suspension_type_a', 1.0)
        
        # 2. RaymondsIndex 급락 (20%+)
        is_index_drop = self._check_index_drop(company_id)
        events['index_drop'] = is_index_drop
        if is_index_drop:
            weights['index_drop'] = self.config.event_weights.get('index_drop', 0.4)
        
        # 3. 연속 적자 (2년+)
        is_consecutive_loss = self._check_consecutive_loss(company_id)
        events['consecutive_loss'] = is_consecutive_loss
        if is_consecutive_loss:
            weights['consecutive_loss'] = self.config.event_weights.get('consecutive_loss', 0.3)
        
        # 가중합 계산
        label_score = sum(weights.values())
        label = 1 if label_score >= 0.5 else 0
        
        return {
            'label': label,
            'label_score': round(label_score, 4),
            'events': events,
            'event_weights': weights,
        }

    def _check_suspension_type_a(self, company_id: str) -> bool:
        """거래정지 (재무악화) 여부 확인"""
        result = self.conn.execute(text("""
            SELECT 1 FROM suspension_classifications
            WHERE company_id = :cid
              AND suspension_type = 'TYPE_A'
        """), {'cid': company_id}).fetchone()
        return result is not None

    def _check_index_drop(self, company_id: str) -> bool:
        """RaymondsIndex 20%+ 하락 여부 확인 (2024 vs 2023)"""
        result = self.conn.execute(text("""
            WITH yearly_scores AS (
                SELECT fiscal_year, total_score
                FROM raymonds_index
                WHERE company_id = :cid
                  AND fiscal_year IN (2023, 2024)
            )
            SELECT
                CASE 
                    WHEN COUNT(*) = 2 AND 
                         (MAX(CASE WHEN fiscal_year = 2024 THEN total_score END) - 
                          MAX(CASE WHEN fiscal_year = 2023 THEN total_score END)) /
                         NULLIF(MAX(CASE WHEN fiscal_year = 2023 THEN total_score END), 0) <= -0.20
                    THEN 1
                    ELSE 0
                END as is_drop
            FROM yearly_scores
        """), {'cid': company_id}).scalar()
        return result == 1 if result else False

    def _check_consecutive_loss(self, company_id: str) -> bool:
        """연속 적자 (2년+) 여부 확인 (2023, 2024)"""
        result = self.conn.execute(text("""
            SELECT COUNT(*)
            FROM financial_statements
            WHERE company_id = :cid
              AND fiscal_year IN (2023, 2024)
              AND net_income < 0
        """), {'cid': company_id}).scalar()
        return result >= 2 if result else False


def run_label_generation(dry_run: bool = False):
    """전체 기업 라벨 생성"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)

    with engine.connect() as conn:
        generator = LabelGenerator(conn)

        # 대상 기업 조회 (LISTED + TYPE_A SUSPENDED)
        companies = conn.execute(text("""
            SELECT c.id, c.name, c.ticker, c.trading_status
            FROM companies c
            WHERE c.listing_status = 'LISTED'
              AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
            UNION ALL
            SELECT c.id, c.name, c.ticker, c.trading_status
            FROM companies c
            JOIN suspension_classifications sc ON sc.company_id = c.id
            WHERE c.trading_status = 'SUSPENDED'
              AND sc.suspension_type = 'TYPE_A'
              AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
            ORDER BY ticker
        """)).fetchall()

        total = len(companies)
        logger.info(f"라벨 생성 대상: {total}개 기업")

        # 라벨 통계
        positive_count = 0
        negative_count = 0
        event_counts = {'suspension': 0, 'index_drop': 0, 'consecutive_loss': 0}

        for i, company in enumerate(companies):
            try:
                result = generator.generate_label(str(company.id))
                
                if result['label'] == 1:
                    positive_count += 1
                else:
                    negative_count += 1
                
                for event, occurred in result['events'].items():
                    if occurred:
                        event_counts[event] += 1

                if (i + 1) % 500 == 0:
                    logger.info(f"  진행: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

            except Exception as e:
                logger.warning(f"  실패: {company.name} ({company.ticker}) - {type(e).__name__}")
                try:
                    conn.rollback()
                except:
                    pass

        # 결과 보고
        logger.info("=" * 60)
        logger.info("라벨 생성 완료 보고서")
        logger.info("=" * 60)
        logger.info(f"  대상: {total}개 기업")
        logger.info(f"  양성 (Y=1): {positive_count}개 ({positive_count/max(total,1)*100:.1f}%)")
        logger.info(f"  음성 (Y=0): {negative_count}개 ({negative_count/max(total,1)*100:.1f}%)")
        logger.info("")
        logger.info("이벤트별 발생 건수:")
        for event, count in event_counts.items():
            logger.info(f"  {event:30s}: {count:5d}건 ({count/max(total,1)*100:.1f}%)")

        if dry_run:
            logger.info("\n[DRY-RUN] 라벨 저장 없이 종료합니다.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='라벨 생성기 (Phase 3)')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 결과만 확인')
    args = parser.parse_args()

    run_label_generation(dry_run=args.dry_run)
