# RaymondsIndex v3.0 시스템 설계서
## HDI 정규화 방식 적용 (Option B)

> **버전**: 3.0  
> **작성일**: 2026-01-21  
> **목적**: Claude Code에서 기존 구현을 재개발하기 위한 설계 명세  
> **핵심 변경**: OECD/UNDP HDI 방식의 정규화 및 기하평균 집계 적용

---

## 📋 v3.0 변경 요약 (v2.1 → v3.0)

| 항목 | v2.1 (기존) | v3.0 (신규) | 변경 근거 |
|------|-------------|-------------|-----------|
| **정규화** | 없음/직관적 스코어링 | **Min-Max 정규화 (0~100)** | OECD Handbook |
| **극단값 처리** | 없음 (-999% 버그 발생) | **Winsorizing (상하위 2.5%)** | OECD Handbook |
| **범위 제한** | 없음 | **Clamping** | 버그 방지 |
| **로그 변환** | 없음 | **성장률 지표에 적용** | HDI Income Index |
| **집계 방식** | 산술평균(가중합) | **기하평균 (부분 대체)** | HDI 2010 개정 |
| **데이터 검증** | 없음 | **검증 레이어 추가** | 안정성 확보 |

### 방법론 근거 (실제 논문/사례)

| 방법론 | 출처 | 적용 부분 |
|--------|------|-----------|
| Min-Max + Goalposts | OECD Handbook (2008) | 모든 지표 정규화 |
| 기하평균 집계 | UNDP HDI (2010~) | Sub-Index → 최종 점수 |
| 로그 변환 | HDI Income Index | 성장률/소득 지표 |
| 이진 스코어링 참조 | Piotroski F-Score (2000) | 특별 규칙 |

---

## 1. 시스템 아키텍처 (기존 유지)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Raymontology Frontend                        │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 시스템 (유지)           │   RaymondsIndex (신규)               │
│   ├─ MainSearchPage          │   ├─ RaymondsIndexRankingPage        │
│   ├─ ReportPage              │   ├─ RaymondsIndexCard (위젯)         │
│   ├─ GraphPage               │   ├─ SubIndexChart                   │
│   └─ AdminPage               │   └─ InvestmentGapMeter              │
└──────────────────────────────┴──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Raymontology Backend                         │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 API (유지)              │   RaymondsIndex API (신규)           │
│   ├─ /api/companies          │   ├─ /api/raymonds-index/{id}        │
│   ├─ /api/report             │   ├─ /api/raymonds-index/ranking     │
│   ├─ /api/risks              │   ├─ /api/raymonds-index/search      │
│   └─ /api/graph              │   └─ /api/raymonds-index/calculate   │
└──────────────────────────────┴──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                          │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 테이블 (변경 금지)       │   신규 테이블                         │
│   ├─ companies               │   ├─ financial_details (상세 재무)    │
│   ├─ financial_statements    │   ├─ raymonds_index (지수 결과)       │
│   ├─ risk_scores             │   └─ normalization_params (v3.0 신규) │
│   └─ convertible_bonds       │                                      │
└──────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. 핵심 계산 프로세스 (5단계)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RaymondsIndex v3.0 계산 프로세스                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Step 1] 원본 지표 계산 (Raw Metrics)                              │
│      ↓                                                               │
│  [Step 2] 데이터 검증 & 전처리                                        │
│      ├─ 필수 필드 검증                                               │
│      ├─ 이상치 탐지 (IQR 방식)                                       │
│      ├─ Winsorizing (상하위 2.5%)                                   │
│      └─ 범위 제한 (Clamping) ⭐ -999% 버그 방지                      │
│      ↓                                                               │
│  [Step 3] 정규화 (0~100 변환)                                       │
│      ├─ Min-Max 정규화 (일반 지표)                                  │
│      ├─ 로그 정규화 (성장률 지표)                                    │
│      └─ V-Score 정규화 (최적값이 중간인 지표)                        │
│      ↓                                                               │
│  [Step 4] Sub-Index 집계 (기하평균)                                  │
│      ↓                                                               │
│  [Step 5] 최종 RaymondsIndex (가중 기하평균)                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 상수 정의 (constants.py)

### 3.1 범위 제한값 (Clamping) - ⭐ 핵심 버그 수정

```python
"""
범위 제한 (Clamping)
- 목적: -999% 같은 극단값 방지
- 적용 대상: % 직접 산출 지표 (분모가 극소값일 수 있는 지표)
"""
CLAMP_LIMITS = {
    'capex_growth': {'min': -95, 'max': 500},       # CAPEX 성장률
    'cash_cagr': {'min': -50, 'max': 200},          # 현금 CAGR
    'investment_gap': {'min': -100, 'max': 100},    # 투자괴리율 (핵심)
    'asset_turnover': {'min': 0, 'max': 10},        # 자산회전율
    'roic': {'min': -50, 'max': 100},               # ROIC
    'tangible_efficiency': {'min': 0, 'max': 50},   # 유형자산효율성
    'cash_yield': {'min': -100, 'max': 200},        # 현금수익률
}
```

### 3.2 정규화 경계값 (Goalposts) - HDI 방식

