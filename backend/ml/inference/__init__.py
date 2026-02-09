"""
추론 서비스 모듈

API 엔드포인트:
- POST /api/ml/predict: 단일 기업 예측
- POST /api/ml/predict/batch: 배치 예측
- GET /api/ml/models/active: 활성 모델 정보
"""

from .predictor import RiskPredictor

__all__ = ['RiskPredictor']
