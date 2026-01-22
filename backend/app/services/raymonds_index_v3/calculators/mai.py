"""
MAI: Momentum Alignment Index (모멘텀 정합성) - 20%

구성 지표:
- 매출-투자 동조성 (30%): 매출 성장률과 CAPEX 성장률 차이 (V자 스코어링: 0 최적)
- 이익 품질 (25%): OCF / 순이익 (V자 스코어링: 1 최적)
- 성장 투자 비율 (15%): (CAPEX - 유지CAPEX) / CAPEX
- FCF 추세 (10%): Free Cash Flow 추세
- CAPEX 추세 점수 (20%): CAPEX 추세 평가
"""

from typing import Dict, Any
from .base import SubIndexCalculator
from ..normalizers import clamp


class MAICalculator(SubIndexCalculator):
    """Momentum Alignment Index 계산기"""

    INDEX_NAME = "MAI"

    def _calculate_raw_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """원본 지표 계산"""
        raw = {}

        # 현재 값 추출
        revenue = self._get_latest(data, 'revenue')
        prev_revenue = self._get_previous(data, 'revenue')
        net_income = self._get_latest(data, 'net_income')
        ocf = self._get_latest(data, 'operating_cash_flow')
        capex = abs(self._get_latest(data, 'capex'))
        tangible = self._get_latest(data, 'tangible_assets')

        # ═══════════════════════════════════════════════════════════════
        # 1. 매출-투자 동조성 (Revenue-CAPEX Sync)
        # ═══════════════════════════════════════════════════════════════
        # 매출 성장률 - CAPEX 성장률
        # V자 스코어링: 0이 최적 (동조)
        revenue_growth = 0.0
        if prev_revenue and prev_revenue > 0:
            revenue_growth = ((revenue - prev_revenue) / prev_revenue) * 100

        all_capex = self._get_all_values(data, 'capex')
        capex_growth = 0.0
        if len(all_capex) >= 2:
            early_capex = [abs(c) for c in all_capex[:2]]
            late_capex = [abs(c) for c in all_capex[-2:]]
            early_avg = sum(early_capex) / len(early_capex) if early_capex else 0
            late_avg = sum(late_capex) / len(late_capex) if late_capex else 0
            if early_avg > 0:
                capex_growth = ((late_avg - early_avg) / early_avg) * 100

        # 동조성: 0에 가까울수록 좋음
        raw['revenue_capex_sync'] = revenue_growth - capex_growth

        # ═══════════════════════════════════════════════════════════════
        # 2. 이익 품질 (Earnings Quality)
        # ═══════════════════════════════════════════════════════════════
        # OCF / 순이익
        # V자 스코어링: 1이 최적 (OCF와 순이익이 일치)
        if net_income and net_income != 0:
            raw['earnings_quality'] = ocf / net_income
        else:
            raw['earnings_quality'] = 1.0  # 순손실이면 중립

        # ═══════════════════════════════════════════════════════════════
        # 3. 성장 투자 비율 (Growth Investment Ratio)
        # ═══════════════════════════════════════════════════════════════
        # 성장 CAPEX / 총 CAPEX (%)
        # 유지 CAPEX 추정: 유형자산 × 10%
        maintenance_capex = tangible * 0.10 if tangible > 0 else 0
        if capex > 0:
            growth_capex = max(0, capex - maintenance_capex)
            raw['growth_investment_ratio'] = (growth_capex / capex) * 100
        else:
            raw['growth_investment_ratio'] = 0.0

        # ═══════════════════════════════════════════════════════════════
        # 4. FCF 추세 (Free Cash Flow Trend)
        # ═══════════════════════════════════════════════════════════════
        all_ocf = self._get_all_values(data, 'operating_cash_flow')
        all_capex_abs = [abs(c) for c in all_capex]

        fcf_values = []
        min_len = min(len(all_ocf), len(all_capex_abs))
        for i in range(min_len):
            fcf_values.append(all_ocf[i] - all_capex_abs[i])

        if len(fcf_values) >= 2:
            trend, slope = self._analyze_trend(fcf_values)
            raw['fcf_trend'] = slope
        else:
            raw['fcf_trend'] = 0.0

        # ═══════════════════════════════════════════════════════════════
        # 5. CAPEX 추세 점수 (CAPEX Trend Score)
        # ═══════════════════════════════════════════════════════════════
        if len(all_capex_abs) >= 2:
            trend, slope = self._analyze_trend(all_capex_abs)
            if trend == 'increasing':
                raw['capex_trend_score'] = 85.0
            elif trend == 'stable':
                raw['capex_trend_score'] = 70.0
            else:  # decreasing
                raw['capex_trend_score'] = 35.0
        else:
            raw['capex_trend_score'] = 50.0  # 중립

        return raw
