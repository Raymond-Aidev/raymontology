"""
ML 예측 결과 저장 모델

배치 추론 결과를 기업별로 저장
"""
from sqlalchemy import Column, String, Numeric, DateTime, Date, ForeignKey, UniqueConstraint, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.database import Base


class RiskPrediction(Base):
    """
    ML 예측 결과 테이블

    배치 추론으로 산출된 기업별 악화확률(%)과 위험 요인을 저장
    """
    __tablename__ = "risk_predictions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    prediction_date = Column(Date, nullable=False)

    # 예측 결과
    deterioration_probability = Column(Numeric(5, 4), nullable=False)  # 0.0000 ~ 1.0000
    risk_level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_score = Column(Numeric(5, 4))

    # 피처 중요도 (SHAP)
    top_risk_factors = Column(JSONB)  # [{"feature": "cb_count_1y", "contribution": 0.15, "value": 2.5}, ...]

    # 모델 정보
    model_version = Column(String(50), nullable=False)
    feature_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("ml_features.id"), nullable=True)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 제약조건
    __table_args__ = (
        UniqueConstraint('company_id', 'prediction_date', 'model_version',
                         name='uq_risk_predictions_company_date_model'),
        Index('idx_risk_predictions_company', 'company_id', 'prediction_date'),
        Index('idx_risk_predictions_level', 'risk_level'),
    )

    def __repr__(self):
        return f"<RiskPrediction(company_id={self.company_id}, prob={self.deterioration_probability}, level={self.risk_level})>"