```python
"""
정규화 경계값 (Goalposts)
- 최소값: "natural zero" (생존 최소 수준)
- 최대값: "aspirational target" (달성 목표 수준)
- 출처: HDI Technical Notes 참조
"""
GOALPOSTS = {
    # ═══════════════════════════════════════════════════════════════
    # CEI: Capital Efficiency Index (자본 효율성)
    # ═══════════════════════════════════════════════════════════════
    'CEI': {
        'asset_turnover': {'min': 0.1, 'max': 3.0, 'method': 'min_max'},
        'tangible_efficiency': {'min': 0.1, 'max': 5.0, 'method': 'min_max'},
        'cash_yield': {'min': -10, 'max': 50, 'method': 'min_max'},
        'roic': {'min': -10, 'max': 30, 'method': 'min_max'},
        'efficiency_trend': {'min': -0.5, 'max': 0.5, 'method': 'min_max'},
    },
    
    # ═══════════════════════════════════════════════════════════════
    # RII: Reinvestment Intensity Index (재투자 강도) ⭐ 핵심
    # ═══════════════════════════════════════════════════════════════
    'RII': {
        'capex_intensity': {'min': 0, 'max': 30, 'method': 'min_max'},
        'rd_intensity': {'min': 0, 'max': 20, 'method': 'min_max'},
        # ⭐ 투자괴리율: 0이 최적, 양수/음수 모두 감점 (V자 스코어링)
        'investment_gap': {'min': -50, 'max': 50, 'optimal': 0, 'method': 'v_score'},
        'reinvestment_rate': {'min': 0, 'max': 100, 'method': 'min_max'},
        'capex_volatility': {'min': 0, 'max': 1, 'method': 'inverse'},
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CGI: Cash Governance Index (현금 거버넌스)
    # ═══════════════════════════════════════════════════════════════
    'CGI': {
        'cash_utilization': {'min': 0, 'max': 100, 'method': 'min_max'},
        'funding_efficiency': {'min': 0, 'max': 100, 'method': 'min_max'},
        'payout_ratio': {'min': 0, 'max': 100, 'optimal': 35, 'method': 'v_score'},
        'cash_to_assets': {'min': 5, 'max': 30, 'optimal': 15, 'method': 'v_score'},
        'debt_to_ebitda': {'min': 0, 'max': 10, 'method': 'inverse'},
    },
    
    # ═══════════════════════════════════════════════════════════════
    # MAI: Momentum Alignment Index (모멘텀 정합성)
    # ═══════════════════════════════════════════════════════════════
    'MAI': {
        'revenue_capex_sync': {'min': -50, 'max': 50, 'optimal': 0, 'method': 'v_score'},
        'earnings_quality': {'min': 0, 'max': 2, 'optimal': 1, 'method': 'v_score'},
        'growth_investment_ratio': {'min': 0, 'max': 100, 'method': 'min_max'},
        'fcf_trend': {'min': -0.5, 'max': 0.5, 'method': 'min_max'},
    },
}
```

### 3.3 가중치

```python
# Sub-Index 가중치 (합계 = 1.0)
SUBINDEX_WEIGHTS = {
    'CEI': 0.20,  # Capital Efficiency Index
    'RII': 0.35,  # Reinvestment Intensity Index ⭐ 핵심
    'CGI': 0.25,  # Cash Governance Index
    'MAI': 0.20,  # Momentum Alignment Index
}

# 각 Sub-Index 내 세부 지표 가중치
METRIC_WEIGHTS = {
    'CEI': {
        'asset_turnover': 0.25,
        'tangible_efficiency': 0.20,
        'cash_yield': 0.20,
        'roic': 0.25,
        'efficiency_trend': 0.10,
    },
    'RII': {
        'capex_intensity': 0.25,
        'rd_intensity': 0.15,
        'investment_gap': 0.25,  # ⭐ 핵심
        'reinvestment_rate': 0.20,
        'capex_consistency': 0.15,
    },
    'CGI': {
        'cash_utilization': 0.20,
        'funding_efficiency': 0.25,
        'payout_balance': 0.20,
        'cash_adequacy': 0.15,
        'debt_health': 0.20,
    },
    'MAI': {
        'revenue_investment_sync': 0.30,
        'earnings_quality': 0.25,
        'investment_momentum': 0.20,
        'growth_ratio': 0.15,
        'fcf_trend': 0.10,
    },
}

# 등급 기준
GRADE_THRESHOLDS = [
    (95, 'A++'),
    (88, 'A+'),
    (80, 'A'),
    (72, 'A-'),
    (64, 'B+'),
    (55, 'B'),
    (45, 'B-'),
    (30, 'C+'),
    (0, 'C'),
]

# 데이터 검증 상수
MIN_REQUIRED_YEARS = 3
MIN_DENOMINATOR = 100_000_000  # 1억원 (분모 최소값)
WINSORIZE_PERCENTILE = 2.5
```

---

## 4. 정규화 함수 (normalizers.py)

### 4.1 Min-Max 정규화

```python
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
    """
    if value <= min_val:
        return 0.0
    if value >= max_val:
        return 100.0
    return ((value - min_val) / (max_val - min_val)) * 100
```

### 4.2 V-Score 정규화 (최적값이 중간인 지표)

