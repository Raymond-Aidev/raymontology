"""
Stock Prices API 엔드포인트

월별 종가 데이터 조회 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, func
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
import logging

from app.database import get_db
from app.models.stock_prices import StockPrice
from app.models.companies import Company
from app.services.stock_price_collector import stock_price_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stock-prices", tags=["StockPrices"])


# ============================================================================
# Response Formatters
# ============================================================================

def format_price_response(price: StockPrice) -> dict:
    """StockPrice 응답 포맷"""
    return {
        "id": str(price.id),
        "year_month": price.year_month,
        "price_date": price.price_date.isoformat() if price.price_date else None,
        "close_price": price.close_price,
        "open_price": price.open_price,
        "high_price": price.high_price,
        "low_price": price.low_price,
        "volume": price.volume,
        "change_rate": price.change_rate,
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/status")
async def get_collection_status(
    db: AsyncSession = Depends(get_db)
):
    """
    주가 데이터 수집 현황 조회

    Returns:
        - total_listed_companies: 전체 상장사 수
        - companies_with_prices: 주가 데이터가 있는 기업 수
        - coverage_rate: 커버리지 비율 (%)
        - total_price_records: 전체 가격 레코드 수
        - latest_data_month: 최신 데이터 월
    """
    try:
        status = await stock_price_collector.get_collection_status(db)
        return status
    except Exception as e:
        logger.error(f"수집 현황 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}")
async def get_company_stock_prices(
    company_id: UUID,
    start_month: Optional[str] = Query(None, description="시작 월 (YYYY-MM)", regex=r"^\d{4}-\d{2}$"),
    end_month: Optional[str] = Query(None, description="종료 월 (YYYY-MM)", regex=r"^\d{4}-\d{2}$"),
    limit: int = Query(100, ge=1, le=500, description="최대 결과 수"),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업의 월별 종가 데이터 조회

    Args:
        company_id: 기업 UUID
        start_month: 시작 월 (YYYY-MM 형식, 예: 2022-01)
        end_month: 종료 월 (YYYY-MM 형식, 예: 2024-12)
        limit: 최대 결과 수

    Returns:
        - company: 기업 정보
        - prices: 월별 가격 데이터 리스트
        - summary: 요약 통계
    """
    try:
        # 기업 조회
        company_result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다")

        # 가격 데이터 조회
        query = select(StockPrice).where(StockPrice.company_id == company_id)

        if start_month:
            query = query.where(StockPrice.year_month >= start_month)
        if end_month:
            query = query.where(StockPrice.year_month <= end_month)

        query = query.order_by(asc(StockPrice.year_month)).limit(limit)

        result = await db.execute(query)
        prices = result.scalars().all()

        # 요약 통계 계산
        summary = None
        if prices:
            close_prices = [p.close_price for p in prices if p.close_price]
            if close_prices:
                first_price = close_prices[0]
                last_price = close_prices[-1]
                total_return = ((last_price - first_price) / first_price * 100) if first_price else 0

                summary = {
                    "total_months": len(prices),
                    "first_month": prices[0].year_month,
                    "last_month": prices[-1].year_month,
                    "first_close": first_price,
                    "last_close": last_price,
                    "total_return_pct": round(total_return, 2),
                    "avg_close": round(sum(close_prices) / len(close_prices), 0),
                    "min_close": min(close_prices),
                    "max_close": max(close_prices),
                }

        return {
            "company": {
                "id": str(company.id),
                "name": company.name,
                "ticker": company.ticker,
                "market": company.market,
                "sector": company.sector,
            },
            "prices": [format_price_response(p) for p in prices],
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주가 조회 실패: {company_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}/chart")
async def get_company_chart_data(
    company_id: UUID,
    period: str = Query("3y", description="기간 (1y, 2y, 3y, all)"),
    db: AsyncSession = Depends(get_db)
):
    """
    차트용 데이터 조회 (Recharts/D3 호환 형식)

    Args:
        company_id: 기업 UUID
        period: 조회 기간
            - 1y: 최근 1년 (12개월)
            - 2y: 최근 2년 (24개월)
            - 3y: 최근 3년 (36개월)
            - all: 전체 기간

    Returns:
        - labels: 월 라벨 배열
        - datasets: 차트 데이터셋
        - company: 기업 정보
    """
    try:
        # 기업 조회
        company_result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다")

        # 기간에 따른 시작 월 계산
        now = datetime.now()
        if period == "1y":
            months = 12
        elif period == "2y":
            months = 24
        elif period == "3y":
            months = 36
        else:  # all
            months = None

        # 시작 월 계산
        start_month = None
        if months:
            year = now.year
            month = now.month - months
            while month <= 0:
                month += 12
                year -= 1
            start_month = f"{year:04d}-{month:02d}"

        # 가격 데이터 조회
        query = select(StockPrice).where(StockPrice.company_id == company_id)

        if start_month:
            query = query.where(StockPrice.year_month >= start_month)

        query = query.order_by(asc(StockPrice.year_month))

        result = await db.execute(query)
        prices = result.scalars().all()

        if not prices:
            return {
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "ticker": company.ticker,
                },
                "labels": [],
                "datasets": [],
                "message": "주가 데이터가 없습니다"
            }

        # Recharts/D3 호환 형식으로 변환
        labels = [p.year_month for p in prices]

        # 차트 데이터 (Recharts용)
        chart_data = []
        for p in prices:
            chart_data.append({
                "month": p.year_month,
                "close": p.close_price,
                "open": p.open_price,
                "high": p.high_price,
                "low": p.low_price,
                "volume": p.volume,
                "change": p.change_rate,
            })

        # 성과 요약
        first_price = prices[0].close_price
        last_price = prices[-1].close_price
        total_return = ((last_price - first_price) / first_price * 100) if first_price else 0

        return {
            "company": {
                "id": str(company.id),
                "name": company.name,
                "ticker": company.ticker,
                "market": company.market,
            },
            "period": period,
            "labels": labels,
            "data": chart_data,
            "performance": {
                "start_month": prices[0].year_month,
                "end_month": prices[-1].year_month,
                "start_price": first_price,
                "end_price": last_price,
                "total_return_pct": round(total_return, 2),
                "data_points": len(prices),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"차트 데이터 조회 실패: {company_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_stock_prices(
    company_ids: str = Query(..., description="비교할 기업 ID들 (콤마 구분)"),
    period: str = Query("3y", description="기간 (1y, 2y, 3y, all)"),
    db: AsyncSession = Depends(get_db)
):
    """
    여러 기업 주가 비교 (차트용)

    Args:
        company_ids: 비교할 기업 UUID들 (콤마 구분, 최대 5개)
        period: 조회 기간

    Returns:
        - companies: 기업 정보 목록
        - data: 비교 데이터 (월별)
    """
    try:
        # ID 파싱
        id_list = [UUID(id.strip()) for id in company_ids.split(",")]

        if len(id_list) > 5:
            raise HTTPException(status_code=400, detail="최대 5개 기업까지 비교 가능합니다")

        # 기간 계산
        now = datetime.now()
        if period == "1y":
            months = 12
        elif period == "2y":
            months = 24
        elif period == "3y":
            months = 36
        else:
            months = None

        start_month = None
        if months:
            year = now.year
            month = now.month - months
            while month <= 0:
                month += 12
                year -= 1
            start_month = f"{year:04d}-{month:02d}"

        # 기업별 데이터 조회
        companies_data = []
        all_months = set()

        for company_id in id_list:
            # 기업 정보
            company_result = await db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = company_result.scalar_one_or_none()

            if not company:
                continue

            # 가격 데이터
            query = select(StockPrice).where(StockPrice.company_id == company_id)
            if start_month:
                query = query.where(StockPrice.year_month >= start_month)
            query = query.order_by(asc(StockPrice.year_month))

            result = await db.execute(query)
            prices = result.scalars().all()

            # 월별 데이터 맵
            price_map = {p.year_month: p.close_price for p in prices}
            all_months.update(price_map.keys())

            # 첫 가격 기준 정규화 (100 기준)
            first_price = prices[0].close_price if prices else None
            normalized_map = {}
            if first_price and first_price > 0:
                for month, price in price_map.items():
                    normalized_map[month] = round((price / first_price) * 100, 2)

            companies_data.append({
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "ticker": company.ticker,
                },
                "price_map": price_map,
                "normalized_map": normalized_map,
            })

        # 월별 데이터 통합
        sorted_months = sorted(all_months)

        comparison_data = []
        for month in sorted_months:
            row = {"month": month}
            for i, cd in enumerate(companies_data):
                key = cd["company"]["ticker"] or f"company_{i}"
                row[key] = cd["price_map"].get(month)
                row[f"{key}_normalized"] = cd["normalized_map"].get(month)
            comparison_data.append(row)

        return {
            "companies": [cd["company"] for cd in companies_data],
            "period": period,
            "months": sorted_months,
            "data": comparison_data,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 기업 ID 형식: {e}")
    except Exception as e:
        logger.error(f"비교 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking")
async def get_stock_performance_ranking(
    period: str = Query("1y", description="기간 (1m, 3m, 6m, 1y, 3y)"),
    sort: str = Query("return_desc", description="정렬 (return_desc, return_asc)"),
    market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    주가 수익률 순위 조회

    Args:
        period: 기간 (1m: 1개월, 3m: 3개월, 6m: 6개월, 1y: 1년, 3y: 3년)
        sort: 정렬 (return_desc: 수익률 높은순, return_asc: 수익률 낮은순)
        market: 시장 필터 (KOSPI, KOSDAQ)
        limit: 결과 수
        offset: 시작 위치

    Returns:
        - total: 전체 수
        - rankings: 순위 목록
    """
    try:
        # 기간 계산 (개월 수)
        period_months = {
            "1m": 1,
            "3m": 3,
            "6m": 6,
            "1y": 12,
            "3y": 36,
        }

        months = period_months.get(period, 12)

        now = datetime.now()
        year = now.year
        month = now.month - months
        while month <= 0:
            month += 12
            year -= 1
        start_month = f"{year:04d}-{month:02d}"
        end_month = now.strftime("%Y-%m")

        # 기업별 시작/종료 가격 조회
        # 서브쿼리로 각 기업의 시작 월과 종료 월 가격 가져오기
        query = """
            WITH price_range AS (
                SELECT
                    sp.company_id,
                    FIRST_VALUE(sp.close_price) OVER (
                        PARTITION BY sp.company_id
                        ORDER BY sp.year_month ASC
                    ) as start_price,
                    LAST_VALUE(sp.close_price) OVER (
                        PARTITION BY sp.company_id
                        ORDER BY sp.year_month ASC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as end_price,
                    COUNT(*) OVER (PARTITION BY sp.company_id) as data_count
                FROM stock_prices sp
                WHERE sp.year_month >= :start_month
                  AND sp.year_month <= :end_month
            )
            SELECT DISTINCT company_id, start_price, end_price, data_count
            FROM price_range
            WHERE data_count >= 2
        """

        from sqlalchemy import text
        result = await db.execute(
            text(query),
            {"start_month": start_month, "end_month": end_month}
        )
        price_data = result.fetchall()

        # 수익률 계산 및 정렬
        rankings = []
        for row in price_data:
            company_id, start_price, end_price, data_count = row
            if start_price and start_price > 0:
                return_pct = ((end_price - start_price) / start_price) * 100

                # 기업 정보 조회
                company_result = await db.execute(
                    select(Company).where(Company.id == company_id)
                )
                company = company_result.scalar_one_or_none()

                if company:
                    # 시장 필터
                    if market and company.market != market:
                        continue

                    rankings.append({
                        "company_id": str(company_id),
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "market": company.market,
                        "start_price": start_price,
                        "end_price": end_price,
                        "return_pct": round(return_pct, 2),
                        "data_points": data_count,
                    })

        # 정렬
        reverse = sort == "return_desc"
        rankings.sort(key=lambda x: x["return_pct"], reverse=reverse)

        # 페이지네이션
        total = len(rankings)
        paginated = rankings[offset:offset + limit]

        # 순위 추가
        for i, item in enumerate(paginated):
            item["rank"] = offset + i + 1

        return {
            "period": period,
            "start_month": start_month,
            "end_month": end_month,
            "total": total,
            "offset": offset,
            "limit": limit,
            "rankings": paginated,
        }

    except Exception as e:
        logger.error(f"순위 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
