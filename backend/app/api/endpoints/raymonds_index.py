"""
RaymondsIndex API 엔드포인트

자본 배분 효율성 지수 조회 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
import logging

from app.database import get_db
from app.models.raymonds_index import RaymondsIndex
from app.models.companies import Company

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/raymonds-index", tags=["RaymondsIndex"])


# ============================================================================
# Response Schemas
# ============================================================================

def format_index_response(index: RaymondsIndex, company: Optional[Company] = None) -> dict:
    """RaymondsIndex 응답 포맷"""
    response = index.to_dict()
    if company:
        response["company_name"] = company.name
        response["company_ticker"] = company.ticker
        response["company_market"] = company.market
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/downgraded")
async def get_downgraded_companies(
    days: int = Query(30, ge=1, le=365, description="기간 (일)"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    등급 하락 기업 목록 (Alert Zone용)

    전년 대비 등급이 하락한 기업을 조회합니다.
    - days: 기간 필터 (현재는 연도 비교만 지원)
    - limit: 최대 결과 수
    """
    try:
        # 등급 순서 정의 (높은 것부터)
        grade_order = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']

        # 2025년과 2024년 데이터 비교
        current_year = 2025
        previous_year = 2024

        # 현재 연도 데이터
        current_query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .where(RaymondsIndex.fiscal_year == current_year)
        )
        current_result = await db.execute(current_query)
        current_data = {str(row[0].company_id): (row[0], row[1]) for row in current_result.all()}

        # 이전 연도 데이터
        previous_query = (
            select(RaymondsIndex)
            .where(RaymondsIndex.fiscal_year == previous_year)
        )
        previous_result = await db.execute(previous_query)
        previous_data = {str(row.company_id): row for row in previous_result.scalars().all()}

        # 등급 하락 기업 찾기
        downgraded = []
        for company_id, (current_index, company) in current_data.items():
            if company_id in previous_data:
                prev_index = previous_data[company_id]
                current_grade = current_index.grade
                previous_grade = prev_index.grade

                # 등급 순서 비교
                try:
                    current_rank = grade_order.index(current_grade)
                    previous_rank = grade_order.index(previous_grade)

                    # 등급이 하락했으면 (rank가 더 커졌으면)
                    if current_rank > previous_rank:
                        downgraded.append({
                            "company_id": company_id,
                            "company_name": company.name,
                            "company_ticker": company.ticker,
                            "company_market": company.market,
                            "previous_grade": previous_grade,
                            "current_grade": current_grade,
                            "previous_score": float(prev_index.total_score) if prev_index.total_score else 0,
                            "current_score": float(current_index.total_score) if current_index.total_score else 0,
                            "score_change": float(current_index.total_score - prev_index.total_score) if current_index.total_score and prev_index.total_score else 0,
                            "grade_drop": current_rank - previous_rank,  # 몇 단계 하락
                            "red_flags": current_index.red_flags or [],
                        })
                except ValueError:
                    continue

        # 점수 하락 폭이 큰 순으로 정렬
        downgraded.sort(key=lambda x: x["score_change"])

        return {
            "total": len(downgraded),
            "period": f"{previous_year} → {current_year}",
            "results": downgraded[:limit]
        }

    except Exception as e:
        logger.error(f"Error fetching downgraded companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/sector")
