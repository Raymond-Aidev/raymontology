"""
BaseParser - DART 파서 공통 기능

검증된 로직 재사용:
- extract_xml_from_zip(): ZIP 해제 (ACODE=11011 우선)
- _decode_xml(): 인코딩 감지 (UTF-8/EUC-KR/CP949)
- _detect_unit_from_content(): 섹션별 단위 감지
- _parse_amount(): 금액 파싱 및 정규화
- _clean_xml_text(): XML 태그 제거
"""

import json
import logging
import os
import re
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """DART 파서 기본 클래스 - 공통 기능 제공"""

    # 기본 설정
    DART_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart'

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        self.stats = {
            'files_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'errors': 0,
        }

    # =========================================================================
    # ZIP/XML 추출 (v2.0 검증 로직)
    # =========================================================================

    def extract_xml_from_zip(self, zip_path: Path, prefer_acode: str = '11011') -> Optional[str]:
        """ZIP에서 XML 추출 (사업보고서 ACODE=11011 우선)

        Args:
            zip_path: ZIP 파일 경로
            prefer_acode: 우선 추출할 ACODE (기본: 11011=사업보고서)

        Returns:
            XML 문자열 또는 None
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                xml_files = [n for n in zf.namelist() if n.endswith('.xml')]

                # 1. 선호 ACODE 찾기
                for name in xml_files:
                    raw_bytes = zf.read(name)
                    content = self._decode_xml(raw_bytes)
                    if content and f'ACODE="{prefer_acode}"' in content:
                        logger.debug(f"Found preferred ACODE ({prefer_acode}): {name}")
                        return content

                # 2. 없으면 가장 큰 XML (일반적으로 본문)
                largest = None
                largest_size = 0
                for name in xml_files:
                    info = zf.getinfo(name)
                    if info.file_size > largest_size:
                        largest = name
                        largest_size = info.file_size

                if largest:
                    raw_bytes = zf.read(largest)
                    content = self._decode_xml(raw_bytes)
                    if content:
                        logger.debug(f"Using largest XML: {largest} ({largest_size:,} bytes)")
                        return content

        except Exception as e:
            logger.error(f"ZIP extraction error: {zip_path}: {e}")
        return None

    def extract_all_xml_from_zip(self, zip_path: Path) -> List[str]:
        """ZIP에서 모든 XML 추출 (임원정보 등 여러 섹션 필요시)"""
        contents = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        raw_bytes = zf.read(name)
                        content = self._decode_xml(raw_bytes)
                        if content:
                            contents.append(content)
        except Exception as e:
            logger.error(f"ZIP extraction error: {zip_path}: {e}")
        return contents

    # =========================================================================
    # 인코딩 처리 (v2.0 검증 로직)
    # =========================================================================

    def _decode_xml(self, raw_bytes: bytes) -> Optional[str]:
        """XML 바이트를 문자열로 디코딩 (다중 인코딩 지원)

        시도 순서: UTF-8 → EUC-KR → CP949 → UTF-8 with errors=replace
        """
        for encoding in ['utf-8', 'euc-kr', 'cp949']:
            try:
                content = raw_bytes.decode(encoding)
                # 한글 키워드로 성공 여부 확인
                if '재무' in content or '자산' in content or '임원' in content:
                    return content
            except UnicodeDecodeError:
                continue
        # 모두 실패시 UTF-8 with replace
        return raw_bytes.decode('utf-8', errors='replace')

    # =========================================================================
    # 단위 감지 (v2.0 핵심 개선 - 섹션별 독립 감지)
    # =========================================================================

    def _detect_unit_from_content(self, content: str) -> int:
        """섹션 내용에서 단위 감지

        v2.0 개선: 문서 전체가 아닌 해당 섹션에서만 단위 감지
        - '단위 : 원' → 1
        - '단위 : 천원' → 1,000
        - '단위 : 백만원' → 1,000,000
        - '단위 : 억원' → 100,000,000

        기본값: 1 (원)
        """
        # 단위 패턴 (공백 유연 처리)
        patterns = [
            (r'단\s*위\s*[:：]\s*원', 1),
            (r'단\s*위\s*[:：]\s*천\s*원', 1_000),
            (r'단\s*위\s*[:：]\s*백\s*만\s*원', 1_000_000),
            (r'단\s*위\s*[:：]\s*억\s*원', 100_000_000),
            # 영문 패턴
            (r'Unit\s*[:：]\s*KRW', 1),
            (r'Unit\s*[:：]\s*In\s+thousands', 1_000),
            (r'Unit\s*[:：]\s*In\s+millions', 1_000_000),
            # 괄호 형태
            (r'\(단위\s*[:：]?\s*원\)', 1),
            (r'\(단위\s*[:：]?\s*천원\)', 1_000),
            (r'\(단위\s*[:：]?\s*백만원\)', 1_000_000),
        ]

        for pattern, multiplier in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return multiplier

        # 기본값: 원 (v2.0에서 변경 - 기존 천원에서 원으로)
        return 1

    # =========================================================================
    # 금액 파싱 (v2.0 검증 로직)
    # =========================================================================

    def _parse_amount(self, value_str: str, unit_multiplier: int = 1) -> Optional[int]:
        """금액 문자열을 정수로 변환

        Args:
            value_str: '1,234,567' 또는 '(1,234,567)' 또는 '-1234567'
            unit_multiplier: 단위 배수

        Returns:
            정수 금액 또는 None
        """
        if not value_str:
            return None

        try:
            # 괄호 = 음수
            is_negative = value_str.startswith('(') or value_str.startswith('-')

            # 숫자만 추출
            cleaned = re.sub(r'[^\d.]', '', value_str)
            if not cleaned:
                return None

            # 소수점 처리
            if '.' in cleaned:
                amount = float(cleaned)
            else:
                amount = int(cleaned)

            # 단위 적용
            result = int(amount * unit_multiplier)

            return -result if is_negative else result

        except (ValueError, TypeError):
            return None

    # =========================================================================
    # XML 텍스트 정리
    # =========================================================================

    def _clean_xml_text(self, xml_content: str) -> str:
        """XML 태그 제거하고 텍스트만 추출"""
        # CDATA 내용 보존
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_content, flags=re.DOTALL)
        # 모든 태그 제거
        text = re.sub(r'<[^>]+>', ' ', text)
        # 연속 공백 정리
        text = re.sub(r'\s+', ' ', text)
        return text

    # =========================================================================
    # 재무제표 섹션 추출
    # =========================================================================

    def _extract_statement_section(self, xml_content: str, title_patterns: List[str]) -> Optional[str]:
        """재무제표 섹션 추출 (TITLE 패턴 기반)

        Args:
            xml_content: 전체 XML
            title_patterns: 섹션 TITLE 패턴 목록

        Returns:
            해당 섹션 내용 또는 None
        """
        for pattern in title_patterns:
            match = re.search(pattern, xml_content, re.IGNORECASE)
            if match:
                start_pos = match.end()

                # 다음 TITLE 또는 섹션 종료 찾기
                next_section = re.search(r'<TITLE[^>]*>', xml_content[start_pos:])
                if next_section:
                    end_pos = start_pos + next_section.start()
                else:
                    end_pos = len(xml_content)

                return xml_content[start_pos:end_pos]

        return None

    # =========================================================================
    # Meta 파일 처리
    # =========================================================================

    def load_meta(self, meta_path: Path) -> Optional[Dict[str, Any]]:
        """meta.json 파일 로드"""
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Meta load error: {meta_path}: {e}")
            return None

    def find_reports(
        self,
        report_type: str = '사업보고서',
        target_years: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """조건에 맞는 보고서 목록 검색

        Args:
            report_type: '사업보고서', '분기보고서', '반기보고서' 등
            target_years: [2023, 2024] 등 대상 연도

        Returns:
            [{'meta': dict, 'zip_path': Path, 'year': int}, ...]
        """
        reports = []

        for batch_dir in sorted(self.DART_DATA_DIR.glob('batch_*')):
            for corp_dir in batch_dir.iterdir():
                if not corp_dir.is_dir():
                    continue

                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir():
                        continue

                    try:
                        year = int(year_dir.name)
                        if target_years and year not in target_years:
                            continue
                    except ValueError:
                        continue

                    for meta_file in year_dir.glob('*_meta.json'):
                        meta = self.load_meta(meta_file)
                        if not meta:
                            continue

                        report_nm = meta.get('report_nm', '')
                        if report_type in report_nm:
                            zip_file = meta_file.with_name(
                                meta_file.name.replace('_meta.json', '.zip')
                            )
                            if zip_file.exists():
                                reports.append({
                                    'meta': meta,
                                    'zip_path': zip_file,
                                    'year': year,
                                    'corp_code': meta.get('corp_code'),
                                })

        logger.info(f"Found {len(reports)} {report_type} reports")
        return reports

    # =========================================================================
    # 추상 메서드 (하위 클래스에서 구현)
    # =========================================================================

    @abstractmethod
    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """단일 보고서 파싱 (하위 클래스에서 구현)"""
        pass

    @abstractmethod
    async def save_to_db(self, conn, data: Dict[str, Any]) -> bool:
        """파싱 결과 DB 저장 (하위 클래스에서 구현)"""
        pass

    def get_stats(self) -> Dict[str, int]:
        """파싱 통계 반환"""
        return self.stats.copy()
