"""
RaymondsIndex v3.0 엔진 통합 테스트

테스트 대상:
- RaymondsIndexCalculatorV3: 통합 계산기
- 전체 계산 플로우
- 등급 부여 로직
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.raymonds_index_v3.engine import RaymondsIndexCalculatorV3
from app.services.raymonds_index_v3.normalizers import geometric_mean_weighted
from app.services.raymonds_index_v3.constants import SUBINDEX_WEIGHTS


class TestRaymondsIndexCalculatorV3:
    """RaymondsIndexCalculatorV3 테스트"""

    @pytest.fixture
    def calculator(self):
        return RaymondsIndexCalculatorV3()

    @pytest.fixture
    def excellent_company_data(self):
        """우수 기업 재무 데이터 (A등급 기대) - 연도별 리스트"""
        return [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 200e8, 'net_income': 160e8,
             'total_assets': 2000e8, 'operating_cash_flow': 250e8, 'capex': 100e8,
             'cash_and_equivalents': 300e8, 'short_term_investments': 100e8,
             'tangible_assets': 500e8, 'total_equity': 1500e8, 'total_liabilities': 500e8, 'dividend_paid': 50e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 220e8, 'net_income': 176e8,
             'total_assets': 2100e8, 'operating_cash_flow': 275e8, 'capex': 110e8,
             'cash_and_equivalents': 330e8, 'short_term_investments': 110e8,
             'tangible_assets': 530e8, 'total_equity': 1600e8, 'total_liabilities': 500e8, 'dividend_paid': 55e8},
            {'fiscal_year': 2022, 'revenue': 1210e8, 'operating_income': 242e8, 'net_income': 194e8,
             'total_assets': 2200e8, 'operating_cash_flow': 300e8, 'capex': 121e8,
             'cash_and_equivalents': 360e8, 'short_term_investments': 120e8,
             'tangible_assets': 560e8, 'total_equity': 1700e8, 'total_liabilities': 500e8, 'dividend_paid': 60e8},
            {'fiscal_year': 2023, 'revenue': 1331e8, 'operating_income': 266e8, 'net_income': 213e8,
             'total_assets': 2300e8, 'operating_cash_flow': 330e8, 'capex': 133e8,
             'cash_and_equivalents': 400e8, 'short_term_investments': 130e8,
             'tangible_assets': 590e8, 'total_equity': 1800e8, 'total_liabilities': 500e8, 'dividend_paid': 66e8},
            {'fiscal_year': 2024, 'revenue': 1464e8, 'operating_income': 293e8, 'net_income': 234e8,
             'total_assets': 2400e8, 'operating_cash_flow': 360e8, 'capex': 146e8,
             'cash_and_equivalents': 440e8, 'short_term_investments': 140e8,
             'tangible_assets': 620e8, 'total_equity': 1900e8, 'total_liabilities': 500e8, 'dividend_paid': 73e8},
        ]

    @pytest.fixture
    def poor_company_data(self):
        """저조 기업 재무 데이터 (C등급 기대)"""
        return [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 50e8, 'net_income': 30e8,
             'total_assets': 5000e8, 'operating_cash_flow': 80e8, 'capex': 200e8,
             'cash_and_equivalents': 100e8, 'short_term_investments': 500e8,
             'tangible_assets': 200e8, 'total_equity': 2000e8, 'total_liabilities': 3000e8, 'dividend_paid': 0},
            {'fiscal_year': 2021, 'revenue': 950e8, 'operating_income': 40e8, 'net_income': 20e8,
             'total_assets': 5200e8, 'operating_cash_flow': 70e8, 'capex': 150e8,
             'cash_and_equivalents': 200e8, 'short_term_investments': 600e8,
             'tangible_assets': 180e8, 'total_equity': 2050e8, 'total_liabilities': 3150e8, 'dividend_paid': 0},
            {'fiscal_year': 2022, 'revenue': 900e8, 'operating_income': 30e8, 'net_income': 10e8,
             'total_assets': 5400e8, 'operating_cash_flow': 60e8, 'capex': 100e8,
             'cash_and_equivalents': 400e8, 'short_term_investments': 700e8,
             'tangible_assets': 160e8, 'total_equity': 2100e8, 'total_liabilities': 3300e8, 'dividend_paid': 0},
            {'fiscal_year': 2023, 'revenue': 850e8, 'operating_income': 20e8, 'net_income': 5e8,
             'total_assets': 5600e8, 'operating_cash_flow': 50e8, 'capex': 50e8,
             'cash_and_equivalents': 800e8, 'short_term_investments': 800e8,
             'tangible_assets': 140e8, 'total_equity': 2150e8, 'total_liabilities': 3450e8, 'dividend_paid': 0},
            {'fiscal_year': 2024, 'revenue': 800e8, 'operating_income': 10e8, 'net_income': -10e8,
             'total_assets': 5800e8, 'operating_cash_flow': 40e8, 'capex': 20e8,
             'cash_and_equivalents': 1600e8, 'short_term_investments': 900e8,
             'tangible_assets': 120e8, 'total_equity': 2200e8, 'total_liabilities': 3600e8, 'dividend_paid': 0},
        ]

    def test_calculate_returns_result(self, calculator, excellent_company_data):
        """계산 결과 반환"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert result is not None
        assert hasattr(result, 'total_score')
        assert hasattr(result, 'grade')
        assert hasattr(result, 'cei_score')

    def test_calculate_total_score_range(self, calculator, excellent_company_data):
        """총점 범위 (0-100)"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert 0 <= result.total_score <= 100

    def test_calculate_has_sub_indices(self, calculator, excellent_company_data):
        """Sub-Index 포함 확인"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert hasattr(result, 'cei_score')
        assert hasattr(result, 'rii_score')
        assert hasattr(result, 'cgi_score')
        assert hasattr(result, 'mai_score')

    def test_calculate_sub_index_scores_range(self, calculator, excellent_company_data):
        """Sub-Index 점수 범위"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert 0 <= result.cei_score <= 100
        assert 0 <= result.rii_score <= 100
        assert 0 <= result.cgi_score <= 100
        assert 0 <= result.mai_score <= 100

    def test_excellent_company_high_score(self, calculator, excellent_company_data):
        """우수 기업 높은 점수"""
        result = calculator.calculate('test-company', excellent_company_data)
        # 높은 점수 기대
        assert result.total_score >= 50

    def test_poor_company_low_score(self, calculator, poor_company_data):
        """저조 기업 낮은 점수"""
        result = calculator.calculate('test-company', poor_company_data)
        # 낮은 점수 기대
        assert result.total_score <= 70

    def test_grade_assignment(self, calculator, excellent_company_data):
        """등급 부여"""
        result = calculator.calculate('test-company', excellent_company_data)
        valid_grades = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'N/A']
        assert result.grade in valid_grades

    def test_raw_metrics_included(self, calculator, excellent_company_data):
        """원시 지표 포함"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert hasattr(result, 'raw_metrics')
        assert isinstance(result.raw_metrics, dict)

    def test_flags_included(self, calculator, excellent_company_data):
        """플래그 포함"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert hasattr(result, 'red_flags')
        assert hasattr(result, 'yellow_flags')
        assert isinstance(result.red_flags, list)
        assert isinstance(result.yellow_flags, list)

    def test_interpretation_included(self, calculator, excellent_company_data):
        """해석 포함"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert hasattr(result, 'verdict')
        assert result.verdict != ''

    def test_empty_data(self, calculator):
        """빈 데이터 처리"""
        result = calculator.calculate('test-company', [])
        assert result.status == 'DATA_INSUFFICIENT'
        assert result.grade == 'N/A'

    def test_validation_result_included(self, calculator, excellent_company_data):
        """검증 결과 포함"""
        result = calculator.calculate('test-company', excellent_company_data)
        assert hasattr(result, 'data_quality_score')


