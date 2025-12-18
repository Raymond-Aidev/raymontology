"""
Ontology Links 모델

관계도 1급 시민 (First-Class Citizen)
"""
from sqlalchemy import Column, String, Float, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class OntologyLink(Base):
    """
    온톨로지 링크 테이블

    모든 관계를 명시적으로 저장
    """
    __tablename__ = "ontology_links"

    # Primary Key
    link_id = Column(String(50), primary_key=True)  # LINK_XXX

    # 링크 타입
    link_type = Column(String(50), nullable=False, index=True)  # RelationshipType enum 값

    # 연결 (Foreign Keys)
    source_object_id = Column(
        String(50),
        ForeignKey('ontology_objects.object_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    target_object_id = Column(
        String(50),
        ForeignKey('ontology_objects.object_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # 시간 버전 관리
    valid_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # 링크 속성
    strength = Column(Float, nullable=False, default=0.5)  # 관계 강도 (0~1)
    confidence = Column(Float, nullable=False, default=1.0)  # 신뢰도 (0~1)

    # 추가 속성 (JSONB)
    properties = Column(JSONB, nullable=False, default={})

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 인덱스
    __table_args__ = (
        Index('idx_ontology_link_type', 'link_type'),
        Index('idx_ontology_link_source', 'source_object_id'),
        Index('idx_ontology_link_target', 'target_object_id'),
        Index('idx_ontology_link_source_target', 'source_object_id', 'target_object_id'),
        Index('idx_ontology_link_type_source', 'link_type', 'source_object_id'),
        Index('idx_ontology_link_valid', 'valid_from', 'valid_until'),
        Index('idx_ontology_link_properties', 'properties', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<OntologyLink(link_id='{self.link_id}', type='{self.link_type}', {self.source_object_id} → {self.target_object_id})>"

    @property
    def is_valid(self) -> bool:
        """현재 시점에 유효한지 확인"""
        from datetime import datetime
        now = datetime.now()
        if self.valid_until is None:
            return self.valid_from <= now
        return self.valid_from <= now <= self.valid_until