```python
def v_score_normalize(value: float, optimal: float, min_val: float, max_val: float) -> float:
    """
    V자 스코어링: 최적값에서 100점, 양쪽 끝에서 0점
    
    적용 대상: 
    - 투자괴리율 (0이 최적)
    - 주주환원율 (35%가 최적)
    - 이익품질 (1이 최적)
    
    예시 (투자괴리율):
    - 0% → 100점 (최적)
    - +50% → 0점 (현금만 축적)
    - -50% → 0점 (과잉 투자)
    """
    if value <= min_val or value >= max_val:
        return 0.0
    
    if value <= optimal:
        # 음수 영역: min_val → 0점, optimal → 100점
        return ((value - min_val) / (optimal - min_val)) * 100
    else:
        # 양수 영역: optimal → 100점, max_val → 0점
        return 100 - ((value - optimal) / (max_val - optimal)) * 100
```

### 4.3 역방향 정규화 (낮을수록 좋은 지표)

```python
def inverse_normalize(value: float, min_val: float, max_val: float) -> float:
    """
    역방향 정규화: 낮을수록 좋은 지표
    
    적용 대상: Debt/EBITDA, CAPEX 변동계수
    """
    if value <= min_val:
        return 100.0
    if value >= max_val:
        return 0.0
    return 100 - ((value - min_val) / (max_val - min_val)) * 100
```

### 4.4 범위 제한 (Clamping) - ⭐ 핵심 버그 수정

```python
def clamp(value: float, metric: str) -> float:
    """
    값을 지정된 범위로 제한 - -999% 버그 방지
    
    예시:
    - capex_growth = 99,900% → 500% (상한)
    - investment_gap = -99,890% → -100% (하한)
    """
    if metric not in CLAMP_LIMITS:
        return value
    
    limits = CLAMP_LIMITS[metric]
    return max(limits['min'], min(limits['max'], value))
```

### 4.5 기하평균 (HDI 방식)

```python
def geometric_mean_weighted(scores: dict, weights: dict) -> float:
    """
    가중 기하평균 계산 (HDI 2010년 방식)
    
    공식: ∏(score_i ^ weight_i)
    
    특징:
    - 한 Sub-Index가 0에 가까우면 전체 점수 급락
    - "균형 잡힌 발전" 유도
    - 산술평균의 "완전 대체" 문제 해결
    
    예시:
    scores = {'CEI': 75, 'RII': 60, 'CGI': 80, 'MAI': 70}
    weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
    
    result = (75^0.20) × (60^0.35) × (80^0.25) × (70^0.20)
           ≈ 68.5 (산술평균 71.25보다 낮음 - RII가 낮아서)
    """
    result = 1.0
    for key, weight in weights.items():
        # 0점 방지 (최소 1점)
        safe_score = max(1.0, scores.get(key, 1.0))
        result *= safe_score ** weight
    return result
```

### 4.6 Winsorizing

```python
import numpy as np

def winsorize(values: list, percentile: float = 2.5) -> list:
    """
    상하위 percentile을 경계값으로 대체
    
    목적: 극단적인 값(-999% 등)이 전체 지수를 왜곡하는 것 방지
    """
    if len(values) < 10:
        return values  # 샘플이 적으면 스킵
    
    lower = np.percentile(values, percentile)
    upper = np.percentile(values, 100 - percentile)
    
    return [max(lower, min(upper, v)) for v in values]
```

---

## 5. 데이터 검증기 (validators.py)

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    is_valid: bool
    can_calculate: bool
    quality_score: float  # 0-100
    errors: List[str]
    warnings: List[str]


class DataValidator:
    """재무 데이터 검증기"""
    
    REQUIRED_FIELDS = [
        'revenue', 'operating_income', 'net_income',
        'total_assets', 'total_cash',
        'operating_cash_flow', 'capex'
    ]
    
    MIN_YEARS = 3
    MIN_DENOMINATOR = 100_000_000  # 1억원
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        
        # 1. 필수 필드 검증
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"필수 필드 누락: {field}")
            elif isinstance(data[field], list) and len(data[field]) == 0:
                errors.append(f"필수 필드 비어있음: {field}")
        
        # 2. 연도 수 검증
        if 'revenue' in data and isinstance(data['revenue'], list):
            if len(data['revenue']) < self.MIN_YEARS:
                errors.append(f"최소 {self.MIN_YEARS}년 데이터 필요")
        
        # 3. 값 범위 검증
        if 'total_assets' in data and isinstance(data['total_assets'], list):
            if any(v is not None and v < 0 for v in data['total_assets']):
                errors.append("총자산이 음수입니다")
        
        # 4. ⭐ 분모 극소값 경고 (핵심 버그 원인)
        if 'capex' in data and isinstance(data['capex'], list):
            early_capex = data['capex'][:2] if len(data['capex']) >= 2 else data['capex']
            if early_capex:
                avg_early = sum(abs(c) for c in early_capex if c is not None) / len(early_capex)
                if avg_early < self.MIN_DENOMINATOR:
                    warnings.append(f"초기 CAPEX가 1억 미만 - 성장률 신뢰도 낮음")
        
        # 5. 일관성 검증
        if ('total_assets' in data and 'revenue' in data and 
            isinstance(data['total_assets'], list) and isinstance(data['revenue'], list)):
            if data['total_assets'][-1] and data['total_assets'][-1] > 0:
                turnover = data['revenue'][-1] / data['total_assets'][-1]
                if turnover > 10:
                    warnings.append("자산회전율이 비정상적으로 높음 (10 이상)")
        
        # 품질 점수 계산
        quality_score = 100 - (len(errors) * 25) - (len(warnings) * 5)
        quality_score = max(0, min(100, quality_score))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            can_calculate=len(errors) == 0 and quality_score >= 50,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
        )
