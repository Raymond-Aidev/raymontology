"""
ML 예측 API 엔드포인트

악화 확률 예측 조회 API
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/ml", tags=["ML Predictions"])


# Response Schemas
class PredictionResponse(BaseModel):
    """단일 예측 응답"""
    company_id: str
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    prediction_date: date
    deterioration_probability: float
    risk_level: str
    model_version: Optional[str] = None

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
    deterioration_probability: float
    risk_level: str


@router.get("/predictions/{company_id}", response_model=PredictionResponse)
async def get_prediction(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    단일 기업의 악화 확률 예측 조회
    """
    result = await db.execute(text("""
        SELECT
            rp.company_id::text,
            c.name as company_name,
            c.ticker,
            rp.prediction_date,
            rp.deterioration_probability,
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
        deterioration_probability=float(row.deterioration_probability),
        risk_level=row.risk_level,
        model_version=row.model_version,
    )


@router.get("/predictions", response_model=PredictionListResponse)
async def list_predictions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    min_prob: Optional[float] = Query(None, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """
    전체 예측 리스트 조회 (페이징)
    """
    offset = (page - 1) * limit

    # 필터 조건 구성
    where_clauses = []
    params = {'limit': limit, 'offset': offset}

    if risk_level:
        where_clauses.append("rp.risk_level = :risk_level")
        params['risk_level'] = risk_level

    if min_prob is not None:
        where_clauses.append("rp.deterioration_probability >= :min_prob")
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
            rp.deterioration_probability,
            rp.risk_level,
            rp.model_version
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        {where_sql}
        ORDER BY rp.deterioration_probability DESC
        LIMIT :limit OFFSET :offset
    """), params)

    rows = result.fetchall()

    data = [
        PredictionResponse(
            company_id=row.company_id,
            company_name=row.company_name,
            ticker=row.ticker,
            prediction_date=row.prediction_date,
            deterioration_probability=float(row.deterioration_probability),
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
    db: AsyncSession = Depends(get_db),
):
    """
    고위험 기업 목록 조회 (확률 0.5 이상)
    """
    result = await db.execute(text("""
        SELECT
            rp.company_id::text,
            c.name as company_name,
            c.ticker,
            c.market,
            rp.deterioration_probability,
            rp.risk_level
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE rp.deterioration_probability >= :min_prob
          AND c.listing_status = 'LISTED'
        ORDER BY rp.deterioration_probability DESC
        LIMIT :limit
    """), {'min_prob': min_prob, 'limit': limit})

    rows = result.fetchall()

    return [
        HighRiskCompanyResponse(
            company_id=row.company_id,
            company_name=row.company_name,
            ticker=row.ticker,
            market=row.market,
            deterioration_probability=float(row.deterioration_probability),
            risk_level=row.risk_level,
        )
        for row in rows
    ]
