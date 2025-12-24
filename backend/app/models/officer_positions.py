"""
OfficerPosition 모델 - 임원-회사 연결 테이블

임원이 어느 회사에서 어떤 직책으로 근무하는지 기록
한 임원이 여러 회사에 겸직 가능
"""
from sqlalchemy import Column, String, Date, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class OfficerPosition(Base):
    """
    임원 직위 테이블

    - 임원과 회사 간의 N:M 관계
    - 한 임원이 여러 회사에 재직 가능 (그룹사 겸직)
    - 동일 회사에서 시기별 다른 직위 가능
    """
    __tablename__ = "officer_positions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    officer_id = Column(UUID(as_uuid=True), ForeignKey("officers.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # 직위 정보
    position = Column(String(100), nullable=False)  # 대표이사, 사내이사, 사외이사, 감사 등

    # 임기 정보
    term_start_date = Column(Date, nullable=True, index=True)
    term_end_date = Column(Date, nullable=True, index=True)
    is_current = Column(Boolean, nullable=False, default=True, index=True)

    # 임원 부가 정보 (공시 기준)
    birth_date = Column(String(10), nullable=True)  # YYYYMM
    gender = Column(String(10), nullable=True)
    appointment_number = Column(Integer, default=1)  # 선임 횟수

    # 데이터 출처
    source_disclosure_id = Column(String(36), nullable=True)  # 출처 공시 ID
    source_report_date = Column(Date, nullable=True, index=True)  # 보고서 기준일

    # 메타데이터
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    officer = relationship("Officer", backref="positions", lazy="joined")
    company = relationship("Company", backref="officer_positions", lazy="joined")

    def __repr__(self):
        return f"<OfficerPosition(officer_id={self.officer_id}, company_id={self.company_id}, position='{self.position}', is_current={self.is_current})>"
