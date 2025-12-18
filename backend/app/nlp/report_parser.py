"""
Report Parser

사업보고서 파싱 파이프라인

PDF → 텍스트 → 섹션 → 개체명 추출 → 구조화된 데이터
"""
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import logging

from app.nlp.pdf_extractor import PDFExtractor
from app.nlp.section_parser import SectionParser
from app.nlp.ner_extractor import NERExtractor

logger = logging.getLogger(__name__)


class ParsedReport:
    """파싱된 보고서 데이터"""

    def __init__(
        self,
        report_id: str,
        company_id: str,
        rcept_no: str,
        pdf_path: Path
    ):
        self.report_id = report_id
        self.company_id = company_id
        self.rcept_no = rcept_no
        self.pdf_path = pdf_path

        # 원시 데이터
        self.full_text: Optional[str] = None
        self.metadata: Dict = {}
        self.total_pages: int = 0

        # 섹션
        self.sections: Dict[str, str] = {}

        # 추출된 개체
        self.officers: List[Dict] = []
        self.convertible_bonds: List[Dict] = []
        self.related_parties: List[Dict] = []
        self.shareholders: List[Dict] = []

        # 파싱 정보
        self.parsed_at: datetime = datetime.utcnow()
        self.parsing_stats: Dict = {
            "extraction_time": 0.0,
            "section_count": 0,
            "officer_count": 0,
            "cb_count": 0,
        }

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "report_id": self.report_id,
            "company_id": self.company_id,
            "rcept_no": self.rcept_no,
            "metadata": self.metadata,
            "total_pages": self.total_pages,
            "sections": {
                section_name: len(section_text)
                for section_name, section_text in self.sections.items()
            },
            "officers": self.officers,
            "convertible_bonds": self.convertible_bonds,
            "related_parties": self.related_parties,
            "shareholders": self.shareholders,
            "parsed_at": self.parsed_at.isoformat(),
            "parsing_stats": self.parsing_stats,
        }


