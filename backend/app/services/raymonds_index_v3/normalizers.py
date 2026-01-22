"""
RaymondsIndex v3.0 정규화 함수

참조 문헌:
- OECD Handbook on Constructing Composite Indicators (2008)
- UNDP Human Development Index Technical Notes (2010~)

핵심 함수:
- min_max_normalize: HDI 방식 Min-Max 정규화
- v_score_normalize: V자 스코어링 (최적값이 중간인 지표)
- inverse_normalize: 역방향 정규화 (낮을수록 좋은 지표)
- clamp: 범위 제한 (-999% 버그 방지)
- winsorize: 극단값 처리
- geometric_mean_weighted: 가중 기하평균 (HDI 2010 방식)
"""

from typing import Dict, List, Optional
from .constants import CLAMP_LIMITS


def min_max_normalize(value: float, min_val: float, max_val: float) -> float:
    """
    HDI 방식 Min-Max 정규화

    공식: (실제값 - 최소값) / (최대값 - 최소값) × 100

    Args:
        value: 원본 값
        min_val: 최소값 (goalpost)
        max_val: 최대값 (goalpost)

    Returns:
        0~100 범위의 정규화된 값

    Examples:
        >>> min_max_normalize(1.5, 0.1, 3.0)  # 자산회전율 1.5
        48.28  # (1.5 - 0.1) / (3.0 - 0.1) * 100
    """
    if max_val <= min_val:
        return 50.0  # 잘못된 경계값

    if value is None:
        return 0.0

    if value <= min_val:
        return 0.0
    if value >= max_val:
        return 100.0

    return ((value - min_val) / (max_val - min_val)) * 100


def v_score_normalize(
    value: float,
    optimal: float,
    min_val: float,
    max_val: float
) -> float:
    """
    V자 스코어링: 최적값에서 100점, 양쪽 끝에서 0점

    적용 대상:
    - 투자괴리율 (0이 최적)
    - 주주환원율 (35%가 최적)
    - 이익품질 (1이 최적)

    Args:
        value: 원본 값
        optimal: 최적값 (100점)
        min_val: 최소값 (0점)
        max_val: 최대값 (0점)

    Returns:
        0~100 범위의 정규화된 값

    Examples:
        >>> v_score_normalize(0, optimal=0, min_val=-50, max_val=50)
        100  # 투자괴리율 0% → 최적
        >>> v_score_normalize(25, optimal=0, min_val=-50, max_val=50)
        50   # 투자괴리율 +25% → 중간
        >>> v_score_normalize(-50, optimal=0, min_val=-50, max_val=50)
        0    # 투자괴리율 -50% → 최저
    """
    if value is None:
        return 50.0  # 데이터 없으면 중립

    if value <= min_val or value >= max_val:
        return 0.0

    if value <= optimal:
        # 음수 영역: min_val → 0점, optimal → 100점
        if optimal == min_val:
            return 100.0
        return ((value - min_val) / (optimal - min_val)) * 100
    else:
        # 양수 영역: optimal → 100점, max_val → 0점
        if max_val == optimal:
            return 100.0
        return 100 - ((value - optimal) / (max_val - optimal)) * 100


def inverse_normalize(value: float, min_val: float, max_val: float) -> float:
    """
    역방향 정규화: 낮을수록 좋은 지표

    적용 대상:
    - Debt/EBITDA (낮을수록 좋음)
    - CAPEX 변동계수 (낮을수록 좋음)

    Args:
        value: 원본 값
        min_val: 최소값 (100점)
        max_val: 최대값 (0점)

    Returns:
        0~100 범위의 정규화된 값

    Examples:
        >>> inverse_normalize(1, min_val=0, max_val=10)
        90   # Debt/EBITDA 1x → 우수
        >>> inverse_normalize(5, min_val=0, max_val=10)
        50   # Debt/EBITDA 5x → 중간
    """
    if max_val <= min_val:
        return 50.0

    if value is None:
        return 50.0

    if value <= min_val:
        return 100.0
    if value >= max_val:
        return 0.0

    return 100 - ((value - min_val) / (max_val - min_val)) * 100


def clamp(value: float, metric: str) -> float:
    """
    값을 지정된 범위로 제한 - ⭐ -999% 버그 방지

    목적:
    - 분모가 극소값일 때 발생하는 극단적인 비율 방지
    - 예: CAPEX 0.001억 → 5억 증가 시 99,900% 성장률 → 500%로 제한

    Args:
        value: 원본 값
        metric: 지표명 (CLAMP_LIMITS 키)

    Returns:
        제한된 값

    Examples:
        >>> clamp(99900, 'capex_growth')
        500   # 상한 제한
        >>> clamp(-99890, 'investment_gap')
        -100  # 하한 제한
    """
    if value is None:
        return 0.0

    if metric not in CLAMP_LIMITS:
        return value

    limits = CLAMP_LIMITS[metric]
    return max(limits['min'], min(limits['max'], value))


