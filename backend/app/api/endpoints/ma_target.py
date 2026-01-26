"""
M&A 타겟 API 엔드포인트

적대적 M&A 검토 대상 기업 조회 API
"""
import logging
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.financial_snapshot import FinancialSnapshot
from app.models.companies import Company

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ma-target", tags=["M&A Target"])


def format_snapshot_response(snapshot: FinancialSnapshot, company: Company) -> dict:
    """스냅샷 데이터를 API 응답 형식으로 변환"""
    return {
        "company_id": str(snapshot.company_id),
        "name": company.name,
        "ticker": company.ticker,
        "stock_code": company.ticker,
        "market": company.market,
        "sector": company.sector,
        "trading_status": company.trading_status,

        # 주가 데이터
        "snapshot_date": snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else None,
        "close_price": snapshot.close_price,
        "market_cap_krx": snapshot.market_cap_krx,
        "market_cap_calculated": snapshot.market_cap_calculated,
        "shares_outstanding": snapshot.shares_outstanding,

        # M&A 타겟 점수
        "ma_target_score": float(snapshot.ma_target_score) if snapshot.ma_target_score else None,
        "ma_target_grade": snapshot.ma_target_grade,
        "ma_target_factors": snapshot.ma_target_factors,

        # 재무 지표
        "cash_and_equivalents": snapshot.cash_and_equivalents,
        "short_term_investments": snapshot.short_term_investments,
        "total_liquid_assets": snapshot.total_liquid_assets,
        "tangible_assets": snapshot.tangible_assets,
        "revenue": snapshot.revenue,
        "operating_profit": snapshot.operating_profit,

        # 증감율
        "tangible_assets_growth": float(snapshot.tangible_assets_growth) if snapshot.tangible_assets_growth else None,
        "revenue_growth": float(snapshot.revenue_growth) if snapshot.revenue_growth else None,
        "operating_profit_growth": float(snapshot.operating_profit_growth) if snapshot.operating_profit_growth else None,

        "fiscal_year": snapshot.fiscal_year,
    }


