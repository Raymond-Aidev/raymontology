"""
RaymondsIndex v3.0 정규화 함수 테스트

테스트 대상:
- min_max_normalize: HDI 방식 Min-Max 정규화
- v_score_normalize: V자 스코어링
- inverse_normalize: 역방향 정규화
- clamp: 범위 제한 (⭐ -999% 버그 방지)
- geometric_mean_weighted: 가중 기하평균
- safe_cagr, safe_growth_rate: 안전 계산
"""

import pytest
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.raymonds_index_v3.normalizers import (
    min_max_normalize,
    v_score_normalize,
    inverse_normalize,
    clamp,
    winsorize,
    geometric_mean_weighted,
    arithmetic_mean_weighted,
    safe_divide,
    safe_cagr,
    safe_growth_rate,
)


class TestMinMaxNormalize:
    """min_max_normalize 테스트"""

    def test_mid_value(self):
        """중간값 정규화"""
        # 자산회전율 1.5 (범위 0.1~3.0)
        result = min_max_normalize(1.5, 0.1, 3.0)
        expected = (1.5 - 0.1) / (3.0 - 0.1) * 100
        assert abs(result - expected) < 0.01
        assert abs(result - 48.28) < 0.1

    def test_min_value(self):
        """최소값 이하"""
        result = min_max_normalize(0.0, 0.1, 3.0)
        assert result == 0.0

    def test_max_value(self):
        """최대값 이상"""
        result = min_max_normalize(5.0, 0.1, 3.0)
        assert result == 100.0

    def test_none_value(self):
        """None 값 처리"""
        result = min_max_normalize(None, 0.1, 3.0)
        assert result == 0.0

    def test_invalid_bounds(self):
        """잘못된 경계값 (max <= min)"""
        result = min_max_normalize(1.5, 3.0, 0.1)
        assert result == 50.0  # 중립값 반환


class TestVScoreNormalize:
    """v_score_normalize 테스트 (V자 스코어링)"""

    def test_optimal_value(self):
        """최적값에서 100점"""
        # 투자괴리율 0% (최적)
        result = v_score_normalize(0, optimal=0, min_val=-50, max_val=50)
        assert result == 100.0

    def test_positive_deviation(self):
        """양수 편차"""
        # 투자괴리율 +25%
        result = v_score_normalize(25, optimal=0, min_val=-50, max_val=50)
        assert result == 50.0

    def test_negative_deviation(self):
        """음수 편차"""
        # 투자괴리율 -25%
        result = v_score_normalize(-25, optimal=0, min_val=-50, max_val=50)
        assert result == 50.0

    def test_extreme_positive(self):
        """극단 양수 (0점)"""
        result = v_score_normalize(50, optimal=0, min_val=-50, max_val=50)
        assert result == 0.0

    def test_extreme_negative(self):
        """극단 음수 (0점)"""
        result = v_score_normalize(-50, optimal=0, min_val=-50, max_val=50)
        assert result == 0.0

    def test_beyond_bounds(self):
        """경계 초과"""
        result = v_score_normalize(100, optimal=0, min_val=-50, max_val=50)
        assert result == 0.0

    def test_none_value(self):
        """None 값 처리"""
        result = v_score_normalize(None, optimal=0, min_val=-50, max_val=50)
        assert result == 50.0  # 중립

    def test_shareholder_return(self):
        """주주환원율 V-Score (35% 최적)"""
        # 최적
        result = v_score_normalize(35, optimal=35, min_val=0, max_val=100)
        assert result == 100.0

        # 0% (최저)
        result = v_score_normalize(0, optimal=35, min_val=0, max_val=100)
        assert result == 0.0

        # 17.5% (중간)
        result = v_score_normalize(17.5, optimal=35, min_val=0, max_val=100)
        assert result == 50.0


class TestInverseNormalize:
    """inverse_normalize 테스트 (역방향)"""

    def test_low_value_high_score(self):
        """낮은 값 = 높은 점수"""
        # Debt/EBITDA 1x
        result = inverse_normalize(1, min_val=0, max_val=10)
        assert result == 90.0

    def test_mid_value(self):
        """중간값"""
        result = inverse_normalize(5, min_val=0, max_val=10)
        assert result == 50.0

    def test_high_value_low_score(self):
        """높은 값 = 낮은 점수"""
        result = inverse_normalize(10, min_val=0, max_val=10)
        assert result == 0.0

    def test_min_value(self):
        """최소값 = 100점"""
        result = inverse_normalize(0, min_val=0, max_val=10)
        assert result == 100.0


