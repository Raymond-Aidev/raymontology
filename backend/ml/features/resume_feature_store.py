"""
피처 추출 재개 스크립트 - 누락된 기업만 처리

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.features.resume_feature_store
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text

from ml.features.feature_store import FeatureStore, get_target_companies
from ml.config import FEATURE_NAMES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_resume_extraction():
    """누락된 기업만 피처 추출"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)

    with engine.connect() as conn:
        # 전체 대상 기업 조회
        all_companies = get_target_companies(conn)
        total_target = len(all_companies)

        # 이미 처리된 company_id 조회
        processed = conn.execute(text(
            "SELECT DISTINCT company_id FROM ml_features"
        )).fetchall()
        processed_ids = {str(row[0]) for row in processed}

        # 누락된 기업 필터링
        missing_companies = [c for c in all_companies if str(c.id) not in processed_ids]
        missing_count = len(missing_companies)

        logger.info(f"전체 대상: {total_target}개")
        logger.info(f"처리 완료: {len(processed_ids)}개")
        logger.info(f"누락 기업: {missing_count}개")

        if missing_count == 0:
            logger.info("모든 기업 처리 완료!")
            return

        store = FeatureStore(conn)
        feature_date = '2024-12-31'
        success = 0
        failed = 0

        for i, company in enumerate(missing_companies):
            try:
                features = store.extract_all_features(
                    str(company.id),
                    feature_date=feature_date,
                    index_year=2024,
                )
                store.save_features(str(company.id), features, feature_date)
                success += 1

                if (i + 1) % 100 == 0:
                    conn.commit()
                    logger.info(f"  진행: {i+1}/{missing_count} ({(i+1)/missing_count*100:.1f}%) - 성공: {success}, 실패: {failed}")

            except Exception as e:
                failed += 1
                logger.warning(f"  실패: {company.name} ({company.ticker}) - {type(e).__name__}: {str(e)[:100]}")
                try:
                    conn.rollback()
                except:
                    pass

        conn.commit()

        # 최종 보고
        logger.info("=" * 60)
        logger.info("피처 추출 재개 완료")
        logger.info("=" * 60)
        logger.info(f"  처리 대상: {missing_count}개")
        logger.info(f"  성공: {success}개")
        logger.info(f"  실패: {failed}개")

        count = conn.execute(text("SELECT COUNT(*) FROM ml_features")).scalar()
        logger.info(f"\nml_features 총 레코드: {count}건")


if __name__ == '__main__':
    run_resume_extraction()