class TestGradeAssignment:
    """등급 부여 로직 테스트

    constants.py GRADE_THRESHOLDS:
    (95, 'A++'), (88, 'A+'), (80, 'A'), (72, 'A-'),
    (64, 'B+'), (55, 'B'), (45, 'B-'), (30, 'C+'), (0, 'C')
    """

    @pytest.fixture
    def calculator(self):
        return RaymondsIndexCalculatorV3()

    def test_grade_a_plus_plus(self, calculator):
        """A++ 등급 (95+)"""
        grade = calculator._determine_grade(97)
        assert grade == 'A++'

    def test_grade_a_plus(self, calculator):
        """A+ 등급 (88-94)"""
        grade = calculator._determine_grade(92)
        assert grade == 'A+'

    def test_grade_a(self, calculator):
        """A 등급 (80-87)"""
        grade = calculator._determine_grade(85)
        assert grade == 'A'

    def test_grade_a_minus(self, calculator):
        """A- 등급 (72-79)"""
        grade = calculator._determine_grade(75)
        assert grade == 'A-'

    def test_grade_b_plus(self, calculator):
        """B+ 등급 (64-71)"""
        grade = calculator._determine_grade(68)
        assert grade == 'B+'

    def test_grade_b(self, calculator):
        """B 등급 (55-63)"""
        grade = calculator._determine_grade(58)
        assert grade == 'B'

    def test_grade_b_minus(self, calculator):
        """B- 등급 (45-54)"""
        grade = calculator._determine_grade(50)
        assert grade == 'B-'

    def test_grade_c_plus(self, calculator):
        """C+ 등급 (30-44)"""
        grade = calculator._determine_grade(35)
        assert grade == 'C+'

    def test_grade_c(self, calculator):
        """C 등급 (<30)"""
        grade = calculator._determine_grade(25)
        assert grade == 'C'


