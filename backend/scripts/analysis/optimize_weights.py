#!/usr/bin/env python3
"""
Phase 5: 통계적 가중치 최적화 (Option C)

Altman Z-Score 방식을 참고한 판별분석 기반 가중치 도출

사용법:
    python -m scripts.analysis.optimize_weights --check-requirements
    python -m scripts.analysis.optimize_weights --optimize
    python -m scripts.analysis.optimize_weights --backtest
    python -m scripts.analysis.optimize_weights --report
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


@dataclass
class OptimizationResult:
    """가중치 최적화 결과"""
    method: str
    weights: Dict[str, float]
    f1_score: float
    precision: float
    recall: float
    threshold: float
    sample_size: int
    failure_count: int


class WeightOptimizer:
    """
    Altman 방식 가중치 최적화기

    판별분석(LDA)을 사용하여 실패 기업과 정상 기업을 구분하는
    최적의 가중치를 통계적으로 도출
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

    async def check_requirements(self) -> Dict:
        """Option C 실행 요건 확인"""
        conn = await asyncpg.connect(self.database_url)

        try:
            # v3.0 계산 완료 기업 수
            v3_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT company_id)
                FROM raymonds_index_v3
                WHERE cei_score IS NOT NULL
                  AND rii_score IS NOT NULL
                  AND cgi_score IS NOT NULL
                  AND mai_score IS NOT NULL
            """)

            # 실패 기업 레이블 수
            failure_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT company_id)
                FROM company_labels
                WHERE label_type = 'FAILURE'
            """) or 0

            # 고신뢰도 실패 기업 수
            high_conf_failure = await conn.fetchval("""
                SELECT COUNT(DISTINCT company_id)
                FROM company_labels
                WHERE label_type = 'FAILURE'
                  AND confidence >= 0.9
            """) or 0

            # v3.0과 레이블이 모두 있는 기업 (분석 가능)
            analyzable = await conn.fetchval("""
                SELECT COUNT(DISTINCT r3.company_id)
                FROM raymonds_index_v3 r3
                LEFT JOIN company_labels cl ON r3.company_id = cl.company_id
                WHERE r3.cei_score IS NOT NULL
            """)

            return {
                'v3_calculated': v3_count,
                'failure_labeled': failure_count,
                'high_conf_failure': high_conf_failure,
                'analyzable_companies': analyzable,
                'requirements_met': v3_count >= 500 and high_conf_failure >= 50,
            }

        finally:
            await conn.close()

    async def load_training_data(self) -> Tuple[List[Dict], List[int]]:
        """학습 데이터 로드"""
        conn = await asyncpg.connect(self.database_url)

        try:
            rows = await conn.fetch("""
                SELECT
                    r3.company_id,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score,
                    CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END as is_failure
                FROM raymonds_index_v3 r3
                LEFT JOIN (
                    SELECT DISTINCT company_id, id
                    FROM company_labels
                    WHERE label_type = 'FAILURE'
                      AND confidence >= 0.9
                ) cl ON r3.company_id = cl.company_id
                WHERE r3.cei_score IS NOT NULL
                  AND r3.rii_score IS NOT NULL
                  AND r3.cgi_score IS NOT NULL
                  AND r3.mai_score IS NOT NULL
            """)

            X = []
            y = []

            for row in rows:
                X.append({
                    'CEI': float(row['cei_score']),
                    'RII': float(row['rii_score']),
                    'CGI': float(row['cgi_score']),
                    'MAI': float(row['mai_score']),
                })
                y.append(row['is_failure'])

            logger.info(f"학습 데이터 로드: {len(X)}개 (실패: {sum(y)}개)")
            return X, y

        finally:
            await conn.close()

    def linear_discriminant_analysis(
        self,
        X: List[Dict],
        y: List[int]
    ) -> Dict[str, float]:
        """
        단순화된 판별분석 (numpy/sklearn 없이 구현)

        Fisher의 선형 판별분석 원리:
        - 클래스 간 분산 최대화
        - 클래스 내 분산 최소화
        """
        if not X or len(set(y)) < 2:
            return {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}

        features = ['CEI', 'RII', 'CGI', 'MAI']

        # 클래스별 데이터 분리
        class_0 = [x for x, label in zip(X, y) if label == 0]
        class_1 = [x for x, label in zip(X, y) if label == 1]

        if not class_0 or not class_1:
            return {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}

        # 클래스별 평균 계산
        mean_0 = {f: sum(x[f] for x in class_0) / len(class_0) for f in features}
        mean_1 = {f: sum(x[f] for x in class_1) / len(class_1) for f in features}

        # 클래스 간 차이 (판별력 지표)
        diff = {f: abs(mean_0[f] - mean_1[f]) for f in features}

        # 클래스 내 분산 (각 클래스의 표준편차 합)
        def std(data, feature, mean):
            if len(data) < 2:
                return 1.0
            variance = sum((x[feature] - mean) ** 2 for x in data) / len(data)
            return max(variance ** 0.5, 0.1)  # 0 방지

        within_std = {
            f: std(class_0, f, mean_0[f]) + std(class_1, f, mean_1[f])
            for f in features
        }

        # Fisher 판별비: 클래스 간 차이 / 클래스 내 분산
        fisher_ratio = {f: diff[f] / within_std[f] for f in features}

        # 가중치로 변환 (정규화)
        total = sum(fisher_ratio.values())
        if total == 0:
            return {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}

        weights = {f: fisher_ratio[f] / total for f in features}

        logger.info(f"판별분석 가중치: {weights}")
        logger.info(f"클래스 0 평균: {mean_0}")
        logger.info(f"클래스 1 평균: {mean_1}")

        return weights

    def calculate_score(self, data: Dict, weights: Dict[str, float]) -> float:
        """가중치로 점수 계산 (산술평균)"""
        return sum(data[f] * weights[f] for f in weights)

    def find_optimal_threshold(
        self,
        X: List[Dict],
        y: List[int],
        weights: Dict[str, float]
    ) -> float:
        """최적 임계값 찾기 (F1 점수 최대화)"""
        scores = [self.calculate_score(x, weights) for x in X]

        # 정렬된 점수에서 임계값 후보 생성
        unique_scores = sorted(set(scores))

        best_threshold = 30.0
        best_f1 = 0.0

        for threshold in unique_scores:
            predictions = [1 if s < threshold else 0 for s in scores]

            # F1 계산
            tp = sum(1 for p, a in zip(predictions, y) if p == 1 and a == 1)
            fp = sum(1 for p, a in zip(predictions, y) if p == 1 and a == 0)
            fn = sum(1 for p, a in zip(predictions, y) if p == 0 and a == 1)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold

        return best_threshold

    def evaluate(
        self,
        X: List[Dict],
        y: List[int],
        weights: Dict[str, float],
        threshold: float
    ) -> Tuple[float, float, float]:
        """모델 평가"""
        scores = [self.calculate_score(x, weights) for x in X]
        predictions = [1 if s < threshold else 0 for s in scores]

        tp = sum(1 for p, a in zip(predictions, y) if p == 1 and a == 1)
        fp = sum(1 for p, a in zip(predictions, y) if p == 1 and a == 0)
        fn = sum(1 for p, a in zip(predictions, y) if p == 0 and a == 1)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return f1, precision, recall

    def cross_validate(
        self,
        X: List[Dict],
        y: List[int],
        weights: Dict[str, float],
        n_folds: int = 5
    ) -> List[float]:
        """K-Fold 교차 검증"""
        n = len(X)
        fold_size = n // n_folds

        f1_scores = []

        for fold in range(n_folds):
            # 테스트셋 인덱스
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < n_folds - 1 else n

            # 분할
            X_train = X[:test_start] + X[test_end:]
            y_train = y[:test_start] + y[test_end:]
            X_test = X[test_start:test_end]
            y_test = y[test_start:test_end]

            # 학습 (가중치는 고정, 임계값만 조정)
            threshold = self.find_optimal_threshold(X_train, y_train, weights)

            # 평가
            f1, _, _ = self.evaluate(X_test, y_test, weights, threshold)
            f1_scores.append(f1)

        return f1_scores

    async def optimize(self) -> OptimizationResult:
        """가중치 최적화 실행"""
        X, y = await self.load_training_data()

        if sum(y) < 10:
            logger.warning("실패 기업이 10개 미만입니다. 결과의 신뢰도가 낮을 수 있습니다.")

        # 판별분석
        weights = self.linear_discriminant_analysis(X, y)

        # 최적 임계값
        threshold = self.find_optimal_threshold(X, y, weights)

        # 평가
        f1, precision, recall = self.evaluate(X, y, weights, threshold)

        # 교차 검증
        cv_scores = self.cross_validate(X, y, weights)
        avg_cv_f1 = sum(cv_scores) / len(cv_scores) if cv_scores else 0

        logger.info(f"최적화 완료")
        logger.info(f"  가중치: {weights}")
        logger.info(f"  임계값: {threshold:.2f}")
        logger.info(f"  F1 Score: {f1:.3f}")
        logger.info(f"  CV F1 Score: {avg_cv_f1:.3f}")

        return OptimizationResult(
            method='Linear Discriminant Analysis',
            weights=weights,
            f1_score=f1,
            precision=precision,
            recall=recall,
            threshold=threshold,
            sample_size=len(X),
            failure_count=sum(y),
        )

    def print_report(self, requirements: Dict, result: Optional[OptimizationResult] = None):
        """결과 보고서 출력"""
        print("\n" + "=" * 70)
        print("RaymondsIndex v3.0 가중치 최적화 보고서 (Option C)")
        print("=" * 70)

        print("\n## 실행 요건 확인")
        print("-" * 50)
        print(f"v3.0 계산 완료 기업:  {requirements['v3_calculated']:>6}개 (요건: 500+)")
        print(f"실패 기업 레이블:     {requirements['failure_labeled']:>6}개")
        print(f"고신뢰도 실패 기업:   {requirements['high_conf_failure']:>6}개 (요건: 50+)")

        if requirements['requirements_met']:
            print("\n✅ Option C 실행 요건 충족")
        else:
            print("\n❌ Option C 실행 요건 미충족")
            if requirements['v3_calculated'] < 500:
                print(f"   - v3.0 계산 필요: {500 - requirements['v3_calculated']}개 추가")
            if requirements['high_conf_failure'] < 50:
                print(f"   - 실패 기업 레이블 필요: {50 - requirements['high_conf_failure']}개 추가")

        if result:
            print("\n## 최적화 결과")
            print("-" * 50)
            print(f"방법론: {result.method}")
            print(f"샘플 크기: {result.sample_size}개 (실패: {result.failure_count}개)")

            print("\n### 최적 가중치")
            current_weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
            print(f"{'지표':<6} {'현재':>10} {'최적화':>10} {'변화':>10}")
            print("-" * 40)
            for key in ['CEI', 'RII', 'CGI', 'MAI']:
                current = current_weights[key]
                optimized = result.weights[key]
                change = optimized - current
                sign = '+' if change >= 0 else ''
                print(f"{key:<6} {current:>10.1%} {optimized:>10.1%} {sign}{change:>9.1%}")

            print(f"\n### 예측 성능")
            print("-" * 40)
            print(f"F1 Score:  {result.f1_score:.3f}")
            print(f"Precision: {result.precision:.3f}")
            print(f"Recall:    {result.recall:.3f}")
            print(f"Threshold: {result.threshold:.2f}")

            # 권장 사항
            print("\n### 권장 사항")
            print("-" * 40)
            if result.f1_score >= 0.7:
                print("✅ F1 Score ≥ 0.7 - 최적화 가중치 적용 권장")
            else:
                print(f"⚠️ F1 Score {result.f1_score:.3f} < 0.7 - 추가 데이터 수집 권장")


async def main():
    parser = argparse.ArgumentParser(description='통계적 가중치 최적화 (Option C)')
    parser.add_argument('--check-requirements', action='store_true', help='실행 요건 확인')
    parser.add_argument('--optimize', action='store_true', help='가중치 최적화 실행')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 실행')
    parser.add_argument('--report', action='store_true', help='전체 보고서')

    args = parser.parse_args()

    optimizer = WeightOptimizer()

    requirements = await optimizer.check_requirements()

    if args.check_requirements or args.report:
        optimizer.print_report(requirements)

    if args.optimize or args.report:
        if requirements['v3_calculated'] > 0:
            result = await optimizer.optimize()
            optimizer.print_report(requirements, result)
        else:
            print("\n❌ v3.0 계산 결과가 없습니다. 먼저 v3.0 계산을 실행하세요.")


if __name__ == '__main__':
    asyncio.run(main())