class ReportParser:
    """
    사업보고서 파서

    통합 파이프라인: PDF → 텍스트 → 섹션 → NER → 구조화
    """

    def __init__(
        self,
        use_ocr: bool = False,
        extract_tables: bool = False
    ):
        """
        Args:
            use_ocr: OCR 사용 여부 (Railway에서는 False 권장)
            extract_tables: 테이블 추출 여부 (선택적)
        """
        self.pdf_extractor = PDFExtractor(use_ocr=use_ocr)
        self.section_parser = SectionParser()
        self.ner_extractor = NERExtractor()
        self.extract_tables = extract_tables

    async def parse_report(
        self,
        pdf_path: Path,
        company_id: str,
        rcept_no: Optional[str] = None
    ) -> ParsedReport:
        """
        사업보고서 파싱 (메인 파이프라인)

        Args:
            pdf_path: PDF 파일 경로
            company_id: 회사 ID (UUID)
            rcept_no: 접수번호

        Returns:
            ParsedReport 객체

        파이프라인:
        1. PDF → 텍스트 추출
        2. 텍스트 → 섹션 분할
        3. 섹션 → 개체명 추출 (임원, CB 등)
        4. 구조화된 데이터 생성
        """
        start_time = datetime.utcnow()

        # 보고서 객체 생성
        report = ParsedReport(
            report_id=str(uuid.uuid4()),
            company_id=company_id,
            rcept_no=rcept_no or str(uuid.uuid4()),
            pdf_path=pdf_path
        )

        logger.info(f"Starting report parsing: {pdf_path}")

        try:
            # 1. PDF → 텍스트
            logger.info("Step 1: Extracting text from PDF")
            pdf_data = await self.pdf_extractor.extract_text(pdf_path)

            report.full_text = pdf_data["full_text"]
            report.metadata = pdf_data["metadata"]
            report.total_pages = pdf_data["total_pages"]

            logger.info(f"Extracted {len(report.full_text)} chars from {report.total_pages} pages")

            # 2. 텍스트 → 섹션 분할
            logger.info("Step 2: Parsing sections")
            report.sections = await self.section_parser.parse_sections(report.full_text)
            report.parsing_stats["section_count"] = len(report.sections)

            logger.info(f"Extracted {len(report.sections)} sections")

            # 3. 섹션 → 개체명 추출
            logger.info("Step 3: Extracting entities")

            # 3-1. 임원 추출
            officer_section = (
                report.sections.get("officers_info") or
                await self.section_parser.extract_officer_section(report.full_text)
            )
            if officer_section:
                report.officers = await self.ner_extractor.extract_officers(officer_section)
                report.parsing_stats["officer_count"] = len(report.officers)
                logger.info(f"Extracted {len(report.officers)} officers")

            # 3-2. 전환사채 추출
            cb_section = (
                report.sections.get("convertible_bonds") or
                await self.section_parser.extract_cb_section(report.full_text)
            )
            if cb_section:
                report.convertible_bonds = await self.ner_extractor.extract_convertible_bonds(cb_section)
                report.parsing_stats["cb_count"] = len(report.convertible_bonds)
                logger.info(f"Extracted {len(report.convertible_bonds)} convertible bonds")

            # 3-3. 특수관계자 추출
            related_party_section = (
                report.sections.get("related_party_transactions") or
                await self.section_parser.extract_related_party_section(report.full_text)
            )
            if related_party_section:
                report.related_parties = await self.ner_extractor.extract_related_parties(related_party_section)
                logger.info(f"Extracted {len(report.related_parties)} related parties")

            # 4. 통계 계산
            end_time = datetime.utcnow()
            report.parsing_stats["extraction_time"] = (end_time - start_time).total_seconds()

            logger.info(f"Report parsing completed in {report.parsing_stats['extraction_time']:.2f}s")
            logger.info(f"Summary: {report.parsing_stats}")

            return report

        except Exception as e:
            logger.error(f"Failed to parse report {pdf_path}: {e}")
            raise

    async def parse_officer_section_only(
        self,
        pdf_path: Path,
        company_id: str
    ) -> List[Dict]:
        """
        임원 정보만 추출 (경량 파싱)

        Args:
            pdf_path: PDF 파일 경로
            company_id: 회사 ID

        Returns:
            임원 리스트
        """
        logger.info(f"Extracting officers only from {pdf_path}")

        # 텍스트 추출
        pdf_data = await self.pdf_extractor.extract_text(pdf_path)
        full_text = pdf_data["full_text"]

        # 임원 섹션 추출
        officer_section = await self.section_parser.extract_officer_section(full_text)

        if not officer_section:
            logger.warning("Officer section not found")
            return []

        # 임원 추출
        officers = await self.ner_extractor.extract_officers(officer_section)

        logger.info(f"Extracted {len(officers)} officers")
        return officers

    async def parse_cb_section_only(
        self,
        pdf_path: Path,
        company_id: str
    ) -> List[Dict]:
        """
        전환사채 정보만 추출 (경량 파싱)

        Args:
            pdf_path: PDF 파일 경로
            company_id: 회사 ID

        Returns:
            전환사채 리스트
        """
        logger.info(f"Extracting CBs only from {pdf_path}")

        # 텍스트 추출
        pdf_data = await self.pdf_extractor.extract_text(pdf_path)
        full_text = pdf_data["full_text"]

        # CB 섹션 추출
        cb_section = await self.section_parser.extract_cb_section(full_text)

        if not cb_section:
            logger.warning("CB section not found")
            return []

        # CB 추출
        cbs = await self.ner_extractor.extract_convertible_bonds(cb_section)

        logger.info(f"Extracted {len(cbs)} convertible bonds")
        return cbs

    async def validate_parsed_data(self, report: ParsedReport) -> Dict[str, List[str]]:
        """
        파싱된 데이터 검증

        Args:
            report: 파싱된 보고서

        Returns:
            {
                "errors": ["...", ...],
                "warnings": ["...", ...],
            }
        """
        errors = []
        warnings = []

        # 필수 섹션 확인
        required_sections = ["company_overview", "officers_info"]
        for section in required_sections:
            if section not in report.sections:
                warnings.append(f"Missing required section: {section}")

        # 임원 데이터 검증
        for officer in report.officers:
            if not officer.get("name"):
                errors.append("Officer missing name")
            if not officer.get("position"):
                errors.append(f"Officer {officer.get('name')} missing position")

        # CB 데이터 검증
        for cb in report.convertible_bonds:
            if not cb.get("amount"):
                warnings.append("CB missing amount")

        logger.info(f"Validation: {len(errors)} errors, {len(warnings)} warnings")

        return {
            "errors": errors,
            "warnings": warnings,
        }

    async def get_parsing_summary(self, report: ParsedReport) -> Dict:
        """
        파싱 요약 정보

        Args:
            report: 파싱된 보고서

        Returns:
            요약 정보
        """
        return {
            "report_id": report.report_id,
            "company_id": report.company_id,
            "total_pages": report.total_pages,
            "text_length": len(report.full_text) if report.full_text else 0,
            "sections": list(report.sections.keys()),
            "officer_count": len(report.officers),
            "cb_count": len(report.convertible_bonds),
            "related_party_count": len(report.related_parties),
            "parsing_time": report.parsing_stats.get("extraction_time", 0),
            "parsed_at": report.parsed_at.isoformat(),
        }


# ============================================================================
# 헬퍼 함수
# ============================================================================

async def parse_business_report(
    pdf_path: Path,
    company_id: str,
    rcept_no: Optional[str] = None,
    use_ocr: bool = False
) -> ParsedReport:
    """
    사업보고서 파싱 (간편 함수)

    Args:
        pdf_path: PDF 파일 경로
        company_id: 회사 ID
        rcept_no: 접수번호
        use_ocr: OCR 사용 여부

    Returns:
        ParsedReport 객체
    """
    parser = ReportParser(use_ocr=use_ocr)
    return await parser.parse_report(pdf_path, company_id, rcept_no)