class TestClamp:
    """clamp 테스트 (⭐ -999% 버그 방지 핵심)"""

    def test_capex_growth_upper_limit(self):
        """CAPEX 성장률 상한 제한"""
        # 99,900% → 500%로 제한
        result = clamp(99900, 'capex_growth')
        assert result == 500.0

    def test_capex_growth_lower_limit(self):
        """CAPEX 성장률 하한 제한"""
        result = clamp(-99, 'capex_growth')
        assert result == -95.0

    def test_investment_gap_limit(self):
        """투자괴리율 제한 (⭐ -999% 버그 방지)"""
        # -999% → -100%로 제한
        result = clamp(-999, 'investment_gap')
        assert result == -100.0

        # +999% → +100%로 제한
        result = clamp(999, 'investment_gap')
        assert result == 100.0

    def test_cash_cagr_limit(self):
        """현금 CAGR 제한"""
        result = clamp(500, 'cash_cagr')
        assert result == 200.0

    def test_no_limit_defined(self):
        """제한 정의 없는 지표"""
        result = clamp(99999, 'unknown_metric')
        assert result == 99999

    def test_none_value(self):
        """None 값 처리"""
        result = clamp(None, 'capex_growth')
        assert result == 0.0

    def test_within_bounds(self):
        """경계 내 값"""
        result = clamp(50, 'capex_growth')
        assert result == 50


class TestWinsorize:
    """winsorize 테스트"""

    def test_basic_winsorize(self):
        """기본 Winsorize"""
        values = list(range(100))
        result = winsorize(values, percentile=5)
        # 상하위 5% 대체
        assert min(result) >= 5
        assert max(result) <= 94

    def test_small_sample(self):
        """샘플 부족 시 스킵"""
        values = [1, 2, 3, 4, 5]
        result = winsorize(values)
        assert result == values  # 변경 없음

    def test_with_none_values(self):
        """None 값 포함"""
        values = [None, 1, 2, 3, None]
        result = winsorize(values)
        assert result[0] is None
        assert result[4] is None


class TestGeometricMeanWeighted:
    """geometric_mean_weighted 테스트 (HDI 2010 방식)"""

    def test_basic_calculation(self):
        """기본 계산"""
        scores = {'CEI': 75, 'RII': 60, 'CGI': 80, 'MAI': 70}
        weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
        result = geometric_mean_weighted(scores, weights)
        # 기하평균은 산술평균보다 낮아야 함 (RII가 낮아서)
        arithmetic = 75*0.2 + 60*0.35 + 80*0.25 + 70*0.2
        assert result < arithmetic
        assert result > 0

    def test_zero_prevention(self):
        """0점 방지 (최소 1점)"""
        scores = {'CEI': 0, 'RII': 100, 'CGI': 100, 'MAI': 100}
        weights = {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}
        result = geometric_mean_weighted(scores, weights)
        # 0점이 1점으로 처리되어 전체가 0이 되지 않음
        assert result > 0

    def test_uniform_scores(self):
        """균일 점수"""
        scores = {'CEI': 80, 'RII': 80, 'CGI': 80, 'MAI': 80}
        weights = {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}
        result = geometric_mean_weighted(scores, weights)
        # 균일하면 기하평균 = 산술평균
        assert abs(result - 80) < 1

    def test_missing_key(self):
        """키 누락"""
        scores = {'CEI': 80, 'RII': 80}
        weights = {'CEI': 0.25, 'RII': 0.25, 'CGI': 0.25, 'MAI': 0.25}
        result = geometric_mean_weighted(scores, weights)
        # CGI, MAI 누락 → 해당 가중치 제외하고 계산
        assert result > 0


class TestArithmeticMeanWeighted:
    """arithmetic_mean_weighted 테스트 (v2.1 호환용)"""

    def test_basic_calculation(self):
        """기본 계산"""
        scores = {'CEI': 80, 'RII': 60, 'CGI': 70, 'MAI': 90}
        weights = {'CEI': 0.20, 'RII': 0.35, 'CGI': 0.25, 'MAI': 0.20}
        result = arithmetic_mean_weighted(scores, weights)
        expected = 80*0.2 + 60*0.35 + 70*0.25 + 90*0.2
        assert abs(result - expected) < 0.1


