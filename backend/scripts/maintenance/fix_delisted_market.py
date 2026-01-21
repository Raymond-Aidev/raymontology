"""
상장폐지 기업의 market 필드 정상화
- DELISTED 기업 중 market='ETF'인 경우 KOSPI/KOSDAQ로 수정
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"


def fix_market():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 60)
        print("상장폐지 기업 market 필드 정상화")
        print("=" * 60)

        # 현황 확인
        result = conn.execute(text("""
            SELECT market, COUNT(*) as cnt
            FROM companies
            WHERE listing_status = 'DELISTED'
            GROUP BY market
        """))
        print("\n수정 전 DELISTED 기업 market 분포:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}개")

        # market 수정
        result = conn.execute(text("""
            UPDATE companies
            SET market = CASE
                  WHEN CAST(ticker AS INTEGER) < 300000 THEN 'KOSPI'
                  ELSE 'KOSDAQ'
                END,
                updated_at = NOW()
            WHERE listing_status = 'DELISTED'
              AND market = 'ETF'
              AND ticker ~ '^\\d+$'
        """))
        conn.commit()
        print(f"\nmarket 수정 완료: {result.rowcount}개")

        # 수정 후 확인
        result = conn.execute(text("""
            SELECT market, COUNT(*) as cnt
            FROM companies
            WHERE listing_status = 'DELISTED'
            GROUP BY market
        """))
        print("\n수정 후 DELISTED 기업 market 분포:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}개")

        print("\n완료!")


if __name__ == "__main__":
    fix_market()
