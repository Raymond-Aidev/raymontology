"""
Risk Signals 모델

관계형 리스크 신호 저장
"""
from sqlalchemy import Column, String, Float, DateTime, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class RiskSeverity(str, enum.Enum):
    """리스크 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, enum.Enum):
    """리스크 상태"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class RiskSignal(Base):
    """
    리스크 신호 테이블

    Raymontology의 핵심 아웃풋
    """
    __tablename__ = "risk_signals"

    # Primary Key
    signal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 대상
    target_company_id = Column(
        UUID(as_uuid=True),
        ForeignKey('companies.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # 패턴 정보
    pattern_type = Column(String(100), nullable=False, index=True)  # circular_cb, pump_dump 등
    severity = Column(SQLEnum(RiskSeverity), nullable=False, default=RiskSeverity.MEDIUM, index=True)
    status = Column(SQLEnum(RiskStatus), nullable=False, default=RiskStatus.DETECTED, index=True)

    # 점수
    risk_score = Column(Float, nullable=False, index=True)  # 0.0 ~ 1.0
    exploitation_probability = Column(Float, nullable=True)  # 착취 확률
    expected_retail_loss = Column(Float, nullable=True)  # 예상 개미 손실액

    # 설명
    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=False)

    # 증거 (JSONB)
    evidence = Column(JSONB, default=[])  # [{"type": "transaction", "id": "...", "description": "..."}]

    # 관련 엔티티
    involved_object_ids = Column(ARRAY(String), default=[])  # 온톨로지 오브젝트 ID들
    involved_link_ids = Column(ARRAY(String), default=[])  # 온톨로지 링크 ID들

    # 온톨로지 연결
    ontology_object_id = Column(String(50), unique=True, nullable=True, index=True)

    # 추가 속성
    properties = Column(JSONB, default={})

    # 메타데이터
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 인덱스
    __table_args__ = (
        Index('idx_risk_signal_company_severity', 'target_company_id', 'severity'),
        Index('idx_risk_signal_score', 'risk_score'),
        Index('idx_risk_signal_status_severity', 'status', 'severity'),
        Index('idx_risk_signal_pattern', 'pattern_type'),
        Index('idx_risk_signal_detected', 'detected_at'),
    )

    def __repr__(self):
        return f"<RiskSignal(signal_id={self.signal_id}, pattern='{self.pattern_type}', severity='{self.severity}', score={self.risk_score})>"
