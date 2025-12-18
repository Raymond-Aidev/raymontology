"""
Raymontology 엔티티 정의

Layer 0: 주체 (Company, Officer, Fund)
Layer 1: 금융 (ConvertibleBond, Transaction)
Layer 2: 리스크 (InformationAsymmetry, PowerAsymmetry, RelationalRiskSignal)
"""
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import OntologyObject, generate_object_id


# ============================================================================
# Layer 0: 주체 (Actors)
# ============================================================================

class Company(OntologyObject):
    """
    기업 엔티티

    상장사, 비상장사 모두 포함
    """
    object_type: str = Field(default="Company")

    # 기본 정보
    company_name: str
    stock_code: Optional[str] = None  # 상장사만
    business_number: Optional[str] = None

    # 분류
    industry: Optional[str] = None
    market: Optional[str] = None  # KOSPI, KOSDAQ, KONEX, 비상장

    # 재무
    market_cap: Optional[float] = None
    revenue: Optional[float] = None

    # 리스크 지표
    ownership_concentration: Optional[float] = None  # 소유 집중도
    affiliate_transaction_ratio: Optional[float] = None  # 특수관계자 거래 비율

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("COMP")


class Officer(OntologyObject):
    """
    임원 엔티티

    등기임원, 사외이사, 감사 등
    """
    object_type: str = Field(default="Officer")

    # 기본 정보
    name: str
    name_en: Optional[str] = None
    resident_number_hash: Optional[str] = None  # 해시값만 저장

    # 직위
    position: str  # 대표이사, 사내이사, 사외이사, 감사 등
    current_company_id: Optional[str] = None

    # 경력
    career_history: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)

    # 네트워크 지표
    board_count: int = Field(default=0)  # 겸직 이사회 수
    network_centrality: Optional[float] = None  # 네트워크 중심성

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("OFFR")


class Fund(OntologyObject):
    """
    펀드 엔티티

    사모펀드, 공모펀드, VC 등
    """
    object_type: str = Field(default="Fund")

    # 기본 정보
    fund_name: str
    fund_type: str  # 사모, 공모, VC, PE 등
    registration_number: Optional[str] = None

    # 운용
    manager_company_id: Optional[str] = None
    aum: Optional[float] = None  # Assets Under Management

    # 투자 전략
    investment_strategy: Optional[str] = None
    target_industries: List[str] = Field(default_factory=list)

    # 리스크 지표
    related_party_investments: int = Field(default=0)  # 특수관계자 투자 건수

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("FUND")


# ============================================================================
# Layer 1: 금융 (Financial Instruments)
# ============================================================================

class ConvertibleBond(OntologyObject):
    """
    전환사채 (CB)

    핵심 착취 도구
    """
    object_type: str = Field(default="ConvertibleBond")

    # 기본 정보
    issuer_company_id: str
    issue_date: datetime
    maturity_date: datetime

    # 조건
    face_value: float
    interest_rate: float
    conversion_price: float
    conversion_ratio: float

    # 전환 이력
    converted_amount: float = Field(default=0.0)
    remaining_amount: float

    # 리스크 지표
    dilution_risk: Optional[float] = None  # 희석 리스크
    below_market_conversion: bool = Field(default=False)  # 시가 이하 전환가

    # 소유자
    holder_ids: List[str] = Field(default_factory=list)  # Fund, Officer 등

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("CB")


class Transaction(OntologyObject):
    """
    거래 이벤트

    주식 거래, CB 발행, 배정 등
    """
    object_type: str = Field(default="Transaction")

    # 기본 정보
    transaction_type: str  # 주식매매, CB발행, 유상증자, M&A 등
    transaction_date: datetime

    # 당사자
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    target_company_id: Optional[str] = None

    # 금액
    amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None

    # 리스크 플래그
    is_related_party: bool = Field(default=False)  # 특수관계자 거래
    price_fairness_score: Optional[float] = None  # 가격 공정성 점수

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("TXN")


# ============================================================================
# Layer 2: 리스크 (Risk Signals)
# ============================================================================

class RiskLevel(str, Enum):
    """리스크 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InformationAsymmetry(OntologyObject):
    """
    정보 비대칭

    내부자와 외부자 간 정보 격차
    """
    object_type: str = Field(default="InformationAsymmetry")

    # 대상
    subject_company_id: str

    # 정보 우위자
    informed_party_ids: List[str] = Field(default_factory=list)  # Officer, Fund 등

    # 지표
    asymmetry_score: float = Field(ge=0.0, le=1.0)  # 0=대칭, 1=극심한 비대칭
    information_type: str  # 실적, M&A, 구조조정, CB발행 등

    # 시간
    detected_at: datetime = Field(default_factory=datetime.now)
    materialized_at: Optional[datetime] = None  # 정보가 공개된 시점

    # 피해
    retail_investor_loss: Optional[float] = None  # 추정 개미 손실액

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("IASYM")


class PowerAsymmetry(OntologyObject):
    """
    권력 비대칭

    의사결정 권한의 불균형
    """
    object_type: str = Field(default="PowerAsymmetry")

    # 대상
    subject_company_id: str

    # 권력자
    dominant_party_ids: List[str] = Field(default_factory=list)

    # 지표
    power_score: float = Field(ge=0.0, le=1.0)  # 0=분산, 1=독재
    control_mechanism: str  # 지배구조, 의결권, 이사회 등

    # 증거
    board_independence_ratio: Optional[float] = None  # 사외이사 비율
    largest_shareholder_ratio: Optional[float] = None  # 최대주주 지분율

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("PASYM")


class RelationalRiskSignal(OntologyObject):
    """
    관계형 리스크 신호

    Raymontology의 핵심: 관계망에서 패턴 탐지
    """
    object_type: str = Field(default="RelationalRiskSignal")

    # 패턴 정보
    pattern_type: str  # "circular_cb", "pump_dump", "related_party_loop" 등
    risk_level: RiskLevel

    # 관련 엔티티
    involved_object_ids: List[str] = Field(default_factory=list)
    involved_link_ids: List[str] = Field(default_factory=list)

    # 점수
    exploitation_probability: float = Field(ge=0.0, le=1.0)
    expected_retail_loss: Optional[float] = None

    # 설명
    description: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

    # 상태
    status: str = Field(default="detected")  # detected, investigating, confirmed, false_positive

    def __init__(self, **data):
        super().__init__(**data)
        self.object_id = generate_object_id("RISK")