class TestSafeDivide:
    """safe_divide 테스트"""

    def test_normal_division(self):
        """정상 나눗셈"""
        assert safe_divide(10, 2) == 5

    def test_zero_denominator(self):
        """0으로 나누기"""
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=999) == 999

    def test_none_values(self):
        """None 값"""
        assert safe_divide(None, 5) == 0.0
        assert safe_divide(10, None) == 0.0


class TestSafeCagr:
    """safe_cagr 테스트"""

    def test_normal_cagr(self):
        """정상 CAGR 계산"""
        # 1000억 → 1331억 (3년, 10% CAGR)
        # MIN_DENOMINATOR = 1억 (100_000_000) 이상인 값으로 테스트
        result = safe_cagr(1000e8, 1331e8, 3)  # 1000억 → 1331억
        assert abs(result - 10.0) < 0.5

    def test_zero_start(self):
        """시작값 0 (폭발 방지)"""
        result = safe_cagr(0, 1000e8, 3)
        assert result == 0.0

    def test_tiny_start(self):
        """극소값 시작 (폭발 방지)"""
        # MIN_DENOMINATOR (1억 = 100_000_000) 미만
        result = safe_cagr(1000, 1000e8, 3)  # 1000원 → 1000억원
        assert result == 0.0

    def test_negative_values(self):
        """음수값 (처리 불가)"""
        result = safe_cagr(-1000e8, 1000e8, 3)
        assert result == 0.0


class TestSafeGrowthRate:
    """safe_growth_rate 테스트"""

    def test_normal_growth(self):
        """정상 성장률"""
        # MIN_DENOMINATOR (1억) 이상인 값으로 테스트
        early = [100e8, 110e8]  # 100억, 110억
        late = [150e8, 160e8]   # 150억, 160억
        # 평균: 105억 → 155억, 성장률 약 47.6%
        result = safe_growth_rate(early, late)
        assert abs(result - 47.6) < 1

    def test_tiny_early_value(self):
        """극소 초기값 (폭발 방지)"""
        early = [1000, 2000]  # 극소 (1억 미만)
        late = [1000e8, 2000e8]  # 엄청 큼
        result = safe_growth_rate(early, late)
        # 폭발하지 않고 상한으로 제한
        assert result == 500.0  # CLAMP_LIMITS['capex_growth']['max']

    def test_abs_for_capex(self):
        """CAPEX 음수 절대값 처리"""
        # MIN_DENOMINATOR (1억) 이상인 값으로 테스트
        early = [-100e8, -110e8]  # CAPEX는 음수로 기록되기도 함
        late = [-150e8, -160e8]
        result = safe_growth_rate(early, late, use_abs=True)
        assert result > 0


class TestBugPrevention:
    """⭐ -999% 버그 방지 통합 테스트"""

    def test_extreme_investment_gap_prevention(self):
        """극단적 투자괴리율 방지"""
        # 시나리오: CAPEX 0.001억 → 100억 (999,900% 증가)
        # 현금은 그대로 → 현금 CAGR 0%
        # 투자괴리율 = 0% - 999,900% = -999,900%

        # clamp로 방지
        extreme_gap = 0 - 999900
        result = clamp(extreme_gap, 'investment_gap')
        assert result == -100.0  # -100%로 제한

    def test_extreme_capex_growth_prevention(self):
        """극단적 CAPEX 성장률 방지"""
        # 99,900% → 500%로 제한
        result = clamp(99900, 'capex_growth')
        assert result == 500.0

    def test_safe_growth_with_tiny_base(self):
        """극소 기준값으로 성장률 계산"""
        # MIN_DENOMINATOR = 1억 (100_000_000)
        # 0.1억 미만 → 100억
        early = [10000000]  # 0.1억 (1천만원) - MIN_DENOMINATOR 미만
        late = [10000000000]  # 100억

        result = safe_growth_rate(early, late)
        # MIN_DENOMINATOR (1억) 체크로 폭발 방지
        # 0.1억 < 1억 이므로 상한으로 반환
        assert result == 500.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
