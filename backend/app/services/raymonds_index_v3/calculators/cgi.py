"""
CGI: Cash Governance Index (현금 거버넌스) - 25%

구성 지표:
- 현금 활용도 (20%): (CAPEX + 배당 + 자사주) / (기초현금 + OCF)
- 자금 조달 효율성 (25%): 투자 / 조달금액
- 주주환원 균형 (20%): (배당 + 자사주) / OCF (V자 스코어링: 35% 최적)
- 현금 적정성 (15%): 현금 / 총자산 (V자 스코어링: 15% 최적)
- 부채 건전성 (20%): Debt / EBITDA (역방향)
"""

from typing import Dict, Any
from .base import SubIndexCalculator
from ..normalizers import clamp


class CGICalculator(SubIndexCalculator):
    """Cash Governance Index 계산기"""

    INDEX_NAME = "CGI"

    def _calculate_raw_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """원본 지표 계산"""
        raw = {}

        # 현재 값 추출
        total_assets = self._get_latest(data, 'total_assets')
        operating_income = self._get_latest(data, 'operating_income')
        ocf = self._get_latest(data, 'operating_cash_flow')
        capex = abs(self._get_latest(data, 'capex'))
        dividend = abs(self._get_latest(data, 'dividend_paid'))
        treasury = abs(self._get_latest(data, 'treasury_stock_acquisition'))
        depreciation = self._get_latest(data, 'depreciation_expense')

        # 현금 계산
        cash = self._get_latest(data, 'cash_and_equivalents')
        short_term = self._get_latest(data, 'short_term_investments')
        other_fin = self._get_latest(data, 'other_financial_assets_current')
        total_cash = cash + short_term + other_fin

        # 이전 현금
        prev_cash = self._get_previous(data, 'cash_and_equivalents')
        prev_short = self._get_previous(data, 'short_term_investments')
        prev_other = self._get_previous(data, 'other_financial_assets_current')
        prev_total_cash = prev_cash + prev_short + prev_other

        # 부채 계산
        short_borrowings = self._get_latest(data, 'short_term_borrowings')
        long_borrowings = self._get_latest(data, 'long_term_borrowings')
        bonds = self._get_latest(data, 'bonds_payable')
        cb = self._get_latest(data, 'convertible_bonds')
        total_debt = short_borrowings + long_borrowings + bonds + cb

        # ═══════════════════════════════════════════════════════════════
        # 1. 현금 활용도 (Cash Utilization)
        # ═══════════════════════════════════════════════════════════════
        # (CAPEX + 배당 + 자사주) / (기초현금 + OCF)
        total_usage = capex + dividend + treasury
        total_available = prev_total_cash + max(ocf, 0)

        raw['cash_utilization'] = self._safe_divide(total_usage, total_available) * 100

        # ═══════════════════════════════════════════════════════════════
        # 2. 자금 조달 효율성 (Funding Efficiency)
        # ═══════════════════════════════════════════════════════════════
        # 3년간 투자 / 3년간 조달금액
        total_investment, total_fundraising = self._calculate_funding_metrics(data)

        if total_fundraising > 0:
            raw['funding_efficiency'] = self._safe_divide(total_investment, total_fundraising) * 100
        else:
            # 조달 없으면 80점 (중립-양호)
            raw['funding_efficiency'] = 80.0

        # ═══════════════════════════════════════════════════════════════
        # 3. 주주환원 균형 (Payout Ratio)
        # ═══════════════════════════════════════════════════════════════
        # (배당 + 자사주) / OCF (%)
        # V자 스코어링: 35% 최적, 0%와 100% 모두 감점
        payout = dividend + treasury
        if ocf > 0:
            raw['payout_ratio'] = self._safe_divide(payout, ocf) * 100
        else:
            raw['payout_ratio'] = 0.0 if payout == 0 else 100.0

        # ═══════════════════════════════════════════════════════════════
        # 4. 현금 적정성 (Cash to Assets)
        # ═══════════════════════════════════════════════════════════════
        # 현금 / 총자산 (%)
        # V자 스코어링: 15% 최적, 너무 적거나 너무 많으면 감점
        raw['cash_to_assets'] = self._safe_divide(total_cash, total_assets) * 100

        # ═══════════════════════════════════════════════════════════════
        # 5. 부채 건전성 (Debt to EBITDA)
        # ═══════════════════════════════════════════════════════════════
        # 역방향: 낮을수록 좋음
        ebitda = operating_income + (depreciation if depreciation else 0)
        if ebitda > 0:
            raw['debt_to_ebitda'] = total_debt / ebitda
        else:
            raw['debt_to_ebitda'] = 99.0  # EBITDA <= 0

        return raw

    def _calculate_funding_metrics(self, data: Dict[str, Any]) -> tuple:
        """
        조달 및 투자 지표 계산

        Returns:
            Tuple[총 투자액, 총 조달액]
        """
        total_investment = 0.0
        total_fundraising = 0.0

        # 연도별 데이터 합산
        all_capex = self._get_all_values(data, 'capex')
        all_stock_issuance = self._get_all_values(data, 'stock_issuance')
        all_bond_issuance = self._get_all_values(data, 'bond_issuance')

        total_investment = sum(abs(c) for c in all_capex)
        total_fundraising = (
            sum(abs(s) for s in all_stock_issuance) +
            sum(abs(b) for b in all_bond_issuance)
        )

        return total_investment, total_fundraising