```

---

## 6. RII 계산기 (핵심 - 투자괴리율)

```python
class RIICalculator:
    """
    재투자 강도 지수 계산기 (핵심 지표)
    
    핵심 질문: "벌어들인 돈을 미래 성장에 얼마나 투자하는가?"
    
    ⭐ v3.0 핵심 변경: 투자괴리율 범위 제한 및 정규화
    """
    
    def calculate(self, data: dict) -> tuple:
        raw = {}
        normalized = {}
        
        # ═══════════════════════════════════════════════════════════════
        # Step 1: 원본 지표 계산
        # ═══════════════════════════════════════════════════════════════
        
        # CAPEX 강도
        raw['capex_intensity'] = self._safe_divide(
            abs(data['capex'][-1]), 
            data['revenue'][-1]
        ) * 100
        
        # R&D 강도
        rd_expense = data.get('rd_expense', [0])
        raw['rd_intensity'] = self._safe_divide(
            rd_expense[-1] if rd_expense else 0,
            data['revenue'][-1]
        ) * 100
        
        # ⭐ 투자괴리율 v3.0 (범위 제한 적용)
        cash_cagr = self._safe_cagr(data['total_cash'])
        capex_growth = self._safe_growth_rate(data['capex'])
        
        # 범위 제한 (Clamping) - ⭐ 핵심 버그 수정
        cash_cagr = clamp(cash_cagr, 'cash_cagr')
        capex_growth = clamp(capex_growth, 'capex_growth')
        
        raw['cash_cagr'] = cash_cagr
        raw['capex_growth'] = capex_growth
        raw['investment_gap'] = clamp(
            cash_cagr - capex_growth, 
            'investment_gap'
        )
        
        # 재투자율
        raw['reinvestment_rate'] = self._safe_divide(
            abs(data['capex'][-1]),
            data['operating_cash_flow'][-1]
        ) * 100
        
        # 투자 지속성 (변동계수)
        raw['capex_volatility'] = self._coefficient_of_variation(data['capex'])
        
        # ═══════════════════════════════════════════════════════════════
        # Step 2: 정규화 (0~100)
        # ═══════════════════════════════════════════════════════════════
        
        gp = GOALPOSTS['RII']
        
        normalized['capex_intensity'] = min_max_normalize(
            raw['capex_intensity'],
            gp['capex_intensity']['min'],
            gp['capex_intensity']['max']
        )
        
        normalized['rd_intensity'] = min_max_normalize(
            raw['rd_intensity'],
            gp['rd_intensity']['min'],
            gp['rd_intensity']['max']
        )
        
        # ⭐ 투자괴리율: V자 스코어링 (0이 최적)
        normalized['investment_gap'] = v_score_normalize(
            raw['investment_gap'],
            optimal=gp['investment_gap']['optimal'],
            min_val=gp['investment_gap']['min'],
            max_val=gp['investment_gap']['max']
        )
        
        normalized['reinvestment_rate'] = min_max_normalize(
            raw['reinvestment_rate'],
            gp['reinvestment_rate']['min'],
            gp['reinvestment_rate']['max']
        )
        
        # 변동계수: 역방향 (낮을수록 좋음)
        normalized['capex_consistency'] = inverse_normalize(
            raw['capex_volatility'],
            gp['capex_volatility']['min'],
            gp['capex_volatility']['max']
        )
        
        # ═══════════════════════════════════════════════════════════════
        # Step 3: 가중 기하평균
        # ═══════════════════════════════════════════════════════════════
        
        score = geometric_mean_weighted(normalized, METRIC_WEIGHTS['RII'])
        
        return score, {'raw': raw, 'normalized': normalized}
    
    def _safe_cagr(self, values: list) -> float:
        """안전한 CAGR 계산 (폭발 방지)"""
        if len(values) < 2:
            return 0.0
        
        start = values[0]
        end = values[-1]
        years = len(values) - 1
        
        # ⭐ 시작값이 너무 작으면 0 반환 (폭발 방지)
        if start is None or abs(start) < MIN_DENOMINATOR:
            return 0.0
        
        if start <= 0 or end <= 0:
            return 0.0
        
        cagr = ((end / start) ** (1 / years) - 1) * 100
        return cagr
    
    def _safe_growth_rate(self, values: list) -> float:
        """안전한 성장률 계산 (폭발 방지)"""
        if len(values) < 2:
            return 0.0
        
        # 절대값 사용 (CAPEX는 음수일 수 있음)
        abs_values = [abs(v) if v else 0 for v in values]
        
        # 초기 2년 평균 vs 최근 2년 평균
        early = sum(abs_values[:2]) / 2 if len(abs_values) >= 2 else abs_values[0]
        late = sum(abs_values[-2:]) / 2 if len(abs_values) >= 2 else abs_values[-1]
        
        # ⭐ 초기값이 너무 작으면 제한된 값 반환
        if early < MIN_DENOMINATOR:
            if late < MIN_DENOMINATOR:
                return 0.0
            else:
                return CLAMP_LIMITS['capex_growth']['max']  # 최대값
        
        return ((late - early) / early) * 100
    
    def _safe_divide(self, numerator, denominator) -> float:
        """안전한 나눗셈"""
        if denominator is None or denominator == 0:
            return 0.0
        if numerator is None:
            return 0.0
        return numerator / denominator
    
    def _coefficient_of_variation(self, values: list) -> float:
        """변동계수 계산"""
        abs_values = [abs(v) if v else 0 for v in values]
        if len(abs_values) < 2:
            return 0.0
        mean = sum(abs_values) / len(abs_values)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in abs_values) / len(abs_values)
        std = variance ** 0.5
        return std / mean
