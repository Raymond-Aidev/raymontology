"""
Sub-Index 계산기 기본 클래스
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from ..constants import GOALPOSTS, METRIC_WEIGHTS
from ..normalizers import (
    min_max_normalize,
    v_score_normalize,
    inverse_normalize,
    clamp,
    geometric_mean_weighted,
    safe_divide,
)


@dataclass
class CalculationResult:
    """Sub-Index 계산 결과"""
    score: float  # 정규화된 점수 (0-100)
    raw_metrics: Dict[str, float] = field(default_factory=dict)  # 원본 지표
    normalized_metrics: Dict[str, float] = field(default_factory=dict)  # 정규화된 지표
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'raw': self.raw_metrics,
            'normalized': self.normalized_metrics,
            'warnings': self.warnings,
        }


class SubIndexCalculator(ABC):
    """
    Sub-Index 계산기 추상 기본 클래스

    각 Sub-Index Calculator는 다음을 구현해야 함:
    1. _calculate_raw_metrics(): 원본 지표 계산
    2. _normalize_metrics(): 지표 정규화
    3. calculate(): 전체 계산 수행
    """

    # 하위 클래스에서 설정
    INDEX_NAME: str = ""  # 'CEI', 'RII', 'CGI', 'MAI'

    def __init__(self):
        self.goalposts = GOALPOSTS.get(self.INDEX_NAME, {})
        self.weights = METRIC_WEIGHTS.get(self.INDEX_NAME, {})

    @abstractmethod
    def _calculate_raw_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        원본 지표 계산

        Args:
            data: 재무 데이터 (연도별 리스트 또는 단일 값)

        Returns:
            원본 지표 딕셔너리
        """
        pass

    def _normalize_metrics(self, raw: Dict[str, float]) -> Dict[str, float]:
        """
        지표 정규화

        Args:
            raw: 원본 지표 딕셔너리

        Returns:
            정규화된 지표 딕셔너리 (0-100)
        """
        normalized = {}

        for metric_name, value in raw.items():
            if metric_name not in self.goalposts:
                # goalpost가 없으면 그대로 사용 (이미 0-100이라고 가정)
                normalized[metric_name] = max(0, min(100, value or 0))
                continue

            gp = self.goalposts[metric_name]
            method = gp.get('method', 'min_max')

            if method == 'min_max':
                normalized[metric_name] = min_max_normalize(
                    value,
                    gp['min'],
                    gp['max']
                )
            elif method == 'v_score':
                normalized[metric_name] = v_score_normalize(
                    value,
                    optimal=gp.get('optimal', (gp['min'] + gp['max']) / 2),
                    min_val=gp['min'],
                    max_val=gp['max']
                )
            elif method == 'inverse':
                normalized[metric_name] = inverse_normalize(
                    value,
                    gp['min'],
                    gp['max']
                )
            else:
                normalized[metric_name] = max(0, min(100, value or 0))

        return normalized

    def _aggregate(self, normalized: Dict[str, float]) -> float:
        """
        정규화된 지표를 가중 기하평균으로 집계

        Args:
            normalized: 정규화된 지표 딕셔너리

        Returns:
            Sub-Index 점수 (0-100)
        """
        return geometric_mean_weighted(normalized, self.weights)

    def calculate(self, data: Dict[str, Any]) -> CalculationResult:
        """
        Sub-Index 계산 수행

        Args:
            data: 재무 데이터

        Returns:
            CalculationResult
        """
        warnings = []

        # 1. 원본 지표 계산
        raw = self._calculate_raw_metrics(data)

        # 2. 정규화
        normalized = self._normalize_metrics(raw)

        # 3. 집계
        score = self._aggregate(normalized)

        return CalculationResult(
            score=round(score, 2),
            raw_metrics=raw,
            normalized_metrics=normalized,
            warnings=warnings,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 유틸리티 메서드
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_latest(self, data: Dict[str, Any], key: str, default: float = 0.0) -> float:
        """리스트에서 최신 값 추출"""
        value = data.get(key)
        if value is None:
            return default
        if isinstance(value, list):
            for v in reversed(value):
                if v is not None:
                    return float(v)
            return default
        return float(value)

    def _get_previous(self, data: Dict[str, Any], key: str, default: float = 0.0) -> float:
        """리스트에서 이전 값 추출"""
        value = data.get(key)
        if value is None:
            return default
        if isinstance(value, list) and len(value) >= 2:
            for v in reversed(value[:-1]):
                if v is not None:
                    return float(v)
            return default
        return default

    def _get_all_values(self, data: Dict[str, Any], key: str) -> List[float]:
        """리스트에서 모든 값 추출 (None 제외)"""
        value = data.get(key)
        if value is None:
            return []
        if isinstance(value, list):
            return [float(v) for v in value if v is not None]
        return [float(value)]

    def _safe_divide(self, numerator: Optional[float], denominator: Optional[float]) -> float:
        """안전한 나눗셈"""
        return safe_divide(numerator, denominator, 0.0)

    def _analyze_trend(self, values: List[float]) -> Tuple[str, float]:
        """
        추세 분석 (선형 회귀 기반)

        Returns:
            Tuple[추세 문자열, 기울기]
            - 'increasing': 증가 추세
            - 'stable': 안정
            - 'decreasing': 감소 추세
        """
        if len(values) < 2:
            return 'stable', 0.0

        # 0인 값 제외
        valid_values = [v for v in values if v != 0]
        if len(valid_values) < 2:
            return 'stable', 0.0

        n = len(valid_values)
        x_mean = (n - 1) / 2
        y_mean = sum(valid_values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(valid_values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 'stable', 0.0

        slope = numerator / denominator
        relative_slope = slope / abs(y_mean) if y_mean != 0 else 0

        if relative_slope > 0.05:
            return 'increasing', relative_slope
        elif relative_slope < -0.05:
            return 'decreasing', relative_slope
        return 'stable', relative_slope

    def _coefficient_of_variation(self, values: List[float]) -> float:
        """변동계수 계산 (표준편차 / 평균)"""
        if len(values) < 2:
            return 0.0

        abs_values = [abs(v) for v in values if v != 0]
        if len(abs_values) < 2:
            return 0.0

        mean = sum(abs_values) / len(abs_values)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in abs_values) / len(abs_values)
        std = variance ** 0.5

        return std / mean
