"""
Phase 0: SUSPENDED 기업 사유 분류

354개 거래정지 기업을 TYPE_A(재무악화), TYPE_B(합병/자진상폐), TYPE_C(기타)로 자동 분류

분류 로직:
  1차: company_type = 'SPAC' → TYPE_C
  2차: risk_score >= 35 (MEDIUM_RISK 이상) → TYPE_A (재무악화 추정)
  3차: risk_score < 15 → TYPE_B (합병/자진상폐 추정)
  4차: 15 ≤ risk_score < 35 → TYPE_A (보수적 판단 - 악화 가능성)

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.data_prep.classify_suspended
    DATABASE_URL="postgresql://..." python -m ml.data_prep.classify_suspended --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """DB URL 획득"""
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise ValueError("DATABASE_URL 환경변수가 필요합니다")
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')
    return url


def classify_suspended_companies(dry_run: bool = False):
    """SUSPENDED 기업 자동 분류"""

    engine = create_engine(get_db_url())

    with engine.connect() as conn:
        # 1. SUSPENDED 기업 조회 (risk_score 포함)
        result = conn.execute(text("""
            SELECT
                c.id, c.name, c.ticker, c.company_type, c.market,
                rs.total_score as risk_score,
                rs.investment_grade
            FROM companies c
            LEFT JOIN risk_scores rs ON rs.company_id = c.id
            WHERE c.trading_status = 'SUSPENDED'
            ORDER BY rs.total_score DESC NULLS LAST
        """))
        companies = result.fetchall()

        logger.info(f"SUSPENDED 기업 총 {len(companies)}개 조회")

        # 2. 분류 로직
        classifications = []
        type_counts = {'TYPE_A': 0, 'TYPE_B': 0, 'TYPE_C': 0}

        for row in companies:
            company_id = row.id
            name = row.name
            company_type = row.company_type
            risk_score = row.risk_score

            # 1차: SPAC → TYPE_C
            if company_type == 'SPAC':
                s_type = 'TYPE_C'
                reason = f"SPAC 기업 (company_type=SPAC)"

            # 2차: REIT → TYPE_C
            elif company_type == 'REIT':
                s_type = 'TYPE_C'
                reason = f"REIT 기업 (company_type=REIT)"

            # 3차: risk_score 없음 → TYPE_C (데이터 부족)
            elif risk_score is None:
                s_type = 'TYPE_C'
                reason = "risk_score 없음 (데이터 부족)"

            # 4차: risk_score >= 35 → TYPE_A (재무악화 추정)
            elif float(risk_score) >= 35:
                s_type = 'TYPE_A'
                reason = f"고위험 risk_score={risk_score} (≥35, 재무악화 추정)"

            # 5차: risk_score < 15 → TYPE_B (합병/자진상폐 추정)
            elif float(risk_score) < 15:
                s_type = 'TYPE_B'
                reason = f"저위험 risk_score={risk_score} (<15, 합병/자진상폐 추정)"

            # 6차: 15 ≤ risk_score < 35 → TYPE_A (보수적 판단)
            else:
                s_type = 'TYPE_A'
                reason = f"중간 risk_score={risk_score} (15-34, 보수적 TYPE_A 분류)"

            classifications.append({
                'company_id': company_id,
                'suspension_type': s_type,
                'suspension_reason': reason,
                'classified_by': 'auto',
            })
            type_counts[s_type] += 1

        # 3. 결과 보고
        logger.info("=" * 60)
        logger.info("SUSPENDED 기업 자동 분류 결과")
        logger.info("=" * 60)
        logger.info(f"  TYPE_A (재무악화 → ML 양성 라벨): {type_counts['TYPE_A']}개")
        logger.info(f"  TYPE_B (합병/자진상폐 → ML 제외): {type_counts['TYPE_B']}개")
        logger.info(f"  TYPE_C (기타/SPAC/REIT → 개별 판단): {type_counts['TYPE_C']}개")
        logger.info(f"  총계: {len(classifications)}개")
        logger.info("=" * 60)

        # TYPE_A 기업 샘플 출력
        type_a_companies = [c for c in zip(companies, classifications) if c[1]['suspension_type'] == 'TYPE_A']
        logger.info(f"\nTYPE_A (재무악화) 상위 10개 기업:")
        for row, cls in type_a_companies[:10]:
            logger.info(f"  {row.name} ({row.ticker}) - risk_score: {row.risk_score}")

        # TYPE_B 기업 샘플 출력
        type_b_companies = [c for c in zip(companies, classifications) if c[1]['suspension_type'] == 'TYPE_B']
        logger.info(f"\nTYPE_B (합병/자진상폐 추정) 상위 10개 기업:")
        for row, cls in type_b_companies[:10]:
            logger.info(f"  {row.name} ({row.ticker}) - risk_score: {row.risk_score}")

        if dry_run:
            logger.info("\n[DRY-RUN] DB 저장 없이 종료합니다.")
            return type_counts

        # 4. DB 저장 (UPSERT)
        logger.info("\nDB 저장 시작...")

        # 기존 데이터 삭제 후 재삽입 (UPSERT 대신 깨끗한 재분류)
        conn.execute(text("DELETE FROM suspension_classifications"))

        inserted = 0
        for cls in classifications:
            conn.execute(text("""
                INSERT INTO suspension_classifications
                    (company_id, suspension_type, suspension_reason, classified_by, classified_at)
                VALUES
                    (:company_id, :suspension_type, :suspension_reason, :classified_by, NOW())
            """), cls)
            inserted += 1

        conn.commit()
        logger.info(f"suspension_classifications 테이블: {inserted}건 INSERT 완료")

        # 5. 검증
        verify = conn.execute(text("""
            SELECT suspension_type, COUNT(*) as cnt
            FROM suspension_classifications
            GROUP BY suspension_type
            ORDER BY suspension_type
        """)).fetchall()

        logger.info("\n검증 - DB 저장 결과:")
        for row in verify:
            logger.info(f"  {row.suspension_type}: {row.cnt}건")

        return type_counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SUSPENDED 기업 사유 분류 (Phase 0)')
    parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 결과만 확인')
    args = parser.parse_args()

    classify_suspended_companies(dry_run=args.dry_run)
