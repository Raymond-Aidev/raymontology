"""
Risk Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime


class RiskFactor(BaseModel):
    """리스크 요소"""
    name: str
    value: float
    score: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)


class RiskComponent(BaseModel):
    """리스크 컴포넌트"""
    score: float = Field(..., ge=0.0, le=1.0, description="컴포넌트 점수")
    factors: List[RiskFactor] = Field(default_factory=list, description="세부 요소")
    details: Dict[str, Any] = Field(default_factory=dict, description="상세 정보")


class RiskScoreResponse(BaseModel):
    """리스크 점수 응답"""
    company_id: str
    company_name: str
    total_score: float = Field(..., ge=0.0, le=1.0, description="종합 리스크 점수")
    risk_level: str = Field(..., description="리스크 레벨 (LOW, MEDIUM, HIGH, CRITICAL)")

    components: Dict[str, RiskComponent] = Field(
        ...,
        description="5가지 리스크 컴포넌트"
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="경고 메시지"
    )

    calculated_at: str = Field(..., description="계산 시각 (ISO 8601)")


class RiskComponentNames:
    """리스크 컴포넌트 이름"""
    INFORMATION_ASYMMETRY = "information_asymmetry"
    POWER_CONCENTRATION = "power_concentration"
    TRANSACTION_PATTERN = "transaction_pattern"
    FUND_RISK = "fund_risk"
    NETWORK_RISK = "network_risk"


class RiskLevel:
    """리스크 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
