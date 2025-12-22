"""
Site Settings 모델
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SiteSetting(Base):
    """
    사이트 설정 테이블 (이용약관, 개인정보처리방침 등)
    """
    __tablename__ = "site_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)  # 'terms', 'privacy'
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=True)  # 수정한 관리자 ID

    def __repr__(self):
        return f"<SiteSetting(key='{self.key}')>"