```

---

## 7. 종합 계산기 (engine.py)

```python
class RaymondsIndexCalculator:
    """
    RaymondsIndex v3.0 종합 계산기
    
    집계 방식: 가중 기하평균 (HDI 방식)
    """
    
    def __init__(self):
        self.cei_calc = CEICalculator()
        self.rii_calc = RIICalculator()
        self.cgi_calc = CGICalculator()
        self.mai_calc = MAICalculator()
        self.validator = DataValidator()
    
    def calculate(self, data: dict) -> dict:
        # ═══════════════════════════════════════════════════════════════
        # Step 1: 데이터 검증
        # ═══════════════════════════════════════════════════════════════
        validation = self.validator.validate(data)
        
        if not validation.can_calculate:
            return {
                'status': 'DATA_INSUFFICIENT',
                'total_score': None,
                'grade': 'N/A',
                'errors': validation.errors,
                'warnings': validation.warnings,
                'data_quality_score': validation.quality_score,
            }
        
        # ═══════════════════════════════════════════════════════════════
        # Step 2: Sub-Index 계산
        # ═══════════════════════════════════════════════════════════════
        cei_score, cei_details = self.cei_calc.calculate(data)
        rii_score, rii_details = self.rii_calc.calculate(data)
        cgi_score, cgi_details = self.cgi_calc.calculate(data)
        mai_score, mai_details = self.mai_calc.calculate(data)
        
        sub_scores = {
            'CEI': cei_score,
            'RII': rii_score,
            'CGI': cgi_score,
            'MAI': mai_score,
        }
        
        # ═══════════════════════════════════════════════════════════════
        # Step 3: ⭐ 가중 기하평균 집계 (HDI 방식)
        # ═══════════════════════════════════════════════════════════════
        total_score = geometric_mean_weighted(sub_scores, SUBINDEX_WEIGHTS)
        
        # ═══════════════════════════════════════════════════════════════
        # Step 4: 등급 결정
        # ═══════════════════════════════════════════════════════════════
        grade = self._determine_grade(total_score)
        
        # ═══════════════════════════════════════════════════════════════
        # Step 5: 특별 규칙 적용 (등급 하향)
        # ═══════════════════════════════════════════════════════════════
        grade, violations = self._apply_special_rules(
            grade, data, rii_details, cgi_details
        )
        
        # ═══════════════════════════════════════════════════════════════
        # Step 6: 결과 생성
        # ═══════════════════════════════════════════════════════════════
        return {
            'status': 'SUCCESS',
            'total_score': round(total_score, 1),
            'grade': grade,
            'cei_score': round(cei_score, 1),
            'rii_score': round(rii_score, 1),
            'cgi_score': round(cgi_score, 1),
            'mai_score': round(mai_score, 1),
            'investment_gap': rii_details['raw']['investment_gap'],
            'cash_cagr': rii_details['raw']['cash_cagr'],
            'capex_growth': rii_details['raw']['capex_growth'],
            'details': {
                'cei': cei_details,
                'rii': rii_details,
                'cgi': cgi_details,
                'mai': mai_details,
            },
            'violations': violations,
            'warnings': validation.warnings,
            'data_quality_score': validation.quality_score,
            'aggregation_method': 'geometric_mean',
            'algorithm_version': 'v3.0',
        }
    
    def _determine_grade(self, score: float) -> str:
        """점수 기반 등급 결정"""
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'C'
    
    def _apply_special_rules(self, grade, data, rii_details, cgi_details):
        """특별 규칙 적용 - 등급 강제 하향"""
        violations = []
        grade_order = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']
        
        def downgrade_to_max(current, max_grade):
            current_idx = grade_order.index(current)
            max_idx = grade_order.index(max_grade)
            return max_grade if current_idx < max_idx else current
        
        # 규칙 1: 현금/유형자산 비율 > 30:1
        total_cash = data['total_cash'][-1] if data.get('total_cash') else 0
        tangible = data.get('tangible_assets', [1])[-1] or 1
        if tangible > 0 and total_cash / tangible > 30:
            violations.append('CASH_TANGIBLE_RATIO_EXCEEDED')
            grade = downgrade_to_max(grade, 'B-')
        
        # 규칙 2: 조달자금 전환율 < 30%
        funding_util = cgi_details['raw'].get('funding_efficiency', 100)
        if funding_util < 30:
            violations.append('FUNDING_UNUTILIZED')
            grade = downgrade_to_max(grade, 'B-')
        
        # 규칙 3: 유휴현금 > 65% + CAPEX 감소
        idle_ratio = cgi_details['raw'].get('idle_cash_ratio', 0)
        capex_growth = rii_details['raw']['capex_growth']
        if idle_ratio > 65 and capex_growth < 0:
            violations.append('IDLE_CASH_WITH_CAPEX_DECLINE')
            grade = downgrade_to_max(grade, 'B')
        
        # 복합 위반: 2개 이상
        if len(violations) >= 2:
            grade = downgrade_to_max(grade, 'C+')
        
        return grade, violations
