"""
RaymondsIndex 계산 엔진

자본 배분 효율성 지수를 계산합니다.
4개 Sub-Index의 가중 평균으로 종합 점수를 산출합니다.

Sub-Index:
- CEI (Capital Efficiency Index): 20% - 자본 효율성
- RII (Reinvestment Intensity Index): 35% - 재투자 강도 (핵심)
- CGI (Cash Governance Index): 25% - 현금 거버넌스
- MAI (Momentum Alignment Index): 20% - 모멘텀 정렬

Grade:
- A+: 80-100 (탁월)
- A:  60-79  (양호)
- B:  40-59  (보통)
- C:  20-39  (주의)
- D:  0-19   (심각)
"""
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class SubIndexScores:
    """Sub-Index 점수"""
    cei: float = 0.0  # Capital Efficiency Index
    rii: float = 0.0  # Reinvestment Intensity Index
    cgi: float = 0.0  # Cash Governance Index
    mai: float = 0.0  # Momentum Alignment Index


@dataclass
class CoreMetrics:
    """핵심 지표"""
    investment_gap: float = 0.0      # 투자괴리율 (%)
    cash_cagr: float = 0.0           # 현금 CAGR (%)
    capex_growth: float = 0.0        # CAPEX 증가율 (%)
    idle_cash_ratio: float = 0.0     # 유휴현금비율 (%)
    asset_turnover: float = 0.0      # 자산회전율 (회)
    reinvestment_rate: float = 0.0   # 재투자율 (%)
    shareholder_return: float = 0.0  # 주주환원율 (%)


@dataclass
class RaymondsIndexResult:
    """RaymondsIndex 계산 결과"""
    company_id: str
    fiscal_year: int
    total_score: float = 0.0
    grade: str = 'D'
    sub_indices: SubIndexScores = field(default_factory=SubIndexScores)
    core_metrics: CoreMetrics = field(default_factory=CoreMetrics)
    red_flags: List[str] = field(default_factory=list)
    yellow_flags: List[str] = field(default_factory=list)
    verdict: str = ''
    key_risk: str = ''
    recommendation: str = ''
    watch_trigger: str = ''
    data_quality_score: float = 0.0


