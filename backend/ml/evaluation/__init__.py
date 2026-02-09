"""
평가 지표 모듈

평가 지표:
- AUC-ROC (목표: >= 0.75)
- Precision@10% (목표: >= 0.50)
- Recall (목표: >= 0.70)
- Brier Score (목표: <= 0.15)
"""

from .metrics import ModelEvaluator

__all__ = ['ModelEvaluator']
