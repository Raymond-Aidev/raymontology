"""
상장폐지 기업 삭제 스크립트
- listing_status = 'DELISTED'인 기업 774개 전체 삭제
- 모든 FK 관계 데이터 함께 삭제
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"


def delete_delisted_companies():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 60)
        print("상장폐지 기업 삭제")
        print("=" * 60)
        print(f"실행 시간: {datetime.now().isoformat()}")

        # 1. 삭제 대상 기업 목록 조회
        result = conn.execute(text("""
            SELECT id, name, ticker, market
            FROM companies
            WHERE listing_status = 'DELISTED'
            ORDER BY ticker
        """))
        delisted_companies = result.fetchall()

        print(f"\n삭제 대상 기업: {len(delisted_companies)}개")
        for row in delisted_companies[:10]:
            print(f"  - {row[1]} ({row[2]}) - {row[3]}")
        if len(delisted_companies) > 10:
            print(f"  ... 외 {len(delisted_companies) - 10}개")

        if len(delisted_companies) == 0:
            print("삭제할 기업이 없습니다.")
            return

        # 기업 ID와 ticker를 SQL IN절 형식으로 변환
        company_ids_str = ",".join([f"'{row[0]}'" for row in delisted_companies])
        company_tickers_str = ",".join([f"'{row[2]}'" for row in delisted_companies])

        # 2. FK 관계 데이터 삭제
        print("\n" + "=" * 60)
        print("연관 데이터 삭제")
        print("=" * 60)

        # cb_subscribers 삭제 (cb_id, subscriber_company_id)
        result = conn.execute(text(f"""
            DELETE FROM cb_subscribers
            WHERE cb_id IN (SELECT id FROM convertible_bonds WHERE company_id IN ({company_ids_str}))
               OR subscriber_company_id IN ({company_ids_str})
        """))
        print(f"cb_subscribers 삭제: {result.rowcount}건")

        # convertible_bonds 삭제
        result = conn.execute(text(f"""
            DELETE FROM convertible_bonds WHERE company_id IN ({company_ids_str})
        """))
        print(f"convertible_bonds 삭제: {result.rowcount}건")

        # risk_scores 삭제
        result = conn.execute(text(f"""
            DELETE FROM risk_scores WHERE company_id IN ({company_ids_str})
        """))
        print(f"risk_scores 삭제: {result.rowcount}건")

        # risk_signals 삭제
        result = conn.execute(text(f"""
            DELETE FROM risk_signals WHERE target_company_id IN ({company_ids_str})
        """))
        print(f"risk_signals 삭제: {result.rowcount}건")

        # disclosures 삭제 (stock_code 기반)
        result = conn.execute(text(f"""
            DELETE FROM disclosures WHERE stock_code IN ({company_tickers_str})
        """))
        print(f"disclosures 삭제: {result.rowcount}건")

        # affiliates 삭제
        result = conn.execute(text(f"""
            DELETE FROM affiliates
            WHERE parent_company_id IN ({company_ids_str})
               OR affiliate_company_id IN ({company_ids_str})
        """))
        print(f"affiliates 삭제: {result.rowcount}건")

        # company_view_history 삭제
        result = conn.execute(text(f"""
            DELETE FROM company_view_history WHERE company_id IN ({company_ids_str})
        """))
        print(f"company_view_history 삭제: {result.rowcount}건")

        # stock_prices 삭제
        result = conn.execute(text(f"""
            DELETE FROM stock_prices WHERE company_id IN ({company_ids_str})
        """))
        print(f"stock_prices 삭제: {result.rowcount}건")

        # largest_shareholder_info 삭제
        result = conn.execute(text(f"""
            DELETE FROM largest_shareholder_info WHERE company_id IN ({company_ids_str})
        """))
        print(f"largest_shareholder_info 삭제: {result.rowcount}건")

        # officer_positions 삭제
        result = conn.execute(text(f"""
            DELETE FROM officer_positions WHERE company_id IN ({company_ids_str})
        """))
        print(f"officer_positions 삭제: {result.rowcount}건")

        # financial_statements 삭제
        result = conn.execute(text(f"""
            DELETE FROM financial_statements WHERE company_id IN ({company_ids_str})
        """))
        print(f"financial_statements 삭제: {result.rowcount}건")

        # financial_details 삭제
        result = conn.execute(text(f"""
            DELETE FROM financial_details WHERE company_id IN ({company_ids_str})
        """))
        print(f"financial_details 삭제: {result.rowcount}건")

        # raymonds_index 삭제
        result = conn.execute(text(f"""
            DELETE FROM raymonds_index WHERE company_id IN ({company_ids_str})
        """))
        print(f"raymonds_index 삭제: {result.rowcount}건")

        # major_shareholders 삭제
        result = conn.execute(text(f"""
            DELETE FROM major_shareholders WHERE company_id IN ({company_ids_str})
        """))
        print(f"major_shareholders 삭제: {result.rowcount}건")

        # 3. companies 삭제
        print("\n" + "=" * 60)
        print("기업 레코드 삭제")
        print("=" * 60)

        result = conn.execute(text(f"""
            DELETE FROM companies WHERE id IN ({company_ids_str})
        """))
        deleted_count = result.rowcount
        print(f"companies 삭제: {deleted_count}건")

        conn.commit()

        # 4. 검증
        print("\n" + "=" * 60)
        print("삭제 후 검증")
        print("=" * 60)

        result = conn.execute(text("""
            SELECT
                listing_status,
                COUNT(*) as cnt
            FROM companies
            GROUP BY listing_status
            ORDER BY listing_status
        """))
        print("\n기업 상장상태별 현황:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}개")

        result = conn.execute(text("SELECT COUNT(*) FROM companies"))
        total = result.fetchone()[0]
        print(f"\n총 기업 수: {total}개")

        print("\n" + "=" * 60)
        print(f"상장폐지 기업 {deleted_count}개 삭제 완료!")
        print("=" * 60)


if __name__ == "__main__":
    delete_delisted_companies()
