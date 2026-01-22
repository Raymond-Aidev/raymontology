"""
RaymondsIndex v3.0 Calculator 테스트

테스트 대상:
- CEICalculator: Capital Efficiency Index
- RIICalculator: Reinvestment Intensity Index (⭐ 핵심)
- CGICalculator: Cash Governance Index
- MAICalculator: Momentum Alignment Index
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.raymonds_index_v3.calculators import (
    CEICalculator,
    RIICalculator,
    CGICalculator,
    MAICalculator,
)


class TestCEICalculator:
    """CEI (Capital Efficiency Index) 테스트"""

    @pytest.fixture
    def calculator(self):
        return CEICalculator()

    @pytest.fixture
    def sample_data(self):
        """샘플 재무 데이터"""
        return {
            'revenue': [1000e8, 1100e8, 1200e8, 1300e8, 1400e8],
            'operating_income': [100e8, 110e8, 120e8, 130e8, 140e8],
            'total_assets': [5000e8, 5200e8, 5400e8, 5600e8, 5800e8],
            'tangible_assets': [1000e8, 1050e8, 1100e8, 1150e8, 1200e8],
            'cash_and_equivalents': [200e8, 220e8, 240e8, 260e8, 280e8],
            'short_term_investments': [100e8, 110e8, 120e8, 130e8, 140e8],
            'total_equity': [3000e8, 3100e8, 3200e8, 3300e8, 3400e8],
            'total_liabilities': [2000e8, 2100e8, 2200e8, 2300e8, 2400e8],
            'net_income': [80e8, 88e8, 96e8, 104e8, 112e8],
        }

    def test_calculate_returns_score(self, calculator, sample_data):
        """점수 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'score')
        assert 0 <= result.score <= 100

    def test_calculate_returns_raw_metrics(self, calculator, sample_data):
        """원시 지표 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'raw_metrics')
        assert 'asset_turnover' in result.raw_metrics

    def test_calculate_returns_normalized_metrics(self, calculator, sample_data):
        """정규화 지표 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'normalized_metrics')

    def test_asset_turnover_calculation(self, calculator, sample_data):
        """자산회전율 계산"""
        result = calculator.calculate(sample_data)
        # 1400억 / 5800억 ≈ 0.24
        expected = 1400e8 / 5800e8
        assert abs(result.raw_metrics['asset_turnover'] - expected) < 0.01

    def test_empty_data(self, calculator):
        """빈 데이터 처리"""
        result = calculator.calculate({})
        # 빈 데이터 시 기본 정규화가 적용되어 0이 아닐 수 있음
        assert 0 <= result.score <= 100


class TestRIICalculator:
    """RII (Reinvestment Intensity Index) 테스트 - ⭐ 핵심"""

    @pytest.fixture
    def calculator(self):
        return RIICalculator()

    @pytest.fixture
    def sample_data(self):
        """샘플 재무 데이터"""
        return {
            'operating_cash_flow': [150e8, 160e8, 170e8, 180e8, 190e8],
            'capex': [50e8, 55e8, 60e8, 65e8, 70e8],
            'cash_and_equivalents': [200e8, 220e8, 240e8, 260e8, 280e8],
            'short_term_investments': [100e8, 110e8, 120e8, 130e8, 140e8],
            'total_assets': [5000e8, 5200e8, 5400e8, 5600e8, 5800e8],
        }

    def test_calculate_returns_score(self, calculator, sample_data):
        """점수 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'score')
        assert 0 <= result.score <= 100

    def test_investment_gap_calculation(self, calculator, sample_data):
        """투자괴리율 계산"""
        result = calculator.calculate(sample_data)
        assert 'investment_gap' in result.raw_metrics
        assert 'cash_cagr' in result.raw_metrics
        assert 'capex_growth' in result.raw_metrics

    def test_investment_gap_clamped(self, calculator):
        """⭐ 투자괴리율 클램핑 테스트"""
        # 극단적인 케이스: 현금 급증, CAPEX 극소
        data = {
            'operating_cash_flow': [150e8, 160e8, 170e8, 180e8, 190e8],
            'capex': [0.01e8, 0.02e8, 100e8, 100e8, 100e8],  # 초기 극소
            'cash_and_equivalents': [10e8, 50e8, 100e8, 200e8, 1000e8],  # 급증
            'short_term_investments': [0, 0, 0, 0, 0],
            'total_assets': [5000e8, 5200e8, 5400e8, 5600e8, 5800e8],
        }
        result = calculator.calculate(data)
        # 투자괴리율이 -100 ~ +100 범위 내
        assert -100 <= result.raw_metrics['investment_gap'] <= 100

    def test_reinvestment_rate(self, calculator, sample_data):
        """재투자율 계산"""
        result = calculator.calculate(sample_data)
        assert 'reinvestment_rate' in result.raw_metrics
        # CAPEX / OCF = 70억 / 190억 ≈ 36.8%
        expected = (70e8 / 190e8) * 100
        assert abs(result.raw_metrics['reinvestment_rate'] - expected) < 1

    def test_capex_intensity(self, calculator, sample_data):
        """CAPEX 강도 계산"""
        result = calculator.calculate(sample_data)
        assert 'capex_intensity' in result.raw_metrics


class TestCGICalculator:
    """CGI (Cash Governance Index) 테스트"""

    @pytest.fixture
    def calculator(self):
        return CGICalculator()

    @pytest.fixture
    def sample_data(self):
        """샘플 재무 데이터"""
        return {
            'cash_and_equivalents': [200e8, 220e8, 240e8, 260e8, 280e8],
            'short_term_investments': [100e8, 110e8, 120e8, 130e8, 140e8],
            'total_assets': [5000e8, 5200e8, 5400e8, 5600e8, 5800e8],
            'operating_income': [100e8, 110e8, 120e8, 130e8, 140e8],
            'operating_cash_flow': [150e8, 160e8, 170e8, 180e8, 190e8],
            'capex': [50e8, 55e8, 60e8, 65e8, 70e8],
            'dividend_paid': [20e8, 22e8, 24e8, 26e8, 28e8],
            'net_income': [80e8, 88e8, 96e8, 104e8, 112e8],
            'total_liabilities': [2000e8, 2100e8, 2200e8, 2300e8, 2400e8],
            'total_equity': [3000e8, 3100e8, 3200e8, 3300e8, 3400e8],
            'tangible_assets': [1000e8, 1050e8, 1100e8, 1150e8, 1200e8],
        }

    def test_calculate_returns_score(self, calculator, sample_data):
        """점수 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'score')
        assert 0 <= result.score <= 100

    def test_cash_utilization(self, calculator, sample_data):
        """현금 활용도 계산"""
        result = calculator.calculate(sample_data)
        assert 'cash_utilization' in result.raw_metrics

    def test_payout_ratio(self, calculator, sample_data):
        """배당률(payout_ratio) 계산"""
        result = calculator.calculate(sample_data)
        # CGI에서는 payout_ratio로 명명됨
        assert 'payout_ratio' in result.raw_metrics
        # payout_ratio 값이 유효한 범위 내인지 확인
        assert 0 <= result.raw_metrics['payout_ratio'] <= 100

    def test_debt_to_ebitda(self, calculator, sample_data):
        """Debt/EBITDA 계산"""
        result = calculator.calculate(sample_data)
        assert 'debt_to_ebitda' in result.raw_metrics


