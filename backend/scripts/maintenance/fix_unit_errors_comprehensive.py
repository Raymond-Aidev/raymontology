#!/usr/bin/env python
"""
financial_details 단위 변환 오류 종합 수정 스크립트

XBRL Enhancer v3.1 버그로 인해 127개 기업의 15개 필드가 오염됨.
TE 태그 값(이미 원 단위)에 섹션 단위(백만원 등)를 중복 적용한 것이 원인.

오류 필드 (15개):
- 자산: tangible_assets, trade_and_other_receivables, inventories, intangible_assets
- 부채: current_liabilities, non_current_liabilities
- 손익: revenue, cost_of_sales, operating_income, net_income
- 현금흐름: operating_cash_flow, investing_cash_flow, financing_cash_flow, capex, dividend_paid

사용법:
    # dry-run (확인만)
    python fix_unit_errors_comprehensive.py --dry-run

    # 실제 수정
    python fix_unit_errors_comprehensive.py --execute

    # 특정 필드만 수정
    python fix_unit_errors_comprehensive.py --execute --field tangible_assets

    # 검증
    python fix_unit_errors_comprehensive.py --verify

2026-02-05
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

import asyncpg

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 오류 필드 정의 (필드명, 임계값 배수, 절대값 사용 여부)
ERROR_FIELDS = {
    # 자산 항목 (값 > total_assets * 10)
    'tangible_assets': {'threshold_multiplier': 10, 'use_abs': False},
    'trade_and_other_receivables': {'threshold_multiplier': 10, 'use_abs': False},
    'inventories': {'threshold_multiplier': 10, 'use_abs': False},
    'intangible_assets': {'threshold_multiplier': 10, 'use_abs': False},

    # 부채 항목 (값 > total_assets * 10)
    'current_liabilities': {'threshold_multiplier': 10, 'use_abs': False},
    'non_current_liabilities': {'threshold_multiplier': 10, 'use_abs': False},

    # 손익 항목 (매출은 100배, 나머지는 10배)
    'revenue': {'threshold_multiplier': 100, 'use_abs': False},
    'cost_of_sales': {'threshold_multiplier': 100, 'use_abs': False},
    'operating_income': {'threshold_multiplier': 10, 'use_abs': True},
    'net_income': {'threshold_multiplier': 10, 'use_abs': True},

    # 현금흐름 항목 (절대값 > total_assets * 10)
    'operating_cash_flow': {'threshold_multiplier': 10, 'use_abs': True},
    'investing_cash_flow': {'threshold_multiplier': 10, 'use_abs': True},
    'financing_cash_flow': {'threshold_multiplier': 10, 'use_abs': True},
    'capex': {'threshold_multiplier': 10, 'use_abs': True},
    'dividend_paid': {'threshold_multiplier': 10, 'use_abs': True},
}


def determine_divisor(ratio: float) -> int:
    """배율에 따라 적절한 나눗수 결정"""
    if ratio >= 100000:
        return 1000000  # 백만 배 이상 → 1,000,000으로 나눔
    elif ratio >= 100:
        return 1000  # 천 배 이상 → 1,000으로 나눔
    else:
        return 1000  # 기본값


async def analyze_errors(conn, field: str, config: dict) -> list:
    """특정 필드의 오류 레코드 분석"""
    threshold = config['threshold_multiplier']
    use_abs = config['use_abs']

    if use_abs:
        condition = f"ABS(fd.{field}) > fd.total_assets * {threshold}"
        ratio_expr = f"ABS(fd.{field})::numeric / fd.total_assets"
    else:
        condition = f"fd.{field} > fd.total_assets * {threshold}"
        ratio_expr = f"fd.{field}::numeric / fd.total_assets"

    query = f"""
        SELECT
            fd.id,
            c.name,
            c.ticker,
            fd.fiscal_year,
            fd.{field} as current_value,
            fd.total_assets,
            ROUND({ratio_expr}, 0) as ratio
        FROM financial_details fd
        JOIN companies c ON fd.company_id = c.id
        WHERE fd.fiscal_year = 2024
          AND fd.{field} IS NOT NULL
          AND fd.total_assets > 0
          AND {condition}
        ORDER BY fd.total_assets DESC
    """

    return await conn.fetch(query)


async def fix_field_errors(conn, field: str, config: dict, dry_run: bool = True) -> dict:
    """특정 필드의 오류 수정"""

    # 1. 오류 레코드 분석
    records = await analyze_errors(conn, field, config)

    if not records:
        return {'field': field, 'count': 0, 'fixed': 0, 'skipped': 0}

    fixed_count = 0
    skipped_count = 0
    details = []

    for r in records:
        ratio = float(r['ratio'])
        divisor = determine_divisor(ratio)

        current_value = r['current_value']
        corrected_value = current_value / divisor

        # 수정 후에도 이상한 값이면 스킵 (예: 수정 후에도 total_assets의 50% 초과)
        if abs(corrected_value) > r['total_assets'] * 0.5 and field not in ['revenue', 'cost_of_sales']:
            skipped_count += 1
            details.append({
                'id': r['id'],
                'name': r['name'],
                'ticker': r['ticker'],
                'action': 'SKIPPED',
                'reason': f'수정 후에도 비정상 (corrected={corrected_value/100_000_000:.0f}억, total={r["total_assets"]/100_000_000:.0f}억)',
                'ratio': ratio,
                'divisor': divisor
            })
            continue

        if not dry_run:
            # 실제 UPDATE 실행
            await conn.execute(f"""
                UPDATE financial_details
                SET {field} = {field} / $1,
                    updated_at = NOW()
                WHERE id = $2
            """, divisor, r['id'])

        fixed_count += 1
        details.append({
            'id': r['id'],
            'name': r['name'],
            'ticker': r['ticker'],
            'action': 'FIXED' if not dry_run else 'WILL_FIX',
            'current': current_value,
            'corrected': corrected_value,
            'ratio': ratio,
            'divisor': divisor
        })

    return {
        'field': field,
        'count': len(records),
        'fixed': fixed_count,
        'skipped': skipped_count,
        'details': details
    }


async def run_comprehensive_fix(dry_run: bool = True, target_field: Optional[str] = None):
    """전체 오류 수정 실행"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print("예: DATABASE_URL='postgresql://...' python fix_unit_errors_comprehensive.py --dry-run")
        return

    conn = await asyncpg.connect(database_url)

    try:
        print(f"\n{'='*80}")
        print("financial_details 단위 변환 오류 종합 수정")
        print(f"{'='*80}")
        print(f"모드: {'DRY-RUN (수정 안 함)' if dry_run else '🔴 EXECUTE (실제 수정)'}")
        print(f"대상 연도: 2024")
        print(f"대상 필드: {target_field if target_field else '전체 15개 필드'}")
        print(f"{'='*80}\n")

        # 백업 권고
        if not dry_run:
            print("⚠️  경고: 실제 데이터를 수정합니다!")
            print("⚠️  백업을 먼저 수행하는 것을 권장합니다.")
            confirm = input("\n계속하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                print("취소되었습니다.")
                return

        # 필드별 수정 실행
        fields_to_fix = {target_field: ERROR_FIELDS[target_field]} if target_field else ERROR_FIELDS

        total_fixed = 0
        total_skipped = 0
        all_results = []

        for field, config in fields_to_fix.items():
            print(f"\n[{field}] 분석 중...")
            result = await fix_field_errors(conn, field, config, dry_run)
            all_results.append(result)

            if result['count'] > 0:
                print(f"  발견: {result['count']}건, 수정: {result['fixed']}건, 스킵: {result['skipped']}건")

                # 상위 5개 상세 표시
                for detail in result['details'][:5]:
                    if detail['action'] in ['FIXED', 'WILL_FIX']:
                        current_억 = detail['current'] / 100_000_000
                        corrected_억 = detail['corrected'] / 100_000_000
                        print(f"    {detail['name']}: {current_억:,.0f}억 → {corrected_억:,.0f}억 (÷{detail['divisor']:,})")
                    else:
                        print(f"    {detail['name']}: SKIPPED - {detail['reason']}")

                if result['count'] > 5:
                    print(f"    ... 외 {result['count'] - 5}건")

                total_fixed += result['fixed']
                total_skipped += result['skipped']

        # 결과 요약
        print(f"\n{'='*80}")
        print("수정 결과 요약")
        print(f"{'='*80}")
        print(f"{'필드':<30} {'발견':>10} {'수정':>10} {'스킵':>10}")
        print("-" * 60)

        for r in all_results:
            if r['count'] > 0:
                print(f"{r['field']:<30} {r['count']:>10} {r['fixed']:>10} {r['skipped']:>10}")

        print("-" * 60)
        print(f"{'합계':<30} {sum(r['count'] for r in all_results):>10} {total_fixed:>10} {total_skipped:>10}")
        print(f"{'='*80}\n")

        if dry_run:
            print("DRY-RUN 모드: 실제 수정하지 않았습니다.")
            print("실제 수정하려면: python fix_unit_errors_comprehensive.py --execute")
        else:
            print(f"✅ 총 {total_fixed}건 수정 완료!")

            # 결과를 JSON으로 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = f"fix_result_{timestamp}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
            print(f"상세 결과 저장: {result_file}")

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
        print(f"\n{'='*80}")
        print("수정 후 검증")
        print(f"{'='*80}\n")

        # 각 필드별 남은 오류 수 확인
        print(f"{'필드':<30} {'남은 오류':>15}")
        print("-" * 50)

        total_remaining = 0
        for field, config in ERROR_FIELDS.items():
            threshold = config['threshold_multiplier']
            use_abs = config['use_abs']

            if use_abs:
                condition = f"ABS({field}) > total_assets * {threshold}"
            else:
                condition = f"{field} > total_assets * {threshold}"

            count = await conn.fetchval(f"""
                SELECT COUNT(*)
                FROM financial_details
                WHERE fiscal_year = 2024
                  AND {field} IS NOT NULL
                  AND total_assets > 0
                  AND {condition}
            """)

            print(f"{field:<30} {count:>15}")
            total_remaining += count

        print("-" * 50)
        print(f"{'합계':<30} {total_remaining:>15}")
        print(f"{'='*80}\n")

        if total_remaining == 0:
            print("✅ 모든 오류가 수정되었습니다!")
        else:
            print(f"⚠️ 아직 {total_remaining}건의 오류가 남아있습니다.")
            print("스킵된 레코드를 수동으로 확인해주세요.")

        # 대표 기업 검증
        print("\n=== 대표 기업 검증 ===")
        result = await conn.fetch("""
            SELECT
                c.name,
                c.ticker,
                fd.fiscal_year,
                fd.total_assets / 100000000 as total_억,
                fd.tangible_assets / 100000000 as tangible_억,
                fd.trade_and_other_receivables / 100000000 as receivables_억,
                fd.operating_cash_flow / 100000000 as ocf_억
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE c.name IN ('금호석유화학', '한솔제지', 'KG스틸', '셀트리온', '카카오')
              AND fd.fiscal_year = 2024
            ORDER BY fd.total_assets DESC
        """)

        print(f"\n{'기업명':<15} {'총자산':>12} {'유형자산':>12} {'매출채권':>12} {'영업CF':>12}")
        print("-" * 65)
        for r in result:
            tangible = f"{r['tangible_억']:,.0f}억" if r['tangible_억'] else '-'
            receivables = f"{r['receivables_억']:,.0f}억" if r['receivables_억'] else '-'
            ocf = f"{r['ocf_억']:,.0f}억" if r['ocf_억'] else '-'
            print(f"{r['name']:<15} {r['total_억']:>10,.0f}억 {tangible:>12} {receivables:>12} {ocf:>12}")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='financial_details 단위 변환 오류 종합 수정')
    parser.add_argument('--dry-run', action='store_true', help='수정하지 않고 확인만')
    parser.add_argument('--execute', action='store_true', help='실제 수정 실행')
    parser.add_argument('--verify', action='store_true', help='수정 후 검증')
    parser.add_argument('--field', type=str, help='특정 필드만 수정 (예: tangible_assets)')

    args = parser.parse_args()

    if args.field and args.field not in ERROR_FIELDS:
        print(f"ERROR: 알 수 없는 필드: {args.field}")
        print(f"지원 필드: {', '.join(ERROR_FIELDS.keys())}")
        return

    if args.verify:
        asyncio.run(verify_fix())
    elif args.execute:
        asyncio.run(run_comprehensive_fix(dry_run=False, target_field=args.field))
    else:
        asyncio.run(run_comprehensive_fix(dry_run=True, target_field=args.field))


if __name__ == '__main__':
    main()
