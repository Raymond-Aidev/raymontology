#!/usr/bin/env python3
"""
RaymondsIndex v3.0 가중치 민감도 분석

Phase 3: 가중치 시나리오별 점수 분포 분석

사용법:
    python -m scripts.analysis.weight_sensitivity --analyze
    python -m scripts.analysis.weight_sensitivity --compare
    python -m scripts.analysis.weight_sensitivity --export results.csv
"""

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 가중치 시나리오 정의
# ═══════════════════════════════════════════════════════════════════════════════

WEIGHT_SCENARIOS = {
    'current': {
        'name': '현재 (v3.0)',
        'description': 'RII 중심 (35%)',
        'weights': {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20},
    },
    'balanced': {
        'name': '균등 배분',
        'description': '모든 지표 25%',
        'weights': {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25},
    },
    'rii_reduced': {
        'name': 'RII 축소',
        'description': 'RII 25%로 축소, CGI 30%',
        'weights': {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.30, 'MAI': 0.20},
    },
    'cei_focus': {
        'name': 'CEI 중심',
        'description': '자본효율성 강조 (30%)',
        'weights': {'CEI': 0.30, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.20},
    },
    'mai_focus': {
        'name': 'MAI 중심',
        'description': '모멘텀 강조 (30%)',
        'weights': {'CEI': 0.20, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.30},
    },
}

# 등급 임계값 시나리오
GRADE_SCENARIOS = {
    'current': {
        'name': '현재 기준',
        'thresholds': [(95, 'A++'), (88, 'A+'), (80, 'A'), (72, 'A-'),
                       (64, 'B+'), (55, 'B'), (45, 'B-'), (30, 'C+'), (0, 'C')],
    },
    'relaxed_10': {
        'name': '10점 완화',
        'thresholds': [(85, 'A++'), (78, 'A+'), (70, 'A'), (62, 'A-'),
                       (54, 'B+'), (45, 'B'), (35, 'B-'), (20, 'C+'), (0, 'C')],
    },
    'relaxed_20': {
        'name': '20점 완화',
        'thresholds': [(75, 'A++'), (68, 'A+'), (60, 'A'), (52, 'A-'),
                       (44, 'B+'), (35, 'B'), (25, 'B-'), (15, 'C+'), (0, 'C')],
    },
    'relative': {
        'name': '상대 등급제',
        'description': '상위 5%=A++, 10%=A+, ...',
        'percentiles': [95, 90, 80, 70, 55, 40, 25, 10, 0],
        'thresholds': None,  # 동적 계산
    },
}


@dataclass
class ScenarioResult:
    """시나리오 분석 결과"""
    scenario_name: str
    avg_score: float
    std_score: float
    min_score: float
    max_score: float
    grade_distribution: Dict[str, int]
    entropy: float  # 등급 분포 엔트로피 (다양성 지표)
    correlation_with_v21: float


