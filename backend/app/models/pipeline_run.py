"""
파이프라인 실행 이력 모델

분기 파이프라인 및 기타 배치 작업의 실행 이력을 저장합니다.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class PipelineStatus(str, Enum):
    """파이프라인 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineType(str, Enum):
    """파이프라인 유형"""
    QUARTERLY = "quarterly"
    DAILY = "daily"
    MANUAL = "manual"
    BACKFILL = "backfill"


class PipelineRun(Base):
    """파이프라인 실행 이력"""

    __tablename__ = "pipeline_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_type = Column(String(50), nullable=False)
    quarter = Column(String(10), nullable=True)  # Q1, Q2, Q3, Q4
    year = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default=PipelineStatus.PENDING)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # 통계
    companies_processed = Column(Integer, nullable=True)
    files_processed = Column(Integer, nullable=True)
    officers_inserted = Column(Integer, nullable=True)
    positions_inserted = Column(Integer, nullable=True)
    errors_count = Column(Integer, nullable=True)

    # 메타데이터
    error_message = Column(Text, nullable=True)
    log_file_path = Column(String(500), nullable=True)
    metadata = Column(JSONB, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def start(self):
        """파이프라인 시작"""
        self.status = PipelineStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, stats: Dict[str, Any] = None):
        """파이프라인 완료"""
        self.status = PipelineStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        if stats:
            self.companies_processed = stats.get('companies_processed')
            self.files_processed = stats.get('files_processed')
            self.officers_inserted = stats.get('officers_inserted')
            self.positions_inserted = stats.get('positions_inserted')
            self.errors_count = stats.get('errors_count')

    def fail(self, error_message: str):
        """파이프라인 실패"""
        self.status = PipelineStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'id': str(self.id),
            'pipeline_type': self.pipeline_type,
            'quarter': self.quarter,
            'year': self.year,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'companies_processed': self.companies_processed,
            'files_processed': self.files_processed,
            'officers_inserted': self.officers_inserted,
            'positions_inserted': self.positions_inserted,
            'errors_count': self.errors_count,
            'error_message': self.error_message,
            'log_file_path': self.log_file_path,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