```

---

## 8. 데이터베이스 스키마 (v3.0)

### 8.1 raymonds_index 테이블 (수정)

```sql
-- RaymondsIndex 계산 결과 (v3.0 컬럼 추가)
CREATE TABLE raymonds_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    fiscal_year INTEGER NOT NULL,
    
    -- 종합 점수
    total_score DECIMAL(5,2),
    grade VARCHAR(5) NOT NULL,
    
    -- Sub-Index 점수 (정규화된 0-100)
    cei_score DECIMAL(5,2),
    rii_score DECIMAL(5,2),
    cgi_score DECIMAL(5,2),
    mai_score DECIMAL(5,2),
    
    -- 핵심 지표 (원본값 - 범위 제한 적용 후)
    investment_gap DECIMAL(6,2),
    cash_cagr DECIMAL(6,2),
    capex_growth DECIMAL(6,2),
    
    -- ⭐ v3.0 신규: 정규화 전 원본값 저장
    raw_metrics JSONB,
    
    -- ⭐ v3.0 신규: 정규화된 세부 지표
    normalized_metrics JSONB,
    
    -- 위험 신호
    red_flags JSONB DEFAULT '[]',
    yellow_flags JSONB DEFAULT '[]',
    violations JSONB DEFAULT '[]',
    
    -- 메타데이터
    data_quality_score DECIMAL(5,2),
    validation_warnings JSONB DEFAULT '[]',
    aggregation_method VARCHAR(20) DEFAULT 'geometric_mean',
    algorithm_version VARCHAR(10) DEFAULT 'v3.0',
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uq_raymonds_index UNIQUE(company_id, fiscal_year)
);

CREATE INDEX idx_ri_company ON raymonds_index(company_id);
CREATE INDEX idx_ri_year ON raymonds_index(fiscal_year);
CREATE INDEX idx_ri_score ON raymonds_index(total_score);
CREATE INDEX idx_ri_grade ON raymonds_index(grade);
CREATE INDEX idx_ri_version ON raymonds_index(algorithm_version);
```

### 8.2 normalization_params 테이블 (v3.0 신규)

```sql
-- 정규화 파라미터 저장 (업종별 커스터마이징용)
CREATE TABLE normalization_params (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_code VARCHAR(10),
    industry_name VARCHAR(100),
    goalposts JSONB NOT NULL,
    percentiles JSONB,
    sample_size INTEGER,
    base_year INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uq_norm_params UNIQUE(industry_code, base_year)
);
```

---

## 9. 백엔드 파일 구조

```
backend/app/
├── api/endpoints/
│   ├── raymonds_index.py          # RaymondsIndex API
│   └── company_report.py          # 수정: raymonds_index 필드 추가
├── models/
│   ├── financial_details.py       # 상세 재무 모델
│   └── raymonds_index.py          # RaymondsIndex 모델
├── services/
│   └── raymonds_index/
│       ├── __init__.py
│       ├── constants.py           # ⭐ GOALPOSTS, WEIGHTS, CLAMP_LIMITS
│       ├── normalizers.py         # ⭐ min_max, v_score, clamp, geometric_mean
│       ├── validators.py          # ⭐ DataValidator
│       ├── calculators/
│       │   ├── __init__.py
│       │   ├── base.py            # SubIndexCalculator (ABC)
│       │   ├── cei.py             # CEICalculator
│       │   ├── rii.py             # ⭐ RIICalculator (투자괴리율)
│       │   ├── cgi.py             # CGICalculator
│       │   └── mai.py             # MAICalculator
│       └── engine.py              # ⭐ RaymondsIndexCalculator
└── main.py
```

---

## 10. 테스트 케이스

### 10.1 정규화 함수 테스트

```python
# tests/test_normalizers.py

def test_min_max_normalize():
    """Min-Max 정규화 테스트"""
    assert min_max_normalize(0.1, 0.1, 3.0) == 0
    assert min_max_normalize(3.0, 0.1, 3.0) == 100
    assert abs(min_max_normalize(1.55, 0.1, 3.0) - 50) < 0.1

def test_v_score_normalize():
    """V자 스코어링 테스트"""
    # 투자괴리율: 0이 최적
    assert v_score_normalize(0, optimal=0, min_val=-50, max_val=50) == 100
    assert v_score_normalize(50, optimal=0, min_val=-50, max_val=50) == 0
    assert v_score_normalize(-50, optimal=0, min_val=-50, max_val=50) == 0
    assert v_score_normalize(25, optimal=0, min_val=-50, max_val=50) == 50

