"""
RaymondsIndex v3.0 통합 계산기

HDI 정규화 방식 적용 (OECD Handbook 2008, UNDP HDI 2010)

핵심 변경:
- 가중 기하평균 집계 (산술평균 → 기하평균)
- 정규화된 Sub-Index (0-100)
- 범위 제한으로 극단값 방지
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Any, Optional, Tuple

from .constants import (
    SUBINDEX_WEIGHTS,
    GRADE_THRESHOLDS,
    GRADE_ORDER,
    SPECIAL_RULES,
    INDUSTRY_WEIGHT_ADJUSTMENTS,
)
from .normalizers import geometric_mean_weighted, arithmetic_mean_weighted
from .validators import DataValidator, ValidationResult
from .calculators import (
    CEICalculator,
    RIICalculator,
    CGICalculator,
    MAICalculator,
    CalculationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class RaymondsIndexResultV3:
    """RaymondsIndex v3.0 계산 결과"""
    company_id: str
    fiscal_year: int
    status: str = 'SUCCESS'  # SUCCESS, DATA_INSUFFICIENT, ERROR

    # 종합 점수
    total_score: float = 0.0
    grade: str = 'C'

    # Sub-Index 점수 (정규화된 0-100)
    cei_score: float = 0.0
    rii_score: float = 0.0
    cgi_score: float = 0.0
    mai_score: float = 0.0

    # 핵심 지표 (원본값)
    investment_gap: float = 0.0
    cash_cagr: float = 0.0
    capex_growth: float = 0.0

    # 상세 데이터
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
    normalized_metrics: Dict[str, Any] = field(default_factory=dict)

    # 위험 신호
    red_flags: List[str] = field(default_factory=list)
    yellow_flags: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    # 해석
    verdict: str = ''
    key_risk: str = ''
    recommendation: str = ''
    watch_trigger: str = ''

    # 메타데이터
    data_quality_score: float = 0.0
    validation_warnings: List[str] = field(default_factory=list)
    aggregation_method: str = 'geometric_mean'
    algorithm_version: str = 'v3.1'
    calculation_date: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'company_id': self.company_id,
            'fiscal_year': self.fiscal_year,
            'status': self.status,
            'calculation_date': self.calculation_date,
            'total_score': self.total_score,
            'grade': self.grade,
            'cei_score': self.cei_score,
            'rii_score': self.rii_score,
            'cgi_score': self.cgi_score,
            'mai_score': self.mai_score,
            'investment_gap': self.investment_gap,
            'cash_cagr': self.cash_cagr,
            'capex_growth': self.capex_growth,
            'raw_metrics': self.raw_metrics,
            'normalized_metrics': self.normalized_metrics,
            'red_flags': self.red_flags,
            'yellow_flags': self.yellow_flags,
            'violations': self.violations,
            'verdict': self.verdict,
            'key_risk': self.key_risk,
            'recommendation': self.recommendation,
            'watch_trigger': self.watch_trigger,
            'data_quality_score': self.data_quality_score,
            'validation_warnings': self.validation_warnings,
            'aggregation_method': self.aggregation_method,
            'algorithm_version': self.algorithm_version,
        }


class RaymondsIndexCalculatorV3:
    """
    RaymondsIndex v3.0 종합 계산기

    집계 방식: 가중 기하평균 (HDI 방식)

    사용법:
        calculator = RaymondsIndexCalculatorV3()
        result = calculator.calculate(company_id, financial_data)
    """

    def __init__(
        self,
        industry_sector: Optional[str] = None,
        use_geometric_mean: bool = True,
    ):
        """
        Args:
            industry_sector: 업종 (가중치 조정용)
            use_geometric_mean: 기하평균 사용 여부 (False면 산술평균)
        """
        self.industry_sector = industry_sector
        self.use_geometric_mean = use_geometric_mean
        self.weights = self._get_adjusted_weights(industry_sector)

        # 계산기 초기화
        self.validator = DataValidator()
        self.cei_calc = CEICalculator()
        self.rii_calc = RIICalculator()
        self.cgi_calc = CGICalculator()
        self.mai_calc = MAICalculator()

    def _get_adjusted_weights(self, industry_sector: Optional[str]) -> Dict[str, float]:
        """업종별 가중치 조정"""
        weights = SUBINDEX_WEIGHTS.copy()

        if not industry_sector:
            return weights

        for industry_type, config in INDUSTRY_WEIGHT_ADJUSTMENTS.items():
            if industry_sector in config['sectors']:
                for key, adjustment in config['adjustments'].items():
                    if key in weights:
                        weights[key] += adjustment
                break

        return weights

    def calculate(
        self,
        company_id: str,
        financial_data: List[Dict],
        target_year: Optional[int] = None,
    ) -> RaymondsIndexResultV3:
        """
        RaymondsIndex v3.0 계산

        Args:
            company_id: 회사 ID
            financial_data: 연도별 재무 데이터 리스트 (fiscal_year 순 정렬)
            target_year: 계산 대상 연도 (기본: 가장 최근)

        Returns:
            RaymondsIndexResultV3
        """
        # ═══════════════════════════════════════════════════════════════
        # Step 1: 데이터 검증
        # ═══════════════════════════════════════════════════════════════
        validation = self.validator.validate_for_calculation(financial_data)

        if not validation.can_calculate:
            return RaymondsIndexResultV3(
                company_id=company_id,
                fiscal_year=target_year or 0,
                status='DATA_INSUFFICIENT',
                grade='N/A',
                data_quality_score=validation.quality_score,
                validation_warnings=validation.errors + validation.warnings,
            )

        # 연도순 정렬
        sorted_data = sorted(financial_data, key=lambda x: x.get('fiscal_year', 0))

        if target_year is None:
            target_year = sorted_data[-1].get('fiscal_year', 0)

        # 리스트 형태로 변환 (Calculator에서 사용)
        data_dict = self._convert_to_dict_format(sorted_data)

        # ═══════════════════════════════════════════════════════════════
        # Step 2: Sub-Index 계산
        # ═══════════════════════════════════════════════════════════════
        cei_result = self.cei_calc.calculate(data_dict)
        rii_result = self.rii_calc.calculate(data_dict)
        cgi_result = self.cgi_calc.calculate(data_dict)
        mai_result = self.mai_calc.calculate(data_dict)

        sub_scores = {
            'CEI': cei_result.score,
            'RII': rii_result.score,
            'CGI': cgi_result.score,
            'MAI': mai_result.score,
        }

        # ═══════════════════════════════════════════════════════════════
        # Step 3: 종합 점수 계산 (가중 기하평균 또는 산술평균)
        # ═══════════════════════════════════════════════════════════════
        if self.use_geometric_mean:
            total_score = geometric_mean_weighted(sub_scores, self.weights)
            aggregation_method = 'geometric_mean'
        else:
            total_score = arithmetic_mean_weighted(sub_scores, self.weights)
            aggregation_method = 'arithmetic_mean'

        # ═══════════════════════════════════════════════════════════════
        # Step 4: 등급 결정
        # ═══════════════════════════════════════════════════════════════
        grade = self._determine_grade(total_score)

        # ═══════════════════════════════════════════════════════════════
        # Step 5: 특별 규칙 적용 (등급 하향)
        # ═══════════════════════════════════════════════════════════════
        grade, violations = self._apply_special_rules(
            grade, data_dict, rii_result, cgi_result
        )

        # ═══════════════════════════════════════════════════════════════
        # Step 6: 위험 신호 생성
        # ═══════════════════════════════════════════════════════════════
        red_flags, yellow_flags = self._generate_flags(
            rii_result.raw_metrics,
            cgi_result.raw_metrics,
        )

        # ═══════════════════════════════════════════════════════════════
        # Step 7: 해석 생성
        # ═══════════════════════════════════════════════════════════════
        verdict, key_risk, recommendation, watch_trigger = self._generate_interpretation(
            grade, red_flags, yellow_flags, violations
        )

        # ═══════════════════════════════════════════════════════════════
        # Step 8: 결과 생성
        # ═══════════════════════════════════════════════════════════════
        return RaymondsIndexResultV3(
            company_id=company_id,
            fiscal_year=target_year,
            status='SUCCESS',
            total_score=round(total_score, 2),
            grade=grade,
            cei_score=cei_result.score,
            rii_score=rii_result.score,
            cgi_score=cgi_result.score,
            mai_score=mai_result.score,
            investment_gap=rii_result.raw_metrics.get('investment_gap', 0),
            cash_cagr=rii_result.raw_metrics.get('cash_cagr', 0),
            capex_growth=rii_result.raw_metrics.get('capex_growth', 0),
            raw_metrics={
                'CEI': cei_result.raw_metrics,
                'RII': rii_result.raw_metrics,
                'CGI': cgi_result.raw_metrics,
                'MAI': mai_result.raw_metrics,
            },
            normalized_metrics={
                'CEI': cei_result.normalized_metrics,
                'RII': rii_result.normalized_metrics,
                'CGI': cgi_result.normalized_metrics,
                'MAI': mai_result.normalized_metrics,
            },
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            violations=violations,
            verdict=verdict,
            key_risk=key_risk,
            recommendation=recommendation,
            watch_trigger=watch_trigger,
            data_quality_score=validation.quality_score,
            validation_warnings=validation.warnings,
            aggregation_method=aggregation_method,
            algorithm_version='v3.0',
        )

    def _convert_to_dict_format(self, financial_data: List[Dict]) -> Dict[str, List]:
        """연도별 데이터를 필드별 리스트로 변환"""
        if not financial_data:
            return {}

        all_fields = set()
        for record in financial_data:
            all_fields.update(record.keys())

        result = {}
        for field_name in all_fields:
            result[field_name] = [record.get(field_name) for record in financial_data]

        return result

    def _determine_grade(self, score: float) -> str:
        """점수 기반 등급 결정"""
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'C'

    def _apply_special_rules(
        self,
        grade: str,
        data: Dict,
        rii_result: CalculationResult,
        cgi_result: CalculationResult,
    ) -> Tuple[str, List[str]]:
        """특별 규칙 적용 - 등급 강제 하향"""
        violations = []

        def downgrade_to_max(current: str, max_grade: str) -> str:
            current_idx = GRADE_ORDER.index(current)
            max_idx = GRADE_ORDER.index(max_grade)
            return max_grade if current_idx < max_idx else current

        # 규칙 1: 현금/유형자산 비율 > 30:1
        total_cash = self._get_latest_value(data, 'cash_and_equivalents', 0) + \
                     self._get_latest_value(data, 'short_term_investments', 0)
        tangible = self._get_latest_value(data, 'tangible_assets', 1)

        if tangible > 0 and total_cash / tangible > SPECIAL_RULES['cash_tangible_ratio_max']:
            violations.append('CASH_TANGIBLE_RATIO_EXCEEDED')
            grade = downgrade_to_max(grade, 'B-')

        # 규칙 2: 조달자금 전환율 < 30%
        funding_efficiency = cgi_result.raw_metrics.get('funding_efficiency', 100)
        if 0 < funding_efficiency < SPECIAL_RULES['funding_utilization_min']:
            violations.append('FUNDING_UNUTILIZED')
            grade = downgrade_to_max(grade, 'B-')

        # 규칙 3: 유휴현금 > 65% + CAPEX 감소
        idle_config = SPECIAL_RULES['idle_cash_capex_decline']
        idle_cash_ratio = cgi_result.raw_metrics.get('cash_to_assets', 0)
        capex_growth = rii_result.raw_metrics.get('capex_growth', 0)

        if (idle_cash_ratio > idle_config['idle_cash_threshold'] and
            capex_growth < idle_config['capex_growth_threshold']):
            violations.append('IDLE_CASH_WITH_CAPEX_DECLINE')
            grade = downgrade_to_max(grade, 'B')

        # 복합 위반: 2개 이상
        if len(violations) >= 2:
            grade = downgrade_to_max(grade, 'C+')

        return grade, violations

    def _get_latest_value(self, data: Dict, key: str, default: float = 0) -> float:
        """리스트에서 최신 값 추출"""
        value = data.get(key)
        if value is None:
            return default
        if isinstance(value, list):
            for v in reversed(value):
                if v is not None:
                    return float(v)
            return default
        return float(value)

    def _generate_flags(
        self,
        rii_metrics: Dict,
        cgi_metrics: Dict,
    ) -> Tuple[List[str], List[str]]:
        """위험 신호 생성"""
        red_flags = []
        yellow_flags = []

        investment_gap = rii_metrics.get('investment_gap', 0)
        funding_efficiency = cgi_metrics.get('funding_efficiency', 100)
        cash_to_assets = cgi_metrics.get('cash_to_assets', 0)
        reinvestment_rate = rii_metrics.get('reinvestment_rate', 0)

        # Red Flags
        if investment_gap > 40:
            red_flags.append(
                f"투자괴리율 CRITICAL: +{investment_gap:.1f}%p (극심한 현금 축적)"
            )
        elif investment_gap > 25:
            red_flags.append(
                f"투자괴리율 HIGH: +{investment_gap:.1f}%p (현금 축적 > 투자)"
            )

        if 0 < funding_efficiency < 30:
            red_flags.append(
                f"조달자금 미사용: 전환율 {funding_efficiency:.1f}%"
            )

        if reinvestment_rate > 0 and reinvestment_rate < 10:
            red_flags.append(
                f"재투자율 극저: {reinvestment_rate:.1f}%"
            )

        # Yellow Flags
        if 15 < investment_gap <= 25:
            yellow_flags.append(
                f"투자괴리율 주의: +{investment_gap:.1f}%p"
            )

        if cash_to_assets > 40:
            yellow_flags.append(
                f"유휴현금 과다: {cash_to_assets:.1f}%"
            )

        return red_flags, yellow_flags

    def _generate_interpretation(
        self,
        grade: str,
        red_flags: List[str],
        yellow_flags: List[str],
        violations: List[str],
    ) -> Tuple[str, str, str, str]:
        """해석 생성"""
        verdicts = {
            'A++': '투자금을 성실히 사업에 활용하는 모범 기업',
            'A+': '투자금 활용이 우수한 기업',
            'A': '투자금 활용이 양호한 기업',
            'A-': '대체로 양호하나 일부 점검 필요',
            'B+': '투자금 활용 현황 지속 관찰 필요',
            'B': '투자금 활용에 의문점 발생',
            'B-': '투자금 유용 가능성 경고',
            'C+': '투자금 배임 가능성 높음',
            'C': '투자금 배임 의심 - 투자 부적격',
        }
        verdict = verdicts.get(grade, '평가 불가')

        if len(violations) >= 2:
            verdict += ' (복합 위반)'
        elif len(violations) == 1:
            verdict += ' (위반 감지)'

        # 핵심 리스크
        if red_flags:
            key_risk = red_flags[0]
        elif yellow_flags:
            key_risk = yellow_flags[0]
        else:
            key_risk = '주요 리스크 없음'

        # 투자자 권고
        if grade in ['A++', 'A+', 'A', 'A-']:
            recommendation = '장기 보유 적합 - 자본 배분 효율성 우수'
        elif grade in ['B+', 'B']:
            recommendation = '중립 - 분기별 투자 현황 모니터링 권장'
        elif grade == 'B-':
            recommendation = '주의 - 경영진 자본 정책 변화 관찰 필요'
        else:
            recommendation = '매도 검토 - 근본적 자본 배분 문제 존재'

        # 재검토 시점
        if violations:
            watch_trigger = '특별 규칙 해소 시 (투자 확대 또는 현금 활용)'
        elif red_flags:
            watch_trigger = '다음 분기 실적 발표 후'
        else:
            watch_trigger = '다음 사업보고서 발표 시'

        return verdict, key_risk, recommendation, watch_trigger
