"""
재무지표 API 엔드포인트

회사 재무제표 및 계산된 지표 조회
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Company, FinancialStatement
from app.services.financial_metrics import FinancialMetricsCalculator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financials", tags=["financials"])


# Response Models
class FinancialMetricsResponse(BaseModel):
    """재무지표 응답"""
    company_id: str
    company_name: str
    cash_assets_billion: Optional[float]
    revenue_cagr: Optional[float]
    ar_turnover: Optional[float]
    ap_turnover: Optional[float]
    inventory_turnover: Optional[float]
    debt_ratio: Optional[float]
    current_ratio: Optional[float]
    calculated_at: str


class HealthAnalysisResponse(BaseModel):
    """재무 건전성 분석 응답"""
    company_id: str
    company_name: str
    health_score: float
    metrics: Dict[str, Optional[float]]
    warnings: list[str]
    strengths: list[str]
    analyzed_at: str


class FinancialStatementResponse(BaseModel):
    """재무제표 응답"""
    id: str
    fiscal_year: int
    quarter: Optional[str]
    statement_date: str
    report_type: str
    # Balance Sheet
    cash_and_equivalents: Optional[int]
    short_term_investments: Optional[int]
    accounts_receivable: Optional[int]
    inventory: Optional[int]
    current_assets: Optional[int]
    non_current_assets: Optional[int]
    total_assets: Optional[int]
    accounts_payable: Optional[int]
    short_term_debt: Optional[int]
    current_liabilities: Optional[int]
    long_term_debt: Optional[int]
    non_current_liabilities: Optional[int]
    total_liabilities: Optional[int]
    capital_stock: Optional[int]
    retained_earnings: Optional[int]
    total_equity: Optional[int]
    # Income Statement
    revenue: Optional[int]
    cost_of_sales: Optional[int]
    gross_profit: Optional[int]
    operating_expenses: Optional[int]
    operating_profit: Optional[int]
    net_income: Optional[int]
    # Cash Flow
    operating_cash_flow: Optional[int]
    investing_cash_flow: Optional[int]
    financing_cash_flow: Optional[int]


# Dependencies
async def get_db():
    """Database session 제공"""
    async with AsyncSessionLocal() as session:
        yield session


# Endpoints
@router.get("/companies/{company_id}/metrics", response_model=FinancialMetricsResponse)
async def get_company_metrics(
    company_id: str,
    recalculate: bool = Query(False, description="강제 재계산"),
    db: AsyncSession = Depends(get_db)
):
    """
    회사 재무지표 조회 (7개 핵심 지표)

    - 현금자산총액 (억원)
    - 매출 CAGR (2022-2024, %)
    - 매출채권 회전율 (회)
    - 매입채무 회전율 (회)
    - 재고자산 회전율 (회)
    - 부채비율 (%)
    - 유동비율 (%)
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 재무지표 계산
        calculator = FinancialMetricsCalculator()
        metrics = await calculator.get_company_metrics(db, company_id)

        return FinancialMetricsResponse(
            company_id=company_id,
            company_name=company.name,
            cash_assets_billion=metrics["cash_assets_billion"],
            revenue_cagr=metrics["revenue_cagr"],
            ar_turnover=metrics["ar_turnover"],
            ap_turnover=metrics["ap_turnover"],
            inventory_turnover=metrics["inventory_turnover"],
            debt_ratio=metrics["debt_ratio"],
            current_ratio=metrics["current_ratio"],
            calculated_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/health", response_model=HealthAnalysisResponse)
async def get_company_health(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    회사 재무 건전성 분석

    - 종합 건전성 점수 (0-100)
    - 경고 사항
    - 강점
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 건전성 분석
        calculator = FinancialMetricsCalculator()
        health = await calculator.analyze_company_health(db, company_id)

        return HealthAnalysisResponse(
            company_id=company_id,
            company_name=company.name,
            health_score=health["health_score"],
            metrics=health["metrics"],
            warnings=health["warnings"],
            strengths=health["strengths"],
            analyzed_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/statements", response_model=list[FinancialStatementResponse])
async def get_company_statements(
    company_id: str,
    fiscal_year: Optional[int] = Query(None, description="특정 연도"),
    quarter: Optional[str] = Query(None, description="분기 (Q1, Q2, Q3, Q4)"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    회사 재무제표 시계열 조회

    - 연도별/분기별 필터링
    - 최신순 정렬
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 재무제표 조회
        query = select(FinancialStatement).where(
            FinancialStatement.company_id == company_id
        )

        if fiscal_year:
            query = query.where(FinancialStatement.fiscal_year == fiscal_year)

        if quarter:
            query = query.where(FinancialStatement.quarter == quarter)

        query = query.order_by(
            FinancialStatement.fiscal_year.desc(),
            FinancialStatement.quarter.desc()
        ).limit(limit)

        result = await db.execute(query)
        statements = result.scalars().all()

        return [
            FinancialStatementResponse(
                id=str(stmt.id),
                fiscal_year=stmt.fiscal_year,
                quarter=stmt.quarter,
                statement_date=stmt.statement_date.isoformat() if stmt.statement_date else None,
                report_type=stmt.report_type,
                # Balance Sheet
                cash_and_equivalents=stmt.cash_and_equivalents,
                short_term_investments=stmt.short_term_investments,
                accounts_receivable=stmt.accounts_receivable,
                inventory=stmt.inventory,
                current_assets=stmt.current_assets,
                non_current_assets=stmt.non_current_assets,
                total_assets=stmt.total_assets,
                accounts_payable=stmt.accounts_payable,
                short_term_debt=stmt.short_term_debt,
                current_liabilities=stmt.current_liabilities,
                long_term_debt=stmt.long_term_debt,
                non_current_liabilities=stmt.non_current_liabilities,
                total_liabilities=stmt.total_liabilities,
                capital_stock=stmt.capital_stock,
                retained_earnings=stmt.retained_earnings,
                total_equity=stmt.total_equity,
                # Income Statement
                revenue=stmt.revenue,
                cost_of_sales=stmt.cost_of_sales,
                gross_profit=stmt.gross_profit,
                operating_expenses=stmt.operating_expenses,
                operating_profit=stmt.operating_profit,
                net_income=stmt.net_income,
                # Cash Flow
                operating_cash_flow=stmt.operating_cash_flow,
                investing_cash_flow=stmt.investing_cash_flow,
                financing_cash_flow=stmt.financing_cash_flow
            )
            for stmt in statements
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching statements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