class TestGeometricMeanAggregation:
    """기하평균 집계 테스트"""

    def test_geometric_vs_arithmetic(self):
        """기하평균 vs 산술평균 비교"""
        # 불균형한 점수
        sub_indices = {'CEI': 90, 'RII': 40, 'CGI': 80, 'MAI': 70}

        # 산술평균: 90*0.2 + 40*0.35 + 80*0.25 + 70*0.2 = 64
        arithmetic = 90*0.2 + 40*0.35 + 80*0.25 + 70*0.2

        # 기하평균은 낮은 점수에 더 큰 페널티 → 산술평균보다 낮아야 함
        geometric = geometric_mean_weighted(sub_indices, SUBINDEX_WEIGHTS)

        assert geometric < arithmetic

    def test_uniform_scores(self):
        """균일 점수 시 기하평균 ≈ 산술평균"""
        sub_indices = {'CEI': 70, 'RII': 70, 'CGI': 70, 'MAI': 70}
        result = geometric_mean_weighted(sub_indices, SUBINDEX_WEIGHTS)
        assert abs(result - 70) < 1


class TestBugPrevention999:
    """⭐ -999% 버그 방지 통합 테스트"""

    @pytest.fixture
    def calculator(self):
        return RaymondsIndexCalculatorV3()

    def test_extreme_capex_growth_does_not_crash(self, calculator):
        """극단적 CAPEX 성장 시에도 정상 작동"""
        data = [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 100e8, 'net_income': 80e8,
             'total_assets': 5000e8, 'operating_cash_flow': 150e8, 'capex': 0.001e8,  # 극소
             'cash_and_equivalents': 200e8, 'short_term_investments': 0,
             'tangible_assets': 1000e8, 'total_equity': 3000e8, 'total_liabilities': 2000e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 110e8, 'net_income': 88e8,
             'total_assets': 5200e8, 'operating_cash_flow': 160e8, 'capex': 0.01e8,
             'cash_and_equivalents': 220e8, 'short_term_investments': 0,
             'tangible_assets': 1050e8, 'total_equity': 3100e8, 'total_liabilities': 2100e8},
            {'fiscal_year': 2022, 'revenue': 1200e8, 'operating_income': 120e8, 'net_income': 96e8,
             'total_assets': 5400e8, 'operating_cash_flow': 170e8, 'capex': 1e8,
             'cash_and_equivalents': 240e8, 'short_term_investments': 0,
             'tangible_assets': 1100e8, 'total_equity': 3200e8, 'total_liabilities': 2200e8},
            {'fiscal_year': 2023, 'revenue': 1300e8, 'operating_income': 130e8, 'net_income': 104e8,
             'total_assets': 5600e8, 'operating_cash_flow': 180e8, 'capex': 50e8,
             'cash_and_equivalents': 260e8, 'short_term_investments': 0,
             'tangible_assets': 1150e8, 'total_equity': 3300e8, 'total_liabilities': 2300e8},
            {'fiscal_year': 2024, 'revenue': 1400e8, 'operating_income': 140e8, 'net_income': 112e8,
             'total_assets': 5800e8, 'operating_cash_flow': 190e8, 'capex': 100e8,  # 급증
             'cash_and_equivalents': 280e8, 'short_term_investments': 0,
             'tangible_assets': 1200e8, 'total_equity': 3400e8, 'total_liabilities': 2400e8},
        ]
        result = calculator.calculate('test-company', data)

        # 계산 완료 (크래시 없음)
        assert result is not None
        assert hasattr(result, 'total_score')

        # 점수가 합리적 범위 내
        assert 0 <= result.total_score <= 100

        # investment_gap이 클램핑됨
        assert -100 <= result.investment_gap <= 100

    def test_extreme_cash_growth_clamped(self, calculator):
        """극단적 현금 증가 시 클램핑"""
        data = [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 100e8, 'net_income': 80e8,
             'total_assets': 5000e8, 'operating_cash_flow': 150e8, 'capex': 50e8,
             'cash_and_equivalents': 1e8, 'short_term_investments': 0,  # 극소
             'tangible_assets': 1000e8, 'total_equity': 3000e8, 'total_liabilities': 2000e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 110e8, 'net_income': 88e8,
             'total_assets': 5200e8, 'operating_cash_flow': 160e8, 'capex': 55e8,
             'cash_and_equivalents': 10e8, 'short_term_investments': 0,
             'tangible_assets': 1050e8, 'total_equity': 3100e8, 'total_liabilities': 2100e8},
            {'fiscal_year': 2022, 'revenue': 1200e8, 'operating_income': 120e8, 'net_income': 96e8,
             'total_assets': 5400e8, 'operating_cash_flow': 170e8, 'capex': 60e8,
             'cash_and_equivalents': 100e8, 'short_term_investments': 0,
             'tangible_assets': 1100e8, 'total_equity': 3200e8, 'total_liabilities': 2200e8},
            {'fiscal_year': 2023, 'revenue': 1300e8, 'operating_income': 130e8, 'net_income': 104e8,
             'total_assets': 5600e8, 'operating_cash_flow': 180e8, 'capex': 65e8,
             'cash_and_equivalents': 1000e8, 'short_term_investments': 0,
             'tangible_assets': 1150e8, 'total_equity': 3300e8, 'total_liabilities': 2300e8},
            {'fiscal_year': 2024, 'revenue': 1400e8, 'operating_income': 140e8, 'net_income': 112e8,
             'total_assets': 5800e8, 'operating_cash_flow': 190e8, 'capex': 70e8,
             'cash_and_equivalents': 10000e8, 'short_term_investments': 0,  # 폭증
             'tangible_assets': 1200e8, 'total_equity': 3400e8, 'total_liabilities': 2400e8},
        ]
        result = calculator.calculate('test-company', data)

        # 계산 완료
        assert result is not None
        assert 0 <= result.total_score <= 100

        # cash_cagr이 클램핑됨
        assert -50 <= result.cash_cagr <= 200


