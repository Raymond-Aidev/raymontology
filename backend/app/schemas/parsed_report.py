"""
Parsed Report Schemas

파싱된 보고서 데이터 스키마
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


# ============================================================================
# Entity Schemas
# ============================================================================

class OfficerSchema(BaseModel):
    """임원 정보"""
    name: str = Field(..., description="이름")
    position: str = Field(..., description="직책")
    term_start: Optional[str] = Field(None, description="임기 시작일 (YYYY-MM-DD)")
    term_end: Optional[str] = Field(None, description="임기 종료일 (YYYY-MM-DD)")
    responsibilities: Optional[str] = Field(None, description="담당업무")


class ConvertibleBondSchema(BaseModel):
    """전환사채 정보"""
    issue_date: Optional[str] = Field(None, description="발행일 (YYYY-MM-DD)")
    maturity_date: Optional[str] = Field(None, description="만기일 (YYYY-MM-DD)")
    amount: int = Field(..., description="발행금액 (원)")
    conversion_price: Optional[int] = Field(None, description="전환가격 (원)")
    holder: Optional[str] = Field(None, description="보유자")
    conversion_rate: float = Field(100.0, description="전환율 (%)")


class RelatedPartySchema(BaseModel):
    """특수관계자 정보"""
    name: str = Field(..., description="특수관계자명")
    relationship: str = Field(..., description="관계 (계열사, 특수관계인 등)")
    transaction_amount: Optional[int] = Field(None, description="거래금액 (원)")


class ShareholderSchema(BaseModel):
    """주주 정보"""
    name: str = Field(..., description="주주명")
    shares: Optional[int] = Field(None, description="보유주식수")
    ownership_ratio: Optional[float] = Field(None, description="지분율 (%)")
    shareholder_type: Optional[str] = Field(None, description="주주 유형 (개인, 법인, 외국인 등)")


# ============================================================================
# Report Schemas
# ============================================================================

class ParsedReportSummary(BaseModel):
    """파싱된 보고서 요약"""
    report_id: str
    company_id: str
    rcept_no: str
    total_pages: int = Field(0, description="전체 페이지 수")
    text_length: int = Field(0, description="텍스트 길이")
    sections: List[str] = Field(default_factory=list, description="추출된 섹션 목록")
    officer_count: int = Field(0, description="임원 수")
    cb_count: int = Field(0, description="전환사채 수")
    related_party_count: int = Field(0, description="특수관계자 수")
    parsing_time: float = Field(0.0, description="파싱 소요 시간 (초)")
    parsed_at: str = Field(..., description="파싱 시각 (ISO 8601)")


class ParsedReportDetail(BaseModel):
    """파싱된 보고서 상세"""
    report_id: str
    company_id: str
    rcept_no: str
    metadata: Dict[str, Any] = Field(default_factory=dict, description="PDF 메타데이터")
    total_pages: int
    sections: Dict[str, int] = Field(
        default_factory=dict,
        description="섹션별 텍스트 길이 (섹션명: 길이)"
    )
    officers: List[OfficerSchema] = Field(default_factory=list, description="임원 목록")
    convertible_bonds: List[ConvertibleBondSchema] = Field(default_factory=list, description="전환사채 목록")
    related_parties: List[RelatedPartySchema] = Field(default_factory=list, description="특수관계자 목록")
    shareholders: List[ShareholderSchema] = Field(default_factory=list, description="주주 목록")
    parsed_at: str = Field(..., description="파싱 시각 (ISO 8601)")
    parsing_stats: Dict[str, Any] = Field(default_factory=dict, description="파싱 통계")


class ParsedReportValidation(BaseModel):
    """파싱 검증 결과"""
    report_id: str
    errors: List[str] = Field(default_factory=list, description="에러 목록")
    warnings: List[str] = Field(default_factory=list, description="경고 목록")
    is_valid: bool = Field(..., description="검증 통과 여부")


# ============================================================================
# Request Schemas
# ============================================================================

class ParseReportRequest(BaseModel):
    """보고서 파싱 요청"""
    rcept_no: str = Field(..., description="접수번호")
    company_id: Optional[str] = Field(None, description="회사 ID (선택)")
    use_ocr: bool = Field(False, description="OCR 사용 여부")
    extract_tables: bool = Field(False, description="테이블 추출 여부")


class ParseSectionRequest(BaseModel):
    """특정 섹션만 파싱 요청"""
    rcept_no: str = Field(..., description="접수번호")
    section_type: str = Field(
        ...,
        description="섹션 유형 (officers, convertible_bonds, related_parties 등)"
    )


# ============================================================================
# Background Task Schemas
# ============================================================================

class ParseJobStatus(BaseModel):
    """파싱 작업 상태"""
    job_id: str
    status: str = Field(..., description="작업 상태 (pending, running, completed, failed)")
    rcept_no: str
    company_id: Optional[str] = None
    progress: float = Field(0.0, ge=0.0, le=100.0, description="진행률 (%)")
    result: Optional[ParsedReportSummary] = None
    error_message: Optional[str] = None
    created_at: str = Field(..., description="생성 시각 (ISO 8601)")
    started_at: Optional[str] = Field(None, description="시작 시각 (ISO 8601)")
    completed_at: Optional[str] = Field(None, description="완료 시각 (ISO 8601)")


# ============================================================================
# Statistics
# ============================================================================

class ParsingStatistics(BaseModel):
    """파싱 통계"""
    total_reports: int = Field(0, description="전체 파싱된 보고서 수")
    total_officers: int = Field(0, description="전체 추출된 임원 수")
    total_cbs: int = Field(0, description="전체 추출된 전환사채 수")
    avg_parsing_time: float = Field(0.0, description="평균 파싱 시간 (초)")
    success_rate: float = Field(0.0, description="파싱 성공률 (%)")
    latest_parsed: Optional[str] = Field(None, description="최근 파싱 시각 (ISO 8601)")