def test_clamp():
    """범위 제한 테스트 - ⭐ 핵심 버그 수정 검증"""
    # capex_growth 제한
    assert clamp(99900, 'capex_growth') == 500   # 상한
    assert clamp(-99890, 'capex_growth') == -95  # 하한
    
    # investment_gap 제한
    assert clamp(-99890, 'investment_gap') == -100
    assert clamp(200, 'investment_gap') == 100

def test_geometric_mean():
    """기하평균 테스트"""
    scores = {'CEI': 75, 'RII': 60, 'CGI': 80, 'MAI': 70}
    weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
    
    result = geometric_mean_weighted(scores, weights)
    expected = (75**0.20) * (60**0.35) * (80**0.25) * (70**0.20)
    
    assert abs(result - expected) < 0.01
```

### 10.2 버그 방지 테스트

```python
# tests/test_bug_prevention.py

def test_no_negative_999_percent():
    """
    -999% 버그 방지 테스트
    
    시나리오: CAPEX가 극소값(0.001억)에서 큰 값(5억)으로 증가
    """
    data = {
        'capex': [-100_000, -100_000_000, -500_000_000],  # 0.001억 → 5억
        'total_cash': [1_000_000_000] * 3,
        'revenue': [10_000_000_000] * 3,
        'operating_cash_flow': [1_000_000_000] * 3,
        'total_assets': [5_000_000_000] * 3,
        'operating_income': [500_000_000] * 3,
        'net_income': [300_000_000] * 3,
    }
    
    calculator = RIICalculator()
    score, details = calculator.calculate(data)
    
    # ⭐ 투자괴리율이 -100 ~ +100 범위 내
    assert -100 <= details['raw']['investment_gap'] <= 100
    
    # 점수가 0 ~ 100 범위 내
    assert 0 <= score <= 100

def test_data_validation_blocks_invalid():
    """데이터 검증이 이상 데이터를 차단하는지 테스트"""
    invalid_data = {
        'revenue': [],  # 빈 데이터
        'capex': [-100, -200, -300],
    }
    
    validator = DataValidator()
    result = validator.validate(invalid_data)
    
    assert result.is_valid == False
    assert result.can_calculate == False
    assert len(result.errors) > 0
```

---

## 11. 구현 체크리스트 (Claude Code용)

### Phase 1: 상수 및 유틸리티 (Day 1)

```
□ 1.1 services/raymonds_index/ 디렉토리 생성

□ 1.2 constants.py 생성
   ├─ CLAMP_LIMITS (범위 제한)
   ├─ GOALPOSTS (정규화 경계값)
   ├─ SUBINDEX_WEIGHTS
   ├─ METRIC_WEIGHTS
   ├─ GRADE_THRESHOLDS
   └─ MIN_DENOMINATOR, MIN_REQUIRED_YEARS

□ 1.3 normalizers.py 생성
   ├─ min_max_normalize()
   ├─ v_score_normalize()
   ├─ inverse_normalize()
   ├─ clamp()
   ├─ winsorize()
   └─ geometric_mean_weighted()

□ 1.4 validators.py 생성
   └─ DataValidator 클래스
```

### Phase 2: 계산기 구현 (Day 1-2)

```
□ 2.1 calculators/base.py
   └─ SubIndexCalculator (ABC)

□ 2.2 calculators/cei.py
   └─ CEICalculator

□ 2.3 calculators/rii.py ⭐ 핵심
   └─ RIICalculator (투자괴리율 범위 제한 포함)

□ 2.4 calculators/cgi.py
   └─ CGICalculator

□ 2.5 calculators/mai.py
   └─ MAICalculator

□ 2.6 engine.py
   └─ RaymondsIndexCalculator
```

### Phase 3: 데이터베이스 (Day 2)

```
□ 3.1 financial_details 테이블 생성 (기존과 동일)

□ 3.2 raymonds_index 테이블 생성 (v3.0 컬럼 추가)

□ 3.3 normalization_params 테이블 생성 (신규)

□ 3.4 마이그레이션 스크립트
```

### Phase 4: API & 테스트 (Day 2-3)

```
□ 4.1 API 엔드포인트
   └─ raymonds_index.py

□ 4.2 단위 테스트
   ├─ test_normalizers.py
   ├─ test_validators.py
   └─ test_calculators.py

□ 4.3 통합 테스트
   └─ test_raymonds_index_api.py
```

### Phase 5: 프론트엔드 (Day 3)

```
□ 5.1 컴포넌트
   ├─ RaymondsIndexCard
   ├─ SubIndexRadar
   └─ InvestmentGapMeter

