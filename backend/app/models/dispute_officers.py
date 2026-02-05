"""
Dispute Officers Model
분쟁 선임 임원 모델

경영분쟁을 통해 선임된 임원 정보 저장
"""
from sqlalchemy import Column, String, Boolean, Date, DateTime, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from app.database import Base


class AppointmentContext(str, Enum):
    """선임 맥락 유형"""
    DISPUTE_NEW = "DISPUTE_NEW"           # 분쟁으로 인한 신규 선임
    DISPUTE_REPLACEMENT = "DISPUTE_REPLACEMENT"  # 분쟁으로 인한 교체 선임
    REGULAR = "REGULAR"                   # 일반 선임 (비분쟁)
    UNKNOWN = "UNKNOWN"                   # 판단 불가


class DisputeOfficer(Base):
    """
    분쟁 선임 임원 테이블

    임시주주총회를 통해 경영분쟁 상황에서 선임된 임원 정보
    기존 officers 테이블과 소프트 참조로 연결
    """
    __tablename__ = "dispute_officers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 임원 연결 (기존 officers 테이블과 소프트 참조)
    officer_id = Column(UUID(as_uuid=True), ForeignKey("officers.id"), nullable=True, index=True)
    officer_match_confidence = Column(String(10), nullable=True)  # "HIGH", "MEDIUM", "LOW"

    # 임원 기본 정보 (공시에서 추출)
    officer_name = Column(String(100), nullable=False, index=True)
    birth_date = Column(String(10), nullable=True)  # 'YYYYMM' 형식
    gender = Column(String(10), nullable=True)

    # 선임 정보
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    position = Column(String(100), nullable=True, index=True)  # 선임 직책
    egm_disclosure_id = Column(UUID(as_uuid=True), ForeignKey("egm_disclosures.id"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=True)  # 선임일 (주총 개최일)

    # 경력 정보 (공시에서 추출)
    career_from_disclosure = Column(Text, nullable=True)  # 공시 원문에서 추출한 경력
    career_parsed = Column(JSONB, default=[])  # 구조화된 경력 [{text, status}]
    education_from_disclosure = Column(Text, nullable=True)  # 학력 정보

    # 분쟁 맥락
    appointment_context = Column(String(30), default=AppointmentContext.UNKNOWN.value, index=True)
    replaced_officer_name = Column(String(100), nullable=True)  # 해임된 전임자 이름
    replacement_reason = Column(Text, nullable=True)  # 교체 사유

    # 투표 결과
    vote_result = Column(String(200), nullable=True)  # "가결 (찬성 85.3%, 반대 14.7%)"
    vote_for_ratio = Column(String(10), nullable=True)  # "85.3%"
    vote_against_ratio = Column(String(10), nullable=True)  # "14.7%"

    # 추가 정보
    agenda_number = Column(String(20), nullable=True)  # 안건 번호 (제1호 의안)
    agenda_title = Column(String(300), nullable=True)  # 안건 제목

    # 검증 상태
    is_verified = Column(Boolean, default=False, index=True)  # 수동 검증 완료 여부
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String(100), nullable=True)

    # 파싱 메타데이터
    extraction_confidence = Column(String(10), nullable=True)  # "HIGH", "MEDIUM", "LOW"
    extraction_source = Column(String(50), nullable=True)  # 추출 위치 (agenda, table, text 등)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    officer = relationship("Officer", foreign_keys=[officer_id])
    company = relationship("Company", foreign_keys=[company_id])
    egm_disclosure = relationship("EGMDisclosure", back_populates="dispute_officers")

    # 인덱스
    __table_args__ = (
        Index('idx_dispute_officers_name', 'officer_name'),
        Index('idx_dispute_officers_context', 'appointment_context'),
        Index('idx_dispute_officers_company', 'company_id'),
        Index('idx_dispute_officers_egm', 'egm_disclosure_id'),
        Index('idx_dispute_officers_verified', 'is_verified'),
    )

    def __repr__(self):
        return f"<DisputeOfficer(id={self.id}, name='{self.officer_name}', position='{self.position}')>"

    @property
    def is_dispute_appointment(self) -> bool:
        """분쟁 관련 선임 여부"""
        return self.appointment_context in [
            AppointmentContext.DISPUTE_NEW.value,
            AppointmentContext.DISPUTE_REPLACEMENT.value
        ]

    @property
    def is_replacement(self) -> bool:
        """교체 선임 여부"""
        return bool(self.replaced_officer_name)

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": str(self.id),
            "officer_id": str(self.officer_id) if self.officer_id else None,
            "officer_name": self.officer_name,
            "birth_date": self.birth_date,
            "position": self.position,
            "company_id": str(self.company_id) if self.company_id else None,
            "appointment_date": self.appointment_date.isoformat() if self.appointment_date else None,
            "appointment_context": self.appointment_context,
            "replaced_officer_name": self.replaced_officer_name,
            "vote_result": self.vote_result,
            "career_from_disclosure": self.career_from_disclosure,
            "career_parsed": self.career_parsed,
            "is_verified": self.is_verified,
            "extraction_confidence": self.extraction_confidence,
        }

    def match_with_officer(self, officer_id: uuid.UUID, confidence: str = "MEDIUM"):
        """기존 officers 테이블과 매칭"""
        self.officer_id = officer_id
        self.officer_match_confidence = confidence
