"""
Officer 모델
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Officer(Base):
    """
    임원 테이블

    등기임원, 사외이사, 감사 등
    """
    __tablename__ = "officers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 기본 정보
    name = Column(String(100), nullable=False, index=True)
    name_en = Column(String(100), nullable=True)
    birth_date = Column(String(10), nullable=True, index=True)  # 출생년월 (YYYY.MM)
    gender = Column(String(10), nullable=True)  # 성별 (남/여)
    resident_number_hash = Column(String(64), unique=True, nullable=True)  # SHA256 해시

    # 직위
    position = Column(String(100), nullable=True, index=True)  # 대표이사, 사내이사, 사외이사, 감사 등
    current_company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # 경력 (JSONB)
    career_history = Column(JSONB, default=[])  # [{"company": "A사", "position": "임원", "from": "2020", "to": "2023"}]
    career_raw_text = Column(String, nullable=True)  # 사업보고서 '주요경력' 원문 (□ → 줄바꿈 변환)
    education = Column(ARRAY(String), default=[])  # ["서울대 경영학과", "하버드 MBA"]

    # 네트워크 지표
    board_count = Column(Integer, default=0)  # 겸직 이사회 수
    network_centrality = Column(Float, nullable=True)  # 네트워크 중심성 (0~1)
    influence_score = Column(Float, default=0.0, index=True)  # 영향력 점수 (0~1)

    # 리스크 플래그
    has_conflict_of_interest = Column(Boolean, default=False)  # 이해충돌 여부
    insider_trading_count = Column(Integer, default=0)  # 내부자 거래 횟수

    # 온톨로지 연결
    ontology_object_id = Column(String(50), unique=True, nullable=True, index=True)

    # 추가 속성
    properties = Column(JSONB, default={})

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 인덱스
    __table_args__ = (
        Index('idx_officer_name_trigram', 'name', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
        Index('idx_officer_influence', 'influence_score'),
        Index('idx_officer_position', 'position'),
    )

    def __repr__(self):
        return f"<Officer(id={self.id}, name='{self.name}', position='{self.position}')>"
