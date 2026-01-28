"""
회사 검색 및 조회 API 엔드포인트

회사 목록, 검색, 상세 정보 조회
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_

from app.database import AsyncSessionLocal
from app.models import Company, ConvertibleBond, Officer, OfficerPosition, FinancialStatement
from app.services.cache_service import cache
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


# Response Models
class CompanyListItem(BaseModel):
    """회사 목록 항목"""
    id: str
    name: str
    ticker: Optional[str]
    corp_code: Optional[str]  # DART 기업코드 추가
    sector: Optional[str]
    market: Optional[str]
    market_cap: Optional[float] = None
    cb_count: int = 0
    officer_count: int = 0
    listing_status: Optional[str] = None  # LISTED, DELISTED, ETF 등
    trading_status: Optional[str] = None  # NORMAL, SUSPENDED, TRADING_HALT


class CompanyDetailResponse(BaseModel):
    """회사 상세 정보"""
    id: str
    name: str
    ticker: Optional[str]
    corp_code: Optional[str]
    name_en: Optional[str]
    business_number: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market: Optional[str]
    cb_count: int
    officer_count: int
    created_at: str
    updated_at: str


class CompanySearchResponse(BaseModel):
    """회사 검색 응답"""
    total: int
    page: int
    page_size: int
    items: List[CompanyListItem]


class PlatformStatsResponse(BaseModel):
    """플랫폼 통계 응답"""
    companies: int
    convertible_bonds: int
    officers: int
    major_shareholders: int
    financial_statements: int


class CompanyCBListItem(BaseModel):
    """회사 CB 발행 항목"""
    id: str
    bond_name: str
    issue_date: Optional[str]
    issue_amount: Optional[int]
    subscribers_count: int


class CompanyOfficerListItem(BaseModel):
    """회사 임원 항목"""
    id: str
    name: str
    position: Optional[str]
    influence_score: Optional[float]


# Dependencies
async def get_db():
    """Database session 제공"""
    async with AsyncSessionLocal() as session:
        yield session


# Endpoints
@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    플랫폼 전체 통계 조회

    - 분석 기업 수
    - CB 발행 건수
    - 임원 데이터 수
    - 주주변동 데이터 수
    - 재무제표 건수
    """
    # 캐시 조회
    cached = cache.get("platform_stats")
    if cached:
        return PlatformStatsResponse(**cached)

    try:
        # 각 테이블의 COUNT 조회
        companies_count = await db.execute(select(func.count(Company.id)))
        cb_count = await db.execute(select(func.count(ConvertibleBond.id)))
        officers_count = await db.execute(select(func.count(Officer.id)))
        financial_count = await db.execute(select(func.count(FinancialStatement.id)))

        # major_shareholders는 모델이 없어서 raw SQL 사용
        major_shareholders_result = await db.execute(
            text("SELECT COUNT(*) FROM major_shareholders")
        )

        result = PlatformStatsResponse(
            companies=companies_count.scalar() or 0,
            convertible_bonds=cb_count.scalar() or 0,
            officers=officers_count.scalar() or 0,
            major_shareholders=major_shareholders_result.scalar() or 0,
            financial_statements=financial_count.scalar() or 0
        )

        # 캐시 저장 (5분)
        cache.set("platform_stats", result.model_dump(), ttl=300)

        return result
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=CompanySearchResponse)
async def list_companies(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    sort_by: str = Query("name", description="정렬 기준 (name, ticker, market)"),
    order: str = Query("asc", description="정렬 순서 (asc, desc)"),
    sector: Optional[str] = Query(None, description="업종 필터"),
    has_cb: Optional[bool] = Query(None, description="CB 발행 여부"),
    listed_only: Optional[bool] = Query(None, description="상장 기업만 조회 (상장폐지/ETF 제외)"),
    db: AsyncSession = Depends(get_db)
):
    """
    회사 목록 조회

    - 페이지네이션 지원
    - 업종 필터링
    - CB 발행 여부 필터링
    - 상장 기업만 필터링 (listed_only=true)
    - 다양한 정렬 옵션
    """
    try:
        # 기본 쿼리
        query = select(Company)

        # 필터링
        if sector:
            query = query.where(Company.sector == sector)

        # 상장 기업만 필터링 (상장폐지, ETF 제외)
        if listed_only:
            query = query.where(Company.listing_status == 'LISTED')

        if has_cb is not None:
            if has_cb:
                # CB가 있는 회사만
                query = query.join(ConvertibleBond, Company.id == ConvertibleBond.company_id, isouter=False)
            # has_cb=False는 나중에 서브쿼리로 처리

        # 전체 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 정렬
        sort_columns = {
            "name": Company.name,
            "ticker": Company.ticker,
            "market": Company.market,
        }

        sort_column = sort_columns.get(sort_by, Company.name)
        if order == "desc":
            sort_column = sort_column.desc()

        query = query.order_by(sort_column)

        # 페이지네이션
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # 실행
        result = await db.execute(query)
        companies = result.scalars().unique().all()

        # CB 및 임원 개수 조회 (배치)
        company_ids = [str(c.id) for c in companies]

        cb_counts = {}
        officer_counts = {}

        if company_ids:
            # CB 개수
            cb_count_query = select(
                ConvertibleBond.company_id,
                func.count(ConvertibleBond.id).label('count')
            ).where(
                ConvertibleBond.company_id.in_(company_ids)
            ).group_by(ConvertibleBond.company_id)

            cb_result = await db.execute(cb_count_query)
            cb_counts = {str(row[0]): row[1] for row in cb_result.all()}

            # 임원 개수 (officer_positions 기반)
            officer_count_query = select(
                OfficerPosition.company_id,
                func.count(func.distinct(OfficerPosition.officer_id)).label('count')
            ).where(
                OfficerPosition.company_id.in_(company_ids),
                OfficerPosition.is_current == True
            ).group_by(OfficerPosition.company_id)

            officer_result = await db.execute(officer_count_query)
            officer_counts = {str(row[0]): row[1] for row in officer_result.all()}

        # 응답 생성
        company_items = [
            CompanyListItem(
                id=str(c.id),
                name=c.name,
                ticker=c.ticker,
                corp_code=c.corp_code,
                sector=c.sector,
                market=c.market,
                market_cap=c.market_cap,
                cb_count=cb_counts.get(str(c.id), 0),
                officer_count=officer_counts.get(str(c.id), 0),
                listing_status=c.listing_status,
                trading_status=c.trading_status
            )
            for c in companies
        ]

        return CompanySearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=company_items
        )

    except Exception as e:
        logger.error(f"Error listing companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    q: str = Query(..., min_length=1, description="검색어 (회사명 또는 종목코드)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    회사 검색

    - 회사명 또는 종목코드로 검색
    - 부분 일치 지원
    """
    try:
        # 검색 쿼리 최적화
        search_pattern = f"%{q}%"

        # Build search conditions (인덱스 활용)
        conditions = [
            Company.name.ilike(search_pattern),
            Company.ticker.ilike(search_pattern),
        ]

        # name_en은 NULL 체크 후 추가 (성능 최적화)
        if len(q) >= 2:  # 영문 검색은 최소 2자 이상
            conditions.append(
                and_(
                    Company.name_en.isnot(None),
                    Company.name_en.ilike(search_pattern)
                )
            )

        query = select(Company).where(or_(*conditions))

        # 전체 개수 (간단한 COUNT 쿼리로 변경)
        count_query = select(func.count(Company.id)).where(or_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        offset = (page - 1) * page_size
        query = query.order_by(Company.name).offset(offset).limit(page_size)

        # 실행
        result = await db.execute(query)
        companies = result.scalars().all()

        # CB 및 임원 개수 조회
        company_ids = [str(c.id) for c in companies]

        cb_counts = {}
        officer_counts = {}

        if company_ids:
            # CB 개수
            cb_count_query = select(
                ConvertibleBond.company_id,
                func.count(ConvertibleBond.id).label('count')
            ).where(
                ConvertibleBond.company_id.in_(company_ids)
            ).group_by(ConvertibleBond.company_id)

            cb_result = await db.execute(cb_count_query)
            cb_counts = {str(row[0]): row[1] for row in cb_result.all()}

            # 임원 개수 (officer_positions 기반)
            officer_count_query = select(
                OfficerPosition.company_id,
                func.count(func.distinct(OfficerPosition.officer_id)).label('count')
            ).where(
                OfficerPosition.company_id.in_(company_ids),
                OfficerPosition.is_current == True
            ).group_by(OfficerPosition.company_id)

            officer_result = await db.execute(officer_count_query)
            officer_counts = {str(row[0]): row[1] for row in officer_result.all()}

        # 응답 생성
        company_items = [
            CompanyListItem(
                id=str(c.id),
                name=c.name,
                ticker=c.ticker,
                corp_code=c.corp_code,
                sector=c.sector,
                market=c.market,
                market_cap=c.market_cap,
                cb_count=cb_counts.get(str(c.id), 0),
                officer_count=officer_counts.get(str(c.id), 0),
                trading_status=c.trading_status
            )
            for c in companies
        ]

        return CompanySearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=company_items
        )

    except Exception as e:
        logger.error(f"Error searching companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-risk", response_model=CompanySearchResponse)
async def get_high_risk_companies(
    limit: int = Query(6, ge=1, le=50, description="결과 개수"),
    min_grade: str = Query("HIGH_RISK", description="최소 등급 (RISK, MEDIUM_RISK, HIGH_RISK)"),
    has_cb: bool = Query(True, description="CB 발행 여부"),
    db: AsyncSession = Depends(get_db)
):
    """
    주의 필요 기업 조회 (관계형리스크등급 기준) - 4등급 체계 (2026-01-28 개편)

    - risk_scores 테이블의 investment_grade 기준
    - HIGH_RISK (고위험) 등급 기업 랜덤 조회 (기본값)
    - CB 발행 기업 우선 (has_cb=true)
    - KOSPI/KOSDAQ 시장만 표시 (ETF, KONEX 등 제외)
    - 상장폐지 제외

    등급 체계:
    - LOW_RISK (저위험): 0-19점
    - RISK (위험): 20-34점
    - MEDIUM_RISK (중위험): 35-49점
    - HIGH_RISK (고위험): 50점 이상
    """
    try:
        # 등급 필터링 조건 설정 (4등급 체계)
        # 기본: 고위험만 (HIGH_RISK)
        grade_filter = ['HIGH_RISK']
        if min_grade == 'RISK':
            grade_filter = ['RISK', 'MEDIUM_RISK', 'HIGH_RISK']
        elif min_grade == 'MEDIUM_RISK':
            grade_filter = ['MEDIUM_RISK', 'HIGH_RISK']

        # Raw SQL로 랜덤 조회 (성능 최적화)
        # KOSPI/KOSDAQ 시장만 표시 (ETF, KONEX 등 제외)
        query = text("""
            SELECT
                c.id::text,
                c.name,
                c.ticker,
                c.corp_code,
                c.sector,
                c.market,
                c.market_cap,
                c.listing_status,
                c.trading_status,
                rs.investment_grade,
                rs.total_score,
                COUNT(cb.id) as cb_count,
                COUNT(DISTINCT op.officer_id) as officer_count
            FROM companies c
            JOIN risk_scores rs ON c.id = rs.company_id
            LEFT JOIN convertible_bonds cb ON c.id = cb.company_id
            LEFT JOIN officer_positions op ON c.id = op.company_id AND op.is_current = true
            WHERE rs.investment_grade = ANY(:grades)
            AND c.listing_status = 'LISTED'
            AND c.market IN ('KOSPI', 'KOSDAQ')
            GROUP BY c.id, c.name, c.ticker, c.corp_code, c.sector, c.market,
                     c.market_cap, c.listing_status, c.trading_status, rs.investment_grade, rs.total_score
            HAVING (:has_cb = false OR COUNT(cb.id) > 0)
            ORDER BY RANDOM()
            LIMIT :limit
        """)

        result = await db.execute(query, {
            "grades": grade_filter,
            "has_cb": has_cb,
            "limit": limit
        })
        rows = result.fetchall()

        # 응답 생성
        company_items = [
            CompanyListItem(
                id=row.id,
                name=row.name,
                ticker=row.ticker,
                corp_code=row.corp_code,
                sector=row.sector,
                market=row.market,
                market_cap=row.market_cap,
                cb_count=row.cb_count,
                officer_count=row.officer_count,
                listing_status=row.listing_status,
                trading_status=row.trading_status
            )
            for row in rows
        ]

        return CompanySearchResponse(
            total=len(company_items),
            page=1,
            page_size=limit,
            items=company_items
        )

    except Exception as e:
        logger.error(f"Error getting high risk companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company_detail(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    회사 상세 정보 조회

    - 기본 정보
    - CB 발행 건수
    - 임원 수
    - company_id: UUID 또는 corp_code로 검색
    """
    # 캐시 조회
    cache_key = f"company_detail:{company_id}"
    cached = cache.get(cache_key)
    if cached:
        return CompanyDetailResponse(**cached)

    try:
        import uuid

        company = None

        # UUID 형식인지 확인 후 조회
        try:
            uuid.UUID(company_id)  # UUID 형식 검증
            result = await db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
        except ValueError:
            pass  # UUID 형식이 아니면 건너뜀

        # UUID로 못 찾으면 corp_code로 조회
        if not company:
            result = await db.execute(
                select(Company).where(Company.corp_code == company_id)
            )
            company = result.scalar_one_or_none()

        # 그래도 못 찾으면 ticker로 조회
        if not company:
            result = await db.execute(
                select(Company).where(Company.ticker == company_id)
            )
            company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 실제 회사 ID 사용 (company_id 파라미터가 corp_code나 ticker일 수 있으므로)
        actual_company_id = str(company.id)

        # CB 개수
        cb_count_query = select(func.count(ConvertibleBond.id)).where(
            ConvertibleBond.company_id == actual_company_id
        )
        cb_count_result = await db.execute(cb_count_query)
        cb_count = cb_count_result.scalar() or 0

        # 임원 개수 (officer_positions 기반)
        officer_count_query = select(func.count(func.distinct(OfficerPosition.officer_id))).where(
            OfficerPosition.company_id == actual_company_id,
            OfficerPosition.is_current == True
        )
        officer_count_result = await db.execute(officer_count_query)
        officer_count = officer_count_result.scalar() or 0

        result = CompanyDetailResponse(
            id=str(company.id),
            name=company.name,
            ticker=company.ticker,
            corp_code=company.corp_code,
            name_en=company.name_en,
            business_number=company.business_number,
            sector=company.sector,
            industry=company.industry,
            market=company.market,
            cb_count=cb_count,
            officer_count=officer_count,
            created_at=company.created_at.isoformat() if company.created_at else datetime.utcnow().isoformat(),
            updated_at=company.updated_at.isoformat() if company.updated_at else datetime.utcnow().isoformat()
        )

        # 캐시 저장 (5분) - 실제 company_id로 저장
        cache.set(f"company_detail:{actual_company_id}", result.model_dump(), ttl=300)
        # 원래 요청 키로도 저장 (corp_code나 ticker로 요청 시)
        if company_id != actual_company_id:
            cache.set(cache_key, result.model_dump(), ttl=300)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/convertible-bonds", response_model=List[CompanyCBListItem])
async def get_company_convertible_bonds(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    회사의 CB 발행 목록 조회

    - 발행일 최신순
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # CB 목록 조회
        cb_query = select(ConvertibleBond).where(
            ConvertibleBond.company_id == company_id
        ).order_by(ConvertibleBond.issue_date.desc())

        cb_result = await db.execute(cb_query)
        cbs = cb_result.scalars().all()

        # 인수자 수 조회 (JSON 배열 길이)
        import json
        cb_items = []
        for cb in cbs:
            subscribers_count = 0
            if cb.subscribers:
                try:
                    subscribers = json.loads(cb.subscribers) if isinstance(cb.subscribers, str) else cb.subscribers
                    subscribers_count = len(subscribers) if isinstance(subscribers, list) else 0
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse subscribers JSON for CB {cb.id}: {e}")
                    subscribers_count = 0

            cb_items.append(CompanyCBListItem(
                id=str(cb.id),
                bond_name=cb.bond_name or "전환사채",
                issue_date=cb.issue_date.isoformat() if cb.issue_date else None,
                issue_amount=cb.issue_amount,
                subscribers_count=subscribers_count
            ))

        return cb_items

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company CBs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/officers", response_model=List[CompanyOfficerListItem])
async def get_company_officers(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    회사의 임원 목록 조회

    - 등기임원 우선 정렬
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 임원 목록 조회 (officer_positions 기반)
        officer_query = (
            select(Officer, OfficerPosition.position.label("op_position"))
            .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
            .where(OfficerPosition.company_id == company_id)
            .where(OfficerPosition.is_current == True)
            .order_by(Officer.influence_score.desc().nulls_last(), Officer.name)
        )

        officer_result = await db.execute(officer_query)
        rows = officer_result.all()

        return [
            CompanyOfficerListItem(
                id=str(officer.id),
                name=officer.name,
                position=op_position or officer.position,
                influence_score=officer.influence_score
            )
            for officer, op_position in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company officers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/list", response_model=List[str])
async def list_sectors(
    db: AsyncSession = Depends(get_db)
):
    """
    업종 목록 조회

    - 중복 제거
    - 알파벳 순 정렬
    """
    # 캐시 조회 (업종 목록은 자주 바뀌지 않음)
    cached = cache.get("sectors_list")
    if cached:
        return cached

    try:
        query = select(Company.sector).where(
            Company.sector.isnot(None)
        ).distinct().order_by(Company.sector)

        result = await db.execute(query)
        sectors = [row[0] for row in result.all()]

        # 캐시 저장 (1시간)
        cache.set("sectors_list", sectors, ttl=3600)

        return sectors

    except Exception as e:
        logger.error(f"Error listing sectors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
