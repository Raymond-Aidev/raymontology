"""
피처 추출 배치 프로세서 - 청크 단위로 안정적인 처리

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.features.batch_processor --chunk 200
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text

from ml.features.feature_store import FeatureStore
from ml.config import FEATURE_NAMES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_missing_companies(conn, limit: int = 200):
    """아직 처리되지 않은 기업 조회"""
    return conn.execute(text(f"""
        SELECT c.id, c.name, c.ticker
        FROM (
            SELECT c.id, c.name, c.ticker
            FROM companies c
            WHERE c.listing_status = 'LISTED'
              AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
            UNION ALL
            SELECT c.id, c.name, c.ticker
            FROM companies c
            JOIN suspension_classifications sc ON sc.company_id = c.id
            WHERE c.trading_status = 'SUSPENDED'
              AND sc.suspension_type = 'TYPE_A'
              AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
        ) c
        WHERE c.id NOT IN (SELECT company_id FROM ml_features)
        ORDER BY c.ticker
        LIMIT {limit}
    """)).fetchall()


def process_chunk(chunk_size: int = 200):
    """단일 청크 처리"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True
    )

    with engine.connect() as conn:
        # 누락 기업 조회
        missing = get_missing_companies(conn, chunk_size)

        if not missing:
            logger.info("모든 기업 처리 완료!")
            return 0

        total = len(missing)
        logger.info(f"처리 대상: {total}개 기업")

        store = FeatureStore(conn)
        success = 0
        failed = 0
        start_time = time.time()

        for i, c in enumerate(missing):
            try:
                features = store.extract_all_features(
                    str(c.id), '2024-12-31', 2024
                )
                store.save_features(str(c.id), features, '2024-12-31')
                success += 1

                if (i + 1) % 20 == 0:
                    conn.commit()
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed * 60  # per minute
                    logger.info(f"  진행: {i+1}/{total} ({(i+1)/total*100:.1f}%) - {rate:.1f}/min")

            except Exception as e:
                failed += 1
                logger.warning(f"  실패: {c.ticker} {c.name} - {type(e).__name__}")
                try:
                    conn.rollback()
                except:
                    pass

        conn.commit()

        elapsed = time.time() - start_time
        logger.info(f"청크 완료: 성공 {success}, 실패 {failed}, 소요 {elapsed:.1f}초")

        # 현재 총 레코드 수
        total_records = conn.execute(text("SELECT COUNT(*) FROM ml_features")).scalar()
        logger.info(f"ml_features 총 레코드: {total_records}건")

        return len(missing)


def run_all_chunks(chunk_size: int = 200, max_chunks: int = None):
    """모든 청크 연속 처리"""
    chunk_num = 0

    while True:
        chunk_num += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"청크 #{chunk_num} 시작")
        logger.info(f"{'='*60}")

        processed = process_chunk(chunk_size)

        if processed == 0:
            logger.info("모든 기업 처리 완료!")
            break

        if max_chunks and chunk_num >= max_chunks:
            logger.info(f"최대 청크 수 ({max_chunks}) 도달")
            break

        # 청크 사이 휴식 (커넥션 정리)
        logger.info("다음 청크 준비 중...")
        time.sleep(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='피처 추출 배치 프로세서')
    parser.add_argument('--chunk', type=int, default=200, help='청크 크기')
    parser.add_argument('--max-chunks', type=int, help='최대 청크 수')
    parser.add_argument('--once', action='store_true', help='단일 청크만 처리')
    args = parser.parse_args()

    if args.once:
        process_chunk(args.chunk)
    else:
        run_all_chunks(args.chunk, args.max_chunks)
