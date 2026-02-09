"""
피처 스토어 - 26개 피처 통합 추출 및 ml_features 테이블 저장

Phase 4: 전체 기업 피처 적재
Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.features.feature_store
    DATABASE_URL="postgresql://..." python -m ml.features.feature_store --sample 10 --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import date
from typing import Dict, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ml.features.officer_features import OfficerFeatureExtractor
from ml.features.cb_features import CBFeatureExtractor
from ml.features.shareholder_features import ShareholderFeatureExtractor
from ml.features.index_features import IndexFeatureExtractor
from ml.config import FEATURE_NAMES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeatureStore:
    """26개 피처 통합 추출 + ml_features 테이블 저장"""

    def __init__(self, conn):
        self.conn = conn
        self.officer_extractor = OfficerFeatureExtractor(conn)
        self.cb_extractor = CBFeatureExtractor(conn)
        self.shareholder_extractor = ShareholderFeatureExtractor(conn)
        self.index_extractor = IndexFeatureExtractor(conn)

    def extract_all_features(self, company_id: str, feature_date: str = '2024-12-31',
                             index_year: int = 2024) -> Dict[str, Optional[float]]:
        """단일 기업의 26개 피처 통합 추출"""
        features = {}

        # [A] 임원 네트워크 (E01-E10)
        features.update(self.officer_extractor.extract(company_id))

        # [B] CB 투자자 (C01-C08)
        features.update(self.cb_extractor.extract(company_id, reference_date=feature_date))

        # [C] 대주주 (S01-S04)
        features.update(self.shareholder_extractor.extract(company_id))

        # [D] 4대 인덱스 (I01-I04)
        features.update(self.index_extractor.extract(company_id, year=index_year))

        return features

    def get_features(self, company_id: str) -> Optional[Dict]:
        """ml_features 테이블에서 최신 피처 조회, 없으면 None"""
        result = self.conn.execute(text("""
            SELECT * FROM ml_features
            WHERE company_id = :cid
            ORDER BY feature_date DESC
            LIMIT 1
        """), {'cid': company_id}).fetchone()

        if result:
            return {name: getattr(result, name, None) for name in FEATURE_NAMES}
        return None

    def save_features(self, company_id: str, features: Dict, feature_date: str):
        """ml_features 테이블에 UPSERT"""
        # 기존 레코드 삭제 후 삽입 (단순 구현)
        self.conn.execute(text("""
            DELETE FROM ml_features
            WHERE company_id = :cid AND feature_date = :fd
        """), {'cid': company_id, 'fd': feature_date})

        columns = ['company_id', 'feature_date'] + FEATURE_NAMES
        values = {'company_id': company_id, 'feature_date': feature_date}
        values.update({name: features.get(name) for name in FEATURE_NAMES})

        placeholders = ', '.join([f':{col}' for col in columns])
        col_names = ', '.join(columns)

        self.conn.execute(
            text(f"INSERT INTO ml_features ({col_names}) VALUES ({placeholders})"),
            values
        )


def get_target_companies(conn, sample: int = None) -> List:
    """피처 추출 대상 기업 조회 (LISTED + SUSPENDED TYPE_A)"""
    query = """
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
    """
    if sample:
        query = f"SELECT * FROM ({query}) t LIMIT {sample}"

    return conn.execute(text(query)).fetchall()


def run_feature_extraction(sample: int = None, dry_run: bool = False):
    """전체 기업 피처 추출 실행"""
    from ml.config import get_sync_db_url
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)

    with engine.connect() as conn:
        store = FeatureStore(conn)

        # 대상 기업 조회
        companies = get_target_companies(conn, sample=sample)
        total = len(companies)
        logger.info(f"피처 추출 대상: {total}개 기업")

        feature_date = '2024-12-31'
        success = 0
        failed = 0
        null_counts = {name: 0 for name in FEATURE_NAMES}

        for i, company in enumerate(companies):
            try:
                features = store.extract_all_features(
                    str(company.id),
                    feature_date=feature_date,
                    index_year=2024,
                )

                # NULL 피처 카운트
                for name in FEATURE_NAMES:
                    if features.get(name) is None:
                        null_counts[name] += 1

                if not dry_run:
                    store.save_features(str(company.id), features, feature_date)

                success += 1

                if (i + 1) % 100 == 0:
                    if not dry_run:
                        conn.commit()
                    logger.info(f"  진행: {i+1}/{total} ({(i+1)/total*100:.1f}%)")

            except Exception as e:
                failed += 1
                logger.warning(f"  실패: {company.name} ({company.ticker}) - {type(e).__name__}")
                # 트랜잭션 오류 복구
                try:
                    conn.rollback()
                except:
                    pass

        if not dry_run:
            conn.commit()

        # 보고서 출력
        logger.info("=" * 60)
        logger.info("피처 추출 완료 보고서")
        logger.info("=" * 60)
        logger.info(f"  대상: {total}개 기업")
        logger.info(f"  성공: {success}개")
        logger.info(f"  실패: {failed}개")
        logger.info(f"  기준일: {feature_date}")
        logger.info("")
        logger.info("피처별 NULL 비율:")
        for name in FEATURE_NAMES:
            pct = null_counts[name] / max(success, 1) * 100
            marker = " ⚠️" if pct > 50 else ""
            logger.info(f"  {name:40s}: {null_counts[name]:5d} NULL ({pct:5.1f}%){marker}")

        if dry_run:
            logger.info("\n[DRY-RUN] DB 저장 없이 종료합니다.")

        # DB 검증
        if not dry_run:
            count = conn.execute(text("SELECT COUNT(*) FROM ml_features")).scalar()
            logger.info(f"\nml_features 테이블: {count}건")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='피처 스토어 구축 (Phase 4)')
    parser.add_argument('--sample', type=int, help='샘플 기업 수 (테스트용)')
    parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 결과만 확인')
    args = parser.parse_args()

    run_feature_extraction(sample=args.sample, dry_run=args.dry_run)