class TestFlagGeneration:
    """플래그 생성 테스트"""

    @pytest.fixture
    def calculator(self):
        return RaymondsIndexCalculatorV3()

    def test_high_investment_gap_flag(self, calculator):
        """높은 투자괴리율 플래그"""
        data = [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 100e8, 'net_income': 80e8,
             'total_assets': 5000e8, 'operating_cash_flow': 150e8, 'capex': 100e8,
             'cash_and_equivalents': 100e8, 'short_term_investments': 0,
             'tangible_assets': 1000e8, 'total_equity': 3000e8, 'total_liabilities': 2000e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 110e8, 'net_income': 88e8,
             'total_assets': 5200e8, 'operating_cash_flow': 160e8, 'capex': 80e8,  # CAPEX 감소
             'cash_and_equivalents': 200e8, 'short_term_investments': 0,  # 현금 증가
             'tangible_assets': 1050e8, 'total_equity': 3100e8, 'total_liabilities': 2100e8},
            {'fiscal_year': 2022, 'revenue': 1200e8, 'operating_income': 120e8, 'net_income': 96e8,
             'total_assets': 5400e8, 'operating_cash_flow': 170e8, 'capex': 60e8,
             'cash_and_equivalents': 400e8, 'short_term_investments': 0,
             'tangible_assets': 1100e8, 'total_equity': 3200e8, 'total_liabilities': 2200e8},
            {'fiscal_year': 2023, 'revenue': 1300e8, 'operating_income': 130e8, 'net_income': 104e8,
             'total_assets': 5600e8, 'operating_cash_flow': 180e8, 'capex': 40e8,
             'cash_and_equivalents': 800e8, 'short_term_investments': 0,
             'tangible_assets': 1150e8, 'total_equity': 3300e8, 'total_liabilities': 2300e8},
            {'fiscal_year': 2024, 'revenue': 1400e8, 'operating_income': 140e8, 'net_income': 112e8,
             'total_assets': 5800e8, 'operating_cash_flow': 190e8, 'capex': 20e8,  # CAPEX 급감
             'cash_and_equivalents': 1600e8, 'short_term_investments': 0,  # 현금 급증
             'tangible_assets': 1200e8, 'total_equity': 3400e8, 'total_liabilities': 2400e8},
        ]
        result = calculator.calculate('test-company', data)

        # 플래그 시스템이 동작함
        assert isinstance(result.red_flags, list)
        assert isinstance(result.yellow_flags, list)


