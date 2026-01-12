"""
기업 유형 필터링 유틸리티

SPAC, ETF, 리츠 등 특수 유형 기업을 파싱/계산 대상에서 제외하기 위한 유틸리티.

사용 예시:
    from scripts.utils.company_filter import should_parse_officers, get_excluded_reason

    for company in companies:
        if not should_parse_officers(company):
            reason = get_excluded_reason(company)
            logger.info(f"Skipped {company['name']}: {reason}")
            continue
        # 파싱 진행...
"""

from typing import Dict, Any, Optional, Set

# 기업 유형별 제외 대상 정의
EXCLUDED_FROM_OFFICER_PARSING: Set[str] = {'SPAC', 'REIT', 'ETF'}
EXCLUDED_FROM_SHAREHOLDER_PARSING: Set[str] = {'ETF'}
EXCLUDED_FROM_INDEX_CALCULATION: Set[str] = {'SPAC', 'REIT', 'ETF'}
EXCLUDED_FROM_FINANCIAL_PARSING: Set[str] = {'SPAC', 'ETF'}

# 제외 사유 메시지
EXCLUSION_REASONS: Dict[str, str] = {
    'SPAC': 'SPAC은 합병 전 껍데기 회사로 데이터가 의미 없음',
    'REIT': '리츠/인프라펀드는 별도 분석 체계 필요',
    'ETF': 'ETF는 펀드 상품으로 개별 기업 분석 대상 아님',
    'HOLDING': '지주회사는 연결재무제표 기준 별도 분석',
    'FINANCIAL': '금융업은 별도 재무구조로 분석 방법 상이',
}


def get_company_type(company: Dict[str, Any]) -> str:
    """기업 유형 반환 (DB 값 또는 이름 기반 추론)"""
    # DB에 company_type이 있으면 사용
    if company.get('company_type'):
        return company['company_type']

    # 레거시: 이름 기반 추론 (DB 마이그레이션 전 호환성)
    name = company.get('name', '').upper()
    if '스팩' in name or 'SPAC' in name:
        return 'SPAC'
    if '리츠' in name or '인프라' in name:
        return 'REIT'
    if company.get('market') == 'ETF':
        return 'ETF'

    return 'NORMAL'


def should_parse_officers(company: Dict[str, Any]) -> bool:
    """임원 파싱 대상인지 확인

    Args:
        company: 기업 정보 딕셔너리 (company_type 또는 name 포함)

    Returns:
        True: 파싱 대상, False: 파싱 제외
    """
    company_type = get_company_type(company)
    return company_type not in EXCLUDED_FROM_OFFICER_PARSING


def should_parse_shareholders(company: Dict[str, Any]) -> bool:
    """대주주 파싱 대상인지 확인

    Args:
        company: 기업 정보 딕셔너리

    Returns:
        True: 파싱 대상, False: 파싱 제외
    """
    company_type = get_company_type(company)
    return company_type not in EXCLUDED_FROM_SHAREHOLDER_PARSING


def should_parse_financials(company: Dict[str, Any]) -> bool:
    """재무 데이터 파싱 대상인지 확인

    Args:
        company: 기업 정보 딕셔너리

    Returns:
        True: 파싱 대상, False: 파싱 제외
    """
    company_type = get_company_type(company)
    return company_type not in EXCLUDED_FROM_FINANCIAL_PARSING


def should_calculate_index(company: Dict[str, Any]) -> bool:
    """RaymondsIndex 계산 대상인지 확인

    Args:
        company: 기업 정보 딕셔너리

    Returns:
        True: 계산 대상, False: 계산 제외
    """
    company_type = get_company_type(company)
    return company_type not in EXCLUDED_FROM_INDEX_CALCULATION


def get_excluded_reason(company: Dict[str, Any]) -> Optional[str]:
    """제외 사유 반환 (로깅용)

    Args:
        company: 기업 정보 딕셔너리

    Returns:
        제외 사유 문자열, 제외 대상 아니면 None
    """
    company_type = get_company_type(company)
    return EXCLUSION_REASONS.get(company_type)


def get_filter_sql_clause(
    column_name: str = 'company_type',
    exclude_types: Optional[Set[str]] = None
) -> str:
    """SQL WHERE 절 생성

    Args:
        column_name: 컬럼명 (기본: company_type)
        exclude_types: 제외할 유형 집합 (기본: 임원 파싱 제외 대상)

    Returns:
        SQL WHERE 절 문자열

    Example:
        >>> get_filter_sql_clause()
        "company_type NOT IN ('SPAC', 'REIT', 'ETF')"
    """
    if exclude_types is None:
        exclude_types = EXCLUDED_FROM_OFFICER_PARSING

    types_str = ', '.join(f"'{t}'" for t in sorted(exclude_types))
    return f"{column_name} NOT IN ({types_str})"


# 편의 함수: 필터링된 기업 목록 반환
def filter_companies(
    companies: list,
    filter_func=should_parse_officers
) -> tuple:
    """기업 목록에서 대상/제외 분리

    Args:
        companies: 기업 딕셔너리 목록
        filter_func: 필터링 함수 (기본: should_parse_officers)

    Returns:
        (대상 기업 목록, 제외 기업 목록) 튜플
    """
    included = []
    excluded = []

    for company in companies:
        if filter_func(company):
            included.append(company)
        else:
            excluded.append(company)

    return included, excluded
