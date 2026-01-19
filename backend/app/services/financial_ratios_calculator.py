"""
FinancialRatiosCalculator v1.0

재무건전성 평가 시스템 - 25개 재무비율 계산 엔진

6개 카테고리:
1. 안정성 지표 (Stability) - 6개: 유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도, 비유동비율
2. 수익성 지표 (Profitability) - 7개: 영업이익률, 순이익률, ROA, ROE, 매출총이익률, EBITDA마진, EBITDA
3. 성장성 지표 (Growth) - 4개: 매출성장률, 영업이익성장률, 순이익성장률, 자산성장률 (YoY 전년비교 필요)
4. 활동성 지표 (Activity) - 8개: 자산회전율, 매출채권회전율, 재고자산회전율, 매입채무회전율, 회전기간 4개
5. 현금흐름 지표 (Cash Flow) - 4개: 영업현금흐름비율, 이자보상배수(OCF), FCF, FCF마진
6. 레버리지 지표 (Leverage) - 6개: 이자보상배수, EBITDA이자보상배수, 순차입금/EBITDA, 금융비용비율, 총차입금, 순차입금

카테고리 점수화 (0-100) → 종합 재무건전성 점수 → 등급 (A+, A, B+, B, B-, C+, C)
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CategoryScores:
    """카테고리별 점수"""
    stability: float = 0.0
    profitability: float = 0.0
    growth: float = 0.0
    activity: float = 0.0
    cashflow: float = 0.0
    leverage: float = 0.0


@dataclass
class FinancialRatiosResult:
    """재무비율 계산 결과"""
    company_id: str
    fiscal_year: int
    fiscal_quarter: Optional[int] = None

    # 안정성 지표
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_ratio: Optional[float] = None
    equity_ratio: Optional[float] = None
    debt_dependency: Optional[float] = None
    non_current_ratio: Optional[float] = None

    # 수익성 지표
    operating_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    roa: Optional[float] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    ebitda: Optional[int] = None

    # 성장성 지표
    revenue_growth: Optional[float] = None
    operating_income_growth: Optional[float] = None
    net_income_growth: Optional[float] = None
    total_assets_growth: Optional[float] = None
    growth_data_available: bool = False

    # 활동성 지표
    asset_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    receivables_days: Optional[float] = None
    inventory_days: Optional[float] = None
    payables_days: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None

    # 현금흐름 지표
    ocf_ratio: Optional[float] = None
    ocf_interest_coverage: Optional[float] = None
    free_cash_flow: Optional[int] = None
    fcf_margin: Optional[float] = None

    # 레버리지 지표
    interest_coverage: Optional[float] = None
    ebitda_interest_coverage: Optional[float] = None
    net_debt_to_ebitda: Optional[float] = None
    financial_expense_ratio: Optional[float] = None
    total_borrowings: Optional[int] = None
    net_debt: Optional[int] = None

    # 연속 적자/흑자
    consecutive_loss_quarters: int = 0
    consecutive_profit_quarters: int = 0
    is_loss_making: bool = False

    # 카테고리별 점수 (0-100)
    category_scores: CategoryScores = field(default_factory=CategoryScores)

    # 종합 평가
    financial_health_score: Optional[float] = None
    financial_health_grade: Optional[str] = None
    financial_risk_level: Optional[str] = None

    # 메타
    data_completeness: float = 0.0
    calculation_notes: List[str] = field(default_factory=list)


class FinancialRatiosCalculator:
    """
    재무비율 계산기 v1.0

    financial_details 데이터를 기반으로 25개 재무비율을 계산하고
    카테고리별 점수화 후 종합 재무건전성 등급을 산출합니다.
    """

    # 카테고리별 가중치
    CATEGORY_WEIGHTS = {
        'stability': 0.20,     # 안정성
        'profitability': 0.25, # 수익성
        'growth': 0.15,        # 성장성
        'activity': 0.10,      # 활동성
        'cashflow': 0.15,      # 현금흐름
        'leverage': 0.15,      # 레버리지
    }

    # 등급 기준
    GRADE_THRESHOLDS = [
        (90, 'A+'),
        (80, 'A'),
        (70, 'B+'),
        (60, 'B'),
        (50, 'B-'),
        (40, 'C+'),
        (0, 'C'),
    ]

    # 위험 수준 기준
    RISK_THRESHOLDS = [
        (80, 'LOW'),      # 저위험
        (60, 'MODERATE'), # 보통
        (40, 'HIGH'),     # 고위험
        (0, 'CRITICAL'),  # 심각
    ]

    def __init__(self):
        self.stats = {
            'calculated': 0,
            'errors': 0,
            'missing_data': 0,
        }

    def calculate(
        self,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]] = None,
        company_id: str = '',
        fiscal_year: int = 0,
        fiscal_quarter: Optional[int] = None,
    ) -> FinancialRatiosResult:
        """
        재무비율 계산

        Args:
            current_data: 당기 financial_details 데이터
            previous_data: 전기 financial_details 데이터 (성장성 계산용)
            company_id: 회사 ID
            fiscal_year: 회계연도
            fiscal_quarter: 분기 (None=연간)

        Returns:
            FinancialRatiosResult
        """
        result = FinancialRatiosResult(
            company_id=company_id,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
        )

        notes = []

        try:
            # 1. 안정성 지표 계산
            self._calculate_stability(result, current_data, notes)

            # 2. 수익성 지표 계산
            self._calculate_profitability(result, current_data, notes)

            # 3. 성장성 지표 계산 (전기 데이터 필요)
            self._calculate_growth(result, current_data, previous_data, notes)

            # 4. 활동성 지표 계산
            self._calculate_activity(result, current_data, notes)

            # 5. 현금흐름 지표 계산
            self._calculate_cashflow(result, current_data, notes)

            # 6. 레버리지 지표 계산
            self._calculate_leverage(result, current_data, notes)

            # 7. 적자/흑자 판정
            self._determine_profit_loss(result, current_data)

            # 8. 카테고리별 점수화
            self._calculate_category_scores(result)

            # 9. 종합 점수 및 등급 산출
            self._calculate_overall_score(result)

            # 10. 데이터 완성도 계산
            result.data_completeness = self._calculate_data_completeness(result)
            result.calculation_notes = notes

            self.stats['calculated'] += 1

        except Exception as e:
            logger.error(f"Calculation error for {company_id}: {e}")
            notes.append(f"Error: {str(e)}")
            result.calculation_notes = notes
            self.stats['errors'] += 1

        return result

    # DB NUMERIC(10,2) 최대값 제한 (10^8 - 1)
    MAX_RATIO_VALUE = 99999999.99

    def _safe_divide(self, numerator: Any, denominator: Any, default: Optional[float] = None) -> Optional[float]:
        """안전한 나눗셈 (0 나누기 방지, 오버플로우 방지)"""
        if numerator is None or denominator is None:
            return default
        try:
            num = float(numerator)
            denom = float(denominator)
            if denom == 0:
                return default
            result = round(num / denom, 4)
            # 오버플로우 방지
            if abs(result) > self.MAX_RATIO_VALUE:
                return self.MAX_RATIO_VALUE if result > 0 else -self.MAX_RATIO_VALUE
            return result
        except (ValueError, TypeError):
            return default

    def _safe_percentage(self, numerator: Any, denominator: Any, default: Optional[float] = None) -> Optional[float]:
        """퍼센트 계산 (x100, 오버플로우 방지)"""
        ratio = self._safe_divide(numerator, denominator, default=None)
        if ratio is None:
            return default
        result = round(ratio * 100, 2)
        # 오버플로우 방지
        if abs(result) > self.MAX_RATIO_VALUE:
            return self.MAX_RATIO_VALUE if result > 0 else -self.MAX_RATIO_VALUE
        return result

    def _get_value(self, data: Dict[str, Any], key: str) -> Optional[int]:
        """데이터에서 값 추출 (None 또는 숫자)"""
        val = data.get(key)
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # =========================================================================
    # 1. 안정성 지표 (Stability)
    # =========================================================================
    def _calculate_stability(self, result: FinancialRatiosResult, data: Dict[str, Any], notes: List[str]):
        """안정성 지표 계산"""
        current_assets = self._get_value(data, 'current_assets')
        current_liabilities = self._get_value(data, 'current_liabilities')
        inventories = self._get_value(data, 'inventories')
        total_assets = self._get_value(data, 'total_assets')
        total_liabilities = self._get_value(data, 'total_liabilities')
        total_equity = self._get_value(data, 'total_equity')
        non_current_assets = self._get_value(data, 'non_current_assets')
        short_term_borrowings = self._get_value(data, 'short_term_borrowings') or 0
        long_term_borrowings = self._get_value(data, 'long_term_borrowings') or 0
        bonds_payable = self._get_value(data, 'bonds_payable') or 0

        # 유동비율 (Current Ratio) = 유동자산 / 유동부채 * 100
        result.current_ratio = self._safe_percentage(current_assets, current_liabilities)

        # 당좌비율 (Quick Ratio) = (유동자산 - 재고자산) / 유동부채 * 100
        if current_assets is not None and inventories is not None:
            quick_assets = current_assets - inventories
            result.quick_ratio = self._safe_percentage(quick_assets, current_liabilities)

        # 부채비율 (Debt Ratio) = 총부채 / 자기자본 * 100
        result.debt_ratio = self._safe_percentage(total_liabilities, total_equity)

        # 자기자본비율 (Equity Ratio) = 자기자본 / 총자산 * 100
        result.equity_ratio = self._safe_percentage(total_equity, total_assets)

        # 차입금의존도 (Debt Dependency) = 총차입금 / 총자산 * 100
        total_borrowings = short_term_borrowings + long_term_borrowings + bonds_payable
        result.debt_dependency = self._safe_percentage(total_borrowings, total_assets)

        # 비유동비율 (Non-current Ratio) = 비유동자산 / 자기자본 * 100
        result.non_current_ratio = self._safe_percentage(non_current_assets, total_equity)

        if result.current_ratio is None:
            notes.append("안정성: 유동비율 계산 불가 (유동자산/유동부채 누락)")

    # =========================================================================
    # 2. 수익성 지표 (Profitability)
    # =========================================================================
    def _calculate_profitability(self, result: FinancialRatiosResult, data: Dict[str, Any], notes: List[str]):
        """수익성 지표 계산"""
        revenue = self._get_value(data, 'revenue')
        gross_profit = self._get_value(data, 'gross_profit')
        operating_income = self._get_value(data, 'operating_income')
        net_income = self._get_value(data, 'net_income')
        total_assets = self._get_value(data, 'total_assets')
        total_equity = self._get_value(data, 'total_equity')
        depreciation = self._get_value(data, 'depreciation_expense') or 0
        amortization = self._get_value(data, 'amortization') or 0
        interest_expense = self._get_value(data, 'interest_expense') or 0
        tax_expense = self._get_value(data, 'tax_expense') or 0

        # 매출총이익률 (Gross Margin) = 매출총이익 / 매출액 * 100
        result.gross_margin = self._safe_percentage(gross_profit, revenue)

        # 매출총이익이 없으면 매출 - 매출원가로 계산 시도
        if result.gross_margin is None and revenue is not None:
            cost_of_sales = self._get_value(data, 'cost_of_sales')
            if cost_of_sales is not None:
                calculated_gross = revenue - cost_of_sales
                result.gross_margin = self._safe_percentage(calculated_gross, revenue)

        # 영업이익률 (Operating Margin) = 영업이익 / 매출액 * 100
        result.operating_margin = self._safe_percentage(operating_income, revenue)

        # 순이익률 (Net Profit Margin) = 순이익 / 매출액 * 100
        result.net_profit_margin = self._safe_percentage(net_income, revenue)

        # ROA (Return on Assets) = 순이익 / 총자산 * 100
        result.roa = self._safe_percentage(net_income, total_assets)

        # ROE (Return on Equity) = 순이익 / 자기자본 * 100
        result.roe = self._safe_percentage(net_income, total_equity)

        # EBITDA = 영업이익 + 감가상각비 + 무형자산상각비
        if operating_income is not None:
            result.ebitda = operating_income + depreciation + amortization

        # EBITDA 마진 = EBITDA / 매출액 * 100
        if result.ebitda is not None and revenue:
            result.ebitda_margin = self._safe_percentage(result.ebitda, revenue)

        if result.operating_margin is None:
            notes.append("수익성: 영업이익률 계산 불가 (영업이익/매출 누락)")

    # =========================================================================
    # 3. 성장성 지표 (Growth) - 전년 대비
    # =========================================================================
    def _calculate_growth(
        self,
        result: FinancialRatiosResult,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]],
        notes: List[str]
    ):
        """성장성 지표 계산 (YoY)"""
        if previous_data is None:
            notes.append("성장성: 전기 데이터 없음 (YoY 계산 불가)")
            result.growth_data_available = False
            return

        result.growth_data_available = True

        # 매출성장률
        curr_revenue = self._get_value(current_data, 'revenue')
        prev_revenue = self._get_value(previous_data, 'revenue')
        result.revenue_growth = self._calculate_growth_rate(curr_revenue, prev_revenue)

        # 영업이익성장률
        curr_op = self._get_value(current_data, 'operating_income')
        prev_op = self._get_value(previous_data, 'operating_income')
        result.operating_income_growth = self._calculate_growth_rate(curr_op, prev_op)

        # 순이익성장률
        curr_ni = self._get_value(current_data, 'net_income')
        prev_ni = self._get_value(previous_data, 'net_income')
        result.net_income_growth = self._calculate_growth_rate(curr_ni, prev_ni)

        # 자산성장률
        curr_assets = self._get_value(current_data, 'total_assets')
        prev_assets = self._get_value(previous_data, 'total_assets')
        result.total_assets_growth = self._calculate_growth_rate(curr_assets, prev_assets)

    def _calculate_growth_rate(self, current: Optional[int], previous: Optional[int]) -> Optional[float]:
        """성장률 계산 ((당기-전기)/전기*100) - 오버플로우 방지"""
        if current is None or previous is None or previous == 0:
            return None
        result = round((current - previous) / abs(previous) * 100, 2)
        # 오버플로우 방지 (NUMERIC(10,2) 최대값)
        if abs(result) > self.MAX_RATIO_VALUE:
            return self.MAX_RATIO_VALUE if result > 0 else -self.MAX_RATIO_VALUE
        return result

    # =========================================================================
    # 4. 활동성 지표 (Activity)
    # =========================================================================
    def _calculate_activity(self, result: FinancialRatiosResult, data: Dict[str, Any], notes: List[str]):
        """활동성 지표 계산"""
        revenue = self._get_value(data, 'revenue')
        cost_of_sales = self._get_value(data, 'cost_of_sales')
        total_assets = self._get_value(data, 'total_assets')
        receivables = self._get_value(data, 'trade_and_other_receivables')
        inventories = self._get_value(data, 'inventories')
        payables = self._get_value(data, 'trade_payables')

        # 자산회전율 (Asset Turnover) = 매출액 / 총자산
        result.asset_turnover = self._safe_divide(revenue, total_assets)

        # 매출채권회전율 = 매출액 / 매출채권
        result.receivables_turnover = self._safe_divide(revenue, receivables)

        # 재고자산회전율 = 매출원가 / 재고자산
        result.inventory_turnover = self._safe_divide(cost_of_sales, inventories)

        # 매입채무회전율 = 매출원가 / 매입채무
        result.payables_turnover = self._safe_divide(cost_of_sales, payables)

        # 회전기간 (일) = 365 / 회전율 - 오버플로우 방지
        if result.receivables_turnover and result.receivables_turnover > 0:
            days = round(365 / result.receivables_turnover, 1)
            result.receivables_days = min(days, self.MAX_RATIO_VALUE) if days > 0 else max(days, -self.MAX_RATIO_VALUE)

        if result.inventory_turnover and result.inventory_turnover > 0:
            days = round(365 / result.inventory_turnover, 1)
            result.inventory_days = min(days, self.MAX_RATIO_VALUE) if days > 0 else max(days, -self.MAX_RATIO_VALUE)

        if result.payables_turnover and result.payables_turnover > 0:
            days = round(365 / result.payables_turnover, 1)
            result.payables_days = min(days, self.MAX_RATIO_VALUE) if days > 0 else max(days, -self.MAX_RATIO_VALUE)

        # 현금전환주기 (CCC) = 매출채권회전기간 + 재고자산회전기간 - 매입채무회전기간
        if result.receivables_days is not None and result.inventory_days is not None and result.payables_days is not None:
            ccc = round(result.receivables_days + result.inventory_days - result.payables_days, 1)
            # 오버플로우 방지
            if abs(ccc) > self.MAX_RATIO_VALUE:
                result.cash_conversion_cycle = self.MAX_RATIO_VALUE if ccc > 0 else -self.MAX_RATIO_VALUE
            else:
                result.cash_conversion_cycle = ccc

        if result.asset_turnover is None:
            notes.append("활동성: 자산회전율 계산 불가")

    # =========================================================================
    # 5. 현금흐름 지표 (Cash Flow)
    # =========================================================================
    def _calculate_cashflow(self, result: FinancialRatiosResult, data: Dict[str, Any], notes: List[str]):
        """현금흐름 지표 계산"""
        revenue = self._get_value(data, 'revenue')
        operating_cash_flow = self._get_value(data, 'operating_cash_flow')
        capex = self._get_value(data, 'capex') or 0
        interest_expense = self._get_value(data, 'interest_expense')
        current_liabilities = self._get_value(data, 'current_liabilities')

        # 영업현금흐름비율 (OCF Ratio) = 영업현금흐름 / 유동부채 * 100
        result.ocf_ratio = self._safe_percentage(operating_cash_flow, current_liabilities)

        # 이자보상배수 (OCF 기준) = 영업현금흐름 / 이자비용 - 오버플로우 방지
        if operating_cash_flow is not None and interest_expense and interest_expense > 0:
            coverage = round(operating_cash_flow / interest_expense, 2)
            if abs(coverage) > self.MAX_RATIO_VALUE:
                result.ocf_interest_coverage = self.MAX_RATIO_VALUE if coverage > 0 else -self.MAX_RATIO_VALUE
            else:
                result.ocf_interest_coverage = coverage

        # FCF (Free Cash Flow) = 영업현금흐름 - CAPEX
        if operating_cash_flow is not None:
            # CAPEX는 보통 양수로 저장됨 (현금유출)
            result.free_cash_flow = operating_cash_flow - abs(capex)

        # FCF 마진 = FCF / 매출액 * 100
        if result.free_cash_flow is not None and revenue:
            result.fcf_margin = self._safe_percentage(result.free_cash_flow, revenue)

        if result.ocf_ratio is None:
            notes.append("현금흐름: OCF 비율 계산 불가")

    # =========================================================================
    # 6. 레버리지 지표 (Leverage)
    # =========================================================================
    def _calculate_leverage(self, result: FinancialRatiosResult, data: Dict[str, Any], notes: List[str]):
        """레버리지 지표 계산"""
        operating_income = self._get_value(data, 'operating_income')
        interest_expense = self._get_value(data, 'interest_expense')
        revenue = self._get_value(data, 'revenue')
        short_term_borrowings = self._get_value(data, 'short_term_borrowings') or 0
        long_term_borrowings = self._get_value(data, 'long_term_borrowings') or 0
        bonds_payable = self._get_value(data, 'bonds_payable') or 0
        cash = self._get_value(data, 'cash_and_equivalents') or 0
        short_term_investments = self._get_value(data, 'short_term_investments') or 0

        # 총차입금 = 단기차입금 + 장기차입금 + 사채
        result.total_borrowings = short_term_borrowings + long_term_borrowings + bonds_payable

        # 순차입금 = 총차입금 - 현금 - 단기금융상품
        result.net_debt = result.total_borrowings - cash - short_term_investments

        # 이자보상배수 = 영업이익 / 이자비용 - 오버플로우 방지
        if operating_income is not None and interest_expense and interest_expense > 0:
            coverage = round(operating_income / interest_expense, 2)
            if abs(coverage) > self.MAX_RATIO_VALUE:
                result.interest_coverage = self.MAX_RATIO_VALUE if coverage > 0 else -self.MAX_RATIO_VALUE
            else:
                result.interest_coverage = coverage

        # EBITDA 이자보상배수 = EBITDA / 이자비용 - 오버플로우 방지
        if result.ebitda is not None and interest_expense and interest_expense > 0:
            coverage = round(result.ebitda / interest_expense, 2)
            if abs(coverage) > self.MAX_RATIO_VALUE:
                result.ebitda_interest_coverage = self.MAX_RATIO_VALUE if coverage > 0 else -self.MAX_RATIO_VALUE
            else:
                result.ebitda_interest_coverage = coverage

        # 순차입금/EBITDA - 오버플로우 방지
        if result.net_debt is not None and result.ebitda and result.ebitda > 0:
            ratio = round(result.net_debt / result.ebitda, 2)
            if abs(ratio) > self.MAX_RATIO_VALUE:
                result.net_debt_to_ebitda = self.MAX_RATIO_VALUE if ratio > 0 else -self.MAX_RATIO_VALUE
            else:
                result.net_debt_to_ebitda = ratio

        # 금융비용비율 = 이자비용 / 매출액 * 100
        result.financial_expense_ratio = self._safe_percentage(interest_expense, revenue)

        if result.interest_coverage is None and interest_expense:
            notes.append("레버리지: 이자보상배수 계산 불가")

    # =========================================================================
    # 7. 적자/흑자 판정
    # =========================================================================
    def _determine_profit_loss(self, result: FinancialRatiosResult, data: Dict[str, Any]):
        """적자/흑자 판정"""
        net_income = self._get_value(data, 'net_income')
        if net_income is not None:
            result.is_loss_making = net_income < 0

    # =========================================================================
    # 8. 카테고리별 점수화
    # =========================================================================
    def _calculate_category_scores(self, result: FinancialRatiosResult):
        """카테고리별 점수 계산 (0-100)"""
        scores = CategoryScores()

        # 안정성 점수
        scores.stability = self._score_stability(result)

        # 수익성 점수
        scores.profitability = self._score_profitability(result)

        # 성장성 점수
        scores.growth = self._score_growth(result)

        # 활동성 점수
        scores.activity = self._score_activity(result)

        # 현금흐름 점수
        scores.cashflow = self._score_cashflow(result)

        # 레버리지 점수
        scores.leverage = self._score_leverage(result)

        result.category_scores = scores

    def _score_stability(self, result: FinancialRatiosResult) -> float:
        """안정성 점수화"""
        score_parts = []

        # 유동비율 (200% 이상 = 100점, 100% = 50점, 50% 이하 = 0점)
        if result.current_ratio is not None:
            if result.current_ratio >= 200:
                score_parts.append(100)
            elif result.current_ratio >= 100:
                score_parts.append(50 + (result.current_ratio - 100) / 2)
            else:
                score_parts.append(max(0, result.current_ratio / 2))

        # 부채비율 (50% 이하 = 100점, 200% = 50점, 400% 이상 = 0점)
        if result.debt_ratio is not None:
            if result.debt_ratio <= 50:
                score_parts.append(100)
            elif result.debt_ratio <= 200:
                score_parts.append(100 - (result.debt_ratio - 50) / 3)
            elif result.debt_ratio <= 400:
                score_parts.append(50 - (result.debt_ratio - 200) / 4)
            else:
                score_parts.append(0)

        # 자기자본비율 (50% 이상 = 100점, 30% = 50점, 10% 이하 = 0점)
        if result.equity_ratio is not None:
            if result.equity_ratio >= 50:
                score_parts.append(100)
            elif result.equity_ratio >= 30:
                score_parts.append(50 + (result.equity_ratio - 30) * 2.5)
            elif result.equity_ratio >= 10:
                score_parts.append(max(0, result.equity_ratio * 2.5))
            else:
                score_parts.append(0)

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 0

    def _score_profitability(self, result: FinancialRatiosResult) -> float:
        """수익성 점수화"""
        score_parts = []

        # 영업이익률 (15% 이상 = 100점, 5% = 50점, 0% 이하 = 0점)
        if result.operating_margin is not None:
            if result.operating_margin >= 15:
                score_parts.append(100)
            elif result.operating_margin >= 5:
                score_parts.append(50 + (result.operating_margin - 5) * 5)
            elif result.operating_margin >= 0:
                score_parts.append(result.operating_margin * 10)
            else:
                score_parts.append(max(0, 50 + result.operating_margin * 5))

        # ROE (15% 이상 = 100점, 5% = 50점, 0% 이하 = 20점)
        if result.roe is not None:
            if result.roe >= 15:
                score_parts.append(100)
            elif result.roe >= 5:
                score_parts.append(50 + (result.roe - 5) * 5)
            elif result.roe >= 0:
                score_parts.append(20 + result.roe * 6)
            else:
                score_parts.append(max(0, 20 + result.roe * 2))

        # ROA (10% 이상 = 100점, 3% = 50점, 0% 이하 = 20점)
        if result.roa is not None:
            if result.roa >= 10:
                score_parts.append(100)
            elif result.roa >= 3:
                score_parts.append(50 + (result.roa - 3) * 7.14)
            elif result.roa >= 0:
                score_parts.append(20 + result.roa * 10)
            else:
                score_parts.append(max(0, 20 + result.roa * 2))

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 0

    def _score_growth(self, result: FinancialRatiosResult) -> float:
        """성장성 점수화"""
        if not result.growth_data_available:
            return 50  # 데이터 없으면 중립 점수

        score_parts = []

        # 매출성장률 (20% 이상 = 100점, 0% = 50점, -20% 이하 = 0점)
        if result.revenue_growth is not None:
            if result.revenue_growth >= 20:
                score_parts.append(100)
            elif result.revenue_growth >= 0:
                score_parts.append(50 + result.revenue_growth * 2.5)
            elif result.revenue_growth >= -20:
                score_parts.append(50 + result.revenue_growth * 2.5)
            else:
                score_parts.append(0)

        # 영업이익성장률 (유사 로직)
        if result.operating_income_growth is not None:
            if result.operating_income_growth >= 30:
                score_parts.append(100)
            elif result.operating_income_growth >= 0:
                score_parts.append(50 + result.operating_income_growth * 1.67)
            elif result.operating_income_growth >= -30:
                score_parts.append(50 + result.operating_income_growth * 1.67)
            else:
                score_parts.append(0)

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 50

    def _score_activity(self, result: FinancialRatiosResult) -> float:
        """활동성 점수화"""
        score_parts = []

        # 자산회전율 (1.5회 이상 = 100점, 0.5회 = 50점, 0.2회 이하 = 0점)
        if result.asset_turnover is not None:
            if result.asset_turnover >= 1.5:
                score_parts.append(100)
            elif result.asset_turnover >= 0.5:
                score_parts.append(50 + (result.asset_turnover - 0.5) * 50)
            else:
                score_parts.append(max(0, result.asset_turnover * 100))

        # 현금전환주기 (30일 이하 = 100점, 90일 = 50점, 180일 이상 = 0점)
        if result.cash_conversion_cycle is not None:
            if result.cash_conversion_cycle <= 30:
                score_parts.append(100)
            elif result.cash_conversion_cycle <= 90:
                score_parts.append(100 - (result.cash_conversion_cycle - 30) * 0.83)
            elif result.cash_conversion_cycle <= 180:
                score_parts.append(50 - (result.cash_conversion_cycle - 90) * 0.56)
            else:
                score_parts.append(0)

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 50

    def _score_cashflow(self, result: FinancialRatiosResult) -> float:
        """현금흐름 점수화"""
        score_parts = []

        # OCF 비율 (100% 이상 = 100점, 50% = 70점, 0% 이하 = 0점)
        if result.ocf_ratio is not None:
            if result.ocf_ratio >= 100:
                score_parts.append(100)
            elif result.ocf_ratio >= 50:
                score_parts.append(70 + (result.ocf_ratio - 50) * 0.6)
            elif result.ocf_ratio >= 0:
                score_parts.append(result.ocf_ratio * 1.4)
            else:
                score_parts.append(0)

        # FCF 마진 (10% 이상 = 100점, 0% = 50점, -10% 이하 = 0점)
        if result.fcf_margin is not None:
            if result.fcf_margin >= 10:
                score_parts.append(100)
            elif result.fcf_margin >= 0:
                score_parts.append(50 + result.fcf_margin * 5)
            elif result.fcf_margin >= -10:
                score_parts.append(50 + result.fcf_margin * 5)
            else:
                score_parts.append(0)

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 50

    def _score_leverage(self, result: FinancialRatiosResult) -> float:
        """레버리지 점수화"""
        score_parts = []

        # 이자보상배수 (5배 이상 = 100점, 2배 = 50점, 1배 이하 = 0점)
        if result.interest_coverage is not None:
            if result.interest_coverage >= 5:
                score_parts.append(100)
            elif result.interest_coverage >= 2:
                score_parts.append(50 + (result.interest_coverage - 2) * 16.67)
            elif result.interest_coverage >= 1:
                score_parts.append(result.interest_coverage * 50)
            else:
                score_parts.append(max(0, result.interest_coverage * 30))

        # 순차입금/EBITDA (0 이하 = 100점, 3배 = 50점, 6배 이상 = 0점)
        if result.net_debt_to_ebitda is not None:
            if result.net_debt_to_ebitda <= 0:
                score_parts.append(100)
            elif result.net_debt_to_ebitda <= 3:
                score_parts.append(100 - result.net_debt_to_ebitda * 16.67)
            elif result.net_debt_to_ebitda <= 6:
                score_parts.append(50 - (result.net_debt_to_ebitda - 3) * 16.67)
            else:
                score_parts.append(0)

        return round(sum(score_parts) / len(score_parts), 2) if score_parts else 50

    # =========================================================================
    # 9. 종합 점수 및 등급
    # =========================================================================
    def _calculate_overall_score(self, result: FinancialRatiosResult):
        """종합 점수 및 등급 산출"""
        scores = result.category_scores

        # 가중 평균 계산
        total_score = (
            scores.stability * self.CATEGORY_WEIGHTS['stability'] +
            scores.profitability * self.CATEGORY_WEIGHTS['profitability'] +
            scores.growth * self.CATEGORY_WEIGHTS['growth'] +
            scores.activity * self.CATEGORY_WEIGHTS['activity'] +
            scores.cashflow * self.CATEGORY_WEIGHTS['cashflow'] +
            scores.leverage * self.CATEGORY_WEIGHTS['leverage']
        )

        result.financial_health_score = round(total_score, 2)

        # 등급 결정
        for threshold, grade in self.GRADE_THRESHOLDS:
            if total_score >= threshold:
                result.financial_health_grade = grade
                break

        # 위험 수준 결정
        for threshold, risk_level in self.RISK_THRESHOLDS:
            if total_score >= threshold:
                result.financial_risk_level = risk_level
                break

    # =========================================================================
    # 10. 데이터 완성도
    # =========================================================================
    def _calculate_data_completeness(self, result: FinancialRatiosResult) -> float:
        """데이터 완성도 계산"""
        # 핵심 비율 필드 체크
        key_fields = [
            result.current_ratio,
            result.debt_ratio,
            result.operating_margin,
            result.net_profit_margin,
            result.roa,
            result.roe,
            result.asset_turnover,
            result.ocf_ratio,
            result.interest_coverage,
        ]

        filled = sum(1 for f in key_fields if f is not None)
        return round(filled / len(key_fields) * 100, 2)

    # =========================================================================
    # 결과 변환
    # =========================================================================
    def result_to_dict(self, result: FinancialRatiosResult) -> Dict[str, Any]:
        """결과를 DB 저장용 딕셔너리로 변환"""
        return {
            'company_id': result.company_id,
            'fiscal_year': result.fiscal_year,
            'fiscal_quarter': result.fiscal_quarter,
            # 안정성
            'current_ratio': result.current_ratio,
            'quick_ratio': result.quick_ratio,
            'debt_ratio': result.debt_ratio,
            'equity_ratio': result.equity_ratio,
            'debt_dependency': result.debt_dependency,
            'non_current_ratio': result.non_current_ratio,
            # 수익성
            'operating_margin': result.operating_margin,
            'net_profit_margin': result.net_profit_margin,
            'roa': result.roa,
            'roe': result.roe,
            'gross_margin': result.gross_margin,
            'ebitda_margin': result.ebitda_margin,
            'ebitda': result.ebitda,
            # 성장성
            'revenue_growth': result.revenue_growth,
            'operating_income_growth': result.operating_income_growth,
            'net_income_growth': result.net_income_growth,
            'total_assets_growth': result.total_assets_growth,
            'growth_data_available': result.growth_data_available,
            # 활동성
            'asset_turnover': result.asset_turnover,
            'receivables_turnover': result.receivables_turnover,
            'inventory_turnover': result.inventory_turnover,
            'payables_turnover': result.payables_turnover,
            'receivables_days': result.receivables_days,
            'inventory_days': result.inventory_days,
            'payables_days': result.payables_days,
            'cash_conversion_cycle': result.cash_conversion_cycle,
            # 현금흐름
            'ocf_ratio': result.ocf_ratio,
            'ocf_interest_coverage': result.ocf_interest_coverage,
            'free_cash_flow': result.free_cash_flow,
            'fcf_margin': result.fcf_margin,
            # 레버리지
            'interest_coverage': result.interest_coverage,
            'ebitda_interest_coverage': result.ebitda_interest_coverage,
            'net_debt_to_ebitda': result.net_debt_to_ebitda,
            'financial_expense_ratio': result.financial_expense_ratio,
            'total_borrowings': result.total_borrowings,
            'net_debt': result.net_debt,
            # 연속 적자/흑자
            'consecutive_loss_quarters': result.consecutive_loss_quarters,
            'consecutive_profit_quarters': result.consecutive_profit_quarters,
            'is_loss_making': result.is_loss_making,
            # 카테고리 점수
            'stability_score': result.category_scores.stability,
            'profitability_score': result.category_scores.profitability,
            'growth_score': result.category_scores.growth,
            'activity_score': result.category_scores.activity,
            'cashflow_score': result.category_scores.cashflow,
            'leverage_score': result.category_scores.leverage,
            # 종합
            'financial_health_score': result.financial_health_score,
            'financial_health_grade': result.financial_health_grade,
            'financial_risk_level': result.financial_risk_level,
            # 메타
            'data_completeness': result.data_completeness,
            'calculation_notes': '\n'.join(result.calculation_notes) if result.calculation_notes else None,
        }
