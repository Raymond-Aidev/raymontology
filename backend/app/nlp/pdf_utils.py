"""
PDF 처리 유틸리티

Railway 환경 최적화:
- 메모리 효율적 처리
- 청크 단위 스트리밍
- 대용량 PDF 처리
"""
import logging
from pathlib import Path
from typing import AsyncIterator, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ============================================================================
# 메모리 효율적 PDF 처리
# ============================================================================

async def extract_text_streaming(
    pdf_path: Path,
    chunk_size: int = 10
) -> AsyncIterator[dict]:
    """
    PDF 텍스트 스트리밍 추출 (메모리 절약)

    Args:
        pdf_path: PDF 파일 경로
        chunk_size: 청크당 페이지 수 (기본 10페이지)

    Yields:
        {
            "page_num": 1,
            "text": "...",
            "chunk_index": 0
        }
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        logger.info(f"Streaming PDF extraction: {total_pages} pages")

        chunk_index = 0
        for start_page in range(0, total_pages, chunk_size):
            end_page = min(start_page + chunk_size, total_pages)

            # 청크 처리
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                text = page.get_text()

                yield {
                    "page_num": page_num + 1,
                    "text": text,
                    "chunk_index": chunk_index
                }

            chunk_index += 1

            logger.debug(
                f"Processed chunk {chunk_index}: pages {start_page+1}-{end_page}"
            )

        doc.close()

    except Exception as e:
        logger.error(f"Streaming extraction failed: {e}")
        raise


def estimate_pdf_size(pdf_path: Path) -> dict:
    """
    PDF 파일 크기 및 복잡도 추정

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        {
            "file_size_mb": 12.5,
            "total_pages": 100,
            "estimated_memory_mb": 50.0,  # 예상 메모리 사용량
            "should_use_streaming": True,  # 스트리밍 사용 권장 여부
            "recommended_chunk_size": 10
        }
    """
    import os

    file_size = os.path.getsize(pdf_path)
    file_size_mb = file_size / 1024 / 1024

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    # 메모리 사용량 추정 (대략 페이지당 500KB)
    estimated_memory_mb = (total_pages * 0.5)

    # Railway Hobby: 512MB
    # 안전하게 100MB 이상이면 스트리밍 권장
    should_use_streaming = estimated_memory_mb > 100

    # 청크 크기 계산 (목표: 청크당 50MB 이하)
    recommended_chunk_size = max(1, int(50 / 0.5))  # 페이지당 500KB 가정

    return {
        "file_size_mb": round(file_size_mb, 2),
        "total_pages": total_pages,
        "estimated_memory_mb": round(estimated_memory_mb, 2),
        "should_use_streaming": should_use_streaming,
        "recommended_chunk_size": recommended_chunk_size
    }


# ============================================================================
# PDF 전처리
# ============================================================================

def clean_text(text: str) -> str:
    """
    추출된 텍스트 정제

    - 불필요한 공백 제거
    - 특수문자 정리
    - 줄바꿈 정규화
    """
    import re

    # 여러 공백 → 단일 공백
    text = re.sub(r'\s+', ' ', text)

    # 여러 줄바꿈 → 2개까지
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 특수문자 정리 (일부만)
    text = text.replace('\u3000', ' ')  # 전각 공백
    text = text.replace('\xa0', ' ')  # non-breaking space

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def split_by_sections(
    text: str,
    max_section_length: int = 5000
) -> list[str]:
    """
    텍스트를 섹션으로 분할 (메모리 효율)

    Args:
        text: 전체 텍스트
        max_section_length: 섹션 최대 길이 (글자 수)

    Returns:
        분할된 섹션 리스트
    """
    sections = []
    current_section = ""

    # 단락 단위로 분할
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # 현재 섹션에 추가 가능한지 확인
        if len(current_section) + len(paragraph) <= max_section_length:
            current_section += paragraph + '\n\n'
        else:
            # 섹션 저장 후 새로 시작
            if current_section:
                sections.append(current_section.strip())
            current_section = paragraph + '\n\n'

    # 마지막 섹션
    if current_section:
        sections.append(current_section.strip())

    logger.debug(f"Split text into {len(sections)} sections")

    return sections


# ============================================================================
# 텍스트 품질 검증
# ============================================================================

def validate_extracted_text(text: str, min_length: int = 100) -> dict:
    """
    추출된 텍스트 품질 검증

    Args:
        text: 추출된 텍스트
        min_length: 최소 텍스트 길이

    Returns:
        {
            "is_valid": True,
            "length": 12345,
            "korean_ratio": 0.85,  # 한글 비율
            "warnings": ["..."]
        }
    """
    import re

    warnings = []

    # 길이 확인
    text_length = len(text)
    if text_length < min_length:
        warnings.append(f"텍스트가 너무 짧음: {text_length}자")

    # 한글 비율 확인
    korean_chars = len(re.findall(r'[가-힣]', text))
    korean_ratio = korean_chars / max(text_length, 1)

    if korean_ratio < 0.1:
        warnings.append(f"한글 비율이 낮음: {korean_ratio:.1%}")

    # 공백 비율 확인
    whitespace_chars = len(re.findall(r'\s', text))
    whitespace_ratio = whitespace_chars / max(text_length, 1)

    if whitespace_ratio > 0.5:
        warnings.append(f"공백 비율이 높음: {whitespace_ratio:.1%}")

    is_valid = len(warnings) == 0

    return {
        "is_valid": is_valid,
        "length": text_length,
        "korean_ratio": round(korean_ratio, 3),
        "whitespace_ratio": round(whitespace_ratio, 3),
        "warnings": warnings
    }


# ============================================================================
# PDF 메타데이터 추출
# ============================================================================

def extract_pdf_metadata(pdf_path: Path) -> dict:
    """
    PDF 메타데이터 추출

    Returns:
        {
            "title": "사업보고서",
            "author": "삼성전자",
            "subject": "...",
            "creator": "...",
            "producer": "...",
            "creation_date": "2023-12-01",
            "modification_date": "2023-12-01"
        }
    """
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()

        # 날짜 파싱
        from datetime import datetime

        def parse_date(date_str):
            """PDF 날짜 형식 파싱 (D:20231201123456)"""
            if not date_str:
                return None

            try:
                # D:YYYYMMDDHHmmss 형식
                if date_str.startswith('D:'):
                    date_str = date_str[2:16]  # YYYYMMDDHHmmss
                    return datetime.strptime(date_str, '%Y%m%d%H%M%S').isoformat()
            except:
                pass

            return date_str

        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": parse_date(metadata.get("creationDate")),
            "modification_date": parse_date(metadata.get("modDate")),
        }

    except Exception as e:
        logger.error(f"Failed to extract PDF metadata: {e}")
        return {}


# ============================================================================
# 이미지 기반 페이지 감지
# ============================================================================

def detect_image_pages(pdf_path: Path, threshold: float = 0.5) -> list[int]:
    """
    이미지 기반 페이지 감지 (OCR 필요 페이지)

    Args:
        pdf_path: PDF 파일 경로
        threshold: 이미지 비율 임계값 (0.5 = 50% 이상)

    Returns:
        이미지 페이지 번호 리스트 [1, 5, 10, ...]
    """
    try:
        doc = fitz.open(pdf_path)
        image_pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # 페이지 내 이미지 리스트
            images = page.get_images()

            # 텍스트 길이
            text = page.get_text()
            text_length = len(text.strip())

            # 이미지가 많고 텍스트가 적으면 이미지 페이지
            if len(images) > 0 and text_length < 100:
                image_pages.append(page_num + 1)

        doc.close()

        if image_pages:
            logger.info(f"Detected {len(image_pages)} image pages: {image_pages}")

        return image_pages

    except Exception as e:
        logger.error(f"Failed to detect image pages: {e}")
        return []


# ============================================================================
# 테이블 추출 (간단한 버전)
# ============================================================================

def extract_tables(text: str) -> list[list[str]]:
    """
    텍스트에서 간단한 테이블 추출

    Args:
        text: 텍스트

    Returns:
        [
            ["이름", "직책", "임기"],
            ["김철수", "대표이사", "2020.01~2023.12"],
            ...
        ]
    """
    import re

    tables = []

    # 간단한 테이블 패턴 (탭 또는 여러 공백으로 구분)
    lines = text.split('\n')

    table_rows = []
    in_table = False

    for line in lines:
        # 탭 또는 연속 공백으로 분할
        cells = re.split(r'\t+|\s{3,}', line.strip())

        # 3개 이상 셀이면 테이블 행으로 간주
        if len(cells) >= 3:
            table_rows.append(cells)
            in_table = True
        else:
            # 테이블 종료
            if in_table and len(table_rows) > 0:
                tables.append(table_rows)
                table_rows = []
            in_table = False

    # 마지막 테이블
    if table_rows:
        tables.append(table_rows)

    logger.debug(f"Extracted {len(tables)} tables")

    return tables
