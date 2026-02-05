#!/usr/bin/env python
"""
short_term_investments 단위 변환 오류 수정 스크립트

v3.1 XBRL Enhancer 버그로 인해 44개 기업의 2024년 short_term_investments 값이
1,000,000배 오염됨. 이 스크립트로 복구.

원인: TE 태그 값(이미 원 단위)에 섹션 단위(백만원 등)를 중복 적용

사용법:
    # dry-run (확인만)
    python fix_short_term_investments.py --dry-run

    # 실제 수정
    python fix_short_term_investments.py --execute

2026-02-05
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

import asyncpg

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def fix_short_term_investments(dry_run: bool = True):
    """오염된 short_term_investments 값 수정"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print("예: DATABASE_URL='postgresql://...' python fix_short_term_investments.py --dry-run")
        return

    conn = await asyncpg.connect(database_url)

    try:
        # 1. 영향 받는 레코드 조회
        affected_records = await conn.fetch("""
            SELECT
                fd.id,
                c.name,
                c.ticker,
                fd.fiscal_year,
                fd.short_term_investments as current_value,
                fd.short_term_investments / 1000000 as corrected_value,
                fd.total_assets,
                ROUND((fd.short_term_investments::numeric / fd.total_assets * 100), 2) as current_pct,
                ROUND(((fd.short_term_investments / 1000000)::numeric / fd.total_assets * 100), 2) as corrected_pct
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.fiscal_year = 2024
              AND fd.short_term_investments IS NOT NULL
              AND fd.total_assets > 0
              AND fd.short_term_investments > fd.total_assets * 10
            ORDER BY fd.short_term_investments DESC
        """)

        print(f"\n{'='*80}")
        print(f"short_term_investments 단위 변환 오류 수정")
        print(f"{'='*80}")
        print(f"발견된 오류 레코드: {len(affected_records)}건")
        print(f"모드: {'DRY-RUN (수정 안 함)' if dry_run else 'EXECUTE (실제 수정)'}")
        print(f"{'='*80}\n")

        if not affected_records:
            print("수정할 레코드가 없습니다.")
            return

        # 2. 영향 받는 레코드 상세 출력
        print(f"{'기업명':<20} {'종목코드':<10} {'현재값':>20} {'수정값':>20} {'현재%':>10} {'수정%':>10}")
        print("-" * 100)

        for r in affected_records[:20]:  # 상위 20개만 표시
            current_억 = r['current_value'] / 100_000_000
            corrected_억 = r['corrected_value'] / 100_000_000
            print(f"{r['name']:<20} {r['ticker']:<10} {current_억:>18,.0f}억 {corrected_억:>18,.0f}억 {r['current_pct']:>9.0f}% {r['corrected_pct']:>9.2f}%")

        if len(affected_records) > 20:
            print(f"... 외 {len(affected_records) - 20}건")

        print()

        # 3. 수정 실행
        if dry_run:
            print("DRY-RUN 모드: 실제 수정하지 않았습니다.")
            print("실제 수정하려면: python fix_short_term_investments.py --execute")
        else:
            # 확인 프롬프트
            confirm = input(f"\n{len(affected_records)}건의 레코드를 수정하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                print("취소되었습니다.")
                return

            # UPDATE 실행
            result = await conn.execute("""
                UPDATE financial_details
                SET short_term_investments = short_term_investments / 1000000,
                    updated_at = NOW()
                WHERE fiscal_year = 2024
                  AND short_term_investments IS NOT NULL
                  AND total_assets > 0
                  AND short_term_investments > total_assets * 10
            """)

            print(f"\n✅ 수정 완료: {result}")

            # 검증
            remaining = await conn.fetchval("""
                SELECT COUNT(*)
                FROM financial_details
                WHERE fiscal_year = 2024
                  AND short_term_investments IS NOT NULL
                  AND total_assets > 0
                  AND short_term_investments > total_assets * 10
            """)

            print(f"검증: 남은 오류 레코드 = {remaining}건")

            if remaining == 0:
                print("✅ 모든 오류가 수정되었습니다!")
            else:
                print(f"⚠️ 아직 {remaining}건의 오류가 남아있습니다.")

    finally:
        await conn.close()


async def verify_fix():
    """수정 후 검증"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return

    conn = await asyncpg.connect(database_url)

    try:
        # 신일전자, 한국철강 확인
        result = await conn.fetch("""
            SELECT
                c.name,
                c.ticker,
                fd.fiscal_year,
                fd.short_term_investments,
                fd.total_assets,
                CASE
                    WHEN fd.total_assets > 0 THEN
                        ROUND((fd.short_term_investments::numeric / fd.total_assets * 100), 2)
                    ELSE 0
                END as pct
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE c.name IN ('신일전자', '한국철강')
            ORDER BY c.name, fd.fiscal_year DESC
        """)

        print("\n=== 검증: 신일전자, 한국철강 ===")
        print(f"{'기업명':<15} {'연도':<6} {'단기금융상품':>20} {'총자산':>20} {'비율':>10}")
        print("-" * 80)

        for r in result:
            short_억 = (r['short_term_investments'] or 0) / 100_000_000
            total_억 = r['total_assets'] / 100_000_000
            print(f"{r['name']:<15} {r['fiscal_year']:<6} {short_억:>18,.0f}억 {total_억:>18,.0f}억 {r['pct']:>9.2f}%")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='short_term_investments 오류 수정')
    parser.add_argument('--dry-run', action='store_true', help='수정하지 않고 확인만')
    parser.add_argument('--execute', action='store_true', help='실제 수정 실행')
    parser.add_argument('--verify', action='store_true', help='수정 후 검증')

    args = parser.parse_args()

    if args.verify:
        asyncio.run(verify_fix())
    elif args.execute:
        asyncio.run(fix_short_term_investments(dry_run=False))
    else:
        asyncio.run(fix_short_term_investments(dry_run=True))


if __name__ == '__main__':
    main()
