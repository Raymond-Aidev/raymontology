"""
Company Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ============================================================================
# Response Schemas
# ============================================================================

class CompanyBase(BaseModel):
    """회사 기본 정보"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticker: Optional[str]
    name: str
    name_en: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market: Optional[str]


class CompanyDetail(CompanyBase):
    """회사 상세 정보"""
    business_number: Optional[str]

    # 재무 지표
    market_cap: Optional[float]
    revenue: Optional[float]
    net_income: Optional[float]
    total_assets: Optional[float]

    # 리스크 지표
    ownership_concentration: Optional[float]
    affiliate_transaction_ratio: Optional[float]
    cb_issuance_count: Optional[float]

    # 온톨로지
    ontology_object_id: Optional[str]

    # 추가 속성
    properties: Dict[str, Any] = {}

    # 메타데이터
    created_at: datetime
    updated_at: datetime


class CompanyListItem(CompanyBase):
    """회사 목록 아이템"""
    market_cap: Optional[float]
    ownership_concentration: Optional[float]


class CompanySearchResult(BaseModel):
    """검색 결과"""
    total: int
    items: List[CompanyListItem]
    page: int
    page_size: int
    has_next: bool


# ============================================================================
# Request Schemas
# ============================================================================

class CompanySearchParams(BaseModel):
    """검색 파라미터"""
    q: Optional[str] = Field(None, description="검색어 (회사명, 티커)")
    market: Optional[str] = Field(None, description="시장 (KOSPI, KOSDAQ, KONEX)")
    sector: Optional[str] = Field(None, description="섹터")
    min_market_cap: Optional[float] = Field(None, description="최소 시가총액")
    max_market_cap: Optional[float] = Field(None, description="최대 시가총액")
    min_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="최소 리스크 점수")
    page: int = Field(1, ge=1, description="페이지 번호")
    page_size: int = Field(20, ge=1, le=100, description="페이지 크기")
    sort_by: str = Field("market_cap", description="정렬 기준")
    sort_order: str = Field("desc", description="정렬 순서 (asc, desc)")


class CompanyCreate(BaseModel):
    """회사 생성"""
    ticker: Optional[str]
    name: str
    name_en: Optional[str]
    business_number: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market: Optional[str]
    market_cap: Optional[float]
    revenue: Optional[float]
    properties: Dict[str, Any] = {}


class CompanyUpdate(BaseModel):
    """회사 업데이트"""
    name: Optional[str] = None
    name_en: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    market_cap: Optional[float] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    ownership_concentration: Optional[float] = None
    affiliate_transaction_ratio: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class CompanyStats(BaseModel):
    """회사 통계"""
    total_companies: int
    by_market: Dict[str, int]
    by_sector: Dict[str, int]
    avg_market_cap: Optional[float]
    total_market_cap: Optional[float]
