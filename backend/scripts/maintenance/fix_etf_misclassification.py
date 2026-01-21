"""
ETF 오분류 기업 정상화 스크립트 v2
- Phase 1: 이미 완료됨 (임원/공시 데이터 보유 287개 정상화)
- Phase 2: 상장폐지 추정 기업 774개 처리

안전성:
- DELETE 없음 (레코드 유지)
- listing_status만 'DELISTED'로 변경
- 기존 FK 관계 영향 없음
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Railway 프로덕션 DB
    DATABASE_URL = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"


def run_delisted_fix():
    """상장폐지 추정 기업 처리 (Phase 2)"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 1. 수정 전 현황 확인
        print("=" * 60)
        print("Phase 2: 상장폐지 추정 기업 처리")
        print("=" * 60)
        print(f"실행 시간: {datetime.now().isoformat()}")

        result = conn.execute(text("""
            SELECT COUNT(*) as remaining_etf
            FROM companies
            WHERE company_type = 'ETF'
              AND sector IS NOT NULL
              AND ticker ~ '^\\d+$'
              AND CAST(ticker AS INTEGER) < 400000
        """))
        remaining = result.fetchone()[0]
        print(f"\n현재 ETF 오분류 기업 수: {remaining}개")

        if remaining == 0:
            print("처리할 기업이 없습니다.")
            return

        # 2. 수정 전 샘플 확인
        print("\n수정 전 샘플 기업 (5개):")
        result = conn.execute(text("""
            SELECT name, ticker, company_type, market, listing_status
            FROM companies
            WHERE company_type = 'ETF'
              AND sector IS NOT NULL
              AND ticker ~ '^\\d+$'
              AND CAST(ticker AS INTEGER) < 400000
            ORDER BY ticker
            LIMIT 5
        """))
        for row in result.fetchall():
            print(f"  - {row[0]} ({row[1]}): {row[2]}/{row[3]}/{row[4]}")

        # 3. 상장폐지 처리 실행
        print("\n" + "=" * 60)
        print("상장폐지 기업 처리 실행")
        print("=" * 60)

        result = conn.execute(text("""
            UPDATE companies
            SET listing_status = 'DELISTED',
                company_type = 'NORMAL',
                market = CASE
                  WHEN CAST(ticker AS INTEGER) < 300000 THEN 'KOSPI'
                  ELSE 'KOSDAQ'
                END,
                updated_at = NOW()
            WHERE company_type = 'ETF'
              AND sector IS NOT NULL
              AND ticker ~ '^\\d+$'
              AND CAST(ticker AS INTEGER) < 400000
        """))
        conn.commit()
        updated_count = result.rowcount
        print(f"상장폐지 처리 완료: {updated_count}개")

        # 4. 수정 후 검증
        print("\n" + "=" * 60)
        print("수정 후 검증")
        print("=" * 60)

        # 전체 분포 확인
        result = conn.execute(text("""
            SELECT
                company_type,
                listing_status,
                COUNT(*) as cnt
            FROM companies
            GROUP BY company_type, listing_status
            ORDER BY company_type, listing_status
        """))
        print("\n기업 분류별 현황:")
        for row in result.fetchall():
            print(f"  - {row[0]} / {row[1]}: {row[2]}개")

        # NORMAL 기업의 listing_status 분포
        result = conn.execute(text("""
            SELECT
                listing_status,
                COUNT(*) as cnt
            FROM companies
            WHERE company_type = 'NORMAL'
            GROUP BY listing_status
            ORDER BY listing_status
        """))
        print("\nNORMAL 기업 상장상태:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}개")

        # 상장폐지 기업 샘플
        print("\n상장폐지 처리된 기업 샘플 (5개):")
        result = conn.execute(text("""
            SELECT name, ticker, company_type, market, listing_status
            FROM companies
            WHERE listing_status = 'DELISTED'
            ORDER BY ticker
            LIMIT 5
        """))
        for row in result.fetchall():
            print(f"  - {row[0]} ({row[1]}): {row[2]}/{row[3]}/{row[4]}")

        # 남은 ETF 분류 기업 (실제 ETF만)
        result = conn.execute(text("""
            SELECT COUNT(*) as real_etf
            FROM companies
            WHERE company_type = 'ETF'
        """))
        real_etf = result.fetchone()[0]
        print(f"\n실제 ETF 상품 수: {real_etf}개")

        print("\n" + "=" * 60)
        print("Phase 2 작업 완료!")
        print("=" * 60)


if __name__ == "__main__":
    run_delisted_fix()