class RaymondsIndexCalculator:
    """
    RaymondsIndex 계산기

    3년간 재무 데이터를 기반으로 자본 배분 효율성 지수를 계산합니다.
    """

    # Sub-Index 가중치
    WEIGHTS = {
        'CEI': 0.20,  # Capital Efficiency Index
        'RII': 0.35,  # Reinvestment Intensity Index (핵심)
        'CGI': 0.25,  # Cash Governance Index
        'MAI': 0.20,  # Momentum Alignment Index
    }

    # 등급 기준
    GRADE_THRESHOLDS = [
        (80, 'A+'),
        (60, 'A'),
        (40, 'B'),
        (20, 'C'),
        (0, 'D'),
    ]

    # Red/Yellow Flag 기준
    FLAG_THRESHOLDS = {
        'red': {
            'investment_gap_high': 15,      # 투자괴리율 15% 이상
            'capex_decline': -50,           # CAPEX 50% 이상 감소
            'negative_ocf_years': 2,        # 영업CF 적자 2년 이상
        },
        'yellow': {
            'idle_cash_high': 30,           # 유휴현금 30% 이상
            'reinvestment_low': 20,         # 재투자율 20% 미만
            'turnover_decline_years': 2,    # 자산회전율 2년 연속 하락
        }
    }

    def __init__(self):
        pass

    def calculate(
        self,
        company_id: str,
        financial_data: List[Dict],
        target_year: Optional[int] = None
    ) -> Optional[RaymondsIndexResult]:
        """
        RaymondsIndex 계산

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

        # 핵심 지표 계산
        core_metrics = self._calculate_core_metrics(current, previous, oldest)

        # Sub-Index 계산
        sub_indices = self._calculate_sub_indices(current, previous, oldest, core_metrics)

        # 종합 점수 계산
        total_score = self._calculate_total_score(sub_indices)

        # 등급 결정
        grade = self._determine_grade(total_score)

        # Red/Yellow Flags 생성
        red_flags, yellow_flags = self._generate_flags(core_metrics, sorted_data)

        # 해석 생성
        verdict, key_risk, recommendation, watch_trigger = self._generate_interpretation(
            grade, core_metrics, red_flags, yellow_flags
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
            data_quality_score=data_quality
        )

    def _calculate_data_quality(self, data: Dict) -> float:
        """데이터 품질 점수 계산"""
        required_fields = [
            'total_assets', 'revenue', 'operating_cash_flow', 'capex',
            'cash_and_equivalents', 'net_income', 'total_equity'
        ]

        filled = sum(1 for f in required_fields if data.get(f) is not None)
        return round(filled / len(required_fields), 2)

    def _calculate_core_metrics(
        self,
        current: Dict,
        previous: Optional[Dict],
        oldest: Optional[Dict]
    ) -> CoreMetrics:
        """핵심 지표 계산"""
        metrics = CoreMetrics()

        # 안전한 값 추출
        def safe_get(d: Optional[Dict], key: str, default: float = 0) -> float:
            if d is None:
                return default
            val = d.get(key)
            return float(val) if val is not None else default

        # 현재 값
        cash = safe_get(current, 'cash_and_equivalents')
        total_assets = safe_get(current, 'total_assets')
        revenue = safe_get(current, 'revenue')
        capex = abs(safe_get(current, 'capex'))  # CAPEX는 절대값
        operating_cf = safe_get(current, 'operating_cash_flow')
        net_income = safe_get(current, 'net_income')
        dividend = abs(safe_get(current, 'dividend_paid'))
        treasury = abs(safe_get(current, 'treasury_stock_acquisition'))

        # 과거 값
        prev_cash = safe_get(previous, 'cash_and_equivalents')
        prev_capex = abs(safe_get(previous, 'capex'))
        oldest_cash = safe_get(oldest, 'cash_and_equivalents')

        # 1. 자산회전율
        if total_assets > 0:
            metrics.asset_turnover = round(revenue / total_assets, 3)

        # 2. 유휴현금비율
        if total_assets > 0:
            metrics.idle_cash_ratio = round((cash / total_assets) * 100, 2)

        # 3. 재투자율 (CAPEX / 영업CF)
        if operating_cf > 0:
            metrics.reinvestment_rate = round((capex / operating_cf) * 100, 2)

        # 4. 주주환원율 ((배당 + 자사주) / 순이익)
        if net_income > 0:
            metrics.shareholder_return = round(
                ((dividend + treasury) / net_income) * 100, 2
            )

        # 5. 현금 CAGR (3년)
        if oldest_cash and oldest_cash > 0 and cash > 0:
            years = 2  # oldest와 current 사이 기간
            metrics.cash_cagr = round(
                (pow(cash / oldest_cash, 1 / years) - 1) * 100, 2
            )

        # 6. CAPEX 증가율
        if prev_capex > 0:
            metrics.capex_growth = round(
                ((capex - prev_capex) / prev_capex) * 100, 2
            )

        # 7. 투자괴리율 (핵심)
        metrics.investment_gap = round(
            metrics.cash_cagr - metrics.capex_growth, 2
        )

        return metrics

    def _calculate_sub_indices(
        self,
        current: Dict,
        previous: Optional[Dict],
        oldest: Optional[Dict],
        core_metrics: CoreMetrics
    ) -> SubIndexScores:
        """Sub-Index 점수 계산 (각 0-100점)"""
        scores = SubIndexScores()

        # ═══════════════════════════════════════════════════════════════
        # CEI: Capital Efficiency Index (20%)
        # ═══════════════════════════════════════════════════════════════
        cei_components = []

        # 자산회전율 점수 (0-100): 0.5이상이면 만점, 0이면 0점
        turnover_score = min(core_metrics.asset_turnover / 0.5, 1) * 100
        cei_components.append(turnover_score * 0.4)

        # 유형자산효율성 (매출/유형자산)
        tangible = current.get('tangible_assets', 0) or 1
        revenue = current.get('revenue', 0) or 0
        tangible_eff = min(revenue / tangible / 2, 1) * 100 if tangible else 50
        cei_components.append(tangible_eff * 0.3)

        # 현금수익률 (순이익/현금)
        cash = current.get('cash_and_equivalents', 0) or 1
        net_income = current.get('net_income', 0) or 0
        cash_return = min(max(net_income / cash, 0), 1) * 100 if cash else 50
        cei_components.append(cash_return * 0.3)

        scores.cei = round(sum(cei_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # RII: Reinvestment Intensity Index (35%) - 핵심
        # ═══════════════════════════════════════════════════════════════
        rii_components = []

        # 투자괴리율 점수: 0에 가까울수록 좋음 (±5% 이내 = 만점)
        gap_abs = abs(core_metrics.investment_gap)
        if gap_abs <= 5:
            gap_score = 100
        elif gap_abs <= 15:
            gap_score = 100 - (gap_abs - 5) * 5  # 5-15% 구간: 100-50
        else:
            gap_score = max(50 - (gap_abs - 15) * 2, 0)  # 15% 이상: 감점
        rii_components.append(gap_score * 0.5)

        # CAPEX 강도 (CAPEX/매출): 적정 수준 5-15%
        capex_intensity = 0
        if revenue > 0:
            capex = abs(current.get('capex', 0) or 0)
            capex_intensity = (capex / revenue) * 100

        if 5 <= capex_intensity <= 15:
            intensity_score = 100
        elif capex_intensity < 5:
            intensity_score = capex_intensity * 20  # 0-5%: 0-100
        else:
            intensity_score = max(100 - (capex_intensity - 15) * 5, 0)  # 15% 이상: 감점
        rii_components.append(intensity_score * 0.25)

        # 재투자율 점수: 적정 수준 30-70%
        reinvest = core_metrics.reinvestment_rate
        if 30 <= reinvest <= 70:
            reinvest_score = 100
        elif reinvest < 30:
            reinvest_score = reinvest * (100 / 30)  # 0-30%: 비례
        else:
            reinvest_score = max(100 - (reinvest - 70) * 2, 0)  # 70% 이상: 감점
        rii_components.append(reinvest_score * 0.25)

        scores.rii = round(sum(rii_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # CGI: Cash Governance Index (25%)
        # ═══════════════════════════════════════════════════════════════
        cgi_components = []

        # 유휴현금비율 점수: 10-20% = 최적, 너무 높거나 낮으면 감점
        idle = core_metrics.idle_cash_ratio
        if 10 <= idle <= 20:
            idle_score = 100
        elif idle < 10:
            idle_score = idle * 10  # 0-10%: 비례
        else:
            idle_score = max(100 - (idle - 20) * 3, 0)  # 20% 이상: 감점
        cgi_components.append(idle_score * 0.4)

        # 자금활용률
        utilization_score = 100 - core_metrics.idle_cash_ratio
        utilization_score = max(min(utilization_score, 100), 0)
        cgi_components.append(utilization_score * 0.3)

        # 주주환원율 점수: 20-50% = 최적
        shareholder = core_metrics.shareholder_return
        if 20 <= shareholder <= 50:
            shareholder_score = 100
        elif shareholder < 20:
            shareholder_score = shareholder * 5  # 0-20%: 비례
        else:
            shareholder_score = max(100 - (shareholder - 50) * 2, 0)  # 50% 이상: 감점
        cgi_components.append(shareholder_score * 0.3)

        scores.cgi = round(sum(cgi_components), 2)

        # ═══════════════════════════════════════════════════════════════
        # MAI: Momentum Alignment Index (20%)
        # ═══════════════════════════════════════════════════════════════
        mai_components = []

        # 매출-투자 동조성: 매출 증가율과 CAPEX 증가율 차이
        prev_revenue = previous.get('revenue', 0) if previous else 0
        curr_revenue = current.get('revenue', 0) or 0
        revenue_growth = 0
        if prev_revenue and prev_revenue > 0:
            revenue_growth = ((curr_revenue - prev_revenue) / prev_revenue) * 100

        sync_diff = abs(revenue_growth - core_metrics.capex_growth)
        if sync_diff <= 10:
            sync_score = 100
        elif sync_diff <= 30:
            sync_score = 100 - (sync_diff - 10) * 2.5
        else:
            sync_score = max(50 - (sync_diff - 30), 0)
        mai_components.append(sync_score * 0.5)

        # 이익의 질 (영업CF / 순이익): 1.0 이상이 좋음
        ocf = current.get('operating_cash_flow', 0) or 0
        net = current.get('net_income', 0) or 1
        earnings_quality = ocf / net if net != 0 else 0

        if earnings_quality >= 1.0:
            quality_score = 100
        elif earnings_quality >= 0.5:
            quality_score = 50 + earnings_quality * 50
        else:
            quality_score = max(earnings_quality * 100, 0)
        mai_components.append(quality_score * 0.5)

        scores.mai = round(sum(mai_components), 2)

        return scores

    def _calculate_total_score(self, sub_indices: SubIndexScores) -> float:
        """종합 점수 계산"""
        total = (
            sub_indices.cei * self.WEIGHTS['CEI'] +
            sub_indices.rii * self.WEIGHTS['RII'] +
            sub_indices.cgi * self.WEIGHTS['CGI'] +
            sub_indices.mai * self.WEIGHTS['MAI']
        )
        return min(max(total, 0), 100)

    def _determine_grade(self, score: float) -> str:
        """등급 결정"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'D'

    def _generate_flags(
        self,
        core_metrics: CoreMetrics,
        historical_data: List[Dict]
    ) -> Tuple[List[str], List[str]]:
        """Red/Yellow Flags 생성"""
        red_flags = []
        yellow_flags = []

        thresholds = self.FLAG_THRESHOLDS

        # Red Flags
        if core_metrics.investment_gap > thresholds['red']['investment_gap_high']:
            red_flags.append(
                f"현금 과다 축적: 투자괴리율 {core_metrics.investment_gap:.1f}% "
                f"(현금증가율이 CAPEX증가율 대비 {thresholds['red']['investment_gap_high']}%p 이상)"
            )

        if core_metrics.capex_growth < thresholds['red']['capex_decline']:
            red_flags.append(
                f"투자 급감: CAPEX가 전년 대비 {abs(core_metrics.capex_growth):.1f}% 감소"
            )

        # 영업CF 적자 연속 체크
        negative_ocf_count = sum(
            1 for d in historical_data
            if (d.get('operating_cash_flow') or 0) < 0
        )
        if negative_ocf_count >= thresholds['red']['negative_ocf_years']:
            red_flags.append(
                f"영업현금흐름 적자 {negative_ocf_count}년 지속"
            )

        # Yellow Flags
        if core_metrics.idle_cash_ratio > thresholds['yellow']['idle_cash_high']:
            yellow_flags.append(
                f"유휴현금 과다: 현금비율 {core_metrics.idle_cash_ratio:.1f}% "
                f"(자금 활용 효율성 점검 필요)"
            )

        if core_metrics.reinvestment_rate < thresholds['yellow']['reinvestment_low']:
            yellow_flags.append(
                f"재투자율 저조: {core_metrics.reinvestment_rate:.1f}% "
                f"(성장 투자 부족 가능성)"
            )

        # 자산회전율 하락 체크
        if len(historical_data) >= 3:
            turnovers = []
            for d in historical_data[-3:]:
                assets = d.get('total_assets', 0) or 1
                rev = d.get('revenue', 0) or 0
                turnovers.append(rev / assets)

            if len(turnovers) >= 2 and all(
                turnovers[i] > turnovers[i+1]
                for i in range(len(turnovers)-1)
            ):
                yellow_flags.append(
                    f"자산회전율 {len(turnovers)-1}년 연속 하락"
                )

        return red_flags, yellow_flags

    def _generate_interpretation(
        self,
        grade: str,
        core_metrics: CoreMetrics,
        red_flags: List[str],
        yellow_flags: List[str]
    ) -> Tuple[str, str, str, str]:
        """해석 및 권고 생성"""

        # 한 줄 요약
        verdicts = {
            'A+': '탁월한 자본 배분 - 적극적 재투자와 효율적 운영',
            'A': '양호한 자본 배분 - 건전한 투자 정책 유지 중',
            'B': '보통 수준 - 자본 활용 개선 여지 있음',
            'C': '주의 필요 - 현금 쌓임 또는 과소 투자 우려',
            'D': '심각한 자본 배분 문제 - 즉각적 재검토 필요',
        }
        verdict = verdicts.get(grade, '평가 불가')

        # 핵심 리스크
        if red_flags:
            key_risk = red_flags[0]
        elif yellow_flags:
            key_risk = yellow_flags[0]
        elif core_metrics.investment_gap > 10:
            key_risk = f'투자괴리 발생: 현금 축적 대비 설비투자 부족 ({core_metrics.investment_gap:.1f}%)'
        elif core_metrics.investment_gap < -10:
            key_risk = f'과잉 투자 우려: CAPEX 증가율이 현금 증가율 초과 ({abs(core_metrics.investment_gap):.1f}%)'
        else:
            key_risk = '주요 리스크 없음'

        # 투자자 권고
        if grade in ['A+', 'A']:
            recommendation = '장기 보유 적합 - 자본 배분 효율성 우수'
        elif grade == 'B':
            recommendation = '중립 - 분기별 CAPEX 추이 모니터링 권장'
        elif grade == 'C':
            recommendation = '주의 - 경영진 자본 정책 변화 필요, 리스크 관리 강화'
        else:
            recommendation = '매도 검토 - 근본적 자본 배분 문제 존재'

        # 재검토 시점
        if core_metrics.investment_gap > 10:
            watch_trigger = 'CAPEX 증가 또는 주주환원 확대 시'
        elif core_metrics.reinvestment_rate < 20:
            watch_trigger = '재투자율 30% 이상 회복 시'
        elif red_flags:
            watch_trigger = '다음 분기 실적 발표 후'
        else:
            watch_trigger = '다음 사업보고서 발표 시'

        return verdict, key_risk, recommendation, watch_trigger

    def to_dict(self, result: RaymondsIndexResult) -> Dict[str, Any]:
        """결과를 딕셔너리로 변환"""
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
            # Core Metrics
            'investment_gap': result.core_metrics.investment_gap,
            'cash_cagr': result.core_metrics.cash_cagr,
            'capex_growth': result.core_metrics.capex_growth,
            'idle_cash_ratio': result.core_metrics.idle_cash_ratio,
            'asset_turnover': result.core_metrics.asset_turnover,
            'reinvestment_rate': result.core_metrics.reinvestment_rate,
            'shareholder_return': result.core_metrics.shareholder_return,
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
