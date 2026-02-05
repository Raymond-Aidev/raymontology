"""
EGM (Extraordinary General Meeting) Disclosures Model
임시주주총회 공시 모델

경영분쟁 관련 임시주주총회 공시 정보 저장
"""
from sqlalchemy import Column, String, Boolean, Integer, Date, DateTime, Text, Numeric, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from app.database import Base


class EGMType(str, Enum):
    """임시주주총회 유형"""
    REGULAR = "REGULAR"           # 일반 임시주총
    SPECIAL = "SPECIAL"           # 특별 주주총회
    COURT_ORDERED = "COURT_ORDERED"  # 법원 명령 주총


class DisputeType(str, Enum):
    """경영분쟁 유형"""
    HOSTILE_TAKEOVER = "HOSTILE_TAKEOVER"       # 적대적 M&A
    MANAGEMENT_CONFLICT = "MANAGEMENT_CONFLICT"  # 경영진 갈등
    SHAREHOLDER_ACTIVISM = "SHAREHOLDER_ACTIVISM"  # 주주 행동주의
    PROXY_FIGHT = "PROXY_FIGHT"                 # 위임장 대결
    OTHER = "OTHER"                             # 기타


class ParseStatus(str, Enum):
    """파싱 상태"""
    PENDING = "PENDING"           # 대기
    PARSED = "PARSED"             # 파싱 완료
    MANUAL_REVIEW = "MANUAL_REVIEW"  # 수동 검토 필요
    FAILED = "FAILED"             # 파싱 실패
    SKIPPED = "SKIPPED"           # 건너뜀 (비관련)


class EGMDisclosure(Base):
    """
    임시주주총회 공시 테이블

    disclosures 테이블의 임시주주총회 관련 공시를 분석한 결과 저장
    경영분쟁 여부, 안건 정보, 임원 변동 정보 포함
    """
    __tablename__ = "egm_disclosures"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 공시 메타데이터 (disclosures 테이블 참조)
    disclosure_id = Column(String(50), nullable=False, unique=True, index=True)  # disclosures.rcept_no
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    corp_code = Column(String(8), nullable=False, index=True)
    corp_name = Column(String(200), nullable=True)

    # 임시주주총회 정보
    egm_date = Column(Date, nullable=True)  # 주주총회 개최일
    egm_type = Column(String(30), default=EGMType.REGULAR.value)  # 주총 유형
    disclosure_date = Column(Date, nullable=True)  # 공시일 (rcept_dt)

    # 경영분쟁 분류
    is_dispute_related = Column(Boolean, default=False, index=True)  # 경영분쟁 관련 여부
    dispute_type = Column(String(50), nullable=True)  # 분쟁 유형
    dispute_confidence = Column(Numeric(3, 2), nullable=True)  # 분쟁 판정 신뢰도 (0.00~1.00)
    dispute_keywords = Column(JSONB, default=[])  # 탐지된 키워드 목록

    # 안건 정보
    agenda_items = Column(JSONB, default=[])
    # 형식: [
    #   {
    #     "number": 1,
    #     "title": "이사 선임의 건",
    #     "result": "가결",
    #     "vote_for": "85.3%",
    #     "vote_against": "14.7%"
    #   }
    # ]

    # 임원 변동 정보
    officer_changes = Column(JSONB, default=[])
    # 형식: [
    #   {
    #     "action": "선임",  # "선임", "해임", "사임"
    #     "officer_name": "홍길동",
    #     "position": "사외이사",
    #     "vote_result": "가결 (85.3%)",
    #     "replaced_officer": "김철수"  # 해임/교체 시
    #   }
    # ]

    # 임원 변동 요약
    officers_appointed = Column(Integer, default=0)  # 선임된 임원 수
    officers_dismissed = Column(Integer, default=0)  # 해임된 임원 수

    # 파싱 메타데이터
    raw_content = Column(Text, nullable=True)  # 원문 (디버깅용, 일부만 저장)
    parse_status = Column(String(20), default=ParseStatus.PENDING.value, index=True)
    parse_confidence = Column(Numeric(3, 2), nullable=True)  # 전체 파싱 신뢰도
    parse_errors = Column(JSONB, default=[])  # 파싱 오류 목록
    parse_version = Column(String(10), default="v1.0")  # 파서 버전

    # 수동 검토
    needs_manual_review = Column(Boolean, default=False, index=True)
    manual_review_reason = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(100), nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    dispute_officers = relationship("DisputeOfficer", back_populates="egm_disclosure")

    # 인덱스
    __table_args__ = (
        Index('idx_egm_disclosures_dispute', 'is_dispute_related'),
        Index('idx_egm_disclosures_egm_date', 'egm_date'),
        Index('idx_egm_disclosures_corp_code', 'corp_code'),
        Index('idx_egm_disclosures_parse_status', 'parse_status'),
    )

    def __repr__(self):
        return f"<EGMDisclosure(id={self.id}, corp_name='{self.corp_name}', is_dispute={self.is_dispute_related})>"

    @property
    def has_officer_changes(self) -> bool:
        """임원 변동 여부"""
        return self.officers_appointed > 0 or self.officers_dismissed > 0

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": str(self.id),
            "disclosure_id": self.disclosure_id,
            "corp_code": self.corp_code,
            "corp_name": self.corp_name,
            "egm_date": self.egm_date.isoformat() if self.egm_date else None,
            "egm_type": self.egm_type,
            "is_dispute_related": self.is_dispute_related,
            "dispute_type": self.dispute_type,
            "dispute_confidence": float(self.dispute_confidence) if self.dispute_confidence else None,
            "agenda_items": self.agenda_items,
            "officer_changes": self.officer_changes,
            "officers_appointed": self.officers_appointed,
            "officers_dismissed": self.officers_dismissed,
            "parse_status": self.parse_status,
        }


# 상수 정의
EGM_REPORT_TYPES = [
    "임시주주총회결과",
    "주주총회소집결의(임시주주총회)",
    "[기재정정]임시주주총회결과",
    "[기재정정]주주총회소집결의(임시주주총회)",
]

DISPUTE_STRONG_KEYWORDS = [
    '경영권 분쟁', '경영권분쟁', '적대적', '경영권 확보',
    '주주제안', '주주 제안', '소수주주', '반대주주',
    '해임 청구', '해임청구', '직무집행정지',
    '가처분', '소송', '소집허가',
]

DISPUTE_MEDIUM_KEYWORDS = [
    '해임', '퇴임', '사임', '교체',
    '대표이사 변경', '이사회 구성',
    '지배구조', '경영진 교체',
]
