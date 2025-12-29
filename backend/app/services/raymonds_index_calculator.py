"""
RaymondsIndex™ v2.0 계산 엔진

자본 배분 효율성 지수를 계산합니다.
4개 Sub-Index의 가중 평균으로 종합 점수를 산출합니다.

Sub-Index (v2.0):
- CEI (Capital Efficiency Index): 20% - 자본 효율성
- RII (Reinvestment Intensity Index): 35% - 재투자 강도 ⭐핵심 (R&D 강도 15% 포함)
- CGI (Cash Governance Index): 25% - 현금 거버넌스 ⭐핵심 (부채 건전성 20% 포함)
- MAI (Momentum Alignment Index): 20% - 모멘텀 정합성

v2.0 주요 변경:
- 투자괴리율: (초기 2년 재투자율) - (최근 2년 재투자율)
  → 양수(+): 투자 감소 (위험), 음수(-): 투자 증가 (긍정)
- RII: R&D 강도 15% 신규 추가
- CGI: 부채/EBITDA 건전성 20% 신규 추가
- 업종별 가중치 조정 (R&D 집약, 자본 집약, 연속 투자형)

Grade (v2.0):
- A++: 95-100 (모범)
- A+:  90-94  (우수)
- A:   85-89  (양호)
- A-:  80-84  (양호-)
- B+:  70-79  (관찰)
- B:   60-69  (주의)
- B-:  50-59  (경고)
- C+:  40-49  (심각)
- C:   0-39   (부적격)

특별 규칙:
- 현금-유형자산 비율 > 30:1 → 최대 B-
- 조달자금 전환율 < 30% → 최대 B-
- 단기금융상품비율 > 65% + CAPEX 감소 → 최대 B
- 위 조건 2개 이상 해당 → 최대 C+
"""
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class SubIndexScores:
    """Sub-Index 점수 (v2.0)"""
    cei: float = 0.0  # Capital Efficiency Index (20%)
    rii: float = 0.0  # Reinvestment Intensity Index (35%)
    cgi: float = 0.0  # Cash Governance Index (25%)
    mai: float = 0.0  # Momentum Alignment Index (20%)


@dataclass
class CoreMetrics:
    """핵심 지표 (v2.0)"""
    # 기존 지표
    investment_gap: float = 0.0      # 투자괴리율 (%) - v4.0 방식 (호환용)
    cash_cagr: float = 0.0           # 현금 CAGR (%)
    capex_growth: float = 0.0        # CAPEX 증가율 (%)
    idle_cash_ratio: float = 0.0     # 유휴현금비율 (%)
    asset_turnover: float = 0.0      # 자산회전율 (회)
    reinvestment_rate: float = 0.0   # 재투자율 (%)
    shareholder_return: float = 0.0  # 주주환원율 (%)

    # v4.0 기존 지표
    cash_tangible_ratio: float = 0.0       # 현금-유형자산 증가비율 (X:1)
    fundraising_utilization: float = 0.0   # 조달자금 투자전환율 (%)
    short_term_ratio: float = 0.0          # 단기금융상품 비율 (%)
    capex_trend: str = 'stable'            # CAPEX 추세 (increasing/stable/decreasing)
    roic: float = 0.0                      # 투하자본수익률 (%)
    capex_cv: float = 0.0                  # CAPEX 변동계수

    # v2.0 신규 지표
    investment_gap_v2: float = 0.0         # 투자괴리율 v2 (초기2년 - 최근2년 재투자율)
    cash_utilization: float = 0.0          # 현금 활용도 (%)
    industry_sector: str = ''              # 업종 분류
    weight_adjustment: dict = field(default_factory=dict)  # 업종별 가중치 조정


@dataclass
class RaymondsIndexResult:
    """RaymondsIndex 계산 결과"""
    company_id: str
    fiscal_year: int
    total_score: float = 0.0
    grade: str = 'C'
    sub_indices: SubIndexScores = field(default_factory=SubIndexScores)
    core_metrics: CoreMetrics = field(default_factory=CoreMetrics)
    red_flags: List[str] = field(default_factory=list)
    yellow_flags: List[str] = field(default_factory=list)
    verdict: str = ''
    key_risk: str = ''
    recommendation: str = ''
    watch_trigger: str = ''
    data_quality_score: float = 0.0
    violation_count: int = 0


