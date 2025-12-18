#!/usr/bin/env python3
"""
회사명으로 종합 데이터 조회 CLI

사용법:
    python scripts/query_company.py "엑시온그룹"
    python scripts/query_company.py "삼성" --search
    python scripts/query_company.py --high-risk
"""
import asyncio
import asyncpg
import argparse
import json
from datetime import date

DB_URL = 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'


def format_number(num, suffix=''):
    """숫자 포맷팅"""
    if num is None:
        return '-'
    if abs(num) >= 1000:
        return f"{num:,.0f}{suffix}"
    return f"{num:.1f}{suffix}"


async def search_companies(query: str, limit: int = 20):
    """회사명 검색"""
    conn = await asyncpg.connect(DB_URL)
    try:
        companies = await conn.fetch("""
            SELECT c.id, c.corp_code, c.name,
                   COALESCE(cb.cb_count, 0) as cb_count,
                   rs.risk_level, rs.investment_grade, rs.total_score
            FROM companies c
            LEFT JOIN (
                SELECT company_id, COUNT(*) as cb_count
                FROM convertible_bonds
                GROUP BY company_id
            ) cb ON c.id = cb.company_id
            LEFT JOIN risk_scores rs ON c.id = rs.company_id
            WHERE c.name ILIKE $1
            ORDER BY rs.total_score DESC NULLS LAST, cb.cb_count DESC NULLS LAST
            LIMIT $2
        """, f"%{query}%", limit)

        print(f"\n검색 결과: '{query}' ({len(companies)}건)")
        print("=" * 80)
        print(f"{'회사명':<20} {'CB건수':>8} {'리스크점수':>10} {'등급':>6} {'레벨':>10}")
        print("-" * 80)

        for row in companies:
            score = f"{row['total_score']:.1f}" if row['total_score'] else '-'
            grade = row['investment_grade'] or '-'
            level = row['risk_level'] or '-'
            print(f"{row['name']:<20} {row['cb_count']:>8} {score:>10} {grade:>6} {level:>10}")

        return companies
    finally:
        await conn.close()


async def get_high_risk_companies(min_score: float = 50, limit: int = 30):
    """고위험 회사 목록"""
    conn = await asyncpg.connect(DB_URL)
    try:
        companies = await conn.fetch("""
            SELECT c.name, rs.total_score, rs.investment_grade, rs.risk_level,
                   COALESCE(cb.cb_count, 0) as cb_count,
                   COALESCE(sig.sig_count, 0) as signal_count
            FROM companies c
            JOIN risk_scores rs ON c.id = rs.company_id
            LEFT JOIN (
                SELECT company_id, COUNT(*) as cb_count
                FROM convertible_bonds
                GROUP BY company_id
            ) cb ON c.id = cb.company_id
            LEFT JOIN (
                SELECT target_company_id, COUNT(*) as sig_count
                FROM risk_signals
                GROUP BY target_company_id
            ) sig ON c.id = sig.target_company_id
            WHERE rs.total_score >= $1
            ORDER BY rs.total_score DESC
            LIMIT $2
        """, min_score, limit)

        print(f"\n고위험 회사 목록 (점수 >= {min_score})")
        print("=" * 90)
        print(f"{'회사명':<25} {'리스크점수':>10} {'등급':>6} {'레벨':>10} {'CB':>6} {'신호':>6}")
        print("-" * 90)

        for row in companies:
            print(f"{row['name']:<25} {row['total_score']:>10.1f} {row['investment_grade']:>6} "
                  f"{row['risk_level']:>10} {row['cb_count']:>6} {row['signal_count']:>6}")

        return companies
    finally:
        await conn.close()