class WeightSensitivityAnalyzer:
    """가중치 민감도 분석기"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

    async def load_data(self) -> List[Dict]:
        """v3.0 계산 결과 로드"""
        conn = await asyncpg.connect(self.database_url)
        try:
            # v3.0 Sub-Index 점수 조회
            v3_data = await conn.fetch("""
                SELECT
                    r3.company_id,
                    c.name as company_name,
                    r3.total_score as v3_score,
                    r3.grade as v3_grade,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score
                FROM raymonds_index_v3 r3
                JOIN companies c ON c.id = r3.company_id
                WHERE r3.fiscal_year = 2024
                  AND r3.cei_score IS NOT NULL
                  AND r3.rii_score IS NOT NULL
                  AND r3.cgi_score IS NOT NULL
                  AND r3.mai_score IS NOT NULL
            """)

            # v2.1 점수 조회 (상관관계 분석용)
            v21_scores = {}
            v21_data = await conn.fetch("""
                SELECT company_id, total_score
                FROM raymonds_index
                WHERE fiscal_year = 2024
            """)
            for row in v21_data:
                v21_scores[row['company_id']] = float(row['total_score'])

            # 병합
            result = []
            for row in v3_data:
                result.append({
                    'company_id': str(row['company_id']),
                    'company_name': row['company_name'],
                    'v3_score': float(row['v3_score']),
                    'v3_grade': row['v3_grade'],
                    'cei': float(row['cei_score']),
                    'rii': float(row['rii_score']),
                    'cgi': float(row['cgi_score']),
                    'mai': float(row['mai_score']),
                    'v21_score': v21_scores.get(row['company_id']),
                })

            logger.info(f"로드 완료: {len(result)}개 기업")
            return result

        finally:
            await conn.close()

    def geometric_mean(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """가중 기하평균 계산"""
        result = 1.0
        for key, weight in weights.items():
            score = max(1.0, scores.get(key.lower(), 1.0))  # 0점 방지
            result *= score ** weight
        return result

    def arithmetic_mean(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """가중 산술평균 계산"""
        result = 0.0
        for key, weight in weights.items():
            result += scores.get(key.lower(), 0.0) * weight
        return result

    def determine_grade(self, score: float, thresholds: List[Tuple[int, str]]) -> str:
        """점수 → 등급 변환"""
        for threshold, grade in thresholds:
            if score >= threshold:
                return grade
        return 'C'

    def calculate_entropy(self, distribution: Dict[str, int]) -> float:
        """등급 분포 엔트로피 계산 (다양성 지표)"""
        total = sum(distribution.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        return entropy

    def calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """피어슨 상관계수 계산"""
        n = len(x)
        if n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denominator_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        return numerator / (denominator_x * denominator_y)

    async def analyze_scenario(
        self,
        data: List[Dict],
        weight_scenario: str,
        grade_scenario: str = 'current',
        use_geometric: bool = True
    ) -> ScenarioResult:
        """시나리오별 분석 실행"""
        weights = WEIGHT_SCENARIOS[weight_scenario]['weights']
        thresholds = GRADE_SCENARIOS[grade_scenario]['thresholds']

        scores = []
        grades = []
        v21_scores = []

        for company in data:
            sub_scores = {
                'cei': company['cei'],
                'rii': company['rii'],
                'cgi': company['cgi'],
                'mai': company['mai'],
            }

            if use_geometric:
                score = self.geometric_mean(sub_scores, weights)
            else:
                score = self.arithmetic_mean(sub_scores, weights)

            scores.append(score)

            if thresholds:
                grade = self.determine_grade(score, thresholds)
            else:
                grade = 'N/A'  # 상대 등급제는 별도 처리

            grades.append(grade)

            if company['v21_score'] is not None:
                v21_scores.append((score, company['v21_score']))

        # 상대 등급제 처리
        if grade_scenario == 'relative' and not thresholds:
            sorted_scores = sorted(scores, reverse=True)
            percentiles = GRADE_SCENARIOS['relative']['percentiles']
            grade_names = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

            thresholds_dynamic = []
            for i, pct in enumerate(percentiles[:-1]):
                idx = int(len(sorted_scores) * (100 - pct) / 100)
                if idx < len(sorted_scores):
                    thresholds_dynamic.append((sorted_scores[idx], grade_names[i]))

            grades = []
            for score in scores:
                grade = self.determine_grade(score, thresholds_dynamic)
                grades.append(grade)

        # 등급 분포
        grade_dist = {}
        for grade in grades:
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

        # 상관계수
        correlation = 0.0
        if v21_scores:
            x = [s[0] for s in v21_scores]
            y = [s[1] for s in v21_scores]
            correlation = self.calculate_correlation(x, y)

        return ScenarioResult(
            scenario_name=f"{weight_scenario}_{grade_scenario}",
            avg_score=sum(scores) / len(scores) if scores else 0,
            std_score=(sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)) ** 0.5 if scores else 0,
            min_score=min(scores) if scores else 0,
            max_score=max(scores) if scores else 0,
            grade_distribution=grade_dist,
            entropy=self.calculate_entropy(grade_dist),
            correlation_with_v21=correlation,
        )

    async def run_all_scenarios(self) -> Dict[str, ScenarioResult]:
        """모든 시나리오 분석 실행"""
        data = await self.load_data()

        if not data:
            logger.error("분석할 데이터가 없습니다. v3.0 계산을 먼저 실행하세요.")
            return {}

        results = {}

        # 가중치 시나리오별 분석
        for weight_key in WEIGHT_SCENARIOS:
            for grade_key in ['current', 'relaxed_10', 'relaxed_20']:
                result = await self.analyze_scenario(data, weight_key, grade_key)
                results[result.scenario_name] = result
                logger.info(f"완료: {result.scenario_name}")

        return results

    def print_report(self, results: Dict[str, ScenarioResult]):
        """분석 결과 출력"""
        print("\n" + "=" * 80)
        print("RaymondsIndex v3.0 가중치 민감도 분석 결과")
        print("=" * 80)

        print("\n## 시나리오별 점수 통계\n")
        print(f"{'시나리오':<30} {'평균':>8} {'표준편차':>8} {'최소':>8} {'최대':>8} {'엔트로피':>8} {'v2.1상관':>8}")
        print("-" * 80)

        for key, result in sorted(results.items()):
            print(f"{result.scenario_name:<30} {result.avg_score:>8.2f} {result.std_score:>8.2f} "
                  f"{result.min_score:>8.2f} {result.max_score:>8.2f} {result.entropy:>8.2f} "
                  f"{result.correlation_with_v21:>8.2f}")

        print("\n## 등급 분포 비교\n")
        grade_order = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

        # current 가중치의 등급 시나리오별 비교
        print("### 현재 가중치 (v3.0) - 등급 기준별 분포")
        print(f"{'등급':<6}", end="")
        for grade_key in ['current', 'relaxed_10', 'relaxed_20']:
            print(f"{grade_key:>12}", end="")
        print()
        print("-" * 50)

        for grade in grade_order:
            print(f"{grade:<6}", end="")
            for grade_key in ['current', 'relaxed_10', 'relaxed_20']:
                key = f"current_{grade_key}"
                if key in results:
                    count = results[key].grade_distribution.get(grade, 0)
                    print(f"{count:>12}", end="")
            print()

        print("\n### 권장 시나리오")
        print("-" * 50)

        # 엔트로피가 가장 높은 시나리오 (등급 분포 균형)
        best_entropy = max(results.values(), key=lambda x: x.entropy)
        print(f"등급 분포 균형 최적: {best_entropy.scenario_name} (엔트로피: {best_entropy.entropy:.2f})")

        # v2.1과 상관관계가 가장 높은 시나리오
        best_corr = max(results.values(), key=lambda x: x.correlation_with_v21)
        print(f"v2.1 호환성 최적: {best_corr.scenario_name} (상관계수: {best_corr.correlation_with_v21:.2f})")


async def main():
    parser = argparse.ArgumentParser(description='RaymondsIndex v3.0 가중치 민감도 분석')
    parser.add_argument('--analyze', action='store_true', help='전체 시나리오 분석')
    parser.add_argument('--compare', action='store_true', help='v2.1과 비교')
    parser.add_argument('--export', type=str, help='결과를 CSV로 내보내기')

    args = parser.parse_args()

    analyzer = WeightSensitivityAnalyzer()

    if args.analyze or not any([args.compare, args.export]):
        results = await analyzer.run_all_scenarios()
        analyzer.print_report(results)

    if args.export:
        # CSV 내보내기 구현
        pass


if __name__ == '__main__':
    asyncio.run(main())
