"""
Pagination Utilities

Railway 최적화: 효율적인 페이지네이션
"""
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Select

T = TypeVar("T")


class PaginationParams(BaseModel):
    """페이지네이션 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호 (1부터 시작)")
    page_size: int = Field(default=20, ge=1, le=50, description="페이지 크기 (최대 50)")

    @property
    def offset(self) -> int:
        """오프셋 계산"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """리미트"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답"""
    items: List[T] = Field(description="데이터 항목들")
    total: int = Field(description="전체 항목 수")
    page: int = Field(description="현재 페이지")
    page_size: int = Field(description="페이지 크기")
    total_pages: int = Field(description="전체 페이지 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
    has_prev: bool = Field(description="이전 페이지 존재 여부")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """
        페이지네이션 응답 생성

        Args:
            items: 데이터 항목들
            total: 전체 항목 수
            params: 페이지네이션 파라미터

        Returns:
            PaginatedResponse
        """
        total_pages = (total + params.page_size - 1) // params.page_size

        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )


async def paginate(
    session: AsyncSession,
    query: Select,
    params: PaginationParams,
    count_query: Optional[Select] = None,
) -> tuple[List, int]:
    """
    SQLAlchemy 쿼리 페이지네이션

    Args:
        session: 데이터베이스 세션
        query: SELECT 쿼리
        params: 페이지네이션 파라미터
        count_query: COUNT 쿼리 (선택사항, 없으면 자동 생성)

    Returns:
        (items, total): 항목 리스트, 전체 개수

    Example:
        query = select(Company).where(Company.market == "KOSPI")
        items, total = await paginate(session, query, PaginationParams(page=1, page_size=20))
    """
    # 전체 개수 조회
    if count_query is None:
        # 자동으로 COUNT 쿼리 생성
        count_query = select(func.count()).select_from(query.subquery())

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # 데이터 조회 (페이지네이션 적용)
    paginated_query = query.offset(params.offset).limit(params.limit)
    result = await session.execute(paginated_query)
    items = result.scalars().all()

    return list(items), total


class CursorPaginationParams(BaseModel):
    """커서 기반 페이지네이션 파라미터 (대용량 데이터용)"""
    cursor: Optional[str] = Field(default=None, description="커서 (다음 페이지 시작점)")
    limit: int = Field(default=20, ge=1, le=100, description="가져올 항목 수 (최대 100)")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """커서 기반 페이지네이션 응답"""
    items: List[T] = Field(description="데이터 항목들")
    next_cursor: Optional[str] = Field(description="다음 커서 (없으면 마지막 페이지)")
    has_more: bool = Field(description="다음 페이지 존재 여부")

    @classmethod
    def create(
        cls,
        items: List[T],
        limit: int,
        cursor_field: str = "id",
    ) -> "CursorPaginatedResponse[T]":
        """
        커서 기반 페이지네이션 응답 생성

        Args:
            items: 데이터 항목들
            limit: 요청한 리미트
            cursor_field: 커서 필드명 (기본: "id")

        Returns:
            CursorPaginatedResponse
        """
        has_more = len(items) > limit

        # 리미트보다 많이 가져왔으면 마지막 항목 제거
        if has_more:
            items = items[:-1]

        # 다음 커서 생성
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            if hasattr(last_item, cursor_field):
                next_cursor = str(getattr(last_item, cursor_field))
            elif isinstance(last_item, dict):
                next_cursor = str(last_item.get(cursor_field))

        return cls(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )


# ============================================================================
# Optimization Helpers
# ============================================================================

def optimize_query_for_pagination(query: Select) -> Select:
    """
    페이지네이션을 위한 쿼리 최적화

    - SELECT DISTINCT 제거 (성능 저하)
    - 불필요한 JOIN 제거
    - 인덱스 활용 가능한 ORDER BY 추가

    Args:
        query: 원본 쿼리

    Returns:
        최적화된 쿼리
    """
    # TODO: 실제 최적화 로직 구현
    # 여기서는 플레이스홀더
    return query


def get_optimized_page_size(total: int, requested_size: int, max_size: int = 50) -> int:
    """
    최적화된 페이지 크기 계산

    Args:
        total: 전체 항목 수
        requested_size: 요청한 크기
        max_size: 최대 크기

    Returns:
        최적화된 페이지 크기
    """
    # 최대 크기 제한
    size = min(requested_size, max_size)

    # 전체 항목이 적으면 크기 조정
    if total <= 10:
        return min(size, 10)
    elif total <= 50:
        return min(size, 25)

    return size
