"""
Financial Ratios API 엔드포인트

재무건전성 평가 시스템 API
- 기업별 재무비율 조회
- 재무비율 히스토리 (3개년 추이)
- 재무건전성 랭킹
- 통계 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
import logging

from app.database import get_db
from app.models.financial_ratios import FinancialRatios
from app.models.financial_details import FinancialDetails
from app.models.companies import Company
from app.services.financial_ratios_calculator import FinancialRatiosCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financial-ratios", tags=["FinancialRatios"])


# ============================================================================
# Response Formatters
# ============================================================================

def format_ratios_response(ratios: FinancialRatios, company: Optional[Company] = None) -> dict:
    """FinancialRatios 응답 포맷"""
    response = ratios.to_dict()
    if company:
        response["company_name"] = company.name
        response["company_ticker"] = company.ticker
        response["company_market"] = company.market
        response["company_sector"] = company.sector
        response["company_type"] = company.company_type
    return response


def format_summary_response(ratios: FinancialRatios, company: Optional[Company] = None) -> dict:
    """요약 응답 포맷 (랭킹용)"""
    response = ratios.to_summary_dict()
    if company:
        response["company_name"] = company.name
        response["company_ticker"] = company.ticker
        response["company_market"] = company.market
        response["company_sector"] = company.sector
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/{company_id}")
async def get_financial_ratios(
    company_id: UUID = Path(..., description="회사 UUID"),
    year: Optional[int] = Query(None, description="연도 (기본: 최신)"),
    db: AsyncSession = Depends(get_db)
):
    """
    기업별 재무비율 조회

    6개 카테고리, 25개 재무비율 및 종합 재무건전성 등급 반환
    """
    try:
        # 회사 존재 확인
        company_query = select(Company).where(Company.id == company_id)
        company_result = await db.execute(company_query)
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_id}")

        # 재무비율 조회
        query = (
            select(FinancialRatios)
            .where(FinancialRatios.company_id == company_id)
        )

        if year:
            query = query.where(FinancialRatios.fiscal_year == year)
        else:
            # 최신 연도
            query = query.order_by(desc(FinancialRatios.fiscal_year))

        result = await db.execute(query)
        ratios = result.scalars().first()

        if not ratios:
            # 재무비율이 없으면 즉석 계산 시도
            return await _calculate_ratios_on_demand(db, company_id, company, year)

        return format_ratios_response(ratios, company)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financial ratios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/history")
async def get_financial_ratios_history(
    company_id: UUID = Path(..., description="회사 UUID"),
    years: int = Query(3, ge=1, le=5, description="조회 연도 수"),
    db: AsyncSession = Depends(get_db)
):
    """
    재무비율 히스토리 (3개년 추이)

    연도별 재무비율 변화를 조회합니다.
    """
    try:
        # 회사 존재 확인
        company_query = select(Company).where(Company.id == company_id)
        company_result = await db.execute(company_query)
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_id}")

        # 최근 N년 재무비율 조회
        query = (
            select(FinancialRatios)
            .where(FinancialRatios.company_id == company_id)
            .order_by(desc(FinancialRatios.fiscal_year))
            .limit(years)
        )

        result = await db.execute(query)
        ratios_list = result.scalars().all()

        if not ratios_list:
            raise HTTPException(status_code=404, detail="No financial ratios data found")

        # 연도별 데이터 구성
        history = []
        for ratios in reversed(ratios_list):  # 오래된 것부터
            history.append(ratios.to_dict())

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "company_ticker": company.ticker,
            "years_count": len(history),
            "history": history,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financial ratios history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking")
async def get_financial_ratios_ranking(
    year: Optional[int] = Query(None, description="연도 (기본: 최신)"),
    grade: Optional[str] = Query(None, description="등급 필터 (A+, A, B+, B, B-, C+, C)"),
    risk_level: Optional[str] = Query(None, description="위험수준 (LOW, MODERATE, HIGH, CRITICAL)"),
    market: Optional[str] = Query(None, description="시장 필터 (KOSPI, KOSDAQ, KONEX)"),
    sector: Optional[str] = Query(None, description="업종 필터"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("score", description="정렬 기준 (score, stability, profitability, growth, leverage)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    재무건전성 랭킹

    재무건전성 점수 기준 기업 랭킹을 조회합니다.
    """
    try:
        # 연도 결정
        if not year:
            year_query = select(func.max(FinancialRatios.fiscal_year))
            year_result = await db.execute(year_query)
            year = year_result.scalar() or 2025

        # 기본 쿼리
        query = (
            select(FinancialRatios, Company)
            .join(Company, FinancialRatios.company_id == Company.id)
            .where(FinancialRatios.fiscal_year == year)
        )

        # 필터 적용
        if grade:
            query = query.where(FinancialRatios.financial_health_grade == grade)
        if risk_level:
            query = query.where(FinancialRatios.financial_risk_level == risk_level)
        if market:
            query = query.where(Company.market == market)
        if sector:
            query = query.where(Company.sector == sector)

        # ETF/SPAC 제외
        query = query.where(
            or_(Company.company_type == None, Company.company_type.notin_(['ETF', 'SPAC']))
        )

        # 정렬
        sort_column_map = {
            'score': FinancialRatios.financial_health_score,
            'stability': FinancialRatios.stability_score,
            'profitability': FinancialRatios.profitability_score,
            'growth': FinancialRatios.growth_score,
            'leverage': FinancialRatios.leverage_score,
        }
        sort_column = sort_column_map.get(sort_by, FinancialRatios.financial_health_score)

        if sort_order == 'asc':
            query = query.order_by(sort_column.asc().nullslast())
        else:
            query = query.order_by(sort_column.desc().nullsfirst())

        # 전체 카운트
        count_query = (
            select(func.count())
            .select_from(FinancialRatios)
            .join(Company, FinancialRatios.company_id == Company.id)
            .where(FinancialRatios.fiscal_year == year)
        )
        if grade:
            count_query = count_query.where(FinancialRatios.financial_health_grade == grade)
        if risk_level:
            count_query = count_query.where(FinancialRatios.financial_risk_level == risk_level)
        if market:
            count_query = count_query.where(Company.market == market)
        if sector:
            count_query = count_query.where(Company.sector == sector)
        count_query = count_query.where(
            or_(Company.company_type == None, Company.company_type.notin_(['ETF', 'SPAC']))
        )

        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # 페이지네이션
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # 응답 구성
        rankings = []
        for idx, (ratios, company) in enumerate(rows, start=offset + 1):
            item = format_summary_response(ratios, company)
            item["rank"] = idx
            rankings.append(item)

        return {
            "year": year,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "results": rankings,
        }

    except Exception as e:
        logger.error(f"Error fetching financial ratios ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_financial_ratios_statistics(
    year: Optional[int] = Query(None, description="연도 (기본: 최신)"),
    db: AsyncSession = Depends(get_db)
):
    """
    재무건전성 통계

    등급별 분포, 위험수준별 분포, 카테고리 평균 등
    """
    try:
        # 연도 결정
        if not year:
            year_query = select(func.max(FinancialRatios.fiscal_year))
            year_result = await db.execute(year_query)
            year = year_result.scalar() or 2025

        # 전체 통계
        total_query = (
            select(func.count(FinancialRatios.id))
            .where(FinancialRatios.fiscal_year == year)
        )
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0

        # 등급별 분포
        grade_query = (
            select(
                FinancialRatios.financial_health_grade,
                func.count(FinancialRatios.id).label('count')
            )
            .where(FinancialRatios.fiscal_year == year)
            .group_by(FinancialRatios.financial_health_grade)
            .order_by(FinancialRatios.financial_health_grade)
        )
        grade_result = await db.execute(grade_query)
        grade_distribution = {row[0]: row[1] for row in grade_result.all() if row[0]}

        # 위험수준별 분포
        risk_query = (
            select(
                FinancialRatios.financial_risk_level,
                func.count(FinancialRatios.id).label('count')
            )
            .where(FinancialRatios.fiscal_year == year)
            .group_by(FinancialRatios.financial_risk_level)
        )
        risk_result = await db.execute(risk_query)
        risk_distribution = {row[0]: row[1] for row in risk_result.all() if row[0]}

        # 카테고리별 평균
        avg_query = (
            select(
                func.avg(FinancialRatios.stability_score).label('stability'),
                func.avg(FinancialRatios.profitability_score).label('profitability'),
                func.avg(FinancialRatios.growth_score).label('growth'),
                func.avg(FinancialRatios.activity_score).label('activity'),
                func.avg(FinancialRatios.cashflow_score).label('cashflow'),
                func.avg(FinancialRatios.leverage_score).label('leverage'),
                func.avg(FinancialRatios.financial_health_score).label('overall'),
            )
            .where(FinancialRatios.fiscal_year == year)
        )
        avg_result = await db.execute(avg_query)
        avg_row = avg_result.one()

        category_averages = {
            'stability': round(float(avg_row.stability), 2) if avg_row.stability else 0,
            'profitability': round(float(avg_row.profitability), 2) if avg_row.profitability else 0,
            'growth': round(float(avg_row.growth), 2) if avg_row.growth else 0,
            'activity': round(float(avg_row.activity), 2) if avg_row.activity else 0,
            'cashflow': round(float(avg_row.cashflow), 2) if avg_row.cashflow else 0,
            'leverage': round(float(avg_row.leverage), 2) if avg_row.leverage else 0,
            'overall': round(float(avg_row.overall), 2) if avg_row.overall else 0,
        }

        # 적자 기업 수
        loss_query = (
            select(func.count(FinancialRatios.id))
            .where(FinancialRatios.fiscal_year == year)
            .where(FinancialRatios.is_loss_making == True)
        )
        loss_result = await db.execute(loss_query)
        loss_count = loss_result.scalar() or 0

        return {
            "year": year,
            "total_companies": total_count,
            "grade_distribution": grade_distribution,
            "risk_distribution": risk_distribution,
            "category_averages": category_averages,
            "loss_making_companies": loss_count,
            "loss_making_ratio": round(loss_count / total_count * 100, 2) if total_count > 0 else 0,
        }

    except Exception as e:
        logger.error(f"Error fetching financial ratios statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/sector")
