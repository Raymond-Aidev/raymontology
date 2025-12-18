"""
PDF Text Extractor

PDF에서 텍스트 추출 (PyMuPDF + Tesseract OCR)
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional
import logging
from PIL import Image
import io
import re

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    PDF 텍스트 추출기

    PyMuPDF로 텍스트 추출, OCR은 이미지 페이지에만 사용
    """

    def __init__(
        self,
        use_ocr: bool = False,
        min_text_length: int = 50
    ):
        """
        Args:
            use_ocr: OCR 사용 여부 (기본 False, Railway 메모리 절약)
            min_text_length: 페이지당 최소 텍스트 길이 (이하면 OCR 시도)
        """
        self.use_ocr = use_ocr
        self.min_text_length = min_text_length

    async def extract_text(self, pdf_path: Path) -> Dict[str, any]:
        """
        PDF에서 텍스트 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            {
                "pages": [{"page_num": 1, "text": "..."}, ...],
                "full_text": "전체 텍스트",
                "metadata": {"title": "...", "author": "...", ...},
                "total_pages": 100
            }
        """
        try:
            # PDF 열기
            doc = fitz.open(pdf_path)

            # 메타데이터
            metadata = doc.metadata
            total_pages = len(doc)

            logger.info(f"Extracting text from PDF: {pdf_path} ({total_pages} pages)")

            # 페이지별 텍스트 추출
            pages = []
            for page_num in range(total_pages):
                page = doc[page_num]
                text = await self._extract_page_text(page, page_num + 1)

                pages.append({
                    "page_num": page_num + 1,
                    "text": text
                })

            # 전체 텍스트
            full_text = "\n\n".join(p["text"] for p in pages)

            doc.close()

            logger.info(f"Extracted {len(full_text)} characters from {total_pages} pages")

            return {
                "pages": pages,
                "full_text": full_text,
                "metadata": metadata,
                "total_pages": total_pages
            }

        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
            raise

    async def _extract_page_text(self, page: fitz.Page, page_num: int) -> str:
        """
        단일 페이지에서 텍스트 추출

        Args:
            page: PyMuPDF 페이지 객체
            page_num: 페이지 번호

        Returns:
            추출된 텍스트
        """
        # 기본 텍스트 추출
        text = page.get_text("text")

        # 텍스트 정리
        text = self._clean_text(text)

        # OCR 필요 여부 확인
        if self.use_ocr and len(text) < self.min_text_length:
            logger.info(f"Page {page_num} has insufficient text ({len(text)} chars), trying OCR")
            ocr_text = await self._extract_with_ocr(page, page_num)
            if len(ocr_text) > len(text):
                text = ocr_text

        return text

    async def _extract_with_ocr(self, page: fitz.Page, page_num: int) -> str:
        """
        OCR로 텍스트 추출 (이미지 페이지용)

        Args:
            page: PyMuPDF 페이지 객체
            page_num: 페이지 번호

        Returns:
            OCR 추출 텍스트
        """
        try:
            import pytesseract

            # 페이지를 이미지로 변환
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # OCR 실행 (한글 + 영어)
            text = pytesseract.image_to_string(img, lang='kor+eng')

            # 정리
            text = self._clean_text(text)

            logger.info(f"OCR extracted {len(text)} chars from page {page_num}")
            return text

        except ImportError:
            logger.warning("pytesseract not available, skipping OCR")
            return ""
        except Exception as e:
            logger.error(f"OCR failed for page {page_num}: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """
        텍스트 정리

        - 연속된 공백 제거
        - 연속된 줄바꿈 정리
        - 특수문자 정규화
        """
        if not text:
            return ""

        # 연속된 공백 → 단일 공백
        text = re.sub(r' +', ' ', text)

        # 연속된 줄바꿈 → 최대 2개
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 탭 → 공백
        text = text.replace('\t', ' ')

        # 양쪽 공백 제거
        text = text.strip()

        return text

    async def extract_tables(self, pdf_path: Path) -> List[Dict]:
        """
        PDF에서 테이블 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            테이블 리스트 [{"page": 1, "table": [[...], [...]]}, ...]
        """
        try:
            import camelot

            # Camelot으로 테이블 추출
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')

            results = []
            for table in tables:
                results.append({
                    "page": table.page,
                    "table": table.df.values.tolist(),  # DataFrame → 리스트
                    "accuracy": table.accuracy
                })

            logger.info(f"Extracted {len(results)} tables from {pdf_path}")
            return results

        except ImportError:
            logger.warning("camelot-py not available, skipping table extraction")
            return []
        except Exception as e:
            logger.error(f"Table extraction failed for {pdf_path}: {e}")
            return []

    async def get_page_count(self, pdf_path: Path) -> int:
        """
        PDF 페이지 수 조회

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            페이지 수
        """
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get page count for {pdf_path}: {e}")
            return 0

    async def extract_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """
        PDF에서 이미지 추출

        Args:
            pdf_path: PDF 파일 경로
            output_dir: 이미지 저장 디렉토리

        Returns:
            추출된 이미지 경로 리스트
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            doc = fitz.open(pdf_path)
            image_paths = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images()

                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 이미지 저장
                    image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                    image_path = output_dir / image_filename
                    image_path.write_bytes(image_bytes)

                    image_paths.append(image_path)

            doc.close()

            logger.info(f"Extracted {len(image_paths)} images from {pdf_path}")
            return image_paths

        except Exception as e:
            logger.error(f"Image extraction failed for {pdf_path}: {e}")
            return []


# ============================================================================
# 헬퍼 함수
# ============================================================================

async def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = False) -> str:
    """
    PDF에서 전체 텍스트 추출 (간편 함수)

    Args:
        pdf_path: PDF 파일 경로
        use_ocr: OCR 사용 여부

    Returns:
        추출된 전체 텍스트
    """
    extractor = PDFExtractor(use_ocr=use_ocr)
    result = await extractor.extract_text(pdf_path)
    return result["full_text"]
