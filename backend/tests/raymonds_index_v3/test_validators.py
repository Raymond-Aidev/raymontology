"""
RaymondsIndex v3.0 검증기 테스트

테스트 대상:
- DataValidator: 재무 데이터 검증
- ValidationResult: 검증 결과
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.raymonds_index_v3.validators import (
    DataValidator,
    ValidationResult,
)


class TestValidationResult:
    """ValidationResult 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        result = ValidationResult(
            is_valid=True,
            can_calculate=True,
            quality_score=85.0,
            errors=[],
            warnings=['테스트 경고'],
            missing_fields=['cash_and_equivalents'],
            data_years=5,
        )
        d = result.to_dict()
        assert d['is_valid'] is True
        assert d['quality_score'] == 85.0
        assert len(d['warnings']) == 1


class TestDataValidator:
    """DataValidator 테스트"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    @pytest.fixture
    def complete_data(self):
        """완전한 재무 데이터"""
        return {
            'revenue': [1000e8, 1100e8, 1200e8, 1300e8, 1400e8],
            'operating_income': [100e8, 110e8, 120e8, 130e8, 140e8],
            'net_income': [80e8, 88e8, 96e8, 104e8, 112e8],
            'total_assets': [5000e8, 5200e8, 5400e8, 5600e8, 5800e8],
            'operating_cash_flow': [150e8, 160e8, 170e8, 180e8, 190e8],
            'capex': [50e8, 55e8, 60e8, 65e8, 70e8],
            'cash_and_equivalents': [200e8, 220e8, 240e8, 260e8, 280e8],
            'short_term_investments': [100e8, 110e8, 120e8, 130e8, 140e8],
            'tangible_assets': [1000e8, 1050e8, 1100e8, 1150e8, 1200e8],
            'total_equity': [3000e8, 3100e8, 3200e8, 3300e8, 3400e8],
            'total_liabilities': [2000e8, 2100e8, 2200e8, 2300e8, 2400e8],
            'dividend_paid': [20e8, 22e8, 24e8, 26e8, 28e8],
        }

    def test_valid_complete_data(self, validator, complete_data):
        """완전한 데이터 검증"""
        result = validator.validate(complete_data)
        assert result.is_valid is True
        assert result.can_calculate is True
        assert result.quality_score >= 80
        assert len(result.errors) == 0
        assert result.data_years == 5

    def test_missing_required_field(self, validator):
        """필수 필드 누락"""
        data = {
            'revenue': [1000e8, 1100e8, 1200e8],
            'operating_income': [100e8, 110e8, 120e8],
            # net_income 누락
            'total_assets': [5000e8, 5200e8, 5400e8],
            'operating_cash_flow': [150e8, 160e8, 170e8],
            'capex': [50e8, 55e8, 60e8],
        }
        result = validator.validate(data)
        assert result.is_valid is False
        assert 'net_income' in result.missing_fields
        assert any('net_income' in e for e in result.errors)

    def test_insufficient_years(self, validator):
        """연도 부족"""
        # MIN_REQUIRED_YEARS = 2, 그래서 1년만 있으면 실패
        data = {
            'revenue': [1000e8],  # 1년 (최소 2년 필요)
            'operating_income': [100e8],
            'net_income': [80e8],
            'total_assets': [5000e8],
            'operating_cash_flow': [150e8],
            'capex': [50e8],
        }
        result = validator.validate(data)
        assert result.is_valid is False
        assert result.data_years == 1

    def test_negative_total_assets(self, validator, complete_data):
        """총자산 음수 검증"""
        complete_data['total_assets'] = [-5000e8, 5200e8, 5400e8, 5600e8, 5800e8]
        result = validator.validate(complete_data)
        assert result.is_valid is False
        assert any('총자산' in e and '음수' in e for e in result.errors)

    def test_tiny_capex_warning(self, validator, complete_data):
        """⭐ CAPEX 극소값 경고 (-999% 버그 원인)"""
        # 초기 CAPEX를 극소값으로 설정
        complete_data['capex'] = [0.001e8, 0.002e8, 50e8, 55e8, 60e8]  # 0.001억
        result = validator.validate(complete_data)
        # 경고 발생해야 함
        assert any('CAPEX' in w and '미만' in w for w in result.warnings)

    def test_tiny_cash_warning(self, validator, complete_data):
        """현금 극소값 경고"""
        complete_data['cash_and_equivalents'] = [0.005e8, 220e8, 240e8, 260e8, 280e8]  # 초기 0.005억
        result = validator.validate(complete_data)
        assert any('현금' in w and 'CAGR' in w for w in result.warnings)

    def test_high_asset_turnover_warning(self, validator, complete_data):
        """자산회전율 이상 경고"""
        # 매출 >> 자산 (비정상)
        complete_data['revenue'] = [50000e8, 51000e8, 52000e8, 53000e8, 54000e8]
        complete_data['total_assets'] = [500e8, 520e8, 540e8, 560e8, 580e8]
        result = validator.validate(complete_data)
        assert any('자산회전율' in w for w in result.warnings)

    def test_oi_greater_than_revenue_warning(self, validator, complete_data):
        """영업이익 > 매출 경고"""
        complete_data['operating_income'] = [100e8, 110e8, 120e8, 130e8, 2000e8]  # 마지막 비정상
        complete_data['revenue'] = [1000e8, 1100e8, 1200e8, 1300e8, 1400e8]
        result = validator.validate(complete_data)
        assert any('영업이익이 매출보다' in w for w in result.warnings)

    def test_quality_score_calculation(self, validator):
        """품질 점수 계산"""
        # 에러 1개, 경고 2개, 누락 3개
        # 100 - 25 - 10 - 9 = 56
        data = {
            'revenue': [1000e8, 1100e8],  # 연도 부족 (에러 1개)
            'operating_income': [100e8, 110e8],
            'net_income': [80e8, 88e8],
            'total_assets': [5000e8, 5200e8],
            'operating_cash_flow': [150e8, 160e8],
            'capex': [50e8, 55e8],
            # 권장 필드 누락
        }
        result = validator.validate(data)
        assert result.quality_score < 70

    def test_empty_data(self, validator):
        """빈 데이터"""
        result = validator.validate({})
        assert result.is_valid is False
        assert result.can_calculate is False
        assert result.quality_score < 50

    def test_all_none_values(self, validator):
        """모든 값이 None"""
        data = {
            'revenue': [None, None, None, None, None],
            'operating_income': [None, None, None, None, None],
            'net_income': [None, None, None, None, None],
            'total_assets': [None, None, None, None, None],
            'operating_cash_flow': [None, None, None, None, None],
            'capex': [None, None, None, None, None],
        }
        result = validator.validate(data)
        assert result.is_valid is False


class TestValidateForCalculation:
    """validate_for_calculation 테스트 (연도별 리스트 입력)"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_valid_list_input(self, validator):
        """리스트 형태 입력"""
        financial_data = [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 100e8, 'net_income': 80e8, 'total_assets': 5000e8, 'operating_cash_flow': 150e8, 'capex': 50e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 110e8, 'net_income': 88e8, 'total_assets': 5200e8, 'operating_cash_flow': 160e8, 'capex': 55e8},
            {'fiscal_year': 2022, 'revenue': 1200e8, 'operating_income': 120e8, 'net_income': 96e8, 'total_assets': 5400e8, 'operating_cash_flow': 170e8, 'capex': 60e8},
            {'fiscal_year': 2023, 'revenue': 1300e8, 'operating_income': 130e8, 'net_income': 104e8, 'total_assets': 5600e8, 'operating_cash_flow': 180e8, 'capex': 65e8},
            {'fiscal_year': 2024, 'revenue': 1400e8, 'operating_income': 140e8, 'net_income': 112e8, 'total_assets': 5800e8, 'operating_cash_flow': 190e8, 'capex': 70e8},
        ]
        result = validator.validate_for_calculation(financial_data)
        assert result.is_valid is True
        assert result.data_years == 5

    def test_empty_list(self, validator):
        """빈 리스트"""
        result = validator.validate_for_calculation([])
        assert result.is_valid is False
        assert '비어있습니다' in result.errors[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
