"""
거래정지 사유 분류 모델

SUSPENDED 기업을 TYPE_A(재무악화), TYPE_B(합병/자진상폐), TYPE_C(기타)로 분류
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SuspensionClassification(Base):
    """
    거래정지 사유 분류 테이블

    ML 라벨링을 위해 거래정지 기업의 사유를 분류:
    - TYPE_A: 재무악화 (감사의견 거절, 자본잠식, 횡령 등) → ML 양성 라벨 (Y=1)
    - TYPE_B: 합병/인수 (합병 상장폐지, 자진 상장폐지) → ML 라벨에서 제외
    - TYPE_C: 기타 (SPAC 합병, 거래재개 대기 등) → 개별 판단
    """
    __tablename__ = "suspension_classifications"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # 분류 결과
    suspension_type = Column(String(20), nullable=False)  # TYPE_A, TYPE_B, TYPE_C
    suspension_reason = Column(String(500))                # 거래정지 사유 상세

    # 분류 메타데이터
    classified_by = Column(String(50))  # 'auto' 또는 'manual'
    classified_at = Column(DateTime(timezone=True), server_default=func.now())

    # 제약조건
    __table_args__ = (
        UniqueConstraint('company_id', name='uq_suspension_class_company'),
        Index('idx_suspension_class_type', 'suspension_type'),
    )

    def __repr__(self):
        return f"<SuspensionClassification(company_id={self.company_id}, type={self.suspension_type})>"
