#!/usr/bin/env python3
"""
RaymondsIndex v3.0 Option C: 로컬 가중치 최적화

⚠️ 주의: 이 스크립트는 프로덕션 DB/백엔드에 어떤 변경도 하지 않습니다.
- DB에서 READ ONLY로 데이터 추출
- 모든 계산은 로컬 메모리에서 수행
- 결과는 로컬 파일(CSV, JSON)로만 저장

사용법:
    # 500개 샘플로 가중치 최적화
    python -m scripts.analysis.option_c_local_optimize --sample 500

    # 전체 데이터로 분석 (시간 오래 걸림)
    python -m scripts.analysis.option_c_local_optimize --full

    # 결과만 확인
    python -m scripts.analysis.option_c_local_optimize --report
"""

import argparse
import asyncio
import csv
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import math
import random

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 데이터 클래스
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompanySample:
    """분석용 기업 샘플"""
    company_id: str
    company_name: str
    ticker: str
    is_failure: bool
    failure_reason: Optional[str]
    confidence: float
    cei_score: float
    rii_score: float
    cgi_score: float
    mai_score: float
    total_score: float


@dataclass
class OptimizationResult:
    """최적화 결과"""
    method: str
    weights: Dict[str, float]
    f1_score: float
    precision: float
    recall: float
    auc_roc: float
    threshold: float
    cv_scores: List[float]
    cv_mean: float
    cv_std: float


@dataclass
class FinalReport:
    """최종 분석 보고서"""
    timestamp: str
    sample_size: int
    failure_count: int
    normal_count: int

    # 각 방법별 결과
    lda_result: Optional[OptimizationResult]
    logistic_result: Optional[OptimizationResult]
    rf_result: Optional[OptimizationResult]

    # 앙상블 결과
    ensemble_weights: Dict[str, float]
    ensemble_f1: float
    ensemble_auc: float

    # 현재 가중치와 비교
    current_weights: Dict[str, float]
    improvement: float

    # 권장사항
    recommendation: str


# ═══════════════════════════════════════════════════════════════════════════════
# 로컬 전용 분석기
# ═══════════════════════════════════════════════════════════════════════════════