async def get_company_report(company_name: str, exact_match: bool = False):
    """회사 종합 보고서"""
    conn = await asyncpg.connect(DB_URL)
    try:
        # 1. 회사 찾기
        if exact_match:
            company = await conn.fetchrow(
                "SELECT id, corp_code, name FROM companies WHERE name = $1",
                company_name
            )
        else:
            company = await conn.fetchrow("""
                SELECT id, corp_code, name FROM companies
                WHERE name ILIKE $1
                ORDER BY CASE WHEN name = $2 THEN 0 ELSE 1 END, LENGTH(name)
                LIMIT 1
            """, f"%{company_name}%", company_name)

        if not company:
            print(f"\n회사를 찾을 수 없습니다: {company_name}")
            print("검색을 시도하려면: python scripts/query_company.py \"검색어\" --search")
            return None

        company_id = company['id']
        corp_code = company['corp_code']

        print("\n" + "=" * 80)
        print(f"  {company['name']} 종합 보고서")
        print("=" * 80)

        # 2. 기본정보
        print(f"\n[기본정보]")
        print(f"  회사명: {company['name']}")
        print(f"  corp_code: {corp_code}")

        disclosure_count = await conn.fetchval(
            "SELECT COUNT(*) FROM disclosures WHERE corp_code = $1", corp_code
        ) or 0
        print(f"  공시 건수: {disclosure_count:,}건")

        # 3. 리스크 점수
        risk_score = await conn.fetchrow("""
            SELECT analysis_year, analysis_quarter, total_score, risk_level,
                   investment_grade, raymondsrisk_score, human_risk_score,
                   cb_risk_score, financial_health_score
            FROM risk_scores WHERE company_id = $1
            ORDER BY analysis_year DESC, analysis_quarter DESC NULLS LAST LIMIT 1
        """, company_id)

        print(f"\n[리스크 평가]")
        if risk_score:
            print(f"  분석기간: {risk_score['analysis_year']}년 Q{risk_score['analysis_quarter'] or 4}")
            print(f"  종합점수: {risk_score['total_score']:.1f}점")
            print(f"  리스크레벨: {risk_score['risk_level']}")
            print(f"  투자등급: {risk_score['investment_grade']}")
            print(f"  ---")
            print(f"  RaymondsRisk: {risk_score['raymondsrisk_score']:.1f}점")
            print(f"    - 인적리스크: {risk_score['human_risk_score']:.1f}점")
            print(f"    - CB리스크: {risk_score['cb_risk_score']:.1f}점")
            print(f"  재무건전성: {risk_score['financial_health_score']:.1f}점")
        else:
            print("  데이터 없음")

        # 4. 리스크 신호
        signals = await conn.fetch("""
            SELECT pattern_type, severity, risk_score, title, description
            FROM risk_signals WHERE target_company_id = $1
            ORDER BY risk_score DESC
        """, company_id)

        print(f"\n[리스크 신호] ({len(signals)}건)")
        if signals:
            for sig in signals:
                print(f"  - [{sig['severity']}] {sig['title']} (점수: {sig['risk_score']:.0f})")
                print(f"    {sig['description'][:60]}...")
        else:
            print("  감지된 신호 없음")

        # 5. CB 발행
        cbs = await conn.fetch("""
            SELECT issue_date, issue_amount / 100000000.0 as amount_billion,
                   conversion_price, maturity_date
            FROM convertible_bonds WHERE company_id = $1
            ORDER BY issue_date DESC NULLS LAST
        """, company_id)

        print(f"\n[CB 발행 현황] ({len(cbs)}건)")
        if cbs:
            total_amount = sum(cb['amount_billion'] or 0 for cb in cbs)
            print(f"  총 발행액: {total_amount:,.0f}억원")
            print(f"  {'발행일':<12} {'발행액':>10} {'전환가':>10} {'만기일':<12}")
            print(f"  {'-'*46}")
            for cb in cbs[:10]:
                issue_dt = str(cb['issue_date']) if cb['issue_date'] else '-'
                amount = f"{cb['amount_billion']:.0f}억" if cb['amount_billion'] else '-'
                price = f"{cb['conversion_price']:,}원" if cb['conversion_price'] else '-'
                maturity = str(cb['maturity_date']) if cb['maturity_date'] else '-'
                print(f"  {issue_dt:<12} {amount:>10} {price:>10} {maturity:<12}")
            if len(cbs) > 10:
                print(f"  ... 외 {len(cbs) - 10}건")
        else:
            print("  CB 발행 이력 없음")

        # 6. CB 인수인
        subscribers = await conn.fetch("""
            SELECT cs.subscriber_name, SUM(cs.subscription_amount) / 100000000.0 as total_billion,
                   COUNT(*) as count
            FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            WHERE cb.company_id = $1
            GROUP BY cs.subscriber_name
            ORDER BY total_billion DESC
            LIMIT 10
        """, company_id)

        print(f"\n[주요 CB 인수인]")
        if subscribers:
            for sub in subscribers:
                print(f"  - {sub['subscriber_name']}: {sub['total_billion']:.0f}억원 ({sub['count']}건)")
        else:
            print("  인수인 정보 없음")

        # 7. 재무제표
        financials = await conn.fetch("""
            SELECT fiscal_year, quarter,
                   total_assets / 100000000.0 as assets,
                   total_liabilities / 100000000.0 as liabilities,
                   total_equity / 100000000.0 as equity,
                   revenue / 100000000.0 as revenue,
                   operating_profit / 100000000.0 as op_profit,
                   net_income / 100000000.0 as net_income
            FROM financial_statements WHERE company_id = $1
            ORDER BY fiscal_year DESC, quarter DESC NULLS LAST
        """, company_id)

        print(f"\n[재무제표]")
        if financials:
            for fin in financials[:3]:
                yr = fin['fiscal_year']
                q = f"Q{fin['quarter']}" if fin['quarter'] else "연간"
                print(f"  {yr}년 {q}:")
                print(f"    자산: {format_number(fin['assets'], '억')} | "
                      f"부채: {format_number(fin['liabilities'], '억')} | "
                      f"자본: {format_number(fin['equity'], '억')}")
                print(f"    매출: {format_number(fin['revenue'], '억')} | "
                      f"영업이익: {format_number(fin['op_profit'], '억')} | "
                      f"순이익: {format_number(fin['net_income'], '억')}")
        else:
            print("  재무제표 없음")

        # 8. 임원
        officers = await conn.fetch("""
            SELECT o.name, op.position, op.term_end_date
            FROM officers o
            JOIN officer_positions op ON o.id = op.officer_id
            WHERE op.company_id = $1
            AND (op.term_end_date IS NULL OR op.term_end_date >= '2024-01-01')
            ORDER BY op.term_end_date DESC NULLS FIRST
            LIMIT 10
        """, company_id)

        print(f"\n[현재 임원] ({len(officers)}명)")
        if officers:
            for off in officers:
                term = str(off['term_end_date']) if off['term_end_date'] else '현재'
                print(f"  - {off['name']} ({off['position']}) ~ {term}")
        else:
            print("  임원 정보 없음")

        # 9. 주주
        shareholders = await conn.fetch("""
            SELECT shareholder_name, share_ratio, is_largest_shareholder
            FROM major_shareholders WHERE company_id = $1
            ORDER BY share_ratio DESC NULLS LAST LIMIT 5
        """, company_id)

        print(f"\n[주요 주주]")
        if shareholders:
            for sh in shareholders:
                largest = " (최대주주)" if sh['is_largest_shareholder'] else ""
                ratio = f"{sh['share_ratio']:.2f}%" if sh['share_ratio'] else "-"
                print(f"  - {sh['shareholder_name']}: {ratio}{largest}")
        else:
            print("  주주 정보 없음")

        # 10. 계열회사
        affiliates = await conn.fetch("""
            SELECT c2.name FROM affiliates a
            JOIN companies c2 ON a.affiliate_company_id = c2.id
            WHERE a.parent_company_id = $1
        """, company_id)

        print(f"\n[계열회사] ({len(affiliates)}개)")
        if affiliates:
            for aff in affiliates[:5]:
                print(f"  - {aff['name']}")
            if len(affiliates) > 5:
                print(f"  ... 외 {len(affiliates) - 5}개")
        else:
            print("  계열회사 정보 없음")

        print("\n" + "=" * 80)
        return company

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='회사 데이터 조회 CLI')
    parser.add_argument('query', nargs='?', help='회사명 또는 검색어')
    parser.add_argument('--search', '-s', action='store_true', help='검색 모드')
    parser.add_argument('--high-risk', '-r', action='store_true', help='고위험 회사 목록')
    parser.add_argument('--min-score', type=float, default=50, help='최소 리스크 점수 (기본: 50)')
    parser.add_argument('--limit', '-l', type=int, default=30, help='결과 개수 제한')
    parser.add_argument('--exact', '-e', action='store_true', help='정확히 일치하는 회사만')

    args = parser.parse_args()

    if args.high_risk:
        asyncio.run(get_high_risk_companies(args.min_score, args.limit))
    elif args.search and args.query:
        asyncio.run(search_companies(args.query, args.limit))
    elif args.query:
        asyncio.run(get_company_report(args.query, args.exact))
    else:
        parser.print_help()
        print("\n예시:")
        print("  python scripts/query_company.py '엑시온그룹'        # 종합보고서")
        print("  python scripts/query_company.py '삼성' --search    # 검색")
        print("  python scripts/query_company.py --high-risk        # 고위험 목록")


if __name__ == "__main__":
    main()