def winsorize(values: List[float], percentile: float = 2.5) -> List[float]:
    """
    상하위 percentile을 경계값으로 대체

    목적:
    - 극단적인 값(-999% 등)이 전체 지수를 왜곡하는 것 방지
    - 통계적 이상치 처리

    Args:
        values: 값 리스트
        percentile: 상하위 백분위 (기본 2.5%)

    Returns:
        Winsorize된 값 리스트

    Notes:
        - 샘플이 10개 미만이면 스킵 (통계적 의미 없음)
        - None 값은 제외하고 처리
    """
    # None 값 필터링
    valid_values = [v for v in values if v is not None]

    if len(valid_values) < 10:
        return values  # 샘플이 적으면 스킵

    sorted_vals = sorted(valid_values)
    n = len(sorted_vals)

    lower_idx = int(n * percentile / 100)
    upper_idx = int(n * (100 - percentile) / 100) - 1

    lower = sorted_vals[max(0, lower_idx)]
    upper = sorted_vals[min(n - 1, upper_idx)]

    result = []
    for v in values:
        if v is None:
            result.append(None)
        else:
            result.append(max(lower, min(upper, v)))

    return result


def geometric_mean_weighted(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    가중 기하평균 계산 (HDI 2010년 방식)

    공식: ∏(score_i ^ weight_i)

    특징:
    - 한 Sub-Index가 0에 가까우면 전체 점수 급락
    - "균형 잡힌 발전" 유도
    - 산술평균의 "완전 대체" 문제 해결

    Args:
        scores: Sub-Index 점수 딕셔너리 {'CEI': 75, 'RII': 60, ...}
        weights: 가중치 딕셔너리 {'CEI': 0.20, 'RII': 0.35, ...}

    Returns:
        가중 기하평균 (0~100)

    Examples:
        >>> scores = {'CEI': 75, 'RII': 60, 'CGI': 80, 'MAI': 70}
        >>> weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
        >>> geometric_mean_weighted(scores, weights)
        68.5  # 산술평균 71.25보다 낮음 - RII가 낮아서

    Notes:
        - 0점 방지: 최소 1점으로 처리 (log(0) 방지)
        - 가중치 합이 1.0이 아니어도 계산 가능하지만, 1.0 권장
    """
    result = 1.0
    total_weight = 0.0

    for key, weight in weights.items():
        if key not in scores:
            continue

        # 0점 방지 (최소 1점) - log(0) 방지
        safe_score = max(1.0, scores.get(key, 1.0) or 1.0)
        result *= safe_score ** weight
        total_weight += weight

    # 가중치 합이 1이 아닌 경우 보정
    if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
        # 가중치 합으로 정규화
        result = result ** (1.0 / total_weight)

    return round(result, 2)


def arithmetic_mean_weighted(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    가중 산술평균 계산 (v2.1 호환용)

    Args:
        scores: Sub-Index 점수 딕셔너리
        weights: 가중치 딕셔너리

    Returns:
        가중 산술평균 (0~100)
    """
    total = 0.0
    total_weight = 0.0

    for key, weight in weights.items():
        if key not in scores:
            continue
        score = scores.get(key, 0) or 0
        total += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(total / total_weight * total_weight, 2)


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = 0.0) -> float:
    """
    안전한 나눗셈 (0으로 나누기 방지)

    Args:
        numerator: 분자
        denominator: 분모
        default: 기본값 (분모가 0일 때)

    Returns:
        나눗셈 결과 또는 기본값
    """
    if numerator is None:
        return default
    if denominator is None or denominator == 0:
        return default
    return numerator / denominator


def safe_cagr(start_value: Optional[float], end_value: Optional[float], years: int) -> float:
    """
    안전한 CAGR 계산 (폭발 방지)

    Args:
        start_value: 시작 값
        end_value: 종료 값
        years: 기간 (년)

    Returns:
        CAGR (%) 또는 0.0

    Notes:
        - 시작값이 MIN_DENOMINATOR 미만이면 0 반환 (폭발 방지)
        - 음수값 처리 불가 (0 반환)
    """
    from .constants import MIN_DENOMINATOR

    if start_value is None or end_value is None:
        return 0.0
    if years <= 0:
        return 0.0
    if abs(start_value) < MIN_DENOMINATOR:
        return 0.0  # 폭발 방지
    if start_value <= 0 or end_value <= 0:
        return 0.0

    cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
    return cagr


def safe_growth_rate(
    early_values: List[float],
    late_values: List[float],
    use_abs: bool = True
) -> float:
    """
    안전한 성장률 계산 (폭발 방지)

    초기 평균 vs 최근 평균 비교

    Args:
        early_values: 초기 값 리스트
        late_values: 최근 값 리스트
        use_abs: 절대값 사용 여부 (CAPEX 등 음수 가능 지표)

    Returns:
        성장률 (%) 또는 0.0
    """
    from .constants import MIN_DENOMINATOR, CLAMP_LIMITS

    # 값 전처리
    if use_abs:
        early = [abs(v) if v is not None else 0 for v in early_values]
        late = [abs(v) if v is not None else 0 for v in late_values]
    else:
        early = [v if v is not None else 0 for v in early_values]
        late = [v if v is not None else 0 for v in late_values]

    # 평균 계산
    early_avg = sum(early) / len(early) if early else 0
    late_avg = sum(late) / len(late) if late else 0

    # 폭발 방지
    if early_avg < MIN_DENOMINATOR:
        if late_avg < MIN_DENOMINATOR:
            return 0.0
        else:
            return CLAMP_LIMITS.get('capex_growth', {}).get('max', 500.0)

    return ((late_avg - early_avg) / early_avg) * 100
