"""
ML Pipeline - 관계형 리스크 악화가능성 예측 모델

모듈 구조:
- features/: 피처 엔지니어링 (임원 네트워크, CB 투자자, 대주주, 4대 인덱스)
- labels/: 라벨 생성 (악화 이벤트 정의)
- models/: 앙상블 모델 (XGBoost, LightGBM, CatBoost)
- inference/: 추론 서비스
- evaluation/: 평가 지표

버전: 1.0.0
작성일: 2026-02-05
"""

__version__ = "1.0.0"
