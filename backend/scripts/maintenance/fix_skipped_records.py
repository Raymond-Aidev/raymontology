#!/usr/bin/env python
"""
스킵된 레코드 수동 수정 스크립트

이전 스크립트에서 수정 후에도 비정상으로 판단되어 스킵된 67건을 수동으로 수정.
대부분 1,000이 아닌 1,000,000으로 나눠야 하는 케이스.

사용법:
    python fix_skipped_records.py --dry-run
    python fix_skipped_records.py --execute

2026-02-05
"""

import argparse
import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 스킵된 레코드 중 수동 수정 대상 정의
# (기업명, 필드, 나눗수)
MANUAL_FIXES = [
    # tangible_assets - 1,000,000으로 나눠야 하는 케이스
    ('동국제강', 'tangible_assets', 1_000_000),
    ('한솔제지', 'tangible_assets', 1_000_000),
    ('삼양홀딩스', 'tangible_assets', 1_000_000),
    ('LX인터내셔널', 'tangible_assets', 1_000_000),
    ('동국씨엠', 'tangible_assets', 1_000_000),
    ('녹십자홀딩스', 'tangible_assets', 1_000_000),
    ('STX엔진', 'tangible_assets', 1_000_000),
    ('솔루스첨단소재', 'tangible_assets', 1_000_000),
    ('한미사이언스', 'tangible_assets', 1_000_000),
    ('핸즈코퍼레이션', 'tangible_assets', 1_000_000),
    ('롯데에너지머티리얼즈', 'tangible_assets', 1_000_000),
    ('남해화학', 'tangible_assets', 1_000_000),
    ('일신방직', 'tangible_assets', 1_000_000),
    ('태림포장', 'tangible_assets', 1_000_000),
    ('한국특강', 'tangible_assets', 1_000_000),
    ('한솔테크닉스', 'tangible_assets', 1_000_000),
    ('무림SP', 'tangible_assets', 1_000_000),
    ('유수홀딩스', 'tangible_assets', 1_000_000),
    ('한농화성', 'tangible_assets', 1_000_000),
    ('코아시아', 'tangible_assets', 1_000_000),
    ('신화인터텍', 'tangible_assets', 1_000_000),

    # trade_and_other_receivables - 1,000,000으로 나눠야 하는 케이스
    ('LX인터내셔널', 'trade_and_other_receivables', 1_000_000),
    ('동국제강', 'trade_and_other_receivables', 1_000_000),
    ('동국씨엠', 'trade_and_other_receivables', 1_000_000),
    ('STX엔진', 'trade_and_other_receivables', 1_000_000),
    ('핸즈코퍼레이션', 'trade_and_other_receivables', 1_000_000),
    ('남해화학', 'trade_and_other_receivables', 1_000_000),

    # inventories - 1,000,000으로 나눠야 하는 케이스
    ('한국철강', 'inventories', 1_000_000),
    ('STX엔진', 'inventories', 1_000_000),

    # intangible_assets - 1,000,000으로 나눠야 하는 케이스
    ('금호석유화학', 'intangible_assets', 1_000_000),
    ('동국제강', 'intangible_assets', 1_000_000),
    ('동국씨엠', 'intangible_assets', 1_000_000),

    # operating_cash_flow - 1,000,000으로 나눠야 하는 케이스
    ('KG스틸', 'operating_cash_flow', 1_000_000),
    ('SPC삼립', 'operating_cash_flow', 1_000_000),
    ('동국제약', 'operating_cash_flow', 1_000_000),
    ('KPX홀딩스', 'operating_cash_flow', 1_000_000),

    # investing_cash_flow - 1,000,000으로 나눠야 하는 케이스
    ('KG스틸', 'investing_cash_flow', 1_000_000),
    ('SPC삼립', 'investing_cash_flow', 1_000_000),
    ('유화증권', 'investing_cash_flow', 1_000_000),
    ('동국제약', 'investing_cash_flow', 1_000_000),
    ('KPX홀딩스', 'investing_cash_flow', 1_000_000),
    ('한국경제TV', 'investing_cash_flow', 1_000_000),
    ('참엔지니어링', 'investing_cash_flow', 1_000_000),

    # financing_cash_flow - 1,000,000으로 나눠야 하는 케이스
    ('KG스틸', 'financing_cash_flow', 1_000_000),
    ('SPC삼립', 'financing_cash_flow', 1_000_000),
    ('유화증권', 'financing_cash_flow', 1_000_000),
    ('동국제약', 'financing_cash_flow', 1_000_000),
    ('KPX홀딩스', 'financing_cash_flow', 1_000_000),
    ('참엔지니어링', 'financing_cash_flow', 1_000_000),

    # capex - 1,000,000으로 나눠야 하는 케이스
    ('KG스틸', 'capex', 1_000_000),
    ('한국토지신탁', 'capex', 1_000_000),
    ('SPC삼립', 'capex', 1_000_000),
    ('유화증권', 'capex', 1_000_000),
    ('동국제약', 'capex', 1_000_000),
    ('KPX홀딩스', 'capex', 1_000_000),

    # dividend_paid - 1,000,000으로 나눠야 하는 케이스
    ('KG스틸', 'dividend_paid', 1_000_000),
    ('한국토지신탁', 'dividend_paid', 1_000_000),
    ('에스에프에이', 'dividend_paid', 1_000_000),
    ('동국제약', 'dividend_paid', 1_000_000),
    ('KPX홀딩스', 'dividend_paid', 1_000_000),

    # operating_income - 추가
    ('CJ CGV', 'operating_income', 1_000_000),

    # net_income - 추가
    ('CJ CGV', 'net_income', 1_000_000),
    ('SBS', 'net_income', 1_000_000),
    ('솔브레인', 'net_income', 1_000_000),
    ('한국경제TV', 'net_income', 1_000_000),
]