async def get_sector_statistics(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    업종별 RaymondsIndex 통계

    - year: 연도 필터 (기본: 최신)
    """
    try:
        # 연도 결정
        if not year:
            year_query = select(func.max(RaymondsIndex.fiscal_year))
            year_result = await db.execute(year_query)
            year = year_result.scalar() or 2025

        # 업종별 통계
        sector_query = (
            select(
                Company.sector,
                func.count(RaymondsIndex.id).label('company_count'),
                func.avg(RaymondsIndex.total_score).label('avg_score'),
                func.min(RaymondsIndex.total_score).label('min_score'),
                func.max(RaymondsIndex.total_score).label('max_score'),
                func.avg(RaymondsIndex.investment_gap).label('avg_gap'),
            )
            .select_from(RaymondsIndex)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .where(RaymondsIndex.fiscal_year == year)
            .where(Company.sector.isnot(None))
            .group_by(Company.sector)
            .order_by(desc(func.avg(RaymondsIndex.total_score)))
        )

        sector_result = await db.execute(sector_query)
        sectors = []

        for row in sector_result.all():
            sectors.append({
                "sector": row.sector,
                "company_count": row.company_count,
                "avg_score": round(float(row.avg_score), 2) if row.avg_score else 0,
                "min_score": round(float(row.min_score), 2) if row.min_score else 0,
                "max_score": round(float(row.max_score), 2) if row.max_score else 0,
                "avg_investment_gap": round(float(row.avg_gap), 2) if row.avg_gap else 0,
            })

        # 업종별 등급 분포
        grade_query = (
            select(
                Company.sector,
                RaymondsIndex.grade,
                func.count(RaymondsIndex.id).label('count')
            )
            .select_from(RaymondsIndex)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .where(RaymondsIndex.fiscal_year == year)
            .where(Company.sector.isnot(None))
            .group_by(Company.sector, RaymondsIndex.grade)
        )

        grade_result = await db.execute(grade_query)
        grade_by_sector = {}
        for row in grade_result.all():
            if row.sector not in grade_by_sector:
                grade_by_sector[row.sector] = {}
            grade_by_sector[row.sector][row.grade] = row.count

        # 결과에 등급 분포 추가
        for sector in sectors:
            sector["grade_distribution"] = grade_by_sector.get(sector["sector"], {})

        return {
            "year": year,
            "total_sectors": len(sectors),
            "sectors": sectors
        }

    except Exception as e:
        logger.error(f"Error fetching sector statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}")
async def get_raymonds_index(
    company_id: UUID,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    단일 회사의 RaymondsIndex 조회

    - company_id: 회사 UUID
    - year: 특정 연도 (없으면 최신)
    """
    try:
        query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .where(RaymondsIndex.company_id == company_id)
        )

        if year:
            query = query.where(RaymondsIndex.fiscal_year == year)
        else:
            query = query.order_by(desc(RaymondsIndex.fiscal_year))

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="RaymondsIndex not found for this company")

        index, company = row
        return format_index_response(index, company)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching RaymondsIndex for {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/history")
async def get_raymonds_index_history(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    회사의 연도별 RaymondsIndex 추이

    - company_id: 회사 UUID
    """
    try:
        query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .where(RaymondsIndex.company_id == company_id)
            .order_by(desc(RaymondsIndex.fiscal_year))
        )

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            raise HTTPException(status_code=404, detail="No RaymondsIndex history found")

        company = rows[0][1]
        history = [format_index_response(row[0]) for row in rows]

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history for {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking/list")
async def get_raymonds_index_ranking(
    sort: str = Query("score_desc", regex="^(score_desc|score_asc|gap_asc|gap_desc)$"),
    grade: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    RaymondsIndex 전체 랭킹

    - sort: 정렬 기준 (score_desc, score_asc, gap_asc, gap_desc)
    - grade: 등급 필터 (A+,A,B,C,D 쉼표 구분)
    - year: 연도 필터
    - limit: 조회 개수
    - offset: 시작 위치
    """
    try:
        # 기본 쿼리 - 최신 연도만 조회
        if year:
            subquery = (
                select(RaymondsIndex.company_id)
                .where(RaymondsIndex.fiscal_year == year)
            )
        else:
            # 각 회사의 최신 연도만 조회
            subquery = (
                select(
                    RaymondsIndex.company_id,
                    func.max(RaymondsIndex.fiscal_year).label('max_year')
                )
                .group_by(RaymondsIndex.company_id)
            ).subquery()

        query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
        )

        if year:
            query = query.where(RaymondsIndex.fiscal_year == year)
        else:
            query = query.join(
                subquery,
                (RaymondsIndex.company_id == subquery.c.company_id) &
                (RaymondsIndex.fiscal_year == subquery.c.max_year)
            )

        # 등급 필터
        if grade:
            grades = [g.strip() for g in grade.split(',')]
            query = query.where(RaymondsIndex.grade.in_(grades))

        # 정렬
        sort_map = {
            "score_desc": desc(RaymondsIndex.total_score),
            "score_asc": RaymondsIndex.total_score,
            "gap_asc": RaymondsIndex.investment_gap,
            "gap_desc": desc(RaymondsIndex.investment_gap),
        }
        query = query.order_by(sort_map.get(sort, desc(RaymondsIndex.total_score)))

        # 페이징
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        rankings = []
        for i, (index, company) in enumerate(rows, start=offset + 1):
            item = format_index_response(index, company)
            item["rank"] = i
            rankings.append(item)

        # 전체 개수
        count_query = select(func.count()).select_from(RaymondsIndex)
        if year:
            count_query = count_query.where(RaymondsIndex.fiscal_year == year)
        if grade:
            count_query = count_query.where(RaymondsIndex.grade.in_(grades))

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "rankings": rankings
        }

    except Exception as e:
        logger.error(f"Error fetching ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/filter")
