"""
File Streaming and Memory Management

Railway 환경 최적화: 큰 파일 처리
"""
import logging
from typing import AsyncIterator, BinaryIO, Optional
from pathlib import Path
import aiofiles
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# ============================================================================
# Streaming Constants
# ============================================================================

# 청크 크기 (Railway Hobby 메모리 제한 고려)
CHUNK_SIZE_SMALL = 8 * 1024  # 8KB (작은 파일)
CHUNK_SIZE_MEDIUM = 64 * 1024  # 64KB (중간 파일)
CHUNK_SIZE_LARGE = 512 * 1024  # 512KB (큰 파일)

# 메모리 임계값
MEMORY_THRESHOLD_MB = 400  # 400MB (Railway Hobby: 512MB)


# ============================================================================
# File Streaming
# ============================================================================

async def stream_file(
    file_path: Path,
    chunk_size: int = CHUNK_SIZE_MEDIUM,
) -> AsyncIterator[bytes]:
    """
    파일 스트리밍 (메모리 효율적)

    Args:
        file_path: 파일 경로
        chunk_size: 청크 크기

    Yields:
        bytes: 파일 청크

    Example:
        return StreamingResponse(
            stream_file(pdf_path),
            media_type="application/pdf"
        )
    """
    try:
        async with aiofiles.open(file_path, mode='rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        logger.debug(f"File streamed: {file_path}")

    except Exception as e:
        logger.error(f"File streaming error: {file_path} - {e}")
        raise


async def stream_large_file(
    file_path: Path,
    start_byte: int = 0,
    end_byte: Optional[int] = None,
) -> AsyncIterator[bytes]:
    """
    대용량 파일 스트리밍 (Range Request 지원)

    Args:
        file_path: 파일 경로
        start_byte: 시작 바이트
        end_byte: 종료 바이트 (None이면 끝까지)

    Yields:
        bytes: 파일 청크
    """
    try:
        async with aiofiles.open(file_path, mode='rb') as f:
            # 시작 위치로 이동
            await f.seek(start_byte)

            # 읽을 총 크기
            total_to_read = None
            if end_byte is not None:
                total_to_read = end_byte - start_byte + 1

            read_so_far = 0
            while True:
                # 읽을 청크 크기 계산
                if total_to_read is not None:
                    remaining = total_to_read - read_so_far
                    chunk_size = min(CHUNK_SIZE_LARGE, remaining)
                    if chunk_size <= 0:
                        break
                else:
                    chunk_size = CHUNK_SIZE_LARGE

                chunk = await f.read(chunk_size)
                if not chunk:
                    break

                yield chunk
                read_so_far += len(chunk)

        logger.debug(
            f"Large file streamed: {file_path}",
            extra={
                "start_byte": start_byte,
                "end_byte": end_byte,
                "bytes_read": read_so_far,
            }
        )

    except Exception as e:
        logger.error(f"Large file streaming error: {file_path} - {e}")
        raise


def create_streaming_response(
    file_path: Path,
    media_type: str = "application/octet-stream",
    filename: Optional[str] = None,
    chunk_size: int = CHUNK_SIZE_MEDIUM,
) -> StreamingResponse:
    """
    스트리밍 응답 생성

    Args:
        file_path: 파일 경로
        media_type: MIME 타입
        filename: 다운로드 파일명 (선택사항)
        chunk_size: 청크 크기

    Returns:
        StreamingResponse
    """
    headers = {}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    # 파일 크기 확인
    file_size = file_path.stat().st_size
    headers["Content-Length"] = str(file_size)

    return StreamingResponse(
        stream_file(file_path, chunk_size),
        media_type=media_type,
        headers=headers,
    )


# ============================================================================
# Batch Processing
# ============================================================================

async def process_in_batches(
    items: list,
    batch_size: int,
    process_func,
) -> list:
    """
    배치 단위로 처리 (메모리 최적화)

    Args:
        items: 처리할 항목들
        batch_size: 배치 크기
        process_func: 처리 함수 (async)

    Returns:
        list: 처리 결과

    Example:
        results = await process_in_batches(
            companies,
            batch_size=10,
            process_func=analyze_company
        )
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        logger.debug(
            f"Processing batch {i // batch_size + 1}",
            extra={
                "batch_size": len(batch),
                "total_items": len(items),
                "progress": f"{i + len(batch)}/{len(items)}",
            }
        )

        # 배치 처리
        batch_results = []
        for item in batch:
            result = await process_func(item)
            batch_results.append(result)

        results.extend(batch_results)

        # 메모리 사용량 체크
        from app.middleware.performance import get_memory_usage
        memory = get_memory_usage()
        if memory.get("rss_mb", 0) > MEMORY_THRESHOLD_MB:
            logger.warning(
                f"High memory usage during batch processing",
                extra={
                    "rss_mb": memory.get("rss_mb"),
                    "batch_index": i // batch_size + 1,
                }
            )

    return results


def get_optimal_batch_size(
    total_items: int,
    item_size_mb: float = 0.1,
    max_memory_mb: int = 100,
) -> int:
    """
    최적 배치 크기 계산

    Args:
        total_items: 전체 항목 수
        item_size_mb: 항목당 메모리 크기 (MB)
        max_memory_mb: 최대 메모리 사용량 (MB)

    Returns:
        int: 최적 배치 크기
    """
    # 메모리 기반 계산
    memory_based_size = int(max_memory_mb / item_size_mb)

    # 전체 항목 수 기반 조정
    if total_items < 100:
        return min(10, memory_based_size)
    elif total_items < 1000:
        return min(50, memory_based_size)
    else:
        return min(100, memory_based_size)


# ============================================================================
# Chunked Data Processing
# ============================================================================

class ChunkedProcessor:
    """
    청크 단위 데이터 처리기

    메모리 효율적인 대용량 데이터 처리
    """

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.processed_count = 0

    async def process_query_in_chunks(
        self,
        session,
        query,
        process_func,
    ) -> int:
        """
        쿼리 결과를 청크 단위로 처리

        Args:
            session: 데이터베이스 세션
            query: SQLAlchemy 쿼리
            process_func: 처리 함수 (async)

        Returns:
            int: 처리된 항목 수
        """
        offset = 0
        processed_total = 0

        while True:
            # 청크 조회
            chunk_query = query.offset(offset).limit(self.chunk_size)
            result = await session.execute(chunk_query)
            items = result.scalars().all()

            if not items:
                break

            # 청크 처리
            for item in items:
                await process_func(item)
                processed_total += 1

            logger.debug(
                f"Processed chunk",
                extra={
                    "offset": offset,
                    "chunk_size": len(items),
                    "total_processed": processed_total,
                }
            )

            # 다음 청크로
            offset += self.chunk_size

            # 청크 크기보다 적으면 마지막 청크
            if len(items) < self.chunk_size:
                break

        self.processed_count = processed_total
        return processed_total


# ============================================================================
# Memory-Efficient Iterators
# ============================================================================

async def iterate_large_dataset(
    session,
    model,
    chunk_size: int = 1000,
    filters: Optional[dict] = None,
) -> AsyncIterator:
    """
    대용량 데이터셋 이터레이터

    Args:
        session: 데이터베이스 세션
        model: SQLAlchemy 모델
        chunk_size: 청크 크기
        filters: 필터 조건

    Yields:
        모델 인스턴스
    """
    from sqlalchemy import select

    query = select(model)

    # 필터 적용
    if filters:
        for key, value in filters.items():
            query = query.where(getattr(model, key) == value)

    offset = 0

    while True:
        # 청크 조회
        chunk_query = query.offset(offset).limit(chunk_size)
        result = await session.execute(chunk_query)
        items = result.scalars().all()

        if not items:
            break

        # 아이템 yield
        for item in items:
            yield item

        offset += chunk_size

        if len(items) < chunk_size:
            break


# ============================================================================
# Temporary File Management
# ============================================================================

class TempFileManager:
    """임시 파일 관리자"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.created_files = []

    async def create_temp_file(
        self,
        content: bytes,
        suffix: str = ".tmp",
    ) -> Path:
        """
        임시 파일 생성

        Args:
            content: 파일 내용
            suffix: 파일 확장자

        Returns:
            Path: 임시 파일 경로
        """
        import uuid

        filename = f"temp_{uuid.uuid4().hex}{suffix}"
        file_path = self.base_dir / filename

        async with aiofiles.open(file_path, mode='wb') as f:
            await f.write(content)

        self.created_files.append(file_path)
        return file_path

    async def cleanup(self):
        """생성된 임시 파일 삭제"""
        for file_path in self.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Temp file deleted: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {file_path}: {e}")

        self.created_files.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
