"""
ML 예측 API 엔드포인트 (Phase 8)

FastAPI 라우터로 악화 확률 조회 API 제공

엔드포인트:
    GET /api/ml/predictions/{company_id} - 단일 기업 예측 조회
    GET /api/ml/predictions - 전체 예측 리스트 (페이징)
    GET /api/ml/predictions/high-risk - 고위험 기업 목록
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# app.database에서 세션 의존성 가져오기 (기존 프로젝트 구조 활용)
# from app.database import get_async_session

router = APIRouter(prefix="/api/ml", tags=["ML Predictions"])


# =============================================================================
# Response Schemas
# =============================================================================

class PredictionResponse(BaseModel):
    """단일 예측 응답"""
    company_id: str
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    prediction_date: date
    deterioration_prob: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    model_version: str
    
    class Config:
        from_attributes = True


class PredictionListResponse(BaseModel):
    """예측 목록 응답"""
    total: int
    page: int
    limit: int
    data: List[PredictionResponse]


class HighRiskCompanyResponse(BaseModel):
    """고위험 기업 응답"""
    company_id: str
    company_name: str
    ticker: str
    market: Optional[str] = None
    deterioration_prob: float
    risk_level: str
    risk_factors: Optional[List[str]] = None


# =============================================================================
# API Endpoints
# =============================================================================

# 주의: 아래 엔드포인트들은 기존 FastAPI 앱에 통합되어야 합니다.
# app/main.py에서 router를 include해야 합니다.

@router.get("/predictions/{company_id}", response_model=PredictionResponse)
async def get_prediction(
    company_id: UUID,
    db: AsyncSession = None,  # Depends(get_async_session)
):
    """
    단일 기업의 악화 확률 예측 조회
    
    Args:
        company_id: 기업 UUID
        
    Returns:
        PredictionResponse: 예측 결과
    """
    result = await db.execute(text("""
        SELECT 
            rp.company_id::text,
            c.name as company_name,
            c.ticker,
            rp.prediction_date,
            rp.deterioration_prob,
            rp.risk_level,
            rp.model_version
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE rp.company_id = :cid
        ORDER BY rp.prediction_date DESC
        LIMIT 1
    """), {'cid': str(company_id)})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="예측 데이터 없음")
    
    return PredictionResponse(
        company_id=row.company_id,
        company_name=row.company_name,
        ticker=row.ticker,
        prediction_date=row.prediction_date,
        deterioration_prob=float(row.deterioration_prob),
        risk_level=row.risk_level,
        model_version=row.model_version,
    )


@router.get("/predictions", response_model=PredictionListResponse)
async def list_predictions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, regex="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    min_prob: Optional[float] = Query(None, ge=0, le=1),
    db: AsyncSession = None,  # Depends(get_async_session)
):
    """
    전체 예측 리스트 조회 (페이징)
    
    Args:
        page: 페이지 번호 (1부터)
        limit: 페이지당 결과 수
        risk_level: 위험 등급 필터 (LOW, MEDIUM, HIGH, CRITICAL)
        min_prob: 최소 확률 필터
        
    Returns:
        PredictionListResponse: 예측 목록
    """
    offset = (page - 1) * limit
    
    # 필터 조건 구성
    where_clauses = []
    params = {'limit': limit, 'offset': offset}
    
    if risk_level:
        where_clauses.append("rp.risk_level = :risk_level")
        params['risk_level'] = risk_level
    
    if min_prob is not None:
        where_clauses.append("rp.deterioration_prob >= :min_prob")
        params['min_prob'] = min_prob
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # 총 개수 조회
    count_result = await db.execute(text(f"""
        SELECT COUNT(*) 
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        {where_sql}
    """), params)
    total = count_result.scalar()
    
    # 데이터 조회
    result = await db.execute(text(f"""
        SELECT 
            rp.company_id::text,
            c.name as company_name,
            c.ticker,
            rp.prediction_date,
            rp.deterioration_prob,
            rp.risk_level,
            rp.model_version
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        {where_sql}
        ORDER BY rp.deterioration_prob DESC
        LIMIT :limit OFFSET :offset
    """), params)
    
    rows = result.fetchall()
    
    data = [
        PredictionResponse(
            company_id=row.company_id,
            company_name=row.company_name,
            ticker=row.ticker,
            prediction_date=row.prediction_date,
            deterioration_prob=float(row.deterioration_prob),
            risk_level=row.risk_level,
            model_version=row.model_version,
        )
        for row in rows
    ]
    
    return PredictionListResponse(
        total=total,
        page=page,
        limit=limit,
        data=data,
    )


@router.get("/predictions/high-risk", response_model=List[HighRiskCompanyResponse])
async def get_high_risk_companies(
    limit: int = Query(20, ge=1, le=100),
    min_prob: float = Query(0.5, ge=0, le=1),
    db: AsyncSession = None,  # Depends(get_async_session)
):
    """
    고위험 기업 목록 조회
    
    Args:
        limit: 최대 결과 수
        min_prob: 최소 확률 (기본 0.5 = HIGH 이상)
        
    Returns:
        List[HighRiskCompanyResponse]: 고위험 기업 목록
    """
    result = await db.execute(text("""
        SELECT 
            rp.company_id::text,
            c.name as company_name,
            c.ticker,
            c.market,
            rp.deterioration_prob,
            rp.risk_level
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE rp.deterioration_prob >= :min_prob
          AND c.listing_status = 'LISTED'
        ORDER BY rp.deterioration_prob DESC
        LIMIT :limit
    """), {'min_prob': min_prob, 'limit': limit})
    
    rows = result.fetchall()
    
    return [
        HighRiskCompanyResponse(
            company_id=row.company_id,
            company_name=row.company_name,
            ticker=row.ticker,
            market=row.market,
            deterioration_prob=float(row.deterioration_prob),
            risk_level=row.risk_level,
        )
        for row in rows
    ]


# =============================================================================
# 기존 앱에 라우터 통합 방법
# =============================================================================
"""
app/main.py에 다음 코드 추가:

from ml.api.prediction_routes import router as ml_router
app.include_router(ml_router)
"""
