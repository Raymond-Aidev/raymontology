"""
RII: Reinvestment Intensity Index (재투자 강도) - 35% ⭐ 핵심

핵심 질문: "벌어들인 돈을 미래 성장에 얼마나 투자하는가?"

구성 지표:
- CAPEX 강도 (25%): CAPEX / 매출
- 투자괴리율 (30%): 현금 CAGR - CAPEX 성장률 ⭐ 핵심
- 재투자율 (25%): CAPEX / OCF
- 투자 지속성 (20%): CAPEX 변동계수 (역방향)

⭐ v3.0 핵심 변경:
- 투자괴리율에 Clamping 적용 (-100 ~ +100)
- V자 스코어링 (0이 최적)
"""

from typing import Dict, Any, Tuple
from .base import SubIndexCalculator, CalculationResult
from ..normalizers import clamp, safe_cagr, safe_growth_rate
from ..constants import MIN_DENOMINATOR, CLAMP_LIMITS


class RIICalculator(SubIndexCalculator):
    """Reinvestment Intensity Index 계산기"""

    INDEX_NAME = "RII"

    def _calculate_raw_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """원본 지표 계산"""
        raw = {}

        # 현재 값 추출
        revenue = self._get_latest(data, 'revenue')
        capex = abs(self._get_latest(data, 'capex'))
        ocf = self._get_latest(data, 'operating_cash_flow')

        # ═══════════════════════════════════════════════════════════════
        # 1. CAPEX 강도 (CAPEX Intensity)
        # ═══════════════════════════════════════════════════════════════
        # CAPEX / 매출 (%)
        raw['capex_intensity'] = clamp(
            self._safe_divide(capex, revenue) * 100,
            'capex_intensity'
        )

        # ═══════════════════════════════════════════════════════════════
        # 2. 투자괴리율 (Investment Gap) ⭐ 핵심
        # ═══════════════════════════════════════════════════════════════
        gap, cash_cagr, capex_growth = self._calculate_investment_gap(data)
        raw['investment_gap'] = gap
        raw['cash_cagr'] = cash_cagr
        raw['capex_growth'] = capex_growth

        # ═══════════════════════════════════════════════════════════════
        # 3. 재투자율 (Reinvestment Rate)
        # ═══════════════════════════════════════════════════════════════
        # CAPEX / OCF (%)
        if ocf > 0:
            raw['reinvestment_rate'] = clamp(
                (capex / ocf) * 100,
                'reinvestment_rate'
            )
        elif ocf <= 0 and capex > 0:
            # OCF 음수이지만 투자 의지 존재
            raw['reinvestment_rate'] = 100.0
        else:
            raw['reinvestment_rate'] = 0.0

        # ═══════════════════════════════════════════════════════════════
        # 4. 투자 지속성 (CAPEX Volatility)
        # ═══════════════════════════════════════════════════════════════
        all_capex = self._get_all_values(data, 'capex')
        raw['capex_volatility'] = self._coefficient_of_variation(all_capex)

        return raw

    def _calculate_investment_gap(self, data: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        투자괴리율 v3.0 계산 ⭐ 핵심 (범위 제한 적용)

        투자괴리율 = 현금 CAGR - CAPEX 성장률

        양수(+): 현금 축적 > 투자 증가 (현금만 쌓는 중 - 위험 신호)
        음수(-): 투자 증가 > 현금 축적 (적극 투자 중 - 긍정 신호)

        Returns:
            Tuple[투자괴리율, 현금 CAGR, CAPEX 성장률]
        """
        # 현금 데이터 추출
        all_cash = self._calculate_total_cash_series(data)

        # CAPEX 데이터 추출
        all_capex = self._get_all_values(data, 'capex')
        all_capex_abs = [abs(c) for c in all_capex]

        if len(all_cash) < 2 or len(all_capex_abs) < 2:
            return 0.0, 0.0, 0.0

        # ═══════════════════════════════════════════════════════════════
        # 현금 CAGR 계산
        # ═══════════════════════════════════════════════════════════════
        years = len(all_cash) - 1
        cash_cagr = safe_cagr(all_cash[0], all_cash[-1], years)
        cash_cagr = clamp(cash_cagr, 'cash_cagr')

        # ═══════════════════════════════════════════════════════════════
        # CAPEX 성장률 계산 (초기 2년 평균 vs 최근 2년 평균)
        # ═══════════════════════════════════════════════════════════════
        early_capex = all_capex_abs[:2] if len(all_capex_abs) >= 2 else all_capex_abs
        late_capex = all_capex_abs[-2:] if len(all_capex_abs) >= 2 else all_capex_abs

        capex_growth = safe_growth_rate(early_capex, late_capex, use_abs=True)
        capex_growth = clamp(capex_growth, 'capex_growth')

        # ═══════════════════════════════════════════════════════════════
        # 투자괴리율 = 현금 CAGR - CAPEX 성장률
        # ═══════════════════════════════════════════════════════════════
        # 범위 제한 (Clamping) - ⭐ -999% 버그 수정
        investment_gap = clamp(cash_cagr - capex_growth, 'investment_gap')

        return investment_gap, cash_cagr, capex_growth

    def _calculate_total_cash_series(self, data: Dict[str, Any]) -> list:
        """
        연도별 총 현금성자산 계산

        현금성자산 = 현금 + 단기금융상품 + 기타금융자산(유동)
        """
        cash_list = data.get('cash_and_equivalents', [])
        short_term_list = data.get('short_term_investments', [])
        other_fin_list = data.get('other_financial_assets_current', [])

        if not isinstance(cash_list, list):
            cash_list = [cash_list] if cash_list else []
        if not isinstance(short_term_list, list):
            short_term_list = [short_term_list] if short_term_list else []
        if not isinstance(other_fin_list, list):
            other_fin_list = [other_fin_list] if other_fin_list else []

        # 가장 긴 리스트 길이에 맞춤
        max_len = max(len(cash_list), len(short_term_list), len(other_fin_list), 1)

        # 리스트 길이 맞추기 (부족하면 0으로 채움)
        cash_list = list(cash_list) + [0] * (max_len - len(cash_list))
        short_term_list = list(short_term_list) + [0] * (max_len - len(short_term_list))
        other_fin_list = list(other_fin_list) + [0] * (max_len - len(other_fin_list))

        total_cash = []
        for i in range(max_len):
            c = cash_list[i] if cash_list[i] is not None else 0
            s = short_term_list[i] if short_term_list[i] is not None else 0
            o = other_fin_list[i] if other_fin_list[i] is not None else 0
            total_cash.append(c + s + o)

        return total_cash