class OptionCLocalOptimizer:
    """
    Option C 로컬 가중치 최적화기

    ⚠️ 프로덕션 영향 없음:
    - DB는 READ ONLY 접근
    - 모든 계산은 메모리에서 수행
    - 결과는 로컬 파일로만 저장
    """

    CURRENT_WEIGHTS = {
        'CEI': 0.20,
        'RII': 0.35,
        'CGI': 0.25,
        'MAI': 0.20,
    }

    # 고신뢰도 실패 사유 (Tier 1-2)
    # Tier 1: 명확한 실패 지표 (재무적 위기의 명확한 증거)
    # Tier 2: 잠재적 실패 지표 (외부 규제/감사 기반)
    TIER1_FAILURES = [
        'EMBEZZLEMENT',      # 횡령/배임 (가장 명확한 실패)
        'CAPITAL_EROSION',   # 자본잠식 (재무적 실패)
        'CONTINUOUS_LOSS',   # 3년 연속 적자 (지속적 재무 악화)
    ]

    TIER2_FAILURES = [
        'AUDIT_QUALIFIED',   # 감사의견 한정
        'MANAGED_STOCK',     # 관리종목
    ]

    HIGH_CONFIDENCE_FAILURES = TIER1_FAILURES + TIER2_FAILURES

    def __init__(self, database_url: Optional[str] = None, tier1_only: bool = False):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

        if self.database_url.startswith('postgresql+asyncpg://'):
            self.database_url = self.database_url.replace('postgresql+asyncpg://', 'postgresql://')

        self.tier1_only = tier1_only
        self.failure_types = self.TIER1_FAILURES if tier1_only else self.HIGH_CONFIDENCE_FAILURES

        self.samples: List[CompanySample] = []
        self.results_dir = os.path.join(
            os.path.dirname(__file__),
            '..', '..', 'data', 'option_c_results'
        )
        os.makedirs(self.results_dir, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 1: 데이터 추출 (READ ONLY)
    # ═══════════════════════════════════════════════════════════════════════════

    async def extract_samples(self, sample_size: int = 500) -> List[CompanySample]:
        """
        DB에서 샘플 데이터 추출 (READ ONLY)

        ⚠️ SELECT 쿼리만 사용, INSERT/UPDATE/DELETE 없음
        """
        logger.info(f"샘플 추출 시작 (목표: {sample_size}개)")

        conn = await asyncpg.connect(self.database_url)

        try:
            # 1. 실패 기업 추출 (tier1_only에 따라 다르게)
            tier_label = "Tier 1 only" if self.tier1_only else "Tier 1-2"
            logger.info(f"실패 기업 필터: {tier_label} ({', '.join(self.failure_types)})")

            # 동적으로 IN 절 생성
            placeholders = ', '.join(f"'{ft}'" for ft in self.failure_types)

            failure_rows = await conn.fetch(f"""
                SELECT DISTINCT
                    r3.company_id,
                    c.name as company_name,
                    c.ticker,
                    cl.failure_reason,
                    cl.confidence,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score,
                    r3.total_score
                FROM raymonds_index_v3 r3
                JOIN companies c ON c.id = r3.company_id
                JOIN company_labels cl ON cl.company_id = r3.company_id
                WHERE r3.fiscal_year = 2024
                  AND cl.label_type = 'FAILURE'
                  AND cl.confidence >= 0.85
                  AND cl.failure_reason IN ({placeholders})
                  AND r3.cei_score IS NOT NULL
                  AND r3.rii_score IS NOT NULL
                  AND r3.cgi_score IS NOT NULL
                  AND r3.mai_score IS NOT NULL
                ORDER BY cl.confidence DESC
                LIMIT $1
            """, int(sample_size * 0.25))  # 실패 기업은 25%

            logger.info(f"실패 기업 추출: {len(failure_rows)}개")

            # 2. 정상 기업 추출 (실패 레이블 없는 기업)
            normal_rows = await conn.fetch("""
                SELECT
                    r3.company_id,
                    c.name as company_name,
                    c.ticker,
                    r3.cei_score,
                    r3.rii_score,
                    r3.cgi_score,
                    r3.mai_score,
                    r3.total_score
                FROM raymonds_index_v3 r3
                JOIN companies c ON c.id = r3.company_id
                WHERE r3.fiscal_year = 2024
                  AND r3.cei_score IS NOT NULL
                  AND r3.rii_score IS NOT NULL
                  AND r3.cgi_score IS NOT NULL
                  AND r3.mai_score IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM company_labels cl
                      WHERE cl.company_id = r3.company_id
                        AND cl.label_type = 'FAILURE'
                  )
                ORDER BY RANDOM()
                LIMIT $1
            """, int(sample_size * 0.75))  # 정상 기업은 75%

            logger.info(f"정상 기업 추출: {len(normal_rows)}개")

            # 샘플 생성
            samples = []

            for row in failure_rows:
                samples.append(CompanySample(
                    company_id=str(row['company_id']),
                    company_name=row['company_name'],
                    ticker=row['ticker'] or '',
                    is_failure=True,
                    failure_reason=row['failure_reason'],
                    confidence=float(row['confidence']),
                    cei_score=float(row['cei_score']),
                    rii_score=float(row['rii_score']),
                    cgi_score=float(row['cgi_score']),
                    mai_score=float(row['mai_score']),
                    total_score=float(row['total_score']),
                ))

            for row in normal_rows:
                samples.append(CompanySample(
                    company_id=str(row['company_id']),
                    company_name=row['company_name'],
                    ticker=row['ticker'] or '',
                    is_failure=False,
                    failure_reason=None,
                    confidence=1.0,
                    cei_score=float(row['cei_score']),
                    rii_score=float(row['rii_score']),
                    cgi_score=float(row['cgi_score']),
                    mai_score=float(row['mai_score']),
                    total_score=float(row['total_score']),
                ))

            self.samples = samples
            logger.info(f"총 샘플: {len(samples)}개 (실패: {len(failure_rows)}, 정상: {len(normal_rows)})")

            return samples

        finally:
            await conn.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 2: 가중치 최적화 (순수 로컬 계산)
    # ═══════════════════════════════════════════════════════════════════════════

    def optimize_lda(self) -> OptimizationResult:
        """
        Method 1: Linear Discriminant Analysis

        Fisher's LDA 직접 구현 (sklearn 의존성 제거)
        """
        logger.info("LDA 최적화 시작...")

        # 데이터 준비
        X = [[s.cei_score, s.rii_score, s.cgi_score, s.mai_score] for s in self.samples]
        y = [1 if s.is_failure else 0 for s in self.samples]

        # 클래스별 분리
        class_0 = [X[i] for i in range(len(y)) if y[i] == 0]
        class_1 = [X[i] for i in range(len(y)) if y[i] == 1]

        if not class_0 or not class_1:
            logger.error("클래스 불균형: 한 클래스에 데이터가 없습니다")
            return self._empty_result('LDA')

        # 클래스별 평균
        mean_0 = [sum(x[i] for x in class_0) / len(class_0) for i in range(4)]
        mean_1 = [sum(x[i] for x in class_1) / len(class_1) for i in range(4)]

        # 클래스 내 분산
        within_var = []
        for i in range(4):
            var_0 = sum((x[i] - mean_0[i])**2 for x in class_0) / len(class_0)
            var_1 = sum((x[i] - mean_1[i])**2 for x in class_1) / len(class_1)
            within_var.append((var_0 + var_1) / 2 + 1e-10)  # 0 방지

        # Fisher Ratio: (클래스 간 차이)^2 / (클래스 내 분산)
        fisher_ratios = []
        for i in range(4):
            ratio = (mean_0[i] - mean_1[i])**2 / within_var[i]
            fisher_ratios.append(ratio)

        # 가중치 변환 (정규화)
        total = sum(fisher_ratios)
        weights = {
            'CEI': fisher_ratios[0] / total,
            'RII': fisher_ratios[1] / total,
            'CGI': fisher_ratios[2] / total,
            'MAI': fisher_ratios[3] / total,
        }

        # 성능 평가
        f1, precision, recall, threshold = self._evaluate_weights(weights, X, y)
        cv_scores = self._cross_validate(weights, X, y, k=5)

        return OptimizationResult(
            method='LDA',
            weights=weights,
            f1_score=f1,
            precision=precision,
            recall=recall,
            auc_roc=self._calculate_auc(weights, X, y),
            threshold=threshold,
            cv_scores=cv_scores,
            cv_mean=sum(cv_scores) / len(cv_scores) if cv_scores else 0,
            cv_std=self._std(cv_scores) if cv_scores else 0,
        )

    def optimize_logistic(self) -> OptimizationResult:
        """
        Method 2: Logistic Regression (경사하강법 직접 구현)
        """
        logger.info("Logistic Regression 최적화 시작...")

        X = [[s.cei_score, s.rii_score, s.cgi_score, s.mai_score] for s in self.samples]
        y = [1 if s.is_failure else 0 for s in self.samples]

        # 정규화
        X_norm, means, stds = self._normalize_features(X)

        # 초기 가중치
        w = [0.25, 0.25, 0.25, 0.25]
        bias = 0.0
        lr = 0.01
        epochs = 1000
        lambda_reg = 0.1  # L2 정규화

        # 경사하강법
        for _ in range(epochs):
            gradients = [0.0] * 4
            grad_bias = 0.0

            for i in range(len(X_norm)):
                # 예측
                z = sum(w[j] * X_norm[i][j] for j in range(4)) + bias
                pred = 1 / (1 + math.exp(-max(-500, min(500, z))))

                # 오차
                error = pred - y[i]

                # 그래디언트
                for j in range(4):
                    gradients[j] += error * X_norm[i][j]
                grad_bias += error

            # 업데이트 (L2 정규화 포함)
            for j in range(4):
                w[j] -= lr * (gradients[j] / len(X_norm) + lambda_reg * w[j])
            bias -= lr * (grad_bias / len(X_norm))

        # 가중치 변환 (절대값 → 비율)
        abs_w = [abs(wj) for wj in w]
        total = sum(abs_w)
        weights = {
            'CEI': abs_w[0] / total,
            'RII': abs_w[1] / total,
            'CGI': abs_w[2] / total,
            'MAI': abs_w[3] / total,
        }

        # 성능 평가
        f1, precision, recall, threshold = self._evaluate_weights(weights, X, y)
        cv_scores = self._cross_validate(weights, X, y, k=5)

        return OptimizationResult(
            method='Logistic',
            weights=weights,
            f1_score=f1,
            precision=precision,
            recall=recall,
            auc_roc=self._calculate_auc(weights, X, y),
            threshold=threshold,
            cv_scores=cv_scores,
            cv_mean=sum(cv_scores) / len(cv_scores) if cv_scores else 0,
            cv_std=self._std(cv_scores) if cv_scores else 0,
        )

    def optimize_feature_importance(self) -> OptimizationResult:
        """
        Method 3: Feature Importance (단순 상관관계 기반)

        Random Forest 없이 간단한 상관계수 기반 중요도 계산
        """
        logger.info("Feature Importance 최적화 시작...")

        X = [[s.cei_score, s.rii_score, s.cgi_score, s.mai_score] for s in self.samples]
        y = [1 if s.is_failure else 0 for s in self.samples]

        # 각 특성과 레이블의 상관계수 계산
        correlations = []
        for j in range(4):
            feature_values = [X[i][j] for i in range(len(X))]
            corr = self._correlation(feature_values, y)
            correlations.append(abs(corr))  # 절대값 (방향 무관)

        # 가중치 변환
        total = sum(correlations) + 1e-10
        weights = {
            'CEI': correlations[0] / total,
            'RII': correlations[1] / total,
            'CGI': correlations[2] / total,
            'MAI': correlations[3] / total,
        }

        # 성능 평가
        f1, precision, recall, threshold = self._evaluate_weights(weights, X, y)
        cv_scores = self._cross_validate(weights, X, y, k=5)

        return OptimizationResult(
            method='FeatureImportance',
            weights=weights,
            f1_score=f1,
            precision=precision,
            recall=recall,
            auc_roc=self._calculate_auc(weights, X, y),
            threshold=threshold,
            cv_scores=cv_scores,
            cv_mean=sum(cv_scores) / len(cv_scores) if cv_scores else 0,
            cv_std=self._std(cv_scores) if cv_scores else 0,
        )

    def ensemble_optimize(self) -> Tuple[Dict[str, float], float, float]:
        """
        앙상블: 3가지 방법의 가중 평균

        가중치: LDA(0.4) + Logistic(0.3) + FeatureImportance(0.3)
        """
        logger.info("앙상블 최적화 시작...")

        lda = self.optimize_lda()
        logistic = self.optimize_logistic()
        fi = self.optimize_feature_importance()

        # 앙상블 가중치
        ensemble = {}
        for key in ['CEI', 'RII', 'CGI', 'MAI']:
            ensemble[key] = (
                0.4 * lda.weights[key] +
                0.3 * logistic.weights[key] +
                0.3 * fi.weights[key]
            )

        # 앙상블 성능 평가
        X = [[s.cei_score, s.rii_score, s.cgi_score, s.mai_score] for s in self.samples]
        y = [1 if s.is_failure else 0 for s in self.samples]

        f1, _, _, _ = self._evaluate_weights(ensemble, X, y)
        auc = self._calculate_auc(ensemble, X, y)

        return ensemble, f1, auc, lda, logistic, fi

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 3: 유틸리티 함수
    # ═══════════════════════════════════════════════════════════════════════════

    def _evaluate_weights(
        self,
        weights: Dict[str, float],
        X: List[List[float]],
        y: List[int]
    ) -> Tuple[float, float, float, float]:
        """가중치로 점수 계산 후 F1, Precision, Recall, 최적 임계값 반환"""

        # 새 가중치로 점수 계산
        scores = []
        for x in X:
            score = (
                weights['CEI'] * x[0] +
                weights['RII'] * x[1] +
                weights['CGI'] * x[2] +
                weights['MAI'] * x[3]
            )
            scores.append(score)

        # 최적 임계값 탐색
        best_f1 = 0
        best_threshold = 0
        best_precision = 0
        best_recall = 0

        # 실패 기업은 점수가 낮다고 가정
        for percentile in range(10, 90, 5):
            threshold = sorted(scores)[int(len(scores) * percentile / 100)]

            # 예측: 점수 < 임계값 → 실패
            predictions = [1 if s < threshold else 0 for s in scores]

            tp = sum(1 for i in range(len(y)) if predictions[i] == 1 and y[i] == 1)
            fp = sum(1 for i in range(len(y)) if predictions[i] == 1 and y[i] == 0)
            fn = sum(1 for i in range(len(y)) if predictions[i] == 0 and y[i] == 1)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
                best_precision = precision
                best_recall = recall

        return best_f1, best_precision, best_recall, best_threshold

    def _cross_validate(
        self,
        weights: Dict[str, float],
        X: List[List[float]],
        y: List[int],
        k: int = 5
    ) -> List[float]:
        """K-Fold 교차 검증"""
        n = len(X)
        fold_size = n // k
        indices = list(range(n))
        random.shuffle(indices)

        cv_scores = []

        for i in range(k):
            # 테스트 인덱스
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < k - 1 else n
            test_indices = set(indices[test_start:test_end])

            # 테스트 데이터
            X_test = [X[j] for j in range(n) if j in test_indices]
            y_test = [y[j] for j in range(n) if j in test_indices]

            # 평가
            f1, _, _, _ = self._evaluate_weights(weights, X_test, y_test)
            cv_scores.append(f1)

        return cv_scores

    def _calculate_auc(
        self,
        weights: Dict[str, float],
        X: List[List[float]],
        y: List[int]
    ) -> float:
        """간단한 AUC 계산 (정확한 ROC가 아닌 근사치)"""
        scores = []
        for x in X:
            score = (
                weights['CEI'] * x[0] +
                weights['RII'] * x[1] +
                weights['CGI'] * x[2] +
                weights['MAI'] * x[3]
            )
            scores.append(score)

        # 실패=1인 경우 점수가 낮다고 가정
        # AUC ≈ P(score_failure < score_normal)
        positives = [scores[i] for i in range(len(y)) if y[i] == 1]
        negatives = [scores[i] for i in range(len(y)) if y[i] == 0]

        if not positives or not negatives:
            return 0.5

        correct = 0
        total = 0
        for p in positives:
            for n in negatives:
                total += 1
                if p < n:  # 실패 기업 점수가 낮으면 정답
                    correct += 1
                elif p == n:
                    correct += 0.5

        return correct / total if total > 0 else 0.5

    def _correlation(self, x: List[float], y: List[int]) -> float:
        """피어슨 상관계수"""
        n = len(x)
        if n == 0:
            return 0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denom_x == 0 or denom_y == 0:
            return 0

        return numerator / (denom_x * denom_y)

    def _normalize_features(
        self, X: List[List[float]]
    ) -> Tuple[List[List[float]], List[float], List[float]]:
        """특성 정규화 (Z-score)"""
        n = len(X)
        if n == 0:
            return X, [0]*4, [1]*4

        means = []
        stds = []

        for j in range(4):
            vals = [X[i][j] for i in range(n)]
            m = sum(vals) / n
            s = (sum((v - m)**2 for v in vals) / n) ** 0.5 + 1e-10
            means.append(m)
            stds.append(s)

        X_norm = []
        for i in range(n):
            X_norm.append([(X[i][j] - means[j]) / stds[j] for j in range(4)])

        return X_norm, means, stds

    def _std(self, values: List[float]) -> float:
        """표준편차"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        return (sum((v - mean)**2 for v in values) / len(values)) ** 0.5

    def _empty_result(self, method: str) -> OptimizationResult:
        """빈 결과"""
        return OptimizationResult(
            method=method,
            weights={'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25},
            f1_score=0,
            precision=0,
            recall=0,
            auc_roc=0.5,
            threshold=0,
            cv_scores=[],
            cv_mean=0,
            cv_std=0,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 4: 결과 저장 (로컬 파일만)
    # ═══════════════════════════════════════════════════════════════════════════

    def save_results(
        self,
        lda: OptimizationResult,
        logistic: OptimizationResult,
        fi: OptimizationResult,
        ensemble: Dict[str, float],
        ensemble_f1: float,
        ensemble_auc: float,
    ):
        """결과를 로컬 파일로 저장 (DB 변경 없음)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        tier_suffix = '_tier1' if self.tier1_only else '_tier12'

        # 1. JSON 결과 저장
        result = {
            'timestamp': timestamp,
            'tier1_only': self.tier1_only,
            'failure_types': self.failure_types,
            'sample_size': len(self.samples),
            'failure_count': sum(1 for s in self.samples if s.is_failure),
            'normal_count': sum(1 for s in self.samples if not s.is_failure),
            'methods': {
                'LDA': asdict(lda),
                'Logistic': asdict(logistic),
                'FeatureImportance': asdict(fi),
            },
            'ensemble': {
                'weights': ensemble,
                'f1_score': ensemble_f1,
                'auc_roc': ensemble_auc,
            },
            'current_weights': self.CURRENT_WEIGHTS,
            'improvement': {
                'f1_delta': ensemble_f1 - 0.578,  # Phase 5 결과 대비
            },
        }

        json_path = os.path.join(self.results_dir, f'option_c_result{tier_suffix}_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON 결과 저장: {json_path}")

        # 2. CSV 요약 저장
        csv_path = os.path.join(self.results_dir, f'option_c_summary{tier_suffix}_{timestamp}.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Method', 'CEI', 'RII', 'CGI', 'MAI', 'F1', 'AUC', 'CV_Mean', 'CV_Std'])
            writer.writerow(['Current', '20%', '35%', '25%', '20%', '0.578', '-', '-', '-'])
            writer.writerow([
                'LDA',
                f"{lda.weights['CEI']:.1%}",
                f"{lda.weights['RII']:.1%}",
                f"{lda.weights['CGI']:.1%}",
                f"{lda.weights['MAI']:.1%}",
                f"{lda.f1_score:.3f}",
                f"{lda.auc_roc:.3f}",
                f"{lda.cv_mean:.3f}",
                f"{lda.cv_std:.3f}",
            ])
            writer.writerow([
                'Logistic',
                f"{logistic.weights['CEI']:.1%}",
                f"{logistic.weights['RII']:.1%}",
                f"{logistic.weights['CGI']:.1%}",
                f"{logistic.weights['MAI']:.1%}",
                f"{logistic.f1_score:.3f}",
                f"{logistic.auc_roc:.3f}",
                f"{logistic.cv_mean:.3f}",
                f"{logistic.cv_std:.3f}",
            ])
            writer.writerow([
                'FeatureImportance',
                f"{fi.weights['CEI']:.1%}",
                f"{fi.weights['RII']:.1%}",
                f"{fi.weights['CGI']:.1%}",
                f"{fi.weights['MAI']:.1%}",
                f"{fi.f1_score:.3f}",
                f"{fi.auc_roc:.3f}",
                f"{fi.cv_mean:.3f}",
                f"{fi.cv_std:.3f}",
            ])
            writer.writerow([
                'Ensemble',
                f"{ensemble['CEI']:.1%}",
                f"{ensemble['RII']:.1%}",
                f"{ensemble['CGI']:.1%}",
                f"{ensemble['MAI']:.1%}",
                f"{ensemble_f1:.3f}",
                f"{ensemble_auc:.3f}",
                '-',
                '-',
            ])
        logger.info(f"CSV 요약 저장: {csv_path}")

        # 3. 샘플 데이터 저장
        samples_path = os.path.join(self.results_dir, f'samples{tier_suffix}_{timestamp}.csv')
        with open(samples_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'company_id', 'company_name', 'ticker',
                'is_failure', 'failure_reason', 'confidence',
                'CEI', 'RII', 'CGI', 'MAI', 'total_score'
            ])
            for s in self.samples:
                writer.writerow([
                    s.company_id, s.company_name, s.ticker,
                    s.is_failure, s.failure_reason or '', s.confidence,
                    f"{s.cei_score:.2f}", f"{s.rii_score:.2f}",
                    f"{s.cgi_score:.2f}", f"{s.mai_score:.2f}",
                    f"{s.total_score:.2f}",
                ])
        logger.info(f"샘플 데이터 저장: {samples_path}")

    def print_report(
        self,
        lda: OptimizationResult,
        logistic: OptimizationResult,
        fi: OptimizationResult,
        ensemble: Dict[str, float],
        ensemble_f1: float,
        ensemble_auc: float,
    ):
        """결과 출력"""
        tier_label = "Tier 1 only" if self.tier1_only else "Tier 1-2"
        print("\n" + "=" * 70)
        print(f"RaymondsIndex v3.0 Option C: 로컬 가중치 최적화 결과 [{tier_label}]")
        print("=" * 70)
        print("⚠️  이 분석은 프로덕션 DB에 어떤 변경도 하지 않았습니다.")
        print(f"📊 실패 기업 필터: {', '.join(self.failure_types)}")
        print("=" * 70)

        print(f"\n## 샘플 정보")
        print(f"총 샘플: {len(self.samples)}개")
        print(f"  - 실패 기업: {sum(1 for s in self.samples if s.is_failure)}개")
        print(f"  - 정상 기업: {sum(1 for s in self.samples if not s.is_failure)}개")

        print(f"\n## 방법별 최적 가중치")
        print("-" * 70)
        print(f"{'Method':<20} {'CEI':>10} {'RII':>10} {'CGI':>10} {'MAI':>10} {'F1':>8} {'AUC':>8}")
        print("-" * 70)
        print(f"{'Current':<20} {'20.0%':>10} {'35.0%':>10} {'25.0%':>10} {'20.0%':>10} {'0.578':>8} {'-':>8}")
        print(f"{'LDA':<20} {lda.weights['CEI']:>9.1%} {lda.weights['RII']:>9.1%} {lda.weights['CGI']:>9.1%} {lda.weights['MAI']:>9.1%} {lda.f1_score:>8.3f} {lda.auc_roc:>8.3f}")
        print(f"{'Logistic':<20} {logistic.weights['CEI']:>9.1%} {logistic.weights['RII']:>9.1%} {logistic.weights['CGI']:>9.1%} {logistic.weights['MAI']:>9.1%} {logistic.f1_score:>8.3f} {logistic.auc_roc:>8.3f}")
        print(f"{'FeatureImportance':<20} {fi.weights['CEI']:>9.1%} {fi.weights['RII']:>9.1%} {fi.weights['CGI']:>9.1%} {fi.weights['MAI']:>9.1%} {fi.f1_score:>8.3f} {fi.auc_roc:>8.3f}")
        print("-" * 70)
        print(f"{'★ Ensemble':<20} {ensemble['CEI']:>9.1%} {ensemble['RII']:>9.1%} {ensemble['CGI']:>9.1%} {ensemble['MAI']:>9.1%} {ensemble_f1:>8.3f} {ensemble_auc:>8.3f}")

        print(f"\n## 교차 검증 (5-Fold)")
        print("-" * 50)
        print(f"LDA:              Mean={lda.cv_mean:.3f}, Std={lda.cv_std:.3f}")
        print(f"Logistic:         Mean={logistic.cv_mean:.3f}, Std={logistic.cv_std:.3f}")
        print(f"FeatureImportance: Mean={fi.cv_mean:.3f}, Std={fi.cv_std:.3f}")

        print(f"\n## 가중치 변화 (Current → Ensemble)")
        print("-" * 50)
        for key in ['CEI', 'RII', 'CGI', 'MAI']:
            current = self.CURRENT_WEIGHTS[key]
            new = ensemble[key]
            delta = (new - current) * 100
            direction = "⬆️" if delta > 0 else "⬇️" if delta < 0 else "→"
            print(f"{key}: {current:.0%} → {new:.1%} ({direction} {abs(delta):.1f}%p)")

        print(f"\n## 권장 사항")
        print("-" * 50)
        if ensemble_f1 >= 0.7:
            print("✅ F1 >= 0.7 달성 - 앙상블 가중치 적용 권장")
        else:
            print(f"⚠️ F1 = {ensemble_f1:.3f} < 0.7 - 추가 데이터 수집 후 재분석 권장")

        if ensemble_auc >= 0.75:
            print("✅ AUC >= 0.75 달성 - 예측력 충분")
        else:
            print(f"⚠️ AUC = {ensemble_auc:.3f} < 0.75 - 특성 엔지니어링 검토 필요")

        print("\n" + "=" * 70)
        print("결과 파일 위치:", self.results_dir)
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description='RaymondsIndex v3.0 Option C: 로컬 가중치 최적화 (프로덕션 영향 없음)'
    )
    parser.add_argument('--sample', type=int, default=500, help='샘플 크기 (기본: 500)')
    parser.add_argument('--full', action='store_true', help='전체 데이터 사용')
    parser.add_argument('--report', action='store_true', help='기존 결과 출력만')
    parser.add_argument('--tier1-only', action='store_true',
                        help='Tier 1 실패만 사용 (EMBEZZLEMENT, CAPITAL_EROSION)')

    args = parser.parse_args()

    optimizer = OptionCLocalOptimizer(tier1_only=args.tier1_only)

    if args.report:
        # 기존 결과 파일 출력
        results_dir = optimizer.results_dir
        files = sorted([f for f in os.listdir(results_dir) if f.endswith('.json')], reverse=True)
        if files:
            latest = os.path.join(results_dir, files[0])
            with open(latest, 'r', encoding='utf-8') as f:
                result = json.load(f)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("저장된 결과가 없습니다. --sample 옵션으로 먼저 분석을 실행하세요.")
        return

    # 샘플 추출
    sample_size = 10000 if args.full else args.sample
    await optimizer.extract_samples(sample_size)

    if len(optimizer.samples) < 50:
        logger.error(f"샘플이 너무 적습니다: {len(optimizer.samples)}개")
        return

    # 최적화 실행
    ensemble, ensemble_f1, ensemble_auc, lda, logistic, fi = optimizer.ensemble_optimize()

    # 결과 저장 (로컬 파일만)
    optimizer.save_results(lda, logistic, fi, ensemble, ensemble_f1, ensemble_auc)

    # 보고서 출력
    optimizer.print_report(lda, logistic, fi, ensemble, ensemble_f1, ensemble_auc)


if __name__ == '__main__':
    asyncio.run(main())
