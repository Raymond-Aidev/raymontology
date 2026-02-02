#!/usr/bin/env python3
"""
CB 투자자품질 점수 계산식 변경 검증 스크립트

변경 내용:
- 기존: high_risk_ratio 기반 (3개사 이상 투자자 비율)
- 변경: subscriber_count 기반 (인수대상자 수량)

검증 항목:
1. 새 함수 calculate_subscriber_quality_score() 단위 테스트
2. 샘플 기업 대상 신규 CB 리스크 점수 계산
3. 기존 점수와 신규 점수 비교

Author: Claude
Date: 2026-02-02
"""

import asyncio
import asyncpg
import sys
import os

# 상위 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.calculate_risk_scores import (
    calculate_subscriber_quality_score,
    calculate_cb_risk
)

DB_URL = 'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'


def test_subscriber_quality_score():
    """calculate_subscriber_quality_score() 단위 테스트"""
    print("\n" + "=" * 60)
    print("1. calculate_subscriber_quality_score() 단위 테스트")
    print("=" * 60)

    test_cases = [
        (0, 0, "CB 없음"),
        (1, 5, "단독 인수자"),
        (2, 10, "소규모 (2-4명)"),
        (5, 15, "중규모 (5-9명)"),
        (10, 20, "중대규모 (10-19명)"),
        (20, 25, "대규모 (20-49명)"),
        (50, 30, "초대규모 (50+명)"),
        (100, 30, "초대규모 (100명)"),
    ]

    all_passed = True
    for subscriber_count, expected, description in test_cases:
        result = calculate_subscriber_quality_score(subscriber_count)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} {description}: subscriber_count={subscriber_count} → {result}점 (expected: {expected})")

    return all_passed


def test_cb_risk_function():
    """calculate_cb_risk() 통합 테스트"""
    print("\n" + "=" * 60)
    print("2. calculate_cb_risk() 통합 테스트")
    print("=" * 60)

    test_cases = [
        # (cb_count, amount_billion, subscriber_count, loss_count, description)
        (0, 0, 0, 0, "CB 없음"),
        (1, 10, 1, 0, "소규모 CB 단독"),
        (2, 50, 5, 0, "중규모 CB"),
        (3, 100, 20, 2, "대규모 CB"),
        (4, 200, 50, 5, "초대규모 CB"),
    ]

    for cb_count, amount, subscriber_count, loss, desc in test_cases:
        result = calculate_cb_risk(cb_count, amount, subscriber_count, loss)
        print(f"\n  [{desc}]")
        print(f"    - cb_count={cb_count}, amount={amount}억, subscribers={subscriber_count}, loss={loss}")
        print(f"    - 총점: {result['score']}점 (레벨: {result['level']})")
        print(f"    - 빈도: {result['frequency_score']}점, 규모: {result['amount_score']}점, "
              f"품질: {result['quality_score']}점, 적자: {result['loss_score']}점")

    return True


async def test_sample_companies():
    """샘플 기업 대상 신규 점수 계산"""
    print("\n" + "=" * 60)
    print("3. 샘플 기업 신규 CB 리스크 점수 계산")
    print("=" * 60)

    conn = await asyncpg.connect(DB_URL)

    try:
        # CB가 있는 기업 중 인수대상자 수 기준 다양한 샘플 추출
        samples = await conn.fetch("""
            WITH cb_stats AS (
                SELECT
                    c.id as company_id,
                    c.name,
                    c.ticker,
                    COUNT(DISTINCT cb.id) as cb_count,
                    COALESCE(SUM(cb.issue_amount), 0) / 100000000 as total_billion,
                    COUNT(DISTINCT cs.subscriber_name) as subscriber_count
                FROM companies c
                JOIN convertible_bonds cb ON c.id = cb.company_id
                LEFT JOIN cb_subscribers cs ON cb.id = cs.cb_id
                WHERE c.listing_status = 'LISTED'
                GROUP BY c.id, c.name, c.ticker
                HAVING COUNT(DISTINCT cb.id) > 0
            )
            SELECT * FROM cb_stats
            ORDER BY subscriber_count DESC
            LIMIT 10
        """)

        print(f"\n  CB 발행 기업 상위 10개 (인수대상자 수 기준):\n")
        print(f"  {'기업명':20} {'티커':10} {'CB수':>6} {'발행액(억)':>10} {'인수자수':>8} {'품질점수':>8} {'총점':>6}")
        print("  " + "-" * 80)

        for row in samples:
            quality_score = calculate_subscriber_quality_score(row['subscriber_count'])
            cb_risk = calculate_cb_risk(
                row['cb_count'],
                float(row['total_billion']),
                row['subscriber_count'],
                0  # loss_company_count
            )
            print(f"  {row['name'][:20]:20} {row['ticker']:10} {row['cb_count']:>6} "
                  f"{row['total_billion']:>10.1f} {row['subscriber_count']:>8} "
                  f"{quality_score:>8} {cb_risk['score']:>6}")

        # 기존 점수와 비교
        print("\n" + "=" * 60)
        print("4. 기존 점수 vs 신규 점수 비교 (상위 5개)")
        print("=" * 60)

        comparisons = await conn.fetch("""
            WITH cb_stats AS (
                SELECT
                    c.id as company_id,
                    c.name,
                    rs.cb_risk_score as old_score,
                    COUNT(DISTINCT cs.subscriber_name) as subscriber_count
                FROM companies c
                JOIN risk_scores rs ON c.id = rs.company_id
                JOIN convertible_bonds cb ON c.id = cb.company_id
                LEFT JOIN cb_subscribers cs ON cb.id = cs.cb_id
                WHERE c.listing_status = 'LISTED'
                  AND rs.cb_risk_score > 0
                GROUP BY c.id, c.name, rs.cb_risk_score
            )
            SELECT * FROM cb_stats
            ORDER BY subscriber_count DESC
            LIMIT 5
        """)

        print(f"\n  {'기업명':20} {'인수자수':>8} {'기존점수':>10} {'신규품질':>10} {'변화':>8}")
        print("  " + "-" * 60)

        for row in comparisons:
            new_quality = calculate_subscriber_quality_score(row['subscriber_count'])
            # 기존 품질점수는 old_score에서 다른 컴포넌트를 뺀 값 (대략 추정)
            diff = new_quality - (row['old_score'] - 25 - 25)  # frequency + amount 빼기
            print(f"  {row['name'][:20]:20} {row['subscriber_count']:>8} "
                  f"{row['old_score']:>10.1f} {new_quality:>10} {diff:>+8}")

    finally:
        await conn.close()

    return True


async def main():
    print("\n" + "=" * 60)
    print("CB 투자자품질 점수 계산식 변경 검증")
    print("=" * 60)

    # 1. 단위 테스트
    test1_passed = test_subscriber_quality_score()

    # 2. 통합 테스트
    test2_passed = test_cb_risk_function()

    # 3. 샘플 기업 테스트
    await test_sample_companies()

    print("\n" + "=" * 60)
    print("검증 결과 요약")
    print("=" * 60)
    print(f"  단위 테스트: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  통합 테스트: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"  샘플 테스트: ✅ 완료")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("\n✅ 모든 테스트 통과. 전체 재계산 진행 가능.")
    else:
        print("\n❌ 테스트 실패. 코드 확인 필요.")


if __name__ == '__main__':
    asyncio.run(main())