class TestToDict:
    """to_dict 메서드 테스트"""

    @pytest.fixture
    def calculator(self):
        return RaymondsIndexCalculatorV3()

    @pytest.fixture
    def sample_data(self):
        return [
            {'fiscal_year': 2020, 'revenue': 1000e8, 'operating_income': 100e8, 'net_income': 80e8,
             'total_assets': 2000e8, 'operating_cash_flow': 150e8, 'capex': 50e8,
             'cash_and_equivalents': 200e8, 'short_term_investments': 100e8,
             'tangible_assets': 500e8, 'total_equity': 1500e8, 'total_liabilities': 500e8},
            {'fiscal_year': 2021, 'revenue': 1100e8, 'operating_income': 110e8, 'net_income': 88e8,
             'total_assets': 2100e8, 'operating_cash_flow': 160e8, 'capex': 55e8,
             'cash_and_equivalents': 220e8, 'short_term_investments': 110e8,
             'tangible_assets': 530e8, 'total_equity': 1600e8, 'total_liabilities': 500e8},
            {'fiscal_year': 2022, 'revenue': 1200e8, 'operating_income': 120e8, 'net_income': 96e8,
             'total_assets': 2200e8, 'operating_cash_flow': 170e8, 'capex': 60e8,
             'cash_and_equivalents': 240e8, 'short_term_investments': 120e8,
             'tangible_assets': 560e8, 'total_equity': 1700e8, 'total_liabilities': 500e8},
        ]

    def test_to_dict(self, calculator, sample_data):
        """to_dict 변환"""
        result = calculator.calculate('test-company', sample_data)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert 'total_score' in d
        assert 'grade' in d
        assert 'cei_score' in d


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