class TestMAICalculator:
    """MAI (Momentum Alignment Index) 테스트"""

    @pytest.fixture
    def calculator(self):
        return MAICalculator()

    @pytest.fixture
    def sample_data(self):
        """샘플 재무 데이터"""
        return {
            'revenue': [1000e8, 1100e8, 1200e8, 1300e8, 1400e8],
            'operating_income': [100e8, 110e8, 120e8, 130e8, 140e8],
            'net_income': [80e8, 88e8, 96e8, 104e8, 112e8],
            'operating_cash_flow': [150e8, 160e8, 170e8, 180e8, 190e8],
            'capex': [50e8, 55e8, 60e8, 65e8, 70e8],
            'tangible_assets': [1000e8, 1050e8, 1100e8, 1150e8, 1200e8],
        }

    def test_calculate_returns_score(self, calculator, sample_data):
        """점수 반환 확인"""
        result = calculator.calculate(sample_data)
        assert hasattr(result, 'score')
        assert 0 <= result.score <= 100

    def test_revenue_capex_sync(self, calculator, sample_data):
        """매출-CAPEX 동조성 계산"""
        result = calculator.calculate(sample_data)
        assert 'revenue_capex_sync' in result.raw_metrics

    def test_earnings_quality(self, calculator, sample_data):
        """이익 품질 계산"""
        result = calculator.calculate(sample_data)
        assert 'earnings_quality' in result.raw_metrics
        # OCF / 순이익 = 190억 / 112억 ≈ 1.7
        expected = 190e8 / 112e8
        assert abs(result.raw_metrics['earnings_quality'] - expected) < 0.1

    def test_fcf_trend(self, calculator, sample_data):
        """FCF 추세 계산"""
        result = calculator.calculate(sample_data)
        assert 'fcf_trend' in result.raw_metrics

    def test_growth_investment_ratio(self, calculator, sample_data):
        """성장 투자 비율 계산"""
        result = calculator.calculate(sample_data)
        assert 'growth_investment_ratio' in result.raw_metrics


class TestCalculatorEdgeCases:
    """Calculator 공통 엣지 케이스 테스트"""

    def test_empty_data_all_calculators(self):
        """모든 Calculator에 빈 데이터"""
        for calc_class in [CEICalculator, RIICalculator, CGICalculator, MAICalculator]:
            calc = calc_class()
            result = calc.calculate({})
            # 빈 데이터 시 기본 정규화로 0이 아닐 수 있음
            assert 0 <= result.score <= 100

    def test_none_values_handling(self):
        """None 값 처리"""
        data = {
            'revenue': [None, None, None, None, None],
            'total_assets': [None, None, None, None, None],
        }
        for calc_class in [CEICalculator, RIICalculator, CGICalculator, MAICalculator]:
            calc = calc_class()
            result = calc.calculate(data)
            # 에러 없이 처리되어야 함
            assert hasattr(result, 'score')

    def test_single_year_data(self):
        """단일 연도 데이터"""
        data = {
            'revenue': [1000e8],
            'operating_income': [100e8],
            'net_income': [80e8],
            'total_assets': [5000e8],
            'operating_cash_flow': [150e8],
            'capex': [50e8],
        }
        for calc_class in [CEICalculator, RIICalculator, CGICalculator, MAICalculator]:
            calc = calc_class()
            result = calc.calculate(data)
            # 일부 추세 지표는 0이지만 에러 없이 처리
            assert hasattr(result, 'score')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
