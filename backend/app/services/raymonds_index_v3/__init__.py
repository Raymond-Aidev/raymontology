"""
RaymondsIndex v3.0 계산 엔진

HDI 정규화 방식 적용 (OECD Handbook 2008, UNDP HDI 2010)

핵심 변경사항 (v2.1 → v3.0):
- Min-Max 정규화 (0~100 범위)
- Winsorizing (상하위 2.5% 극단값 처리)
- Clamping (범위 제한) - -999% 버그 방지
- 기하평균 집계 (산술평균 → 기하평균)
- 데이터 검증 레이어 추가

모듈 구조:
- constants.py: 상수 정의 (GOALPOSTS, WEIGHTS, CLAMP_LIMITS)
- normalizers.py: 정규화 함수 (min_max, v_score, clamp, geometric_mean)
- validators.py: 데이터 검증기 (DataValidator)
- calculators/: Sub-Index 계산기 (CEI, RII, CGI, MAI)
- engine.py: 통합 계산기 (RaymondsIndexCalculatorV3)
"""

from .constants import (
    CLAMP_LIMITS,
    GOALPOSTS,
    SUBINDEX_WEIGHTS,
    METRIC_WEIGHTS,
    GRADE_THRESHOLDS,
    MIN_DENOMINATOR,
    MIN_REQUIRED_YEARS,
    WINSORIZE_PERCENTILE,
)
from .normalizers import (
    min_max_normalize,
    v_score_normalize,
    inverse_normalize,
    clamp,
    winsorize,
    geometric_mean_weighted,
)
from .validators import DataValidator, ValidationResult

__version__ = "3.0.0"
__all__ = [
    # Constants
    "CLAMP_LIMITS",
    "GOALPOSTS",
    "SUBINDEX_WEIGHTS",
    "METRIC_WEIGHTS",
    "GRADE_THRESHOLDS",
    "MIN_DENOMINATOR",
    "MIN_REQUIRED_YEARS",
    "WINSORIZE_PERCENTILE",
    # Normalizers
    "min_max_normalize",
    "v_score_normalize",
    "inverse_normalize",
    "clamp",
    "winsorize",
    "geometric_mean_weighted",
    # Validators
    "DataValidator",
    "ValidationResult",
]
