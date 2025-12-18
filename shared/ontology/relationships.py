"""
Raymontology 관계 타입 및 가중치

관계도 1급 시민 (Relationship as First-Class Citizen)
"""
from enum import Enum
from typing import Dict


class RelationshipType(str, Enum):
    """
    관계 타입 35개

    팔란티어 온톨로지: 관계가 엔티티만큼 중요
    """

    # ========================================
    # Category 1: 고용/직위 (10개)
    # ========================================
    EMPLOYED_BY = "employed_by"  # Officer → Company
    EXECUTIVE_OF = "executive_of"  # Officer → Company (임원)
    DIRECTOR_OF = "director_of"  # Officer → Company (이사)
    OUTSIDE_DIRECTOR_OF = "outside_director_of"  # Officer → Company (사외이사)
    AUDITOR_OF = "auditor_of"  # Officer → Company (감사)

    FORMERLY_EMPLOYED_BY = "formerly_employed_by"  # 전직
    BOARD_MEMBER_OF = "board_member_of"  # 이사회 멤버
    FOUNDING_MEMBER_OF = "founding_member_of"  # 창립 멤버
    SHADOW_DIRECTOR_OF = "shadow_director_of"  # 실질적 지배자
    REPRESENTS = "represents"  # 대표

    # ========================================
    # Category 2: 소유/지분 (8개)
    # ========================================
    OWNS_SHARES_IN = "owns_shares_in"  # Fund/Officer → Company
    MAJOR_SHAREHOLDER_OF = "major_shareholder_of"  # 대주주
    CONTROLLING_SHAREHOLDER_OF = "controlling_shareholder_of"  # 지배주주
    BENEFICIAL_OWNER_OF = "beneficial_owner_of"  # 실소유주

    OWNS_CB_IN = "owns_cb_in"  # Fund/Officer → Company (전환사채)
    CONVERTED_CB_TO_SHARES = "converted_cb_to_shares"  # CB 전환
    DILUTED_BY = "diluted_by"  # 희석 당함
    ACQUIRED_SHARES_FROM = "acquired_shares_from"  # 주식 매입

    # ========================================
    # Category 3: 펀드 관련 (5개)
    # ========================================
    MANAGES_FUND = "manages_fund"  # Company/Officer → Fund
    INVESTED_IN = "invested_in"  # Fund → Company
    CO_INVESTED_WITH = "co_invested_with"  # Fund ↔ Fund (동반 투자)
    ALLOCATED_TO = "allocated_to"  # Company → Fund (배정)
    RECEIVED_INVESTMENT_FROM = "received_investment_from"  # Company ← Fund

    # ========================================
    # Category 4: 특수관계 (7개)
    # ========================================
    FAMILY_RELATION = "family_relation"  # 가족 관계
    CROSS_SHAREHOLDING = "cross_shareholding"  # 순환 출자
    AFFILIATE_OF = "affiliate_of"  # 계열사
    RELATED_PARTY_TRANSACTION = "related_party_transaction"  # 특수관계자 거래

    CIRCULAR_INVESTMENT = "circular_investment"  # 순환 투자
    SHELL_COMPANY_FOR = "shell_company_for"  # 페이퍼컴퍼니
    PROXY_FOR = "proxy_for"  # 대리인

    # ========================================
    # Category 5: 리스크 신호 (5개)
    # ========================================
    EXPLOITED = "exploited"  # 착취 관계
    INFORMATION_ADVANTAGE_OVER = "information_advantage_over"  # 정보 우위
    POWER_ADVANTAGE_OVER = "power_advantage_over"  # 권력 우위
    COLLUSION_WITH = "collusion_with"  # 담합
    SUSPICIOUS_TRANSACTION_WITH = "suspicious_transaction_with"  # 의심 거래


# ============================================================================
# 착취 가능성 가중치
# ============================================================================

