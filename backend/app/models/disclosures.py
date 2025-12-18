"""
Disclosure Models

DART 공시 메타데이터 저장
"""
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Disclosure(Base):
    """
    DART 공시 메타데이터

    실제 문서는 S3/R2에 저장, 메타데이터만 DB에 저장
    """
    __tablename__ = "disclosures"

    # 기본 정보
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rcept_no = Column(String(14), unique=True, nullable=False, index=True, comment="접수번호 (고유키)")

    # 기업 정보
    corp_code = Column(String(8), ForeignKey('companies.corp_code', ondelete='CASCADE'), nullable=False, index=True)
    corp_name = Column(String(200), nullable=False)
    stock_code = Column(String(6), nullable=True, index=True)

    # 공시 정보
    report_nm = Column(String(500), nullable=False, comment="보고서명")
    rcept_dt = Column(String(8), nullable=False, index=True, comment="접수일자 (YYYYMMDD)")
    flr_nm = Column(String(200), nullable=True, comment="공시 제출인명")

    # 문서 정보
    rm = Column(Text, nullable=True, comment="비고")

    # 저장 위치 (S3/R2)
    storage_url = Column(String(500), nullable=True, comment="S3/R2 문서 URL")
    storage_key = Column(String(500), nullable=True, comment="S3/R2 객체 키")

    # 크롤링 정보
    crawled_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="크롤링 시각")
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow, comment="업데이트 시각")

    # 추가 메타데이터
    extra_metadata = Column(JSONB, default={}, comment="추가 메타데이터 (JSON)")

    # Relationships
    company = relationship("Company", back_populates="disclosures")

    __table_args__ = (
        # 복합 인덱스: 기업별 날짜 조회
        Index('idx_disclosures_corp_date', 'corp_code', 'rcept_dt'),

        # 복합 인덱스: 종목별 날짜 조회
        Index('idx_disclosures_stock_date', 'stock_code', 'rcept_dt'),

        # 전문 검색: 보고서명
        Index('idx_disclosures_report_nm_trgm', 'report_nm', postgresql_using='gin', postgresql_ops={'report_nm': 'gin_trgm_ops'}),
    )

    def __repr__(self):
        return f"<Disclosure(rcept_no={self.rcept_no}, corp_name={self.corp_name}, report_nm={self.report_nm})>"


class DisclosureParsedData(Base):
    """
    파싱된 공시 데이터

    공시 문서에서 추출한 구조화된 데이터 저장
    """
    __tablename__ = "disclosure_parsed_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rcept_no = Column(String(14), ForeignKey('disclosures.rcept_no', ondelete='CASCADE'), nullable=False, unique=True)

    # 파싱된 데이터 (JSON)
    parsed_data = Column(JSONB, nullable=False, comment="파싱된 공시 데이터")

    # 파싱 정보
    parsed_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="파싱 시각")
    parser_version = Column(String(20), nullable=True, comment="파서 버전")

    # 파싱 통계
    sections_count = Column(Integer, default=0, comment="섹션 수")
    tables_count = Column(Integer, default=0, comment="테이블 수")

    __table_args__ = (
        # GIN 인덱스: JSON 데이터 검색
        Index('idx_parsed_data_jsonb', 'parsed_data', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<DisclosureParsedData(rcept_no={self.rcept_no}, sections={self.sections_count})>"


class CrawlJob(Base):
    """
    크롤링 작업 기록

    백그라운드 작업 추적 및 모니터링
    """
    __tablename__ = "crawl_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 작업 정보
    job_type = Column(String(50), nullable=False, index=True, comment="작업 유형 (full, recent, company)")
    status = Column(String(20), nullable=False, default="pending", index=True, comment="작업 상태 (pending, running, completed, failed)")

    # 작업 파라미터
    parameters = Column(JSONB, default={}, comment="작업 파라미터 (JSON)")

    # 작업 결과
    total_companies = Column(Integer, default=0)
    total_disclosures = Column(Integer, default=0)
    downloaded_documents = Column(Integer, default=0)
    failed_downloads = Column(Integer, default=0)

    # 에러 정보
    errors = Column(JSONB, default=[], comment="에러 목록 (JSON)")
    error_message = Column(Text, nullable=True, comment="에러 메시지")

    # 시간 정보
    started_at = Column(DateTime, nullable=True, comment="시작 시각")
    completed_at = Column(DateTime, nullable=True, comment="완료 시각")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="생성 시각")

    # Celery task ID
    task_id = Column(String(100), nullable=True, unique=True, index=True, comment="Celery 태스크 ID")

    __table_args__ = (
        # 복합 인덱스: 작업 유형별 상태 조회
        Index('idx_crawl_jobs_type_status', 'job_type', 'status'),
    )

    def __repr__(self):
        return f"<CrawlJob(id={self.id}, type={self.job_type}, status={self.status})>"
