"""
RaymondsIndex v3.0 Sub-Index 계산기 모듈

각 Calculator는 원본 지표 계산 + 정규화를 담당합니다.

- CEICalculator: Capital Efficiency Index (자본 효율성) - 20%
- RIICalculator: Reinvestment Intensity Index (재투자 강도) - 35% ⭐ 핵심
- CGICalculator: Cash Governance Index (현금 거버넌스) - 25%
- MAICalculator: Momentum Alignment Index (모멘텀 정합성) - 20%
"""

from .base import SubIndexCalculator, CalculationResult
from .cei import CEICalculator
from .rii import RIICalculator
from .cgi import CGICalculator
from .mai import MAICalculator

__all__ = [
    "SubIndexCalculator",
    "CalculationResult",
    "CEICalculator",
    "RIICalculator",
    "CGICalculator",
    "MAICalculator",
]
