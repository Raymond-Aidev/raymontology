"""
Affiliate (계열사) 모델

회사 간 계열사 관계를 저장
"""
from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Affiliate(Base):
    """
    계열사 관계 테이블

    회사 간 계열사/자회사/손자회사 등의 관계 저장
    """
    __tablename__ = "affiliates"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 관계 정보
    parent_company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True, comment="모회사 ID")
    affiliate_company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True, comment="계열사 ID")

    # 계열사 정보
    affiliate_name = Column(String(200), nullable=False, index=True, comment="계열사명")
    business_number = Column(String(20), nullable=True, comment="사업자등록번호")

    # 관계 유형
    relationship_type = Column(String(50), nullable=True, index=True, comment="관계 유형 (subsidiary, affiliate, etc.)")
    is_listed = Column(Boolean, default=False, index=True, comment="상장 여부")

    # 지분 정보
    ownership_ratio = Column(Float, nullable=True, comment="지분율 (%)")
    voting_rights_ratio = Column(Float, nullable=True, comment="의결권 비율 (%)")

    # 재무 정보
    total_assets = Column(Float, nullable=True, comment="총자산")
    revenue = Column(Float, nullable=True, comment="매출액")
    net_income = Column(Float, nullable=True, comment="순이익")

    # 출처 정보
    source_disclosure_id = Column(String(36), nullable=True, comment="출처 공시 ID")
    source_date = Column(String(8), nullable=True, index=True, comment="기준일자 (YYYYMMDD)")

    # 온톨로지 연결
    ontology_object_id = Column(String(50), unique=True, nullable=True, index=True)

    # 추가 속성
    properties = Column(JSONB, default={}, comment="추가 정보 (JSON)")

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    parent_company = relationship("Company", foreign_keys=[parent_company_id])
    affiliate_company = relationship("Company", foreign_keys=[affiliate_company_id])

    # 인덱스
    __table_args__ = (
        # 중복 방지: 동일 관계는 1개만
        Index('idx_unique_affiliation', 'parent_company_id', 'affiliate_company_id', 'source_date', unique=True),

        # 조회 최적화
        Index('idx_affiliate_parent', 'parent_company_id', 'source_date'),
        Index('idx_affiliate_company', 'affiliate_company_id'),
        Index('idx_affiliate_type', 'relationship_type'),

        # 전문 검색
        Index('idx_affiliate_name_trigram', 'affiliate_name', postgresql_using='gin', postgresql_ops={'affiliate_name': 'gin_trgm_ops'}),
    )

    def __repr__(self):
        return f"<Affiliate(id={self.id}, parent={self.parent_company_id}, affiliate={self.affiliate_name})>"
