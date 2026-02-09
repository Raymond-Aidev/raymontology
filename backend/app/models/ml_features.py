"""
ML 피처 저장 모델

26개 피처를 기업별/날짜별로 저장
"""
from sqlalchemy import Column, String, Integer, BigInteger, Numeric, DateTime, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class MLFeature(Base):
    """
    ML 피처 테이블

    기업별, 날짜별 26개 피처 스냅샷 저장
    """
    __tablename__ = "ml_features"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    feature_date = Column(Date, nullable=False)

    # =========================================================================
    # 임원 네트워크 피처 (E01-E10)
    # =========================================================================
    exec_count = Column(Integer)                          # E01: 임원 수
    exec_turnover_rate = Column(Numeric(5, 4))            # E02: 임원 이직률
    exec_avg_tenure = Column(Numeric(6, 2))               # E03: 평균 재직 기간(월)
    exec_other_company_count = Column(Integer)            # E04: 타사 재직 건수 합계
    exec_avg_other_companies = Column(Numeric(5, 2))      # E05: 임원당 평균 타사 재직
    exec_delisted_connection = Column(Integer)            # E06: 상장폐지 기업 연결 수
    exec_managed_connection = Column(Integer)             # E07: 관리종목 기업 연결 수
    exec_concurrent_positions = Column(Integer)           # E08: 겸직 임원 수
    exec_network_density = Column(Numeric(5, 4))          # E09: 네트워크 밀도
    exec_high_risk_ratio = Column(Numeric(5, 4))          # E10: 고위험 임원 비율

    # =========================================================================
    # CB 투자자 피처 (C01-C08)
    # =========================================================================
    cb_count_1y = Column(Integer)                         # C01: CB 발행 횟수 (1년)
    cb_total_amount_1y = Column(BigInteger)               # C02: CB 발행 총액 (1년, 원)
    cb_subscriber_count = Column(Integer)                 # C03: CB 참여자 수
    cb_high_risk_subscriber_ratio = Column(Numeric(5, 4)) # C04: 고위험 투자자 비율
    cb_subscriber_avg_investments = Column(Numeric(5, 2)) # C05: 투자자 평균 투자 건수
    cb_loss_company_connections = Column(Integer)         # C06: 적자기업 연결 수
    cb_delisted_connections = Column(Integer)             # C07: 상장폐지 연결 수
    cb_repeat_subscriber_ratio = Column(Numeric(5, 4))    # C08: 반복 투자자 비율

    # =========================================================================
    # 대주주 피처 (S01-S04)
    # =========================================================================
    largest_shareholder_ratio = Column(Numeric(5, 2))     # S01: 최대주주 지분율 (%)
    shareholder_change_1y = Column(Numeric(6, 2))         # S02: 지분 변동폭 (1년, %p)
    related_party_ratio = Column(Numeric(5, 2))           # S03: 특수관계인 지분율
    shareholder_count = Column(Integer)                   # S04: 주요주주 수 (5%+)

    # =========================================================================
    # 4대 인덱스 (I01-I04)
    # =========================================================================
    cei_score = Column(Numeric(5, 2))                     # I01: CEI (임원집중도지수)
    cgi_score = Column(Numeric(5, 2))                     # I02: CGI (지배구조지수)
    rii_score = Column(Numeric(5, 2))                     # I03: RII (관계강도지수)
    mai_score = Column(Numeric(5, 2))                     # I04: MAI (시장이상지수)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 제약조건
    __table_args__ = (
        UniqueConstraint('company_id', 'feature_date', name='uq_ml_features_company_date'),
        Index('idx_ml_features_company_date', 'company_id', 'feature_date'),
    )

    def __repr__(self):
        return f"<MLFeature(company_id={self.company_id}, date={self.feature_date})>"
