"""
RaymondsIndex v3.0 데이터 검증기

목적:
- 계산 전 데이터 품질 검증
- 이상치 탐지 및 경고
- 계산 가능 여부 판단
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .constants import MIN_REQUIRED_YEARS, MIN_DENOMINATOR


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    can_calculate: bool
    quality_score: float  # 0-100
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    data_years: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'can_calculate': self.can_calculate,
            'quality_score': self.quality_score,
            'errors': self.errors,
            'warnings': self.warnings,
            'missing_fields': self.missing_fields,
            'data_years': self.data_years,
        }


class DataValidator:
    """
    재무 데이터 검증기

    검증 항목:
    1. 필수 필드 존재 여부
    2. 최소 연도 수 충족 여부
    3. 값 범위 유효성
    4. 분모 극소값 경고 (-999% 버그 원인)
    5. 데이터 일관성
    """

    # 필수 필드 (최소한 이 필드들이 있어야 계산 가능)
    REQUIRED_FIELDS = [
        'revenue',
        'operating_income',
        'net_income',
        'total_assets',
        'operating_cash_flow',
        'capex',
    ]

    # 권장 필드 (있으면 더 정확한 계산)
    RECOMMENDED_FIELDS = [
        'cash_and_equivalents',
        'short_term_investments',
        'tangible_assets',
        'total_equity',
        'total_liabilities',
        'dividend_paid',
    ]

    def __init__(self, min_years: int = MIN_REQUIRED_YEARS):
        self.min_years = min_years

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        재무 데이터 검증

        Args:
            data: 재무 데이터 딕셔너리
                  - 단일 값 또는 리스트 형태 지원
                  - 리스트: 연도별 데이터 [2022, 2023, 2024]

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        missing_fields = []
        data_years = 0

        # 1. 필수 필드 검증
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data or data[field_name] is None:
                errors.append(f"필수 필드 누락: {field_name}")
                missing_fields.append(field_name)
            elif isinstance(data[field_name], list):
                if len(data[field_name]) == 0:
                    errors.append(f"필수 필드 비어있음: {field_name}")
                    missing_fields.append(field_name)
                elif all(v is None for v in data[field_name]):
                    errors.append(f"필수 필드 모든 값이 None: {field_name}")
                    missing_fields.append(field_name)

        # 2. 권장 필드 검증
        for field_name in self.RECOMMENDED_FIELDS:
            if field_name not in data or data[field_name] is None:
                warnings.append(f"권장 필드 누락: {field_name}")
                missing_fields.append(field_name)

        # 3. 연도 수 검증
        if 'revenue' in data and isinstance(data['revenue'], list):
            valid_revenues = [v for v in data['revenue'] if v is not None]
            data_years = len(valid_revenues)
            if data_years < self.min_years:
                errors.append(f"최소 {self.min_years}년 데이터 필요 (현재: {data_years}년)")

        # 4. 값 범위 검증
        self._validate_value_ranges(data, errors, warnings)

        # 5. 분모 극소값 경고 (⭐ -999% 버그 원인)
        self._validate_denominators(data, warnings)

        # 6. 데이터 일관성 검증
        self._validate_consistency(data, warnings)

        # 품질 점수 계산
        quality_score = self._calculate_quality_score(errors, warnings, missing_fields)

        return ValidationResult(
            is_valid=len(errors) == 0,
            can_calculate=len(errors) == 0 and quality_score >= 40,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            data_years=data_years,
        )

    def _validate_value_ranges(
        self,
        data: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """값 범위 검증"""
        # 총자산은 양수여야 함
        if 'total_assets' in data:
            assets = data['total_assets']
            if isinstance(assets, list):
                if any(v is not None and v < 0 for v in assets):
                    errors.append("총자산이 음수입니다")
            elif assets is not None and assets < 0:
                errors.append("총자산이 음수입니다")

        # 매출은 음수가 아니어야 함 (대부분의 경우)
        if 'revenue' in data:
            revenue = data['revenue']
            if isinstance(revenue, list):
                if any(v is not None and v < 0 for v in revenue):
                    warnings.append("매출이 음수입니다 (특수한 경우가 아니면 확인 필요)")
            elif revenue is not None and revenue < 0:
                warnings.append("매출이 음수입니다")

    def _validate_denominators(
        self,
        data: Dict[str, Any],
        warnings: List[str]
    ) -> None:
        """
        분모 극소값 경고 (⭐ -999% 버그 원인)

        CAPEX, 현금 등 성장률 계산에 사용되는 값이 극소값이면
        성장률이 폭발적으로 커질 수 있음
        """
        # CAPEX 초기값 검증
        if 'capex' in data and isinstance(data['capex'], list):
            capex_values = data['capex']
            if len(capex_values) >= 2:
                early_capex = capex_values[:2]
                valid_early = [abs(c) for c in early_capex if c is not None]
                if valid_early:
                    avg_early = sum(valid_early) / len(valid_early)
                    if avg_early < MIN_DENOMINATOR:
                        warnings.append(
                            f"초기 CAPEX가 {MIN_DENOMINATOR/1e8:.0f}억 미만 "
                            f"({avg_early/1e8:.2f}억) - 성장률 신뢰도 낮음"
                        )

        # 현금 초기값 검증
        cash_fields = ['cash_and_equivalents', 'total_cash']
        for field_name in cash_fields:
            if field_name in data and isinstance(data[field_name], list):
                cash_values = data[field_name]
                if len(cash_values) >= 2:
                    early_cash = cash_values[0]
                    if early_cash is not None and early_cash < MIN_DENOMINATOR:
                        warnings.append(
                            f"초기 현금이 {MIN_DENOMINATOR/1e8:.0f}억 미만 "
                            f"({early_cash/1e8:.2f}억) - CAGR 신뢰도 낮음"
                        )

    def _validate_consistency(
        self,
        data: Dict[str, Any],
        warnings: List[str]
    ) -> None:
        """데이터 일관성 검증"""
        # 자산회전율 비정상 체크
        if ('total_assets' in data and 'revenue' in data):
            assets = data['total_assets']
            revenue = data['revenue']

            if isinstance(assets, list) and isinstance(revenue, list):
                if assets[-1] and assets[-1] > 0 and revenue[-1]:
                    turnover = revenue[-1] / assets[-1]
                    if turnover > 10:
                        warnings.append(
                            f"자산회전율이 비정상적으로 높음 ({turnover:.1f}회)"
                        )
            elif assets and assets > 0 and revenue:
                turnover = revenue / assets
                if turnover > 10:
                    warnings.append(
                        f"자산회전율이 비정상적으로 높음 ({turnover:.1f}회)"
                    )

        # 영업이익 > 매출 체크 (비정상)
        if ('operating_income' in data and 'revenue' in data):
            oi = data['operating_income']
            rev = data['revenue']

            if isinstance(oi, list) and isinstance(rev, list):
                latest_oi = oi[-1] if oi else 0
                latest_rev = rev[-1] if rev else 0
                if latest_oi and latest_rev and latest_oi > latest_rev:
                    warnings.append("영업이익이 매출보다 큼 (데이터 확인 필요)")

    def _calculate_quality_score(
        self,
        errors: List[str],
        warnings: List[str],
        missing_fields: List[str]
    ) -> float:
        """
        데이터 품질 점수 계산

        기준:
        - 에러 1개당 -25점
        - 경고 1개당 -5점
        - 누락 필드 1개당 -3점 (최대 -30점)
        """
        score = 100.0

        # 에러 감점
        score -= len(errors) * 25

        # 경고 감점
        score -= len(warnings) * 5

        # 누락 필드 감점 (최대 30점)
        missing_penalty = min(len(missing_fields) * 3, 30)
        score -= missing_penalty

        return max(0, min(100, score))

    def validate_for_calculation(self, financial_data: List[Dict]) -> ValidationResult:
        """
        계산용 재무 데이터 리스트 검증

        Args:
            financial_data: 연도별 재무 데이터 리스트
                          [{'fiscal_year': 2022, 'revenue': 1000, ...}, ...]

        Returns:
            ValidationResult
        """
        if not financial_data:
            return ValidationResult(
                is_valid=False,
                can_calculate=False,
                quality_score=0,
                errors=["재무 데이터가 비어있습니다"],
                data_years=0,
            )

        # 리스트 형태로 변환
        data_dict = self._convert_to_list_format(financial_data)

        return self.validate(data_dict)

    def _convert_to_list_format(self, financial_data: List[Dict]) -> Dict[str, List]:
        """
        연도별 데이터 리스트를 필드별 리스트로 변환

        [{'revenue': 100, 'capex': 10}, {'revenue': 110, 'capex': 12}]
        →
        {'revenue': [100, 110], 'capex': [10, 12]}
        """
        if not financial_data:
            return {}

        # 모든 필드 수집
        all_fields = set()
        for record in financial_data:
            all_fields.update(record.keys())

        # 필드별 리스트 생성
        result = {}
        for field_name in all_fields:
            result[field_name] = [record.get(field_name) for record in financial_data]

        return result