async def search_raymonds_index(
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    min_gap: Optional[float] = None,
    max_gap: Optional[float] = None,
    has_red_flags: Optional[bool] = None,
    grade: Optional[str] = None,
    market: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    RaymondsIndex 조건 검색

    - min_score, max_score: 점수 범위
    - min_gap, max_gap: 투자괴리율 범위
    - has_red_flags: Red Flag 유무
    - grade: 등급 필터
    - market: 시장 필터 (KOSPI, KOSDAQ, KONEX)
    - year: 연도 필터
    """
    try:
        query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
        )

        # 연도 필터 (기본: 각 회사의 최신)
        if year:
            query = query.where(RaymondsIndex.fiscal_year == year)
        else:
            subquery = (
                select(
                    RaymondsIndex.company_id,
                    func.max(RaymondsIndex.fiscal_year).label('max_year')
                )
                .group_by(RaymondsIndex.company_id)
            ).subquery()
            query = query.join(
                subquery,
                (RaymondsIndex.company_id == subquery.c.company_id) &
                (RaymondsIndex.fiscal_year == subquery.c.max_year)
            )

        # 점수 필터
        if min_score is not None:
            query = query.where(RaymondsIndex.total_score >= min_score)
        if max_score is not None:
            query = query.where(RaymondsIndex.total_score <= max_score)

        # 투자괴리율 필터
        if min_gap is not None:
            query = query.where(RaymondsIndex.investment_gap >= min_gap)
        if max_gap is not None:
            query = query.where(RaymondsIndex.investment_gap <= max_gap)

        # Red Flag 필터
        if has_red_flags is not None:
            if has_red_flags:
                query = query.where(func.jsonb_array_length(RaymondsIndex.red_flags) > 0)
            else:
                query = query.where(func.jsonb_array_length(RaymondsIndex.red_flags) == 0)

        # 등급 필터
        if grade:
            grades = [g.strip() for g in grade.split(',')]
            query = query.where(RaymondsIndex.grade.in_(grades))

        # 시장 필터
        if market:
            markets = [m.strip() for m in market.split(',')]
            query = query.where(Company.market.in_(markets))

        # 정렬 및 페이징
        query = query.order_by(desc(RaymondsIndex.total_score))
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        items = [format_index_response(index, company) for index, company in rows]

        return {
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "results": items
        }

    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/summary")
async def get_raymonds_index_statistics(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    RaymondsIndex 전체 통계

    - 평균/중앙값/분포
    - 등급별 비율
    - 주요 지표 분포
    """
    try:
        base_query = select(RaymondsIndex)

        if year:
            base_query = base_query.where(RaymondsIndex.fiscal_year == year)
        else:
            # 각 회사의 최신 연도만
            subquery = (
                select(
                    RaymondsIndex.company_id,
                    func.max(RaymondsIndex.fiscal_year).label('max_year')
                )
                .group_by(RaymondsIndex.company_id)
            ).subquery()
            base_query = base_query.join(
                subquery,
                (RaymondsIndex.company_id == subquery.c.company_id) &
                (RaymondsIndex.fiscal_year == subquery.c.max_year)
            )

        # 기본 통계 - 최신 연도 기준 (중복 제거)
        if year:
            stats_query = select(
                func.count(func.distinct(RaymondsIndex.company_id)).label('total_count'),
                func.avg(RaymondsIndex.total_score).label('avg_score'),
                func.min(RaymondsIndex.total_score).label('min_score'),
                func.max(RaymondsIndex.total_score).label('max_score'),
                func.avg(RaymondsIndex.investment_gap).label('avg_gap'),
            ).where(RaymondsIndex.fiscal_year == year)
        else:
            # 각 회사의 최신 연도만 집계
            latest_subquery = (
                select(
                    RaymondsIndex.company_id,
                    func.max(RaymondsIndex.fiscal_year).label('max_year')
                )
                .group_by(RaymondsIndex.company_id)
            ).subquery()

            stats_query = (
                select(
                    func.count(func.distinct(RaymondsIndex.company_id)).label('total_count'),
                    func.avg(RaymondsIndex.total_score).label('avg_score'),
                    func.min(RaymondsIndex.total_score).label('min_score'),
                    func.max(RaymondsIndex.total_score).label('max_score'),
                    func.avg(RaymondsIndex.investment_gap).label('avg_gap'),
                )
                .select_from(RaymondsIndex)
                .join(
                    latest_subquery,
                    (RaymondsIndex.company_id == latest_subquery.c.company_id) &
                    (RaymondsIndex.fiscal_year == latest_subquery.c.max_year)
                )
            )

        stats_result = await db.execute(stats_query)
        stats = stats_result.first()

        # 등급별 분포 - 최신 연도 기준
        if year:
            grade_query = (
                select(
                    RaymondsIndex.grade,
                    func.count(RaymondsIndex.id).label('count')
                )
                .where(RaymondsIndex.fiscal_year == year)
                .group_by(RaymondsIndex.grade)
            )
        else:
            # 각 회사의 최신 연도만 집계
            grade_subquery = (
                select(
                    RaymondsIndex.company_id,
                    func.max(RaymondsIndex.fiscal_year).label('max_year')
                )
                .group_by(RaymondsIndex.company_id)
            ).subquery()

            grade_query = (
                select(
                    RaymondsIndex.grade,
                    func.count(RaymondsIndex.id).label('count')
                )
                .select_from(RaymondsIndex)
                .join(
                    grade_subquery,
                    (RaymondsIndex.company_id == grade_subquery.c.company_id) &
                    (RaymondsIndex.fiscal_year == grade_subquery.c.max_year)
                )
                .group_by(RaymondsIndex.grade)
            )

        grade_result = await db.execute(grade_query)
        grade_distribution = {row.grade: row.count for row in grade_result.all()}

        return {
            "total_companies": stats.total_count if stats else 0,
            "average_score": float(stats.avg_score) if stats and stats.avg_score else 0,
            "min_score": float(stats.min_score) if stats and stats.min_score else 0,
            "max_score": float(stats.max_score) if stats and stats.max_score else 0,
            "average_investment_gap": float(stats.avg_gap) if stats and stats.avg_gap else 0,
            "grade_distribution": grade_distribution,
            "year": year
        }

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/companies")
async def search_companies(
    q: str = Query(..., min_length=1, description="검색어 (회사명 또는 종목코드)"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    회사명/종목코드로 검색 (자동완성용)

    - q: 검색어 (부분 매칭)
    - limit: 최대 결과 수
    """
    try:
        # 각 회사의 최신 연도만 조회
        subquery = (
            select(
                RaymondsIndex.company_id,
                func.max(RaymondsIndex.fiscal_year).label('max_year')
            )
            .group_by(RaymondsIndex.company_id)
        ).subquery()

        query = (
            select(RaymondsIndex, Company)
            .join(Company, RaymondsIndex.company_id == Company.id)
            .join(
                subquery,
                (RaymondsIndex.company_id == subquery.c.company_id) &
                (RaymondsIndex.fiscal_year == subquery.c.max_year)
            )
            .where(
                (Company.name.ilike(f"%{q}%")) |
                (Company.ticker.ilike(f"%{q}%"))
            )
            .order_by(desc(RaymondsIndex.total_score))
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        return {
            "query": q,
            "total": len(rows),
            "results": [format_index_response(index, company) for index, company in rows]
        }

    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/name/{company_name}")
async def get_raymonds_index_by_name(
    company_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    회사명으로 RaymondsIndex 조회 (프론트엔드 편의용)
    """
    try:
        # 회사 조회
        company_query = select(Company).where(Company.name == company_name)
        company_result = await db.execute(company_query)
        company = company_result.scalar_one_or_none()

        if not company:
            # 부분 매칭 시도
            company_query = select(Company).where(Company.name.ilike(f"%{company_name}%"))
            company_result = await db.execute(company_query)
            company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_name}")

        # RaymondsIndex 조회
        index_query = (
            select(RaymondsIndex)
            .where(RaymondsIndex.company_id == company.id)
            .order_by(desc(RaymondsIndex.fiscal_year))
        )

        index_result = await db.execute(index_query)
        index = index_result.scalar_one_or_none()

        if not index:
            return None  # 데이터 없으면 null 반환 (프론트엔드에서 조건부 렌더링)

        return format_index_response(index, company)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by name {company_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
