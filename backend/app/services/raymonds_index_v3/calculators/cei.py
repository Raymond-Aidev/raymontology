"""
CEI: Capital Efficiency Index (자본 효율성) - 20%

구성 지표:
- 자산회전율 (25%): 매출 / 총자산
- 유형자산효율성 (20%): 매출 / 유형자산
- 현금수익률 (20%): 영업이익 / 총현금
- ROIC (25%): NOPAT / 투하자본
- 효율성 추세 (10%): 자산회전율 추세
"""

from typing import Dict, Any
from .base import SubIndexCalculator, CalculationResult
from ..normalizers import clamp


class CEICalculator(SubIndexCalculator):
    """Capital Efficiency Index 계산기"""

    INDEX_NAME = "CEI"

    def _calculate_raw_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """원본 지표 계산"""
        raw = {}

        # 현재 값 추출
        revenue = self._get_latest(data, 'revenue')
        total_assets = self._get_latest(data, 'total_assets')
        tangible_assets = self._get_latest(data, 'tangible_assets')
        operating_income = self._get_latest(data, 'operating_income')
        total_equity = self._get_latest(data, 'total_equity')
        total_liabilities = self._get_latest(data, 'total_liabilities')

        # 현금 계산 (현금 + 단기금융상품 + 기타금융자산)
        cash = self._get_latest(data, 'cash_and_equivalents')
        short_term = self._get_latest(data, 'short_term_investments')
        other_fin = self._get_latest(data, 'other_financial_assets_current')
        total_cash = cash + short_term + other_fin

        # ═══════════════════════════════════════════════════════════════
        # 1. 자산회전율 (Asset Turnover)
        # ═══════════════════════════════════════════════════════════════
        raw['asset_turnover'] = clamp(
            self._safe_divide(revenue, total_assets),
            'asset_turnover'
        )

        # ═══════════════════════════════════════════════════════════════
        # 2. 유형자산 효율성 (Tangible Efficiency)
        # ═══════════════════════════════════════════════════════════════
        raw['tangible_efficiency'] = clamp(
            self._safe_divide(revenue, tangible_assets) if tangible_assets > 0 else 0,
            'tangible_efficiency'
        )

        # ═══════════════════════════════════════════════════════════════
        # 3. 현금 수익률 (Cash Yield)
        # ═══════════════════════════════════════════════════════════════
        # 영업이익 / 총현금 (%)
        if total_cash > 0:
            raw['cash_yield'] = clamp(
                (operating_income / total_cash) * 100,
                'cash_yield'
            )
        else:
            raw['cash_yield'] = 0.0

        # ═══════════════════════════════════════════════════════════════
        # 4. ROIC (Return on Invested Capital)
        # ═══════════════════════════════════════════════════════════════
        # NOPAT = 영업이익 × (1 - 세율), 세율 22% 가정
        # 투하자본 = 자기자본 + 부채 - 현금
        nopat = operating_income * 0.78 if operating_income else 0
        invested_capital = total_equity + total_liabilities - total_cash

        if invested_capital > 0:
            raw['roic'] = clamp(
                (nopat / invested_capital) * 100,
                'roic'
            )
        else:
            raw['roic'] = 0.0

        # ═══════════════════════════════════════════════════════════════
        # 5. 효율성 추세 (Efficiency Trend)
        # ═══════════════════════════════════════════════════════════════
        # 연도별 자산회전율 추세
        all_revenues = self._get_all_values(data, 'revenue')
        all_assets = self._get_all_values(data, 'total_assets')

        if len(all_revenues) >= 2 and len(all_assets) >= 2:
            min_len = min(len(all_revenues), len(all_assets))
            turnovers = []
            for i in range(min_len):
                if all_assets[i] > 0:
                    turnovers.append(all_revenues[i] / all_assets[i])
                else:
                    turnovers.append(0)

            trend, slope = self._analyze_trend(turnovers)
            raw['efficiency_trend'] = slope
        else:
            raw['efficiency_trend'] = 0.0

        return raw
