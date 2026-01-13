"""
News 관계 분석 시스템 모델

뉴스 기사에서 추출한 엔티티/관계/리스크를 저장합니다.

⚠️ 안전 설계:
- 기존 테이블(companies, officers)에 FK 없음 (소프트 참조)
- news_* 테이블만 사용
- 완전 롤백 가능
"""
from sqlalchemy import Column, String, Text, Date, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class NewsArticle(Base):
    """
    뉴스 기사 테이블

    WebFetch로 파싱한 기사의 메타데이터와 요약을 저장합니다.
    """
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 기사 정보
    url = Column(String(500), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    publisher = Column(String(100), nullable=True)
    publish_date = Column(Date, nullable=True)
    author = Column(String(100), nullable=True)

    # Claude 분석 결과
    summary = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)

    # 메타데이터
    status = Column(String(20), nullable=False, default='active')  # active, archived, deleted
    parse_version = Column(String(10), nullable=True, default='v4')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (news 테이블 내부만)
    entities = relationship("NewsEntity", back_populates="article", cascade="all, delete-orphan")
    relations = relationship("NewsRelation", back_populates="article", cascade="all, delete-orphan")
    risks = relationship("NewsRisk", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_news_articles_status', 'status'),
        Index('idx_news_articles_publish_date', 'publish_date'),
    )

    def __repr__(self):
        return f"<NewsArticle(id={self.id}, title='{self.title[:30]}...')>"


class NewsEntity(Base):
    """
    기사에서 추출된 엔티티 테이블

    company, person, fund, spc 등의 엔티티를 저장합니다.
    기존 DB의 companies/officers와 매칭 시 소프트 참조 사용 (FK 없음).
    """
    __tablename__ = "news_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False)

    # 엔티티 정보
    entity_type = Column(String(30), nullable=False)  # company, person, fund, spc
    entity_name = Column(String(200), nullable=False)
    entity_role = Column(String(300), nullable=True)  # 기사에서의 역할/설명

    # 기존 DB 매칭 (⚠️ FK 없음 - 소프트 참조)
    matched_company_id = Column(UUID(as_uuid=True), nullable=True)  # companies.id
    matched_officer_id = Column(UUID(as_uuid=True), nullable=True)  # officers.id
    matched_corp_code = Column(String(20), nullable=True)  # companies.corp_code
    match_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 ~ 1.00

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    article = relationship("NewsArticle", back_populates="entities")
    source_relations = relationship("NewsRelation", foreign_keys="NewsRelation.source_entity_id", back_populates="source_entity", cascade="all, delete-orphan")
    target_relations = relationship("NewsRelation", foreign_keys="NewsRelation.target_entity_id", back_populates="target_entity", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_news_entities_article', 'article_id'),
        Index('idx_news_entities_company', 'matched_company_id'),
        Index('idx_news_entities_name', 'entity_name'),
        Index('idx_news_entities_type', 'entity_type'),
    )

    def __repr__(self):
        return f"<NewsEntity(id={self.id}, type='{self.entity_type}', name='{self.entity_name}')>"


class NewsRelation(Base):
    """
    엔티티 간 관계 테이블

    기사에서 추출된 관계 정보와 위험 가중치를 저장합니다.
    """
    __tablename__ = "news_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False)

    # 관계 주체
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey('news_entities.id', ondelete='CASCADE'), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey('news_entities.id', ondelete='CASCADE'), nullable=False)

    # 관계 정보
    relation_type = Column(String(50), nullable=False)  # cb_subscriber, major_shareholder, cross_officer, etc.
    relation_detail = Column(String(500), nullable=True)  # 상세 설명
    relation_period = Column(String(100), nullable=True)  # 기간 정보
    risk_weight = Column(Numeric(3, 2), nullable=False, default=1.0)  # 위험 가중치

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    article = relationship("NewsArticle", back_populates="relations")
    source_entity = relationship("NewsEntity", foreign_keys=[source_entity_id], back_populates="source_relations")
    target_entity = relationship("NewsEntity", foreign_keys=[target_entity_id], back_populates="target_relations")

    __table_args__ = (
        Index('idx_news_relations_article', 'article_id'),
        Index('idx_news_relations_type', 'relation_type'),
        Index('idx_news_relations_source', 'source_entity_id'),
        Index('idx_news_relations_target', 'target_entity_id'),
    )

    def __repr__(self):
        return f"<NewsRelation(id={self.id}, type='{self.relation_type}')>"


class NewsRisk(Base):
    """
    기사에서 감지된 위험 요소 테이블
    """
    __tablename__ = "news_risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False)

    # 위험 정보
    risk_type = Column(String(50), nullable=False)  # governance, financial, operational, legal
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default='medium')  # low, medium, high, critical

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    article = relationship("NewsArticle", back_populates="risks")

    __table_args__ = (
        Index('idx_news_risks_article', 'article_id'),
        Index('idx_news_risks_type', 'risk_type'),
        Index('idx_news_risks_severity', 'severity'),
    )

    def __repr__(self):
        return f"<NewsRisk(id={self.id}, type='{self.risk_type}', severity='{self.severity}')>"


class NewsCompanyComplexity(Base):
    """
    기업별 관계 복잡도 스코어 테이블

    뉴스 기반 관계 분석 결과를 집계하여 기업별 복잡도 등급을 산출합니다.

    ⚠️ 소프트 참조: companies 테이블에 FK 없음
    """
    __tablename__ = "news_company_complexity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 소프트 참조 (⚠️ FK 없음)
    company_id = Column(UUID(as_uuid=True), nullable=False, unique=True)  # companies.id
    corp_code = Column(String(20), nullable=False)  # companies.corp_code

    # 스코어
    complexity_score = Column(Numeric(5, 2), nullable=False, default=0)  # 0 ~ 100
    complexity_grade = Column(String(5), nullable=False, default='A')  # A, B, C, D, E, F

    # 통계
    entity_count = Column(Integer, nullable=False, default=0)
    relation_count = Column(Integer, nullable=False, default=0)
    high_risk_count = Column(Integer, nullable=False, default=0)
    article_count = Column(Integer, nullable=False, default=0)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_news_complexity_company', 'company_id'),
        Index('idx_news_complexity_corp', 'corp_code'),
        Index('idx_news_complexity_grade', 'complexity_grade'),
    )

    def __repr__(self):
        return f"<NewsCompanyComplexity(company_id={self.company_id}, grade='{self.complexity_grade}')>"


# 위험 가중치 상수 (복잡도 계산에 사용)
RISK_WEIGHTS = {
    'cb_subscriber': 3.0,       # CB 인수자
    'major_shareholder': 2.5,   # 대주주
    'cross_officer': 2.0,       # 겸직 임원
    'affiliate': 1.5,           # 계열사
    'business_partner': 1.0,    # 거래처
    'investor': 1.5,            # 투자자
    'spc_related': 2.5,         # SPC 관련
    'fund_related': 2.0,        # 펀드 관련
}

# 복잡도 등급 기준
COMPLEXITY_GRADES = {
    'A': (0, 20),      # 단순 (0-20점)
    'B': (20, 40),     # 보통 (20-40점)
    'C': (40, 60),     # 복잡 (40-60점)
    'D': (60, 80),     # 매우 복잡 (60-80점)
    'E': (80, 90),     # 위험 (80-90점)
    'F': (90, 100),    # 고위험 (90-100점)
}