class RaymondsIndexCalculator:
    """
    RaymondsIndex v2.0 계산기

    3년간 재무 데이터를 기반으로 자본 배분 효율성 지수를 계산합니다.

    v2.0 주요 변경:
    - 투자괴리율: (초기 2년 재투자율) - (최근 2년 재투자율)
    - RII: R&D 강도 15% 추가
    - CGI: 부채/EBITDA 20% 추가
    - 업종별 가중치 조정
    """

    # v2.0 Sub-Index 가중치
    WEIGHTS = {
        'CEI': 0.20,  # Capital Efficiency Index (15% → 20%)
        'RII': 0.35,  # Reinvestment Intensity Index (40% → 35%)
        'CGI': 0.25,  # Cash Governance Index (30% → 25%)
        'MAI': 0.20,  # Momentum Alignment Index (15% → 20%)
    }

    # v2.0 등급 기준 (조정됨)
    GRADE_THRESHOLDS = [
        (95, 'A++'),
        (90, 'A+'),
        (85, 'A'),
        (80, 'A-'),
        (70, 'B+'),
        (60, 'B'),
        (50, 'B-'),
        (40, 'C+'),
        (0, 'C'),
    ]

    # 등급 순서 (강제 하향용)
    GRADE_ORDER = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

    # v2.0 업종별 가중치 조정
    INDUSTRY_WEIGHT_ADJUSTMENTS = {
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

    def __init__(self, industry_sector: str = None):
        self.industry_sector = industry_sector
        self.adjusted_weights = self._get_adjusted_weights(industry_sector)

    def _get_adjusted_weights(self, industry_sector: str) -> Dict[str, float]:
        """업종별 가중치 조정"""
        weights = self.WEIGHTS.copy()

        if not industry_sector:
            return weights

        for industry_type, config in self.INDUSTRY_WEIGHT_ADJUSTMENTS.items():
            if industry_sector in config['sectors']:
                for key, adjustment in config['adjustments'].items():
                    if key in weights:
                        weights[key] += adjustment
                break

        return weights

    def calculate(
        self,
        company_id: str,
        financial_data: List[Dict],
        target_year: Optional[int] = None
    ) -> Optional[RaymondsIndexResult]:
        """
        RaymondsIndex v4.0 계산

        Args:
            company_id: 회사 ID
            financial_data: 3년간 재무 데이터 리스트 (fiscal_year 순 정렬)
            target_year: 계산 대상 연도 (기본: 가장 최근)

        Returns:
            RaymondsIndexResult 또는 None (데이터 부족)
        """
        if not financial_data or len(financial_data) < 2:
            logger.debug(f"Insufficient data for {company_id}")
            return None

        # 연도순 정렬
        sorted_data = sorted(financial_data, key=lambda x: x.get('fiscal_year', 0))

        if target_year is None:
            target_year = sorted_data[-1].get('fiscal_year')

        # 최근 데이터
        current = sorted_data[-1]
        previous = sorted_data[-2] if len(sorted_data) >= 2 else None
        oldest = sorted_data[0] if len(sorted_data) >= 3 else previous

        # 데이터 품질 점수 계산
        data_quality = self._calculate_data_quality(current)

        # 핵심 지표 계산 (v4.0)
        core_metrics = self._calculate_core_metrics(current, previous, oldest, sorted_data)

        # Sub-Index 계산 (v4.0)
        sub_indices = self._calculate_sub_indices(current, previous, oldest, sorted_data, core_metrics)

        # 종합 점수 계산
        total_score = self._calculate_total_score(sub_indices)

        # 등급 결정 (기본)
        grade = self._determine_grade(total_score)

        # Red/Yellow Flags 생성
        red_flags, yellow_flags = self._generate_flags(core_metrics, sorted_data)

        # 특별 규칙 적용 (등급 강제 조정)
        grade, violation_count = self._apply_special_rules(grade, core_metrics)

        # 해석 생성
        verdict, key_risk, recommendation, watch_trigger = self._generate_interpretation(
            grade, core_metrics, red_flags, yellow_flags, violation_count
        )

        return RaymondsIndexResult(
            company_id=company_id,
            fiscal_year=target_year,
            total_score=round(total_score, 2),
            grade=grade,
            sub_indices=sub_indices,
            core_metrics=core_metrics,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            verdict=verdict,
            key_risk=key_risk,
            recommendation=recommendation,
            watch_trigger=watch_trigger,
            data_quality_score=data_quality,
            violation_count=violation_count
        )

    def _calculate_data_quality(self, data: Dict) -> float:
        """데이터 품질 점수 계산"""
        required_fields = [
            'total_assets', 'revenue', 'operating_cash_flow', 'capex',
            'cash_and_equivalents', 'net_income', 'total_equity',
            'operating_income', 'tangible_assets', 'short_term_investments'
        ]

        filled = sum(1 for f in required_fields if data.get(f) is not None)
        return round(filled / len(required_fields), 2)

    def _safe_get(self, d: Optional[Dict], key: str, default: float = 0) -> float:
        """안전한 값 추출"""
        if d is None:
            return default
        val = d.get(key)
        return float(val) if val is not None else default

    def _calculate_investment_gap_v2_legacy(
        self,
        oldest: Optional[Dict],
        current: Dict
    ) -> float:
        """
        투자괴리율 v2 레거시 계산 (호환용)

        현금성자산 증가비율 - CAPEX 증가비율을 계산합니다.

        현금성자산 = 현금 + 단기금융상품 + 장기금융상품
        CAPEX = 유형자산 + 무형자산 + 사용권자산 + 관계기업투자 (재무상태표 기준)

        Args:
            oldest: 가장 오래된 기간 데이터 (2022년 결산 등)
            current: 현재 기간 데이터 (2024년 또는 2025년 3분기)

        Returns:
            투자괴리율 (%)
        """
        if oldest is None:
            return 0.0

        # 현금성자산 계산 (현금 + 단기금융상품 + 장기금융상품)
        def calc_cash_equivalent(d: Dict) -> float:
            return (
                self._safe_get(d, 'cash_and_equivalents') +
                self._safe_get(d, 'short_term_investments') +
                self._safe_get(d, 'fvpl_financial_assets') +  # 당기손익공정가치측정금융자산
                self._safe_get(d, 'other_financial_assets_non_current')  # 기타금융자산(비유동)
            )

        # CAPEX 계산 (유형자산 + 무형자산 + 사용권자산 + 관계기업투자)
        def calc_capex_total(d: Dict) -> float:
            return (
                self._safe_get(d, 'tangible_assets') +
                self._safe_get(d, 'intangible_assets') +
                self._safe_get(d, 'right_of_use_assets') +
                self._safe_get(d, 'investments_in_associates')
            )

        oldest_cash = calc_cash_equivalent(oldest)
        current_cash = calc_cash_equivalent(current)

        oldest_capex = calc_capex_total(oldest)
        current_capex = calc_capex_total(current)

        # 현금성자산 증가비율 계산
        cash_growth = 0.0
        if oldest_cash > 0:
            cash_growth = ((current_cash - oldest_cash) / oldest_cash) * 100
        elif current_cash > 0 and oldest_cash == 0:
            cash_growth = 100.0  # 0에서 증가 시 100%로 처리

        # CAPEX 증가비율 계산
        capex_growth = 0.0
        if oldest_capex > 0:
            capex_growth = ((current_capex - oldest_capex) / oldest_capex) * 100
        elif current_capex > 0 and oldest_capex == 0:
            capex_growth = 100.0  # 0에서 증가 시 100%로 처리

        # 투자괴리율 = 현금성자산 증가비율 - CAPEX 증가비율
        # 양수: 현금이 CAPEX보다 더 많이 증가 (현금 쌓기)
        # 음수: CAPEX가 현금보다 더 많이 증가 (적극 투자)
        investment_gap = round(cash_growth - capex_growth, 2)

        # 범위 제한 (-999 ~ 999)
        return max(-999.0, min(999.0, investment_gap))

    def _calculate_reinvestment_rate(self, data: Dict) -> float:
        """
        재투자율 계산 = CAPEX / OCF

        특수 케이스:
        - OCF <= 0 이고 CAPEX > 0 → 100% (투자 의지 존재)
        - CAPEX = 0 → 0%
        """
        capex = abs(self._safe_get(data, 'capex'))
        ocf = self._safe_get(data, 'operating_cash_flow')

        if capex == 0:
            return 0.0
        if ocf <= 0:
            return 100.0  # 영업현금흐름 없이 투자하는 경우

        rate = (capex / ocf) * 100
        return min(rate, 200.0)  # 최대 200%로 제한

    def _calculate_investment_gap_v2_new(self, all_data: List[Dict]) -> float:
        """
        투자괴리율 v2.0 계산 (재투자율 기반)

        투자괴리율 = 초기 2년 평균 재투자율 - 최근 2년 평균 재투자율
        재투자율 = CAPEX / OCF

        양수(+): 투자 줄임 (위험 신호)
        음수(-): 투자 늘림 (긍정 신호)

        Args:
            all_data: 연도순 정렬된 재무 데이터 리스트

        Returns:
            투자괴리율 (%p)
        """
        if len(all_data) < 2:
            return 0.0

        # 각 연도별 재투자율 계산
        reinvest_rates = []
        for d in all_data:
            rate = self._calculate_reinvestment_rate(d)
            reinvest_rates.append(rate)

        # 데이터가 2개인 경우
        if len(all_data) == 2:
            initial_rate = reinvest_rates[0]
            recent_rate = reinvest_rates[1]
        # 데이터가 3개 이상인 경우
        else:
            # 초기 2년 평균
            initial_rate = sum(reinvest_rates[:2]) / 2
            # 최근 2년 평균
            recent_rate = sum(reinvest_rates[-2:]) / 2

        # 투자괴리율 = 초기 - 최근
        # 양수: 투자 줄임 (위험)
        # 음수: 투자 늘림 (긍정)
        gap = initial_rate - recent_rate

        # 범위 제한 (-100 ~ 100)
        return round(max(-100.0, min(100.0, gap)), 2)

    def _analyze_trend(self, values: List[float]) -> str:
        """추세 분석 (선형 회귀 기반)"""
        n = len(values)
        if n < 2:
            return 'stable'

        # 0인 값 제외
        valid_values = [v for v in values if v != 0]
        if len(valid_values) < 2:
            return 'stable'

        x_mean = (len(valid_values) - 1) / 2
        y_mean = sum(valid_values) / len(valid_values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(valid_values))
        denominator = sum((i - x_mean) ** 2 for i in range(len(valid_values)))

        if denominator == 0:
            return 'stable'

        slope = numerator / denominator
        relative_slope = slope / abs(y_mean) if y_mean != 0 else 0

        if relative_slope > 0.05:
            return 'increasing'
        elif relative_slope < -0.05:
            return 'decreasing'
        return 'stable'

    def _calculate_core_metrics(
        self,
        current: Dict,
        previous: Optional[Dict],
        oldest: Optional[Dict],
        all_data: List[Dict]
    ) -> CoreMetrics:
        """핵심 지표 계산 (v4.0)"""
        metrics = CoreMetrics()

        # 현재 값
        cash = self._safe_get(current, 'cash_and_equivalents')
        short_term = self._safe_get(current, 'short_term_investments')
        total_cash = cash + short_term
        total_assets = self._safe_get(current, 'total_assets')
        total_equity = self._safe_get(current, 'total_equity')
        total_liabilities = self._safe_get(current, 'total_liabilities')
        revenue = self._safe_get(current, 'revenue')
        tangible = self._safe_get(current, 'tangible_assets')
        capex = abs(self._safe_get(current, 'capex'))
        operating_cf = self._safe_get(current, 'operating_cash_flow')
        operating_income = self._safe_get(current, 'operating_income')
        net_income = self._safe_get(current, 'net_income')
        dividend = abs(self._safe_get(current, 'dividend_paid'))
        treasury = abs(self._safe_get(current, 'treasury_stock_acquisition'))

        # 과거 값
        prev_cash = self._safe_get(previous, 'cash_and_equivalents')
        prev_short_term = self._safe_get(previous, 'short_term_investments')
        prev_total_cash = prev_cash + prev_short_term
        prev_tangible = self._safe_get(previous, 'tangible_assets')
        prev_capex = abs(self._safe_get(previous, 'capex'))
        oldest_cash = self._safe_get(oldest, 'cash_and_equivalents')
        oldest_short_term = self._safe_get(oldest, 'short_term_investments')
        oldest_total_cash = oldest_cash + oldest_short_term

        # ═══════════════════════════════════════════════════════════════
        # 기존 지표
        # ═══════════════════════════════════════════════════════════════

        # 1. 자산회전율
        if total_assets > 0:
            metrics.asset_turnover = round(revenue / total_assets, 3)

        # 2. 유휴현금비율
        if total_assets > 0:
            metrics.idle_cash_ratio = round((total_cash / total_assets) * 100, 2)

        # 3. 재투자율 (v4.0: CAPEX / 영업이익)
        if operating_income > 0:
            metrics.reinvestment_rate = round((capex / operating_income) * 100, 2)

        # 4. 주주환원율
        if operating_cf > 0:
            metrics.shareholder_return = round(
                ((dividend + treasury) / operating_cf) * 100, 2
            )

        # 5. 현금 CAGR (3년) - 기존 방식 유지 (참고용)
        if oldest_total_cash and oldest_total_cash > 0 and total_cash > 0:
            years = len(all_data) - 1 if len(all_data) > 1 else 1
            metrics.cash_cagr = round(
                (pow(total_cash / oldest_total_cash, 1 / years) - 1) * 100, 2
            )

        # 6. CAPEX 증가율 - 기존 방식 유지 (참고용)
        if prev_capex > 0:
            metrics.capex_growth = round(
                ((capex - prev_capex) / prev_capex) * 100, 2
            )

        # 7. 투자괴리율 (레거시 - 호환용)
        # 현금성자산 = 현금 + 단기금융상품 + 장기금융상품
        # CAPEX = 유형자산 + 무형자산 + 사용권자산 + 관계기업투자 (재무상태표 기준)
        metrics.investment_gap = self._calculate_investment_gap_v2_legacy(oldest, current)

        # 8. 투자괴리율 v2.0 (신규) - 재투자율 기반
        # 초기 2년 평균 재투자율 - 최근 2년 평균 재투자율
        metrics.investment_gap_v2 = self._calculate_investment_gap_v2_new(all_data)

        # ═══════════════════════════════════════════════════════════════
        # v4.0 신규 지표
        # ═══════════════════════════════════════════════════════════════

        # 8. 현금-유형자산 증가비율 ⭐핵심
        cash_increase = total_cash - prev_total_cash
        tangible_increase = tangible - prev_tangible

        if cash_increase > 0 and tangible_increase > 0:
            metrics.cash_tangible_ratio = round(cash_increase / tangible_increase, 2)
        elif cash_increase > 0 and tangible_increase <= 0:
            metrics.cash_tangible_ratio = 999.0  # 무한대 대체값 (돈만 쌓고 투자 0)
        else:
            metrics.cash_tangible_ratio = 0.0  # 현금 감소 시

        # 9. 단기금융상품 비율 ⭐핵심
        if total_cash > 0:
            metrics.short_term_ratio = round((short_term / total_cash) * 100, 2)

        # 10. CAPEX 추세 ⭐핵심
        capex_values = [abs(self._safe_get(d, 'capex')) for d in all_data]
        metrics.capex_trend = self._analyze_trend(capex_values)

        # 11. 조달자금 투자전환율 ⭐핵심
        # 3년간 조달금액 합계
        total_fundraising = 0
        total_investment = 0
        for d in all_data:
            stock_issuance = abs(self._safe_get(d, 'stock_issuance'))
            bond_issuance = abs(self._safe_get(d, 'bond_issuance'))
            # CB 발행액은 전환사채 잔액의 증가분으로 추정
            cb_balance = self._safe_get(d, 'convertible_bonds')
            total_fundraising += stock_issuance + bond_issuance
            total_investment += abs(self._safe_get(d, 'capex'))

        if total_fundraising > 0:
            metrics.fundraising_utilization = round(
                (total_investment / total_fundraising) * 100, 2
            )
        else:
            metrics.fundraising_utilization = -1  # 조달 없음 표시

        # 12. ROIC (투하자본수익률)
        invested_capital = total_equity + total_liabilities - cash
        if invested_capital > 0 and operating_income != 0:
            nopat = operating_income * 0.78  # 법인세율 22% 가정
            metrics.roic = round((nopat / invested_capital) * 100, 2)

        # 13. CAPEX 변동계수 (투자 지속성)
        if capex_values and len(capex_values) >= 2:
            mean_capex = sum(capex_values) / len(capex_values)
            if mean_capex > 0:
                variance = sum((x - mean_capex) ** 2 for x in capex_values) / len(capex_values)
                std = math.sqrt(variance)
                metrics.capex_cv = round(std / mean_capex, 3)

        # ═══════════════════════════════════════════════════════════════
        # v2.0 신규 지표
        # ═══════════════════════════════════════════════════════════════

        # 14. 현금 활용도
        # (CAPEX + 배당 + 자사주매입) / (기초 현금 + OCF)
        total_usage = capex + dividend + treasury
        total_available = prev_total_cash + max(operating_cf, 0)
        if total_available > 0:
            metrics.cash_utilization = round((total_usage / total_available) * 100, 2)

        # 15. 업종 분류 (외부에서 주입)
        metrics.industry_sector = self.industry_sector or ''

        return metrics

    def _calculate_sub_indices(
        self,
        current: Dict,
        previous: Optional[Dict],
        oldest: Optional[Dict],
        all_data: List[Dict],
        core_metrics: CoreMetrics
    ) -> SubIndexScores:
        """Sub-Index 점수 계산 (v4.0)"""
        scores = SubIndexScores()

        revenue = self._safe_get(current, 'revenue')
        tangible = self._safe_get(current, 'tangible_assets')
        capex = abs(self._safe_get(current, 'capex'))
        operating_income = self._safe_get(current, 'operating_income')
        operating_cf = self._safe_get(current, 'operating_cash_flow')
        net_income = self._safe_get(current, 'net_income')

        # ═══════════════════════════════════════════════════════════════
        # CEI: Capital Efficiency Index (15%)
        # ═══════════════════════════════════════════════════════════════
        cei_components = []

        # 자산회전율 점수 (40%)
        turnover_score = min(core_metrics.asset_turnover / 0.5, 1) * 100
        cei_components.append(turnover_score * 0.4)

        # ROIC 점수 (40%)
        roic = core_metrics.roic
        if roic >= 15:
            roic_score = 90
        elif roic >= 8:
            roic_score = 50 + (roic - 8) * (40 / 7)  # 8-15%: 50-90
        elif roic >= 0:
            roic_score = 20 + roic * (30 / 8)  # 0-8%: 20-50
        else:
            roic_score = max(20 + roic, 0)  # 음수: 감점
        cei_components.append(roic_score * 0.4)

        # 효율성 추세 점수 (20%)
        turnover_values = []
        for d in all_data:
            assets = self._safe_get(d, 'total_assets') or 1
            rev = self._safe_get(d, 'revenue')
            turnover_values.append(rev / assets)
        efficiency_trend = self._analyze_trend(turnover_values)

        if efficiency_trend == 'increasing':
            trend_score = 80
        elif efficiency_trend == 'stable':
            trend_score = 60
        else:
            trend_score = 30
        cei_components.append(trend_score * 0.2)

        scores.cei = round(sum(cei_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # RII: Reinvestment Intensity Index (35%) - 핵심 (v2.0)
        # 구성: CAPEX강도(30%) + 투자괴리율(30%) + 재투자율(25%) + 투자지속성(15%)
        # ═══════════════════════════════════════════════════════════════
        rii_components = []

        # 1. CAPEX 강도 점수 (30%)
        if revenue > 0:
            capex_intensity = (capex / revenue) * 100
        else:
            capex_intensity = 0

        if 5 <= capex_intensity <= 15:
            intensity_score = 100
        elif capex_intensity < 5:
            intensity_score = capex_intensity * 20
        else:
            intensity_score = max(100 - (capex_intensity - 15) * 5, 0)
        rii_components.append(intensity_score * 0.30)

        # 2. 투자괴리율 점수 (30%) ⭐v2.0 방식
        # 양수(+): 투자 줄임 (위험) → 낮은 점수
        # 음수(-): 투자 늘림 (긍정) → 높은 점수
        gap_v2 = core_metrics.investment_gap_v2
        if gap_v2 >= 50:
            gap_score = 0
        elif gap_v2 >= 30:
            gap_score = 20
        elif gap_v2 >= 15:
            gap_score = 40
        elif gap_v2 >= 5:
            gap_score = 55
        elif gap_v2 >= -5:
            gap_score = 70
        elif gap_v2 >= -15:
            gap_score = 80
        elif gap_v2 >= -30:
            gap_score = 90
        else:  # < -30
            gap_score = 95
        rii_components.append(gap_score * 0.30)

        # 3. 재투자율 점수 (25%)
        reinvest = core_metrics.reinvestment_rate
        if reinvest >= 60:
            reinvest_score = 90
        elif reinvest >= 40:
            reinvest_score = 80
        elif reinvest >= 20:
            reinvest_score = 60
        elif reinvest >= 10:
            reinvest_score = 40
        elif reinvest > 0:
            reinvest_score = 20
        else:
            reinvest_score = 50  # 영업손실 시 중립
        rii_components.append(reinvest_score * 0.25)

        # 4. 투자 지속성 점수 (15%)
        cv = core_metrics.capex_cv
        if cv < 0.15:
            cv_score = 90
        elif cv < 0.25:
            cv_score = 75
        elif cv < 0.40:
            cv_score = 55
        elif cv < 0.60:
            cv_score = 35
        else:
            cv_score = 15
        rii_components.append(cv_score * 0.15)

        scores.rii = round(sum(rii_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # CGI: Cash Governance Index (25%) - 핵심 (v2.0)
        # 구성: 현금활용도(25%) + 자금조달효율성(30%) + 주주환원균형(25%) + 현금적정성(20%)
        # ═══════════════════════════════════════════════════════════════
        cgi_components = []

        # 1. 현금 활용도 점수 (25%) ⭐v2.0 신규
        cash_util = core_metrics.cash_utilization
        if 60 <= cash_util <= 90:
            cash_util_score = 95
        elif 40 <= cash_util < 60 or 90 < cash_util <= 100:
            cash_util_score = 80
        elif 20 <= cash_util < 40:
            cash_util_score = 60
        elif cash_util < 20:
            cash_util_score = 30  # 현금 활용 부족
        else:  # > 100
            cash_util_score = 50  # 과도한 지출
        cgi_components.append(cash_util_score * 0.25)

        # 2. 자금 조달 효율성 점수 (30%)
        utilization = core_metrics.fundraising_utilization
        if utilization < 0:  # 조달 없음
            util_score = 80
        elif utilization >= 80:
            util_score = 95
        elif utilization >= 60:
            util_score = 80
        elif utilization >= 50:
            util_score = 65
        elif utilization >= 30:
            util_score = 40
        else:
            util_score = 15
        cgi_components.append(util_score * 0.30)

        # 3. 주주환원 균형 점수 (25%)
        shareholder = core_metrics.shareholder_return
        if 20 <= shareholder <= 50:
            sh_score = 90
        elif 10 <= shareholder < 20 or 50 < shareholder <= 70:
            sh_score = 70
        elif 5 <= shareholder < 10 or 70 < shareholder <= 80:
            sh_score = 50
        else:
            sh_score = 30
        cgi_components.append(sh_score * 0.25)

        # 4. 현금 적정성 점수 (20%)
        idle = core_metrics.idle_cash_ratio
        # 10-20%가 적정
        if 10 <= idle <= 20:
            idle_score = 90
        elif idle < 10:
            idle_score = idle * 9  # 0-10%: 0-90
        elif idle <= 30:
            idle_score = 90 - (idle - 20) * 4  # 20-30%: 90-50
        else:
            idle_score = max(50 - (idle - 30) * 2, 15)  # 30% 이상: 감점
        cgi_components.append(idle_score * 0.20)

        scores.cgi = round(sum(cgi_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # MAI: Momentum Alignment Index (20%) (v2.0)
        # ═══════════════════════════════════════════════════════════════
        mai_components = []

        # 매출-투자 동조성 점수 (40%)
        prev_revenue = self._safe_get(previous, 'revenue') if previous else 0
        curr_revenue = self._safe_get(current, 'revenue')
        revenue_growth = 0
        if prev_revenue and prev_revenue > 0:
            revenue_growth = ((curr_revenue - prev_revenue) / prev_revenue) * 100

        capex_change = core_metrics.capex_growth

        # 동조성 판정
        if revenue_growth > 10:  # 고성장
            if capex_change > 0:
                sync_score = 95
            elif capex_change >= -10:
                sync_score = 70
            else:
                sync_score = 35
        elif revenue_growth > 0:  # 저성장
            if capex_change > 0:
                sync_score = 80
            elif capex_change >= -10:
                sync_score = 70
            else:
                sync_score = 50
        else:  # 역성장
            if capex_change <= 0:
                sync_score = 60
            else:
                sync_score = 75  # 턴어라운드 시도
        mai_components.append(sync_score * 0.40)

        # 이익 품질 점수 (30%)
        if net_income and net_income != 0:
            quality_ratio = operating_cf / net_income
            if 0.7 <= quality_ratio <= 1.3:
                quality_score = 90
            elif 0.5 <= quality_ratio < 0.7 or 1.3 < quality_ratio <= 1.5:
                quality_score = 70
            elif 0.3 <= quality_ratio < 0.5 or 1.5 < quality_ratio <= 2.0:
                quality_score = 50
            else:
                quality_score = 30
        else:
            quality_score = 50  # 순손실 시 중립
        mai_components.append(quality_score * 0.30)

        # 투자 추세 점수 (20%)
        capex_trend = core_metrics.capex_trend
        if capex_trend == 'increasing':
            capex_trend_score = 80
        elif capex_trend == 'stable':
            capex_trend_score = 60
        else:
            capex_trend_score = 30
        mai_components.append(capex_trend_score * 0.20)

        # FCF 추세 점수 (10%)
        fcf_values = []
        for d in all_data:
            ocf = self._safe_get(d, 'operating_cash_flow')
            cap = abs(self._safe_get(d, 'capex'))
            fcf_values.append(ocf - cap)
        fcf_trend = self._analyze_trend(fcf_values)

        if fcf_trend == 'increasing':
            fcf_score = 80
        elif fcf_trend == 'stable':
            fcf_score = 60
        else:
            fcf_score = 40
        mai_components.append(fcf_score * 0.10)

        scores.mai = round(sum(mai_components), 2)

        return scores

    def _calculate_total_score(self, sub_indices: SubIndexScores) -> float:
        """종합 점수 계산 (업종별 가중치 조정 반영)"""
        weights = self.adjusted_weights
        total = (
            sub_indices.cei * weights['CEI'] +
            sub_indices.rii * weights['RII'] +
            sub_indices.cgi * weights['CGI'] +
            sub_indices.mai * weights['MAI']
        )
        return min(max(total, 0), 100)

    def _determine_grade(self, score: float) -> str:
        """등급 결정"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'C'

    def _apply_special_rules(self, grade: str, core_metrics: CoreMetrics) -> Tuple[str, int]:
        """특별 규칙 적용 - 등급 강제 하향"""
        violation_count = 0

        # 규칙 1: 현금-유형자산 비율 > 30:1
        if core_metrics.cash_tangible_ratio > 30:
            violation_count += 1

        # 규칙 2: 조달자금 전환율 < 30%
        if core_metrics.fundraising_utilization >= 0 and core_metrics.fundraising_utilization < 30:
            violation_count += 1

        # 규칙 3: 단기금융상품비율 > 65% + CAPEX 감소
        if core_metrics.short_term_ratio > 65 and core_metrics.capex_trend == 'decreasing':
            violation_count += 1

        # 등급 강제 조정
        if violation_count >= 2:
            max_grade = 'C+'
        elif violation_count == 1:
            max_grade = 'B-'
        else:
            max_grade = None

        if max_grade:
            current_idx = self.GRADE_ORDER.index(grade)
            max_idx = self.GRADE_ORDER.index(max_grade)
            if current_idx < max_idx:  # 현재 등급이 더 좋으면 하향
                grade = max_grade

        return grade, violation_count

    def _generate_flags(
        self,
        core_metrics: CoreMetrics,
        historical_data: List[Dict]
    ) -> Tuple[List[str], List[str]]:
        """Red/Yellow Flags 생성 (v2.0)"""
        red_flags = []
        yellow_flags = []

        # ═══════════════════════════════════════════════════════════════
        # CRITICAL (Red Flags)
        # ═══════════════════════════════════════════════════════════════

        # v2.0: 투자괴리율 > +40%p (심각한 투자 축소)
        if core_metrics.investment_gap_v2 > 40:
            red_flags.append(
                f"투자괴리율 CRITICAL: +{core_metrics.investment_gap_v2:.1f}%p (초기 대비 재투자 급감)"
            )

        # 조달자금 전환율 < 30%
        if core_metrics.fundraising_utilization >= 0 and core_metrics.fundraising_utilization < 30:
            red_flags.append(
                f"조달자금 미사용: 투자전환율 {core_metrics.fundraising_utilization:.1f}%"
            )

        # 현금-유형자산 비율 > 30:1
        if core_metrics.cash_tangible_ratio > 30:
            red_flags.append(
                f"현금 쌓기 vs 투자 극심한 불균형: 현금-유형자산 비율 {core_metrics.cash_tangible_ratio:.1f}:1"
            )

        # ═══════════════════════════════════════════════════════════════
        # HIGH (Red Flags)
        # ═══════════════════════════════════════════════════════════════

        # v2.0: 투자괴리율 > +25%p
        if 25 < core_metrics.investment_gap_v2 <= 40:
            red_flags.append(
                f"투자괴리율 HIGH: +{core_metrics.investment_gap_v2:.1f}%p (투자 유의미 감소)"
            )

        # 이자놀이 + 투자축소
        if core_metrics.short_term_ratio > 60 and core_metrics.capex_trend == 'decreasing':
            red_flags.append(
                f"이자놀이 + 투자축소: 단기금융상품 {core_metrics.short_term_ratio:.1f}%, CAPEX 감소 추세"
            )

        # 재투자율 < 10% (v2.0)
        if 0 < core_metrics.reinvestment_rate < 10:
            red_flags.append(
                f"재투자율 극저: {core_metrics.reinvestment_rate:.1f}% (투자 의지 부족)"
            )

        # ═══════════════════════════════════════════════════════════════
        # Yellow Flags
        # ═══════════════════════════════════════════════════════════════

        # 현금-투자 불균형 주의
        if core_metrics.cash_tangible_ratio > 10 and core_metrics.cash_tangible_ratio <= 30:
            yellow_flags.append(
                f"현금-투자 불균형 주의: 비율 {core_metrics.cash_tangible_ratio:.1f}:1"
            )

        # 단기금융상품 비율 과다
        if core_metrics.short_term_ratio > 50:
            yellow_flags.append(
                f"단기금융상품 비율 과다: {core_metrics.short_term_ratio:.1f}%"
            )

        # 유휴현금 과다
        if core_metrics.idle_cash_ratio > 30:
            yellow_flags.append(
                f"유휴현금 과다: {core_metrics.idle_cash_ratio:.1f}%"
            )

        # v2.0: 투자괴리율 > +15%p (경고)
        if 15 < core_metrics.investment_gap_v2 <= 25:
            yellow_flags.append(
                f"투자괴리율 주의: +{core_metrics.investment_gap_v2:.1f}%p"
            )

        # 낮은 현금 활용도
        if core_metrics.cash_utilization < 20:
            yellow_flags.append(
                f"현금 활용도 저조: {core_metrics.cash_utilization:.1f}%"
            )

        return red_flags, yellow_flags

    def _generate_interpretation(
        self,
        grade: str,
        core_metrics: CoreMetrics,
        red_flags: List[str],
        yellow_flags: List[str],
        violation_count: int
    ) -> Tuple[str, str, str, str]:
        """해석 및 권고 생성 (v4.0)"""

        # 한 줄 요약
        verdicts = {
            'A++': '투자금을 성실히 사업에 활용하는 모범 기업',
            'A+': '투자금 활용이 우수한 기업',
            'A': '투자금 활용이 양호한 기업',
            'A-': '대체로 양호하나 일부 점검 필요',
            'B+': '투자금 활용 현황 지속 관찰 필요',
            'B': '투자금 활용에 의문점 발생',
            'B-': '투자금 유용 가능성 경고',
            'C+': '투자금 배임 가능성 높음',
            'C': '투자금 배임 의심 - 투자 부적격',
        }
        verdict = verdicts.get(grade, '평가 불가')

        if violation_count >= 2:
            verdict += ' (복합 위반)'
        elif violation_count == 1:
            verdict += ' (위반 감지)'

        # 핵심 리스크
        if red_flags:
            key_risk = red_flags[0]
        elif yellow_flags:
            key_risk = yellow_flags[0]
        elif core_metrics.cash_tangible_ratio > 10:
            key_risk = f'현금 축적 대비 투자 부족 (비율 {core_metrics.cash_tangible_ratio:.1f}:1)'
        else:
            key_risk = '주요 리스크 없음'

        # 투자자 권고
        if grade in ['A++', 'A+', 'A', 'A-']:
            recommendation = '장기 보유 적합 - 자본 배분 효율성 우수'
        elif grade in ['B+', 'B']:
            recommendation = '중립 - 분기별 투자 현황 모니터링 권장'
        elif grade == 'B-':
            recommendation = '주의 - 경영진 자본 정책 변화 관찰 필요'
        else:
            recommendation = '매도 검토 - 근본적 자본 배분 문제 존재'

        # 재검토 시점
        if violation_count >= 1:
            watch_trigger = '특별 규칙 해소 시 (투자 확대 또는 현금 활용)'
        elif core_metrics.cash_tangible_ratio > 10:
            watch_trigger = '설비투자 확대 시'
        elif red_flags:
            watch_trigger = '다음 분기 실적 발표 후'
        else:
            watch_trigger = '다음 사업보고서 발표 시'

        return verdict, key_risk, recommendation, watch_trigger

    def to_dict(self, result: RaymondsIndexResult) -> Dict[str, Any]:
        """결과를 딕셔너리로 변환 (v2.0)"""
        return {
            'company_id': result.company_id,
            'fiscal_year': result.fiscal_year,
            'calculation_date': date.today().isoformat(),
            'total_score': result.total_score,
            'grade': result.grade,
            # Sub-Indices
            'cei_score': result.sub_indices.cei,
            'rii_score': result.sub_indices.rii,
            'cgi_score': result.sub_indices.cgi,
            'mai_score': result.sub_indices.mai,
            # 기존 Core Metrics
            'investment_gap': result.core_metrics.investment_gap,
            'cash_cagr': result.core_metrics.cash_cagr,
            'capex_growth': result.core_metrics.capex_growth,
            'idle_cash_ratio': result.core_metrics.idle_cash_ratio,
            'asset_turnover': result.core_metrics.asset_turnover,
            'reinvestment_rate': result.core_metrics.reinvestment_rate,
            'shareholder_return': result.core_metrics.shareholder_return,
            # v4.0 기존 지표
            'cash_tangible_ratio': result.core_metrics.cash_tangible_ratio,
            'fundraising_utilization': result.core_metrics.fundraising_utilization,
            'short_term_ratio': result.core_metrics.short_term_ratio,
            'capex_trend': result.core_metrics.capex_trend,
            'roic': result.core_metrics.roic,
            'capex_cv': result.core_metrics.capex_cv,
            'violation_count': result.violation_count,
            # v2.0 신규 지표
            'investment_gap_v2': result.core_metrics.investment_gap_v2,
            'cash_utilization': result.core_metrics.cash_utilization,
            'industry_sector': result.core_metrics.industry_sector,
            'weight_adjustment': result.core_metrics.weight_adjustment,
            # Flags
            'red_flags': result.red_flags,
            'yellow_flags': result.yellow_flags,
            # Interpretation
            'verdict': result.verdict,
            'key_risk': result.key_risk,
            'recommendation': result.recommendation,
            'watch_trigger': result.watch_trigger,
            # Meta
            'data_quality_score': result.data_quality_score
        }
