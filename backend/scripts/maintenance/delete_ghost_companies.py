"""
유령 기업 삭제 스크립트
- 사업보고서 없는 유령 기업 39개 완전 삭제
- FK 관계 데이터 먼저 삭제 후 기업 삭제

대상 기업 조건:
- listing_status = 'LISTED'
- company_type = 'NORMAL'
- 임원 정보 0건
- 재무제표 0건
- 공시 5건 이하
- 사업보고서 0건
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"


def delete_ghost_companies():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 60)
        print("유령 기업 삭제 (사업보고서 없는 기업)")
        print("=" * 60)
        print(f"실행 시간: {datetime.now().isoformat()}")

        # 1. 삭제 대상 기업 목록 조회
        result = conn.execute(text("""
            SELECT c.id, c.name, c.ticker, c.market
            FROM companies c
            WHERE c.listing_status = 'LISTED'
              AND c.company_type = 'NORMAL'
              AND c.id NOT IN (SELECT DISTINCT company_id FROM officer_positions WHERE company_id IS NOT NULL)
              AND c.id NOT IN (SELECT DISTINCT company_id FROM financial_statements WHERE company_id IS NOT NULL)
              AND (SELECT COUNT(*) FROM disclosures d WHERE d.stock_code = c.ticker) <= 5
              AND NOT EXISTS (
                  SELECT 1 FROM disclosures d
                  WHERE d.stock_code = c.ticker AND d.report_nm LIKE '%사업보고서%'
              )
            ORDER BY c.ticker
        """))
        ghost_companies = result.fetchall()

        print(f"\n삭제 대상 기업: {len(ghost_companies)}개")
        for row in ghost_companies[:10]:
            print(f"  - {row[1]} ({row[2]}) - {row[3]}")
        if len(ghost_companies) > 10:
            print(f"  ... 외 {len(ghost_companies) - 10}개")

        if len(ghost_companies) == 0:
            print("삭제할 기업이 없습니다.")
            return

        # 기업 ID와 ticker를 SQL IN절 형식으로 변환
        company_ids_str = ",".join([f"'{row[0]}'" for row in ghost_companies])
        company_tickers_str = ",".join([f"'{row[2]}'" for row in ghost_companies])

        # 2. FK 관계 데이터 삭제
        print("\n" + "=" * 60)
        print("연관 데이터 삭제")
        print("=" * 60)

        # 2-1. cb_subscribers 삭제 (convertible_bonds FK)
        result = conn.execute(text(f"""
            DELETE FROM cb_subscribers
            WHERE cb_id IN (
                SELECT id FROM convertible_bonds WHERE company_id IN ({company_ids_str})
            )
        """))
        print(f"cb_subscribers 삭제: {result.rowcount}건")

        # 2-2. convertible_bonds 삭제
        result = conn.execute(text(f"""
            DELETE FROM convertible_bonds WHERE company_id IN ({company_ids_str})
        """))
        print(f"convertible_bonds 삭제: {result.rowcount}건")

        # 2-3. risk_scores 삭제
        result = conn.execute(text(f"""
            DELETE FROM risk_scores WHERE company_id IN ({company_ids_str})
        """))
        print(f"risk_scores 삭제: {result.rowcount}건")

        # 2-4. risk_signals 삭제
        result = conn.execute(text(f"""
            DELETE FROM risk_signals WHERE target_company_id IN ({company_ids_str})
        """))
        print(f"risk_signals 삭제: {result.rowcount}건")

        # 2-5. disclosures 삭제 (stock_code 기반)
        result = conn.execute(text(f"""
            DELETE FROM disclosures WHERE stock_code IN ({company_tickers_str})
        """))
        print(f"disclosures 삭제: {result.rowcount}건")

        # 2-6. affiliates 삭제 (parent_company_id 또는 affiliate_company_id)
        result = conn.execute(text(f"""
            DELETE FROM affiliates
            WHERE parent_company_id IN ({company_ids_str})
               OR affiliate_company_id IN ({company_ids_str})
        """))
        print(f"affiliates 삭제: {result.rowcount}건")

        # 2-7. company_view_history 삭제
        result = conn.execute(text(f"""
            DELETE FROM company_view_history WHERE company_id IN ({company_ids_str})
        """))
        print(f"company_view_history 삭제: {result.rowcount}건")

        # 2-8. stock_prices 삭제
        result = conn.execute(text(f"""
            DELETE FROM stock_prices WHERE company_id IN ({company_ids_str})
        """))
        print(f"stock_prices 삭제: {result.rowcount}건")

        # 2-9. largest_shareholder_info 삭제
        result = conn.execute(text(f"""
            DELETE FROM largest_shareholder_info WHERE company_id IN ({company_ids_str})
        """))
        print(f"largest_shareholder_info 삭제: {result.rowcount}건")

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
            WHERE company_type = 'NORMAL'
            GROUP BY listing_status
            ORDER BY listing_status
        """))
        print("\nNORMAL 기업 상장상태:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1]}개")

        # 한일건설 삭제 확인
        result = conn.execute(text("""
            SELECT COUNT(*) FROM companies WHERE name = '한일건설'
        """))
        hanil_count = result.fetchone()[0]
        print(f"\n한일건설 존재 여부: {'삭제됨 ✅' if hanil_count == 0 else '아직 존재 ❌'}")

        print("\n" + "=" * 60)
        print(f"유령 기업 {deleted_count}개 삭제 완료!")
        print("=" * 60)


if __name__ == "__main__":
    delete_ghost_companies()