async def get_sector_statistics(
    year: Optional[int] = Query(None, description="연도 (기본: 최신)"),
    db: AsyncSession = Depends(get_db)
):
    """
    업종별 재무건전성 통계
    """
    try:
        # 연도 결정
        if not year:
            year_query = select(func.max(FinancialRatios.fiscal_year))
            year_result = await db.execute(year_query)
            year = year_result.scalar() or 2025

        # 업종별 통계
        sector_query = (
            select(
                Company.sector,
                func.count(FinancialRatios.id).label('company_count'),
                func.avg(FinancialRatios.financial_health_score).label('avg_score'),
                func.avg(FinancialRatios.stability_score).label('avg_stability'),
                func.avg(FinancialRatios.profitability_score).label('avg_profitability'),
                func.avg(FinancialRatios.leverage_score).label('avg_leverage'),
            )
            .join(Company, FinancialRatios.company_id == Company.id)
            .where(FinancialRatios.fiscal_year == year)
            .where(Company.sector != None)
            .group_by(Company.sector)
            .order_by(desc('avg_score'))
        )

        result = await db.execute(sector_query)
        sectors = []
        for row in result.all():
            sectors.append({
                'sector': row.sector,
                'company_count': row.company_count,
                'avg_score': round(float(row.avg_score), 2) if row.avg_score else 0,
                'avg_stability': round(float(row.avg_stability), 2) if row.avg_stability else 0,
                'avg_profitability': round(float(row.avg_profitability), 2) if row.avg_profitability else 0,
                'avg_leverage': round(float(row.avg_leverage), 2) if row.avg_leverage else 0,
            })

        return {
            "year": year,
            "sectors": sectors,
        }

    except Exception as e:
        logger.error(f"Error fetching sector statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================

async def _calculate_ratios_on_demand(
    db: AsyncSession,
    company_id: UUID,
    company: Company,
    year: Optional[int]
) -> dict:
    """
    재무비율 즉석 계산 (DB에 없는 경우)
    """
    try:
        # 최신 재무상세 조회
        query = (
            select(FinancialDetails)
            .where(FinancialDetails.company_id == company_id)
            .order_by(desc(FinancialDetails.fiscal_year))
        )
        if year:
            query = query.where(FinancialDetails.fiscal_year == year)

        result = await db.execute(query)
        current_fd = result.scalars().first()

        if not current_fd:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data available for company {company_id}"
            )

        # 전년 데이터 조회 (성장성 계산용)
        prev_query = (
            select(FinancialDetails)
            .where(FinancialDetails.company_id == company_id)
            .where(FinancialDetails.fiscal_year == current_fd.fiscal_year - 1)
        )
        prev_result = await db.execute(prev_query)
        previous_fd = prev_result.scalars().first()

        # 계산기 실행
        calculator = FinancialRatiosCalculator()

        current_data = _fd_to_dict(current_fd)
        previous_data = _fd_to_dict(previous_fd) if previous_fd else None

        calc_result = calculator.calculate(
            current_data=current_data,
            previous_data=previous_data,
            company_id=str(company_id),
            fiscal_year=current_fd.fiscal_year,
        )

        # 응답 구성
        response = calculator.result_to_dict(calc_result)
        response["company_name"] = company.name
        response["company_ticker"] = company.ticker
        response["company_market"] = company.market
        response["company_sector"] = company.sector
        response["calculated_on_demand"] = True

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating ratios on demand: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fd_to_dict(fd: FinancialDetails) -> dict:
    """FinancialDetails 모델을 딕셔너리로 변환"""
    return {
        'current_assets': fd.current_assets,
        'cash_and_equivalents': fd.cash_and_equivalents,
        'short_term_investments': fd.short_term_investments,
        'trade_and_other_receivables': fd.trade_and_other_receivables,
        'inventories': fd.inventories,
        'non_current_assets': fd.non_current_assets,
        'tangible_assets': fd.tangible_assets,
        'intangible_assets': fd.intangible_assets,
        'total_assets': fd.total_assets,
        'current_liabilities': fd.current_liabilities,
        'trade_payables': fd.trade_payables,
        'short_term_borrowings': fd.short_term_borrowings,
        'non_current_liabilities': fd.non_current_liabilities,
        'long_term_borrowings': fd.long_term_borrowings,
        'bonds_payable': fd.bonds_payable,
        'total_liabilities': fd.total_liabilities,
        'total_equity': fd.total_equity,
        'capital_stock': fd.capital_stock,
        'capital_surplus': fd.capital_surplus,
        'retained_earnings': fd.retained_earnings,
        'treasury_stock': fd.treasury_stock,
        'revenue': fd.revenue,
        'cost_of_sales': fd.cost_of_sales,
        'gross_profit': fd.gross_profit,
        'operating_income': fd.operating_income,
        'net_income': fd.net_income,
        'depreciation_expense': fd.depreciation_expense,
        'interest_expense': fd.interest_expense,
        'interest_income': fd.interest_income,
        'income_before_tax': fd.income_before_tax,
        'tax_expense': fd.tax_expense,
        'amortization': fd.amortization,
        'operating_cash_flow': fd.operating_cash_flow,
        'investing_cash_flow': fd.investing_cash_flow,
        'financing_cash_flow': fd.financing_cash_flow,
        'capex': fd.capex,
        'intangible_acquisition': fd.intangible_acquisition,
        'dividend_paid': fd.dividend_paid,
    }
