"""
Company Service

비즈니스 로직 및 Redis 캐싱 (CacheManager 패턴 적용)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from redis.asyncio import Redis
from typing import Optional, List, Tuple
import json
import uuid

from app.models.companies import Company
from app.schemas.company import (
    CompanySearchParams,
    CompanyListItem,
    CompanySearchResult,
    CompanyDetail,
)
from app.utils.cache import cache


class CompanyService:
    """회사 서비스 (CacheManager 패턴 적용)"""

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        self.db = db
        self.redis = redis
        self.cache = cache  # CacheManager 인스턴스

    async def search_companies(
        self,
        params: CompanySearchParams
    ) -> CompanySearchResult:
        """
        회사 검색 (CacheManager.get_or_compute 패턴)

        Args:
            params: 검색 파라미터

        Returns:
            CompanySearchResult
        """
        if not self.redis:
            # Redis 없으면 직접 DB 조회
            return await self._perform_search(params)

        # CacheManager.get_or_compute 패턴 사용
        cache_key = self._generate_cache_key("search", params)

        result = await self.cache.get_or_compute(
            self.redis,
            cache_key,
            lambda: self._perform_search(params),
            self.cache.TTL_SEARCH_RESULTS
        )

        return CompanySearchResult(**result) if isinstance(result, dict) else result

    async def _perform_search(self, params: CompanySearchParams) -> dict:
        """
        실제 검색 수행 (DB 조회)

        Args:
            params: 검색 파라미터

        Returns:
            dict: 검색 결과 (직렬화 가능)
        """
        # 쿼리 빌드
        query = select(Company)

        # 검색어 필터
        if params.q:
            search_term = f"%{params.q}%"
            query = query.where(
                or_(
                    Company.name.ilike(search_term),
                    Company.ticker.ilike(search_term),
                    Company.name_en.ilike(search_term),
                )
            )

        # 시장 필터
        if params.market:
            query = query.where(Company.market == params.market)

        # 섹터 필터
        if params.sector:
            query = query.where(Company.sector == params.sector)

        # 시가총액 필터
        if params.min_market_cap is not None:
            query = query.where(Company.market_cap >= params.min_market_cap)
        if params.max_market_cap is not None:
            query = query.where(Company.market_cap <= params.max_market_cap)

        # 리스크 점수 필터 (ownership_concentration 활용)
        if params.min_risk_score is not None:
            query = query.where(Company.ownership_concentration >= params.min_risk_score)

        # 총 개수 (정렬/페이징 전)
        count_query = select(func.count()).select_from(query.subquery())
        result = await self.db.execute(count_query)
        total = result.scalar()

        # 정렬
        sort_column = getattr(Company, params.sort_by, Company.market_cap)
        if params.sort_order == "desc":
            query = query.order_by(sort_column.desc().nulls_last())
        else:
            query = query.order_by(sort_column.asc().nulls_last())

        # 페이징
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        # 실행
        result = await self.db.execute(query)
        companies = result.scalars().all()

        # 결과 생성
        items = [CompanyListItem.model_validate(c) for c in companies]

        search_result = CompanySearchResult(
            total=total,
            items=items,
            page=params.page,
            page_size=params.page_size,
            has_next=offset + len(items) < total,
        )

        return search_result.model_dump()

    async def get_company_by_id(self, company_id: uuid.UUID) -> Optional[CompanyDetail]:
        """
        ID로 회사 조회 (CacheManager.get_or_compute 패턴)

        Args:
            company_id: 회사 UUID

        Returns:
            CompanyDetail 또는 None
        """
        if not self.redis:
            # Redis 없으면 직접 DB 조회
            result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
            return CompanyDetail.model_validate(company) if company else None

        # CacheManager.get_or_compute 패턴 사용
        cache_key = f"company:{company_id}"

        async def fetch_from_db():
            result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
            if not company:
                return None
            return CompanyDetail.model_validate(company).model_dump()

        result = await self.cache.get_or_compute(
            self.redis,
            cache_key,
            fetch_from_db,
            self.cache.TTL_COMPANY_INFO
        )

        return CompanyDetail(**result) if result else None

    async def get_company_by_ticker(self, ticker: str) -> Optional[CompanyDetail]:
        """
        티커로 회사 조회

        Args:
            ticker: 종목 코드

        Returns:
            CompanyDetail 또는 None
        """
        # 캐시 확인
        cache_key = f"company:ticker:{ticker}"

        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return CompanyDetail(**data)

        # DB 조회
        result = await self.db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = result.scalar_one_or_none()

        if not company:
            return None

        company_detail = CompanyDetail.model_validate(company)

        # 캐시 저장
        if self.redis:
            await self.redis.setex(
                cache_key,
                self.cache.TTL_COMPANY_INFO,
                json.dumps(company_detail.model_dump(), default=str)
            )

        return company_detail

    async def invalidate_cache(self, company_id: uuid.UUID):
        """
        캐시 무효화

        Args:
            company_id: 회사 UUID
        """
        if not self.redis:
            return

        # 회사 캐시 삭제
        await self.redis.delete(f"company:{company_id}")

        # 검색 캐시 전체 삭제 (패턴 매칭)
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match="company:search:*",
                count=100
            )
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    def _generate_cache_key(self, prefix: str, params: CompanySearchParams) -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 접두사
            params: 검색 파라미터

        Returns:
            캐시 키
        """
        # 파라미터를 정렬된 문자열로 변환
        param_str = "_".join([
            f"{k}={v}" for k, v in sorted(params.model_dump().items())
            if v is not None
        ])

        return f"company:{prefix}:{param_str}"


# ============================================================================
# 헬퍼 함수
# ============================================================================

async def get_company_service(db: AsyncSession, redis: Optional[Redis] = None) -> CompanyService:
    """
    CompanyService 인스턴스 생성

    Args:
        db: 데이터베이스 세션
        redis: Redis 클라이언트

    Returns:
        CompanyService
    """
    return CompanyService(db=db, redis=redis)