□ 5.2 ReportPage 통합
```

---

## 12. Option C: Altman 방식 (향후 검토)

> ⚠️ **Option B 완료 후 검토 사항**
> 
> Option B (HDI 방식) 구현 및 백테스팅 완료 후, 아래 조건 충족 시 Option C 적용 여부 결정

### 12.1 Option C 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Option C: Altman Z-Score 방식                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  핵심 아이디어:                                                      │
│  가중치를 전문가 판단이 아닌 "통계적으로 도출"                       │
│                                                                      │
│  방법론:                                                            │
│  1. 500개 기업 × 5년 데이터 수집                                    │
│  2. "실패 기업" vs "성공 기업" 레이블링                             │
│     - 실패: 상장폐지, 관리종목, 횡령/배임 적발                      │
│     - 성공: 시가총액 상위 유지, 매출/이익 성장                      │
│  3. 판별분석(MDA) 또는 로지스틱 회귀 수행                           │
│  4. 통계적으로 유의한 변수 및 계수(가중치) 도출                     │
│  5. 백테스팅으로 예측력 검증                                        │
│                                                                      │
│  장점:                                                               │
│  ├─ 데이터 기반 객관적 가중치                                       │
│  ├─ 예측력 검증 가능                                                │
│  └─ 학술적 근거 확보                                                │
│                                                                      │
│  단점:                                                               │
│  ├─ 충분한 "실패 기업" 데이터 필요 (최소 50개)                      │
│  ├─ 과적합(overfitting) 위험                                        │
│  └─ 구현 복잡도 높음                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.2 Option C 적용 결정 기준

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Option C 적용 결정 기준                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ 필수 조건 (모두 충족 시 검토):                                  │
│                                                                      │
│  1. 데이터 조건                                                     │
│     □ 500개 이상 기업 데이터 확보                                   │
│     □ "실패 기업" 50개 이상 레이블링 완료                           │
│     □ 5년 이상 시계열 데이터 확보                                   │
│                                                                      │
│  2. Option B 검증 결과 (하나라도 해당 시 검토)                      │
│     □ 백테스팅 F1 Score < 0.7                                       │
│     □ False Positive 비율 > 20%                                    │
│     □ 전문가 리뷰에서 가중치 조정 권고                              │
│                                                                      │
│  3. 리소스 조건                                                     │
│     □ 통계 분석 전문가 확보                                         │
│     □ 추가 개발 기간 4주 이상 확보                                  │
│                                                                      │
│  📅 결정 시점: Option B 구현 완료 후 1개월 (백테스팅 후)            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.3 Option C 구현 시 추가 작업

```python
# Option C 구현 시 추가될 모듈 (참고용)

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import cross_val_score
import pandas as pd

class AltmanStyleOptimizer:
    """
    판별분석을 통한 가중치 최적화
    
    전제조건:
    - Option B 구현 완료
    - 500개 기업 × 5년 데이터 확보
    - "투자금 유용 의심" 레이블링 완료 (최소 50개)
    """
    
    def optimize_weights(self, data: pd.DataFrame) -> dict:
        """
        판별분석으로 최적 가중치 도출
        """
        X = data[['CEI', 'RII', 'CGI', 'MAI']]
        y = data['failure_label']  # 0: 정상, 1: 실패
        
        lda = LinearDiscriminantAnalysis()
        lda.fit(X, y)
        
        # 계수를 가중치로 변환
        raw_coef = lda.coef_[0]
        abs_coef = [abs(c) for c in raw_coef]
        total = sum(abs_coef)
        
        return {
            'CEI': abs_coef[0] / total,
            'RII': abs_coef[1] / total,
            'CGI': abs_coef[2] / total,
            'MAI': abs_coef[3] / total,
        }
    
    def backtest(self, weights: dict, test_data: pd.DataFrame) -> dict:
        """
        백테스팅으로 예측력 검증
        """
        from sklearn.metrics import f1_score, precision_score, recall_score
        
        # 새 가중치로 점수 재계산
        test_data['new_score'] = (
            test_data['CEI'] * weights['CEI'] +
            test_data['RII'] * weights['RII'] +
            test_data['CGI'] * weights['CGI'] +
            test_data['MAI'] * weights['MAI']
        )
        
        # 임계값 최적화
        best_threshold = self._find_optimal_threshold(test_data)
        predictions = (test_data['new_score'] < best_threshold).astype(int)
        
        return {
            'f1_score': f1_score(test_data['failure_label'], predictions),
            'precision': precision_score(test_data['failure_label'], predictions),
            'recall': recall_score(test_data['failure_label'], predictions),
            'threshold': best_threshold,
        }
```

---

## 13. 결론

### 13.1 v3.0 핵심 개선사항 요약

| 문제 | v2.1 | v3.0 해결책 |
|------|------|-------------|
| -999% 스코어 | 발생 | **범위 제한 (Clamping)** |
| 스케일 불일치 | 원본값 혼용 | **Min-Max 정규화** |
| 극단값 왜곡 | 없음 | **Winsorizing** |
| 완전 대체 허용 | 산술평균 | **기하평균** |
| 데이터 오류 | 그대로 계산 | **검증 레이어** |

### 13.2 구현 우선순위

```
1순위: constants.py + normalizers.py (Day 1) → 핵심 함수
2순위: validators.py + RIICalculator (Day 1) → -999% 버그 해결
3순위: 나머지 Calculator + engine.py (Day 2) → 전체 계산
4순위: DB 마이그레이션 + API (Day 2-3) → 배포 준비
5순위: Option C 검토 (완료 후 1개월) → 추가 최적화
```

### 13.3 기대 효과

- **신뢰도 향상**: -999% 같은 이상값 완전 제거
- **일관성 확보**: 모든 지표가 0~100 범위로 통일
- **균형 유도**: 기하평균으로 한쪽만 높은 기업 견제
- **투명성**: 정규화 경계값 공개로 재현 가능
- **확장성**: Option C로 추후 통계적 최적화 가능

---

**다음 단계**: Claude Code에서 `Phase 1 - constants.py 생성` 실행
