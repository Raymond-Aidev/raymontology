"""
RaymondsIndex v3.0 상수 정의

참조 문헌:
- OECD Handbook on Constructing Composite Indicators (2008)
- UNDP Human Development Index Technical Notes (2010~)
- Piotroski F-Score (2000) - 이진 스코어링 참조
"""

from typing import Dict, Any

# ═══════════════════════════════════════════════════════════════════════════════
# 범위 제한값 (Clamping) - ⭐ 핵심 버그 수정
# ═══════════════════════════════════════════════════════════════════════════════
# 목적: -999% 같은 극단값 방지
# 적용 대상: % 직접 산출 지표 (분모가 극소값일 수 있는 지표)

CLAMP_LIMITS: Dict[str, Dict[str, float]] = {
    'capex_growth': {'min': -95.0, 'max': 500.0},       # CAPEX 성장률
    'cash_cagr': {'min': -50.0, 'max': 200.0},          # 현금 CAGR
    'investment_gap': {'min': -100.0, 'max': 100.0},    # 투자괴리율 (핵심)
    'asset_turnover': {'min': 0.0, 'max': 10.0},        # 자산회전율
    'roic': {'min': -50.0, 'max': 100.0},               # ROIC
    'tangible_efficiency': {'min': 0.0, 'max': 50.0},   # 유형자산효율성
    'cash_yield': {'min': -100.0, 'max': 200.0},        # 현금수익률
    'reinvestment_rate': {'min': 0.0, 'max': 200.0},    # 재투자율
    'capex_intensity': {'min': 0.0, 'max': 50.0},       # CAPEX 강도
    'revenue_growth': {'min': -50.0, 'max': 200.0},     # 매출 성장률
}


# ═══════════════════════════════════════════════════════════════════════════════
# 정규화 경계값 (Goalposts) - HDI 방식
# ═══════════════════════════════════════════════════════════════════════════════
# 최소값: "natural zero" (생존 최소 수준)
# 최대값: "aspirational target" (달성 목표 수준)
# method: min_max (높을수록 좋음), inverse (낮을수록 좋음), v_score (최적값 존재)

GOALPOSTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # ═══════════════════════════════════════════════════════════════
    # CEI: Capital Efficiency Index (자본 효율성) - 20%
    # ═══════════════════════════════════════════════════════════════
    'CEI': {
        'asset_turnover': {'min': 0.1, 'max': 3.0, 'method': 'min_max'},
        'tangible_efficiency': {'min': 0.1, 'max': 5.0, 'method': 'min_max'},
        'cash_yield': {'min': -10.0, 'max': 50.0, 'method': 'min_max'},
        'roic': {'min': -10.0, 'max': 30.0, 'method': 'min_max'},
        'efficiency_trend': {'min': -0.5, 'max': 0.5, 'method': 'min_max'},
    },

    # ═══════════════════════════════════════════════════════════════
    # RII: Reinvestment Intensity Index (재투자 강도) - 35% ⭐ 핵심
    # ═══════════════════════════════════════════════════════════════
    'RII': {
        'capex_intensity': {'min': 0.0, 'max': 30.0, 'method': 'min_max'},
        # ⭐ 투자괴리율: 0이 최적, 양수/음수 모두 감점 (V자 스코어링)
        'investment_gap': {'min': -50.0, 'max': 50.0, 'optimal': 0.0, 'method': 'v_score'},
        'reinvestment_rate': {'min': 0.0, 'max': 100.0, 'method': 'min_max'},
        'capex_volatility': {'min': 0.0, 'max': 1.0, 'method': 'inverse'},
    },

    # ═══════════════════════════════════════════════════════════════
    # CGI: Cash Governance Index (현금 거버넌스) - 25%
    # ═══════════════════════════════════════════════════════════════
    'CGI': {
        'cash_utilization': {'min': 0.0, 'max': 100.0, 'method': 'min_max'},
        'funding_efficiency': {'min': 0.0, 'max': 100.0, 'method': 'min_max'},
        'payout_ratio': {'min': 0.0, 'max': 100.0, 'optimal': 35.0, 'method': 'v_score'},
        'cash_to_assets': {'min': 5.0, 'max': 50.0, 'optimal': 15.0, 'method': 'v_score'},
        'debt_to_ebitda': {'min': 0.0, 'max': 10.0, 'method': 'inverse'},
    },

    # ═══════════════════════════════════════════════════════════════
    # MAI: Momentum Alignment Index (모멘텀 정합성) - 20%
    # ═══════════════════════════════════════════════════════════════
    'MAI': {
        'revenue_capex_sync': {'min': -50.0, 'max': 50.0, 'optimal': 0.0, 'method': 'v_score'},
        'earnings_quality': {'min': 0.0, 'max': 2.0, 'optimal': 1.0, 'method': 'v_score'},
        'growth_investment_ratio': {'min': 0.0, 'max': 100.0, 'method': 'min_max'},
        'fcf_trend': {'min': -0.5, 'max': 0.5, 'method': 'min_max'},
        'capex_trend_score': {'min': 0.0, 'max': 100.0, 'method': 'min_max'},
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-Index 가중치 (합계 = 1.0)
# ═══════════════════════════════════════════════════════════════════════════════
# v3.1 업데이트 (2026-01-22): Option C 최적화 결과 적용
# - AUC 0.837 달성 (목표 0.75 초과)
# - F1 Score 0.650 → 0.70 목표
# - 근거: Tier 1 실패기업 571개 기반 LDA/Logistic/FeatureImportance 앙상블

SUBINDEX_WEIGHTS: Dict[str, float] = {
    'CEI': 0.45,  # Capital Efficiency Index ⬆️ (20% → 45%) - 자본 효율성 강화
    'RII': 0.10,  # Reinvestment Intensity Index ⬇️ (35% → 10%) - 역방향 관계 보정
    'CGI': 0.45,  # Cash Governance Index ⬆️ (25% → 45%) - 현금 거버넌스 강화
    'MAI': 0.00,  # Momentum Alignment Index ⬇️ (20% → 0%) - 실패 예측 무관
}

# v3.0 원본 가중치 (롤백용)
SUBINDEX_WEIGHTS_V30: Dict[str, float] = {
    'CEI': 0.20,
    'RII': 0.35,
    'CGI': 0.25,
    'MAI': 0.20,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 각 Sub-Index 내 세부 지표 가중치
# ═══════════════════════════════════════════════════════════════════════════════

METRIC_WEIGHTS: Dict[str, Dict[str, float]] = {
    'CEI': {
        'asset_turnover': 0.25,
        'tangible_efficiency': 0.20,
        'cash_yield': 0.20,
        'roic': 0.25,
        'efficiency_trend': 0.10,
    },
    'RII': {
        'capex_intensity': 0.25,
        'investment_gap': 0.30,  # ⭐ 핵심 지표
        'reinvestment_rate': 0.25,
        'capex_volatility': 0.20,
    },
    'CGI': {
        'cash_utilization': 0.20,
        'funding_efficiency': 0.25,
        'payout_ratio': 0.20,
        'cash_to_assets': 0.15,
        'debt_to_ebitda': 0.20,
    },
    'MAI': {
        'revenue_capex_sync': 0.30,
        'earnings_quality': 0.25,
        'growth_investment_ratio': 0.15,
        'fcf_trend': 0.10,
        'capex_trend_score': 0.20,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 등급 기준 (v2.1 완화 2026-01-27)
# ═══════════════════════════════════════════════════════════════════════════════

GRADE_THRESHOLDS = [
    (88, 'A++'),  # v2.1: 95 → 88 (7점 하향)
    (80, 'A+'),   # v2.1: 88 → 80 (8점 하향)
    (72, 'A'),    # v2.1: 80 → 72 (8점 하향)
    (64, 'A-'),   # v2.1: 72 → 64 (8점 하향)
    (55, 'B+'),   # v2.1: 64 → 55 (9점 하향)
    (45, 'B'),    # v2.1: 55 → 45 (10점 하향)
    (35, 'B-'),   # v2.1: 45 → 35 (10점 하향)
    (20, 'C+'),   # v2.1: 30 → 20 (10점 하향)
    (0, 'C'),
]

GRADE_ORDER = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']


# ═══════════════════════════════════════════════════════════════════════════════
# 데이터 검증 상수
# ═══════════════════════════════════════════════════════════════════════════════

MIN_REQUIRED_YEARS = 2  # 최소 필요 연도 수 (3년 권장, 2년 최소)
MIN_DENOMINATOR = 100_000_000  # 1억원 (분모 최소값 - 폭발 방지)
WINSORIZE_PERCENTILE = 2.5  # 상하위 2.5% 극단값 처리


# ═══════════════════════════════════════════════════════════════════════════════
# 업종별 가중치 조정 (v2.1과 동일)
# ═══════════════════════════════════════════════════════════════════════════════

INDUSTRY_WEIGHT_ADJUSTMENTS: Dict[str, Dict[str, Any]] = {
    'rd_intensive': {
        # 바이오, 반도체 등 R&D 집약 업종
        'sectors': ['의약품', '바이오', '반도체', '제약', 'IT서비스', '소프트웨어'],
        'adjustments': {'RII': +0.05, 'CEI': -0.05}
    },
    'capital_intensive': {
        # 제조, 유틸리티 등 자본 집약 업종
        'sectors': ['제조', '유틸리티', '철강', '화학', '조선', '건설'],
        'adjustments': {'CEI': +0.05, 'MAI': -0.05}
    },
    'continuous_investment': {
        # 외식, 리테일 등 연속 투자 업종
        'sectors': ['외식', '리테일', '유통', '음식료', '호텔'],
        'adjustments': {'RII': +0.03, 'CGI': -0.03}
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# 특별 규칙 임계값
# ═══════════════════════════════════════════════════════════════════════════════

SPECIAL_RULES = {
    'cash_tangible_ratio_max': 30.0,      # 현금/유형자산 비율 > 30:1 → 최대 B-
    'funding_utilization_min': 30.0,      # 조달자금 전환율 < 30% → 최대 B-
    'idle_cash_capex_decline': {          # 유휴현금 > 65% + CAPEX 감소 → 최대 B
        'idle_cash_threshold': 65.0,
        'capex_growth_threshold': 0.0,
    },
}