async def fix_skipped_records(dry_run: bool = True):
    """스킵된 레코드 수동 수정"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return

    conn = await asyncpg.connect(database_url)

    try:
        print(f"\n{'='*80}")
        print("스킵된 레코드 수동 수정")
        print(f"{'='*80}")
        print(f"모드: {'DRY-RUN' if dry_run else '🔴 EXECUTE'}")
        print(f"대상: {len(MANUAL_FIXES)}건")
        print(f"{'='*80}\n")

        fixed_count = 0
        skipped_count = 0

        for company_name, field, divisor in MANUAL_FIXES:
            # 현재 값 조회
            record = await conn.fetchrow(f"""
                SELECT
                    fd.id,
                    fd.{field} as current_value,
                    fd.total_assets
                FROM financial_details fd
                JOIN companies c ON fd.company_id = c.id
                WHERE c.name = $1 AND fd.fiscal_year = 2024
            """, company_name)

            if not record:
                print(f"  ⚠️ {company_name}: 레코드 없음")
                skipped_count += 1
                continue

            current_value = record['current_value']
            if current_value is None:
                print(f"  ⚠️ {company_name}.{field}: NULL")
                skipped_count += 1
                continue

            total_assets = record['total_assets']
            corrected_value = current_value / divisor

            # 수정 후에도 비정상인지 체크 (total_assets의 150% 초과 시)
            if abs(corrected_value) > total_assets * 1.5:
                print(f"  ⚠️ {company_name}.{field}: 수정 후에도 비정상 ({corrected_value/100_000_000:.0f}억 vs {total_assets/100_000_000:.0f}억)")
                skipped_count += 1
                continue

            current_억 = current_value / 100_000_000
            corrected_억 = corrected_value / 100_000_000

            if not dry_run:
                await conn.execute(f"""
                    UPDATE financial_details fd
                    SET {field} = {field} / $1, updated_at = NOW()
                    FROM companies c
                    WHERE fd.company_id = c.id
                      AND c.name = $2
                      AND fd.fiscal_year = 2024
                """, divisor, company_name)

            print(f"  ✓ {company_name}.{field}: {current_억:,.0f}억 → {corrected_억:,.0f}억 (÷{divisor:,})")
            fixed_count += 1

        print(f"\n{'='*80}")
        print(f"결과: {fixed_count}건 수정, {skipped_count}건 스킵")
        print(f"{'='*80}\n")

        if dry_run:
            print("DRY-RUN 모드입니다. 실제 수정: --execute")
        else:
            print("✅ 수정 완료!")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='스킵된 레코드 수동 수정')
    parser.add_argument('--dry-run', action='store_true', help='수정하지 않고 확인만')
    parser.add_argument('--execute', action='store_true', help='실제 수정 실행')

    args = parser.parse_args()

    if args.execute:
        asyncio.run(fix_skipped_records(dry_run=False))
    else:
        asyncio.run(fix_skipped_records(dry_run=True))


if __name__ == '__main__':
    main()