EXPLOITATION_WEIGHTS: Dict[RelationshipType, float] = {
    # 고용/직위 - 낮음~중간
    RelationshipType.EMPLOYED_BY: 0.1,
    RelationshipType.EXECUTIVE_OF: 0.3,
    RelationshipType.DIRECTOR_OF: 0.4,
    RelationshipType.OUTSIDE_DIRECTOR_OF: 0.2,  # 사외이사는 견제 역할
    RelationshipType.AUDITOR_OF: 0.2,
    RelationshipType.FORMERLY_EMPLOYED_BY: 0.15,
    RelationshipType.BOARD_MEMBER_OF: 0.35,
    RelationshipType.FOUNDING_MEMBER_OF: 0.5,
    RelationshipType.SHADOW_DIRECTOR_OF: 0.9,  # 실질 지배자 = 위험
    RelationshipType.REPRESENTS: 0.6,

    # 소유/지분 - 중간~높음
    RelationshipType.OWNS_SHARES_IN: 0.3,
    RelationshipType.MAJOR_SHAREHOLDER_OF: 0.6,
    RelationshipType.CONTROLLING_SHAREHOLDER_OF: 0.8,
    RelationshipType.BENEFICIAL_OWNER_OF: 0.85,
    RelationshipType.OWNS_CB_IN: 0.7,  # CB는 착취 도구
    RelationshipType.CONVERTED_CB_TO_SHARES: 0.75,
    RelationshipType.DILUTED_BY: 0.6,
    RelationshipType.ACQUIRED_SHARES_FROM: 0.4,

    # 펀드 관련 - 중간
    RelationshipType.MANAGES_FUND: 0.5,
    RelationshipType.INVESTED_IN: 0.4,
    RelationshipType.CO_INVESTED_WITH: 0.45,
    RelationshipType.ALLOCATED_TO: 0.55,
    RelationshipType.RECEIVED_INVESTMENT_FROM: 0.4,

    # 특수관계 - 높음
    RelationshipType.FAMILY_RELATION: 0.7,
    RelationshipType.CROSS_SHAREHOLDING: 0.85,
    RelationshipType.AFFILIATE_OF: 0.6,
    RelationshipType.RELATED_PARTY_TRANSACTION: 0.75,
    RelationshipType.CIRCULAR_INVESTMENT: 0.9,
    RelationshipType.SHELL_COMPANY_FOR: 0.95,
    RelationshipType.PROXY_FOR: 0.8,

    # 리스크 신호 - 매우 높음
    RelationshipType.EXPLOITED: 1.0,
    RelationshipType.INFORMATION_ADVANTAGE_OVER: 0.85,
    RelationshipType.POWER_ADVANTAGE_OVER: 0.9,
    RelationshipType.COLLUSION_WITH: 0.95,
    RelationshipType.SUSPICIOUS_TRANSACTION_WITH: 0.8,
}


# ============================================================================
# 관계 조합 패턴 (리스크 증폭)
# ============================================================================

RISK_AMPLIFICATION_PATTERNS = {
    # 임원 + CB 소유 = 위험
    ("executive_of", "owns_cb_in"): 1.5,

    # 대주주 + 사외이사 = 독립성 의심
    ("major_shareholder_of", "outside_director_of"): 1.3,

    # 펀드 운용 + CB 배정 = 이해 충돌
    ("manages_fund", "allocated_to"): 1.6,

    # 순환 출자 + 특수관계자 거래 = 극심한 위험
    ("cross_shareholding", "related_party_transaction"): 2.0,

    # 가족 관계 + 지배주주 = 일가 지배
    ("family_relation", "controlling_shareholder_of"): 1.8,

    # 실질 지배 + 페이퍼컴퍼니 = 자금 세탁 의심
    ("shadow_director_of", "shell_company_for"): 2.5,
}


# ============================================================================
# 관계 설명
# ============================================================================

