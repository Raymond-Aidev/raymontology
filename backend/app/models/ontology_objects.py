"""
Ontology Objects 모델

팔란티어 온톨로지의 핵심: Object-Link-Property
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func

from app.database import Base


class OntologyObject(Base):
    """
    온톨로지 오브젝트 테이블

    모든 엔티티를 통합 관리
    """
    __tablename__ = "ontology_objects"

    # Primary Key
    object_id = Column(String(50), primary_key=True)  # COMP_XXX, OFFR_XXX, FUND_XXX 등

    # 타입
    object_type = Column(String(50), nullable=False, index=True)  # Company, Officer, Fund, ConvertibleBond 등

    # 시간 버전 관리
    valid_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    # 계보 추적
    source_documents = Column(ARRAY(String), default=[])  # ["DART_20231201_001", "NEWS_20231202_123"]
    confidence = Column(Float, nullable=False, default=1.0)  # 0.0 ~ 1.0

    # 속성 (JSONB - 유연한 스키마)
    properties = Column(JSONB, nullable=False, default={})

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 인덱스
    __table_args__ = (
        Index('idx_ontology_object_type', 'object_type'),
        Index('idx_ontology_object_valid', 'valid_from', 'valid_until'),
        Index('idx_ontology_object_properties', 'properties', postgresql_using='gin'),
        Index('idx_ontology_object_type_valid', 'object_type', 'valid_from'),
    )

    def __repr__(self):
        return f"<OntologyObject(object_id='{self.object_id}', type='{self.object_type}', version={self.version})>"

    @property
    def is_valid(self) -> bool:
        """현재 시점에 유효한지 확인"""
        from datetime import datetime
        now = datetime.now()
        if self.valid_until is None:
            return self.valid_from <= now
        return self.valid_from <= now <= self.valid_until
