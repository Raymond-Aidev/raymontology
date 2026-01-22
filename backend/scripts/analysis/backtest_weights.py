#!/usr/bin/env python3
"""
Phase 6: 백테스팅 및 최종 검증

가중치 최적화 결과의 예측력 검증

사용법:
    python -m scripts.analysis.backtest_weights --past-prediction
    python -m scripts.analysis.backtest_weights --stability
    python -m scripts.analysis.backtest_weights --expert-review
    python -m scripts.analysis.backtest_weights --full-report
"""

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 가중치 시나리오
WEIGHT_SCENARIOS = {
    'v21': {
        'name': 'v2.1 가중치',
        'weights': {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20},
        'aggregation': 'arithmetic',  # v2.1은 산술평균
    },
    'v30': {
        'name': 'v3.0 가중치',
        'weights': {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20},
        'aggregation': 'geometric',  # v3.0은 기하평균
    },
    'balanced': {
        'name': '균등 가중치',
        'weights': {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25},
        'aggregation': 'geometric',
    },
}


@dataclass
class BacktestResult:
    """백테스팅 결과"""
    scenario: str
    test_type: str
    metric: str
    value: float
    threshold: float
    passed: bool
    details: str


class BacktestRunner:
    """백테스팅 실행기"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

    async def test_past_prediction(self) -> List[BacktestResult]:
        """
        과거 예측 테스트

        2023년 데이터로 2024년 실패 예측
        (현재 데이터가 2024년까지만 있으므로 시뮬레이션)
        """
        conn = await asyncpg.connect(self.database_url)
        results = []

        try:
            # v3.0 점수와 실패 레이블 매칭
            rows = await conn.fetch("""
                SELECT
                    r3.company_id,
                    r3.total_score,
                    r3.grade,
                    CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END as is_failure
                FROM raymonds_index_v3 r3
                LEFT JOIN (
                    SELECT DISTINCT company_id, id
                    FROM company_labels
                    WHERE label_type = 'FAILURE'
                ) cl ON r3.company_id = cl.company_id
                WHERE r3.fiscal_year = 2024
            """)

            if not rows:
                return [BacktestResult(
                    scenario='v3.0',
                    test_type='past_prediction',
                    metric='data_available',
                    value=0,
                    threshold=1,
                    passed=False,
                    details='v3.0 계산 데이터가 없습니다'
                )]

            # 임계값별 성능 계산
            scores = [(float(r['total_score']), r['is_failure']) for r in rows]
            total_failures = sum(1 for _, f in scores if f == 1)
            total_normal = sum(1 for _, f in scores if f == 0)

            # 점수 30 미만을 실패 예측으로
            threshold = 30
            predictions = [(s < threshold, f) for s, f in scores]

            tp = sum(1 for p, a in predictions if p and a == 1)
            fp = sum(1 for p, a in predictions if p and a == 0)
            fn = sum(1 for p, a in predictions if not p and a == 1)
            tn = sum(1 for p, a in predictions if not p and a == 0)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            results.append(BacktestResult(
                scenario='v3.0',
                test_type='past_prediction',
                metric='f1_score',
                value=f1,
                threshold=0.7,
                passed=f1 >= 0.7,
                details=f'Precision: {precision:.3f}, Recall: {recall:.3f}, 실패기업: {total_failures}개'
            ))

            # False Positive 비율
            fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
            results.append(BacktestResult(
                scenario='v3.0',
                test_type='past_prediction',
                metric='false_positive_rate',
                value=fp_rate,
                threshold=0.2,
                passed=fp_rate <= 0.2,
                details=f'FP: {fp}개, TN: {tn}개'
            ))

        finally:
            await conn.close()

        return results

    async def test_grade_stability(self) -> List[BacktestResult]:
        """
        등급 안정성 테스트

        연도별 등급 변동이 2단계 이내인지 확인
        """
        conn = await asyncpg.connect(self.database_url)
        results = []

        try:
            # 2023-2024 등급 비교 (v2.1 기준, v3.0은 단일 연도만 있음)
            rows = await conn.fetch("""
                WITH grade_pairs AS (
                    SELECT
                        r1.company_id,
                        r1.grade as grade_2023,
                        r2.grade as grade_2024
                    FROM raymonds_index r1
                    JOIN raymonds_index r2 ON r1.company_id = r2.company_id
                    WHERE r1.fiscal_year = 2023
                      AND r2.fiscal_year = 2024
                )
                SELECT grade_2023, grade_2024, COUNT(*) as count
                FROM grade_pairs
                GROUP BY grade_2023, grade_2024
            """)

            grade_order = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

            def grade_distance(g1, g2):
                try:
                    return abs(grade_order.index(g1) - grade_order.index(g2))
                except ValueError:
                    return 9  # 알 수 없는 등급

            total = 0
            stable = 0  # 2단계 이내 변동

            for row in rows:
                count = row['count']
                dist = grade_distance(row['grade_2023'], row['grade_2024'])
                total += count
                if dist <= 2:
                    stable += count

            stability_rate = stable / total if total > 0 else 0

            results.append(BacktestResult(
                scenario='v2.1',
                test_type='grade_stability',
                metric='stability_rate',
                value=stability_rate,
                threshold=0.8,
                passed=stability_rate >= 0.8,
                details=f'안정 기업: {stable}/{total}개 ({stability_rate:.1%})'
            ))

        finally:
            await conn.close()

        return results

    async def test_expert_review(self) -> List[BacktestResult]:
        """
        전문가 검토 시뮬레이션

        상위/하위 기업의 특성 분석
        """
        conn = await asyncpg.connect(self.database_url)
        results = []

        try:
            # 상위 10개 기업
            top_10 = await conn.fetch("""
                SELECT
                    r3.total_score,
                    r3.grade,
                    c.name,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score
                FROM raymonds_index_v3 r3
                JOIN companies c ON c.id = r3.company_id
                WHERE r3.fiscal_year = 2024
                ORDER BY r3.total_score DESC
                LIMIT 10
            """)

            # 하위 10개 기업
            bottom_10 = await conn.fetch("""
                SELECT
                    r3.total_score,
                    r3.grade,
                    c.name,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score,
                    CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END as is_failure
                FROM raymonds_index_v3 r3
                JOIN companies c ON c.id = r3.company_id
                LEFT JOIN company_labels cl ON r3.company_id = cl.company_id
                WHERE r3.fiscal_year = 2024
                ORDER BY r3.total_score ASC
                LIMIT 10
            """)

            # 상위 기업 특성
            if top_10:
                avg_top_score = sum(float(r['total_score']) for r in top_10) / len(top_10)
                top_companies = ', '.join(r['name'][:10] for r in top_10[:5])

                results.append(BacktestResult(
                    scenario='v3.0',
                    test_type='expert_review',
                    metric='top_10_avg_score',
                    value=avg_top_score,
                    threshold=50,  # 상위 기업은 50점 이상이어야
                    passed=avg_top_score >= 50,
                    details=f'상위 기업: {top_companies}...'
                ))

            # 하위 기업 중 실패 레이블 비율
            if bottom_10:
                failure_in_bottom = sum(1 for r in bottom_10 if r['is_failure'] == 1)
                failure_rate = failure_in_bottom / len(bottom_10)
                bottom_companies = ', '.join(r['name'][:10] for r in bottom_10[:5])

                results.append(BacktestResult(
                    scenario='v3.0',
                    test_type='expert_review',
                    metric='bottom_10_failure_rate',
                    value=failure_rate,
                    threshold=0.3,  # 하위 10개 중 30% 이상이 실패 기업이면 좋음
                    passed=failure_rate >= 0.3,
                    details=f'하위 기업: {bottom_companies}...'
                ))

        finally:
            await conn.close()

        return results

    async def run_all_tests(self) -> List[BacktestResult]:
        """모든 테스트 실행"""
        all_results = []

        logger.info("과거 예측 테스트 실행...")
        all_results.extend(await self.test_past_prediction())

        logger.info("등급 안정성 테스트 실행...")
        all_results.extend(await self.test_grade_stability())

        logger.info("전문가 검토 시뮬레이션 실행...")
        all_results.extend(await self.test_expert_review())

        return all_results

    def print_report(self, results: List[BacktestResult]):
        """결과 보고서 출력"""
        print("\n" + "=" * 70)
        print("RaymondsIndex v3.0 백테스팅 결과")
        print("=" * 70)

        # 테스트 유형별 그룹화
        by_type = {}
        for r in results:
            if r.test_type not in by_type:
                by_type[r.test_type] = []
            by_type[r.test_type].append(r)

        test_names = {
            'past_prediction': '과거 예측 테스트',
            'grade_stability': '등급 안정성 테스트',
            'expert_review': '전문가 검토 시뮬레이션',
        }

        for test_type, test_results in by_type.items():
            print(f"\n## {test_names.get(test_type, test_type)}")
            print("-" * 50)

            for r in test_results:
                status = "✅ PASS" if r.passed else "❌ FAIL"
                print(f"{r.metric:<30}: {r.value:.3f} (기준: {r.threshold}) {status}")
                print(f"   └─ {r.details}")

        # 종합 결과
        print("\n" + "=" * 70)
        print("종합 결과")
        print("=" * 70)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        print(f"\n통과: {passed}/{total} ({passed/total*100:.1f}%)")

        if passed == total:
            print("\n✅ 모든 테스트 통과 - v3.0 배포 권장")
        elif passed >= total * 0.7:
            print("\n⚠️ 일부 테스트 미통과 - 추가 검토 필요")
        else:
            print("\n❌ 다수 테스트 미통과 - 가중치 재조정 권장")


async def main():
    parser = argparse.ArgumentParser(description='백테스팅 및 최종 검증')
    parser.add_argument('--past-prediction', action='store_true', help='과거 예측 테스트')
    parser.add_argument('--stability', action='store_true', help='등급 안정성 테스트')
    parser.add_argument('--expert-review', action='store_true', help='전문가 검토 시뮬레이션')
    parser.add_argument('--full-report', action='store_true', help='전체 보고서')

    args = parser.parse_args()

    runner = BacktestRunner()

    if args.full_report or not any([args.past_prediction, args.stability, args.expert_review]):
        results = await runner.run_all_tests()
        runner.print_report(results)
    else:
        results = []
        if args.past_prediction:
            results.extend(await runner.test_past_prediction())
        if args.stability:
            results.extend(await runner.test_grade_stability())
        if args.expert_review:
            results.extend(await runner.test_expert_review())

        runner.print_report(results)


if __name__ == '__main__':
    asyncio.run(main())