RELATIONSHIP_DESCRIPTIONS: Dict[RelationshipType, str] = {
    RelationshipType.EMPLOYED_BY: "일반 직원으로 고용됨",
    RelationshipType.EXECUTIVE_OF: "임원으로 재직 중",
    RelationshipType.DIRECTOR_OF: "사내이사로 재직 중",
    RelationshipType.OUTSIDE_DIRECTOR_OF: "사외이사로 재직 중 (독립성 필요)",
    RelationshipType.AUDITOR_OF: "감사로 재직 중 (감시 역할)",
    RelationshipType.FORMERLY_EMPLOYED_BY: "과거 재직했던 이력",
    RelationshipType.BOARD_MEMBER_OF: "이사회 구성원",
    RelationshipType.FOUNDING_MEMBER_OF: "창립 멤버 (역사적 권한)",
    RelationshipType.SHADOW_DIRECTOR_OF: "실질적 지배자 (위험 신호)",
    RelationshipType.REPRESENTS: "법적 대표자",

    RelationshipType.OWNS_SHARES_IN: "주식 소유",
    RelationshipType.MAJOR_SHAREHOLDER_OF: "대주주 (5% 이상)",
    RelationshipType.CONTROLLING_SHAREHOLDER_OF: "지배주주 (의사결정 권한)",
    RelationshipType.BENEFICIAL_OWNER_OF: "실소유주 (명의 신탁 의심)",
    RelationshipType.OWNS_CB_IN: "전환사채 보유 (착취 도구)",
    RelationshipType.CONVERTED_CB_TO_SHARES: "CB를 주식으로 전환 (희석 발생)",
    RelationshipType.DILUTED_BY: "지분 희석 당함 (피해자)",
    RelationshipType.ACQUIRED_SHARES_FROM: "주식 매입",

    RelationshipType.MANAGES_FUND: "펀드 운용",
    RelationshipType.INVESTED_IN: "투자",
    RelationshipType.CO_INVESTED_WITH: "공동 투자 (담합 의심)",
    RelationshipType.ALLOCATED_TO: "우선 배정 (특혜 의심)",
    RelationshipType.RECEIVED_INVESTMENT_FROM: "투자 유치",

    RelationshipType.FAMILY_RELATION: "가족 관계 (일가 지배)",
    RelationshipType.CROSS_SHAREHOLDING: "순환 출자 (불법 의심)",
    RelationshipType.AFFILIATE_OF: "계열사 관계",
    RelationshipType.RELATED_PARTY_TRANSACTION: "특수관계자 거래 (공정성 의심)",
    RelationshipType.CIRCULAR_INVESTMENT: "순환 투자 (자금 세탁 의심)",
    RelationshipType.SHELL_COMPANY_FOR: "페이퍼컴퍼니 (불법 도구)",
    RelationshipType.PROXY_FOR: "대리인 (실소유 은폐)",

    RelationshipType.EXPLOITED: "착취 관계 확인",
    RelationshipType.INFORMATION_ADVANTAGE_OVER: "정보 우위 (내부자 거래)",
    RelationshipType.POWER_ADVANTAGE_OVER: "권력 우위 (지배 구조)",
    RelationshipType.COLLUSION_WITH: "담합 의심",
    RelationshipType.SUSPICIOUS_TRANSACTION_WITH: "의심스러운 거래",
}


# ============================================================================
# 유틸리티 함수
# ============================================================================

def calculate_relationship_risk(
    relationship_type: RelationshipType,
    source_type: str,
    target_type: str,
    additional_context: Dict = None
) -> float:
    """
    관계의 리스크 점수 계산

    Args:
        relationship_type: 관계 타입
        source_type: 출발 엔티티 타입
        target_type: 도착 엔티티 타입
        additional_context: 추가 컨텍스트 (거래 금액 등)

    Returns:
        0.0 ~ 1.0 사이의 리스크 점수
    """
    base_weight = EXPLOITATION_WEIGHTS.get(relationship_type, 0.5)

    # 컨텍스트 기반 가중치 조정
    if additional_context:
        # 예: 거래 금액이 크면 리스크 증가
        if "transaction_amount" in additional_context:
            amount = additional_context["transaction_amount"]
            if amount > 10_000_000_000:  # 100억 이상
                base_weight *= 1.3
            elif amount > 1_000_000_000:  # 10억 이상
                base_weight *= 1.1

        # 예: 지분율이 높으면 리스크 증가
        if "ownership_ratio" in additional_context:
            ratio = additional_context["ownership_ratio"]
            if ratio > 0.5:  # 50% 이상
                base_weight *= 1.5
            elif ratio > 0.3:  # 30% 이상
                base_weight *= 1.2

    return min(base_weight, 1.0)  # 최대 1.0


def detect_risk_pattern(relationship_chain: list) -> tuple[str, float]:
    """
    관계 체인에서 리스크 패턴 탐지

    Args:
        relationship_chain: [(rel_type, source, target), ...]

    Returns:
        (pattern_name, risk_score)
    """
    if len(relationship_chain) < 2:
        return ("no_pattern", 0.0)

    # 순환 구조 탐지
    entities = []
    for _, source, target in relationship_chain:
        entities.append(source)
        entities.append(target)

    if len(entities) != len(set(entities)):
        # 순환 발견
        rel_types = [rel[0] for rel in relationship_chain]
        if RelationshipType.CROSS_SHAREHOLDING in rel_types:
            return ("circular_shareholding", 0.95)
        elif RelationshipType.CIRCULAR_INVESTMENT in rel_types:
            return ("circular_investment", 0.9)
        else:
            return ("circular_relationship", 0.7)

    # 조합 패턴 탐지
    if len(relationship_chain) >= 2:
        first_rel = relationship_chain[0][0]
        second_rel = relationship_chain[1][0]
        pattern_key = (first_rel.value, second_rel.value)

        if pattern_key in RISK_AMPLIFICATION_PATTERNS:
            amplification = RISK_AMPLIFICATION_PATTERNS[pattern_key]
            base_risk = (
                EXPLOITATION_WEIGHTS[first_rel] +
                EXPLOITATION_WEIGHTS[second_rel]
            ) / 2
            return (f"amplified_{first_rel.value}_{second_rel.value}", base_risk * amplification)

    return ("no_pattern", 0.0)
