"""
ML 모델 메타데이터 저장 모델

학습된 모델의 성능 지표와 파일 경로를 관리
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class MLModel(Base):
    """
    ML 모델 메타데이터 테이블

    학습된 모델 버전, 성능 지표, 파일 경로 관리
    """
    __tablename__ = "ml_models"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version = Column(String(50), nullable=False, unique=True)
    model_type = Column(String(50), nullable=False)  # ensemble_xgb_lgb_cat

    # 성능 지표
    auc_roc = Column(Numeric(5, 4))
    precision_at_10 = Column(Numeric(5, 4))
    recall = Column(Numeric(5, 4))
    brier_score = Column(Numeric(5, 4))

    # 학습 정보
    training_samples = Column(Integer)
    positive_samples = Column(Integer)
    feature_count = Column(Integer)
    training_date = Column(Date)

    # 모델 파일
    model_path = Column(String(500))  # backend/ml/saved_models/{version}_{type}_{date}.pkl

    # 상태
    is_active = Column(Boolean, default=False)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<MLModel(version={self.model_version}, active={self.is_active}, auc={self.auc_roc})>"