@router.get("/ranking")
async def get_ma_target_ranking(
    # 정렬
    sort: str = Query(
        "score_desc",
        regex="^(score_desc|score_asc|cash_ratio_desc|market_cap_asc|market_cap_desc|revenue_growth_desc|tangible_growth_desc)$",
        description="정렬 기준"
    ),
    # 등급 필터
    grade: Optional[str] = Query(None, description="등급 필터 (A+,A,B+,B,C+,C,D 쉼표 구분)"),
    # 시장 필터
    market: Optional[str] = Query(None, description="시장 필터 (KOSPI,KOSDAQ 쉼표 구분)"),
    # 점수 범위
    min_score: Optional[float] = Query(None, ge=0, le=100, description="최소 점수"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="최대 점수"),
    # 시가총액 범위 (억원)
    min_market_cap: Optional[float] = Query(None, ge=0, description="최소 시가총액 (억원)"),
    max_market_cap: Optional[float] = Query(None, ge=0, description="최대 시가총액 (억원)"),
    # 현금비율 필터
    min_cash_ratio: Optional[float] = Query(None, ge=0, description="최소 현금/시총 비율 (%)"),
    # 증감율 필터
    min_revenue_growth: Optional[float] = Query(None, description="최소 매출 증감율 (%)"),
    min_tangible_growth: Optional[float] = Query(None, description="최소 유형자산 증가율 (%)"),
    min_op_profit_growth: Optional[float] = Query(None, description="최소 영업이익 증감율 (%)"),
    # 날짜 필터 (기본: 최신)
    snapshot_date: Optional[str] = Query(None, description="스냅샷 일자 (YYYY-MM-DD)"),
    # 페이징
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    M&A 타겟 랭킹 조회

    적대적 M&A 검토 대상 기업을 점수 기준으로 조회합니다.

    ## 필터 옵션
    - grade: 등급 필터 (A+,A,B+,B,C+,C,D)
    - market: 시장 필터 (KOSPI, KOSDAQ)
    - min_score/max_score: 점수 범위
    - min_market_cap/max_market_cap: 시가총액 범위 (억원)
    - min_cash_ratio: 현금/시총 비율
    - min_revenue_growth: 매출 증감율
    - min_tangible_growth: 유형자산 증가율
    - min_op_profit_growth: 영업이익 증감율

    ## 정렬 옵션
    - score_desc: 점수 높은 순 (기본)
    - score_asc: 점수 낮은 순
    - cash_ratio_desc: 현금비율 높은 순
    - market_cap_asc: 시가총액 낮은 순
    - market_cap_desc: 시가총액 높은 순
    - revenue_growth_desc: 매출성장률 높은 순
    - tangible_growth_desc: 유형자산 증가율 높은 순
    """
    try:
        # 최신 스냅샷 날짜 서브쿼리
        if snapshot_date:
            target_date = date.fromisoformat(snapshot_date)
        else:
            # 가장 최근 스냅샷 날짜 조회
            latest_date_query = select(func.max(FinancialSnapshot.snapshot_date))
            latest_result = await db.execute(latest_date_query)
            target_date = latest_result.scalar()

            if not target_date:
                return {
                    "total": 0,
                    "offset": offset,
                    "limit": limit,
                    "snapshot_date": None,
                    "rankings": []
                }

        # 기본 쿼리
        query = (
            select(FinancialSnapshot, Company)
            .join(Company, FinancialSnapshot.company_id == Company.id)
            .where(FinancialSnapshot.snapshot_date == target_date)
            .where(Company.market != 'KONEX')  # KONEX 제외
            .where(FinancialSnapshot.ma_target_score.isnot(None))
        )

        # 등급 필터
        if grade:
            grades = [g.strip() for g in grade.split(',')]
            query = query.where(FinancialSnapshot.ma_target_grade.in_(grades))

        # 시장 필터
        if market:
            markets = [m.strip() for m in market.split(',')]
            query = query.where(Company.market.in_(markets))

        # 점수 범위
        if min_score is not None:
            query = query.where(FinancialSnapshot.ma_target_score >= min_score)
        if max_score is not None:
            query = query.where(FinancialSnapshot.ma_target_score <= max_score)

        # 시가총액 범위 (억원 → 원으로 변환)
        if min_market_cap is not None:
            query = query.where(FinancialSnapshot.market_cap_calculated >= min_market_cap * 100_000_000)
        if max_market_cap is not None:
            query = query.where(FinancialSnapshot.market_cap_calculated <= max_market_cap * 100_000_000)

        # 현금비율 필터 (total_liquid_assets / market_cap_calculated * 100)
        if min_cash_ratio is not None:
            query = query.where(
                and_(
                    FinancialSnapshot.total_liquid_assets.isnot(None),
                    FinancialSnapshot.market_cap_calculated.isnot(None),
                    FinancialSnapshot.market_cap_calculated > 0,
                    (FinancialSnapshot.total_liquid_assets * 100.0 / FinancialSnapshot.market_cap_calculated) >= min_cash_ratio
                )
            )

        # 증감율 필터
        if min_revenue_growth is not None:
            query = query.where(FinancialSnapshot.revenue_growth >= min_revenue_growth)
        if min_tangible_growth is not None:
            query = query.where(FinancialSnapshot.tangible_assets_growth >= min_tangible_growth)
        if min_op_profit_growth is not None:
            query = query.where(FinancialSnapshot.operating_profit_growth >= min_op_profit_growth)

        # 정렬
        sort_map = {
            "score_desc": desc(FinancialSnapshot.ma_target_score),
            "score_asc": FinancialSnapshot.ma_target_score,
            "cash_ratio_desc": desc(
                FinancialSnapshot.total_liquid_assets * 1.0 / func.nullif(FinancialSnapshot.market_cap_calculated, 0)
            ),
            "market_cap_asc": FinancialSnapshot.market_cap_calculated,
            "market_cap_desc": desc(FinancialSnapshot.market_cap_calculated),
            "revenue_growth_desc": desc(FinancialSnapshot.revenue_growth),
            "tangible_growth_desc": desc(FinancialSnapshot.tangible_assets_growth),
        }
        query = query.order_by(sort_map.get(sort, desc(FinancialSnapshot.ma_target_score)))

        # 페이징
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        rankings = []
        for i, (snapshot, company) in enumerate(rows, start=offset + 1):
            item = format_snapshot_response(snapshot, company)
            item["rank"] = i
            rankings.append(item)

        # 전체 개수 조회 (동일 필터 적용)
        count_query = (
            select(func.count(FinancialSnapshot.id))
            .select_from(FinancialSnapshot)
            .join(Company, FinancialSnapshot.company_id == Company.id)
            .where(FinancialSnapshot.snapshot_date == target_date)
            .where(Company.market != 'KONEX')
            .where(FinancialSnapshot.ma_target_score.isnot(None))
        )

        # 동일 필터 조건 적용
        if grade:
            count_query = count_query.where(FinancialSnapshot.ma_target_grade.in_(grades))
        if market:
            count_query = count_query.where(Company.market.in_(markets))
        if min_score is not None:
            count_query = count_query.where(FinancialSnapshot.ma_target_score >= min_score)
        if max_score is not None:
            count_query = count_query.where(FinancialSnapshot.ma_target_score <= max_score)
        if min_market_cap is not None:
            count_query = count_query.where(FinancialSnapshot.market_cap_calculated >= min_market_cap * 100_000_000)
        if max_market_cap is not None:
            count_query = count_query.where(FinancialSnapshot.market_cap_calculated <= max_market_cap * 100_000_000)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "snapshot_date": target_date.isoformat() if target_date else None,
            "rankings": rankings
        }

    except Exception as e:
        logger.error(f"M&A 타겟 랭킹 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}")
async def get_company_ma_target_detail(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업의 M&A 타겟 상세 정보

    최신 스냅샷 데이터와 점수 요소별 상세 정보를 반환합니다.
    """
    try:
        # 최신 스냅샷 조회
        query = (
            select(FinancialSnapshot, Company)
            .join(Company, FinancialSnapshot.company_id == Company.id)
            .where(FinancialSnapshot.company_id == company_id)
            .order_by(desc(FinancialSnapshot.snapshot_date))
            .limit(1)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="해당 기업의 M&A 타겟 데이터가 없습니다")

        snapshot, company = row
        response = format_snapshot_response(snapshot, company)

        # 시가총액 억원 단위 추가
        if snapshot.market_cap_calculated:
            response["market_cap_bil"] = round(snapshot.market_cap_calculated / 100_000_000, 2)

        # 현금 비율 추가
        if snapshot.total_liquid_assets and snapshot.market_cap_calculated:
            response["cash_ratio"] = round(
                (snapshot.total_liquid_assets / snapshot.market_cap_calculated) * 100, 2
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"M&A 타겟 상세 조회 오류 ({company_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}/history")
async def get_company_ma_target_history(
    company_id: str,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업의 M&A 타겟 점수 히스토리

    일별 스냅샷 데이터를 시계열로 반환합니다.
    패턴 분석에 활용할 수 있습니다.
    """
    try:
        query = (
            select(FinancialSnapshot)
            .where(FinancialSnapshot.company_id == company_id)
            .order_by(desc(FinancialSnapshot.snapshot_date))
            .limit(limit)
        )

        result = await db.execute(query)
        snapshots = result.scalars().all()

        if not snapshots:
            raise HTTPException(status_code=404, detail="히스토리 데이터가 없습니다")

        history = []
        for snapshot in reversed(snapshots):  # 시간순 정렬
            history.append({
                "date": snapshot.snapshot_date.isoformat(),
                "close_price": snapshot.close_price,
                "market_cap": snapshot.market_cap_calculated,
                "ma_target_score": float(snapshot.ma_target_score) if snapshot.ma_target_score else None,
                "ma_target_grade": snapshot.ma_target_grade,
                "cash_ratio": round(
                    (snapshot.total_liquid_assets / snapshot.market_cap_calculated) * 100, 2
                ) if snapshot.total_liquid_assets and snapshot.market_cap_calculated else None,
            })

        return {
            "company_id": company_id,
            "count": len(history),
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"M&A 타겟 히스토리 조회 오류 ({company_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ma_target_stats(
    snapshot_date: Optional[str] = Query(None, description="스냅샷 일자"),
    db: AsyncSession = Depends(get_db)
):
    """
    M&A 타겟 통계

    등급별 분포, 평균 점수 등 전체 통계를 반환합니다.
    """
    try:
        # 대상 날짜
        if snapshot_date:
            target_date = date.fromisoformat(snapshot_date)
        else:
            latest_query = select(func.max(FinancialSnapshot.snapshot_date))
            latest_result = await db.execute(latest_query)
            target_date = latest_result.scalar()

        if not target_date:
            return {
                "snapshot_date": None,
                "total_companies": 0,
                "grade_distribution": {},
                "average_score": None,
            }

        # 전체 통계
        stats_query = select(
            func.count(FinancialSnapshot.id).label('total'),
            func.avg(FinancialSnapshot.ma_target_score).label('avg_score'),
            func.max(FinancialSnapshot.ma_target_score).label('max_score'),
            func.min(FinancialSnapshot.ma_target_score).label('min_score'),
        ).where(
            FinancialSnapshot.snapshot_date == target_date
        ).where(
            FinancialSnapshot.ma_target_score.isnot(None)
        )

        stats_result = await db.execute(stats_query)
        stats = stats_result.first()

        # 등급별 분포
        grade_query = select(
            FinancialSnapshot.ma_target_grade,
            func.count(FinancialSnapshot.id).label('count')
        ).where(
            FinancialSnapshot.snapshot_date == target_date
        ).where(
            FinancialSnapshot.ma_target_score.isnot(None)
        ).group_by(
            FinancialSnapshot.ma_target_grade
        )

        grade_result = await db.execute(grade_query)
        grade_distribution = {row.ma_target_grade: row.count for row in grade_result.fetchall()}

        return {
            "snapshot_date": target_date.isoformat(),
            "total_companies": stats.total or 0,
            "average_score": round(float(stats.avg_score), 2) if stats.avg_score else None,
            "max_score": round(float(stats.max_score), 2) if stats.max_score else None,
            "min_score": round(float(stats.min_score), 2) if stats.min_score else None,
            "grade_distribution": grade_distribution,
        }

    except Exception as e:
        logger.error(f"M&A 타겟 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
async def get_ma_target_filter_options(
    db: AsyncSession = Depends(get_db)
):
    """
    M&A 타겟 필터 옵션

    가능한 등급, 시장 등 필터 옵션 목록을 반환합니다.
    """
    return {
        "grades": ["A+", "A", "B+", "B", "C+", "C", "D"],
        "markets": ["KOSPI", "KOSDAQ"],
        "sort_options": [
            {"value": "score_desc", "label": "점수 높은 순"},
            {"value": "score_asc", "label": "점수 낮은 순"},
            {"value": "cash_ratio_desc", "label": "현금비율 높은 순"},
            {"value": "market_cap_asc", "label": "시가총액 낮은 순"},
            {"value": "market_cap_desc", "label": "시가총액 높은 순"},
            {"value": "revenue_growth_desc", "label": "매출성장률 높은 순"},
            {"value": "tangible_growth_desc", "label": "유형자산 증가율 높은 순"},
        ],
        "score_weights": {
            "cash_ratio": {"weight": 25, "description": "현금성 자산 / 시가총액 비율"},
            "tangible_growth": {"weight": 20, "description": "유형자산 증가율"},
            "revenue_growth": {"weight": 20, "description": "매출 증감율"},
            "op_profit_growth": {"weight": 20, "description": "영업이익 증감율"},
            "market_cap_size": {"weight": 15, "description": "시가총액 규모 (적정 인수 범위)"},
        },
    }
