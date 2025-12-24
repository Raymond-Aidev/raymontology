"""
리스크 점수 모델

기업별 리스크 점수 및 분석 결과
"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class RiskScore(Base):
    """
    리스크 점수 테이블

    기업별 분기/연간 리스크 분석 결과
    """
    __tablename__ = "risk_scores"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 회사 정보 (FK)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)

    # 분석 기간
    analysis_year = Column(Integer, nullable=False, comment="분석 연도")
    analysis_quarter = Column(Integer, nullable=True, comment="분석 분기 (NULL=연간)")

    # 종합 점수
    total_score = Column(Numeric(5, 2), nullable=False, comment="종합 점수 (0-100)")
    risk_level = Column(String(20), nullable=False, comment="리스크 수준 (VERY_LOW/LOW/MEDIUM/HIGH/CRITICAL)")
    investment_grade = Column(String(5), nullable=True, comment="투자 등급 (AAA~D)")
    confidence = Column(Numeric(5, 4), nullable=True, comment="신뢰도 (0-1)")

    # 세부 점수
    raymondsrisk_score = Column(Numeric(5, 2), nullable=True, comment="레이몬드 리스크 점수")
    human_risk_score = Column(Numeric(5, 2), nullable=True, comment="임원 리스크 점수")
    cb_risk_score = Column(Numeric(5, 2), nullable=True, comment="CB 리스크 점수")
    financial_health_score = Column(Numeric(5, 2), nullable=True, comment="재무 건전성 점수")

    # 상세 분석
    score_breakdown = Column(JSONB, nullable=True, comment="점수 상세 분석")

    # 메타데이터
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), comment="계산 시점")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", backref="risk_scores")

    # 인덱스 및 제약조건
    __table_args__ = (
        # 유니크 제약조건: 동일 회사, 동일 분석기간은 1건만 존재
        UniqueConstraint('company_id', 'analysis_year', 'analysis_quarter', name='risk_scores_company_id_analysis_year_analysis_quarter_key'),
        # 인덱스
        Index('idx_risk_scores_company', 'company_id'),
        Index('idx_risk_scores_year', 'analysis_year'),
        Index('idx_risk_scores_grade', 'investment_grade'),
        Index('idx_risk_scores_level', 'risk_level'),
    )

    def __repr__(self):
        return f"<RiskScore(company_id={self.company_id}, year={self.analysis_year}, score={self.total_score})>"
