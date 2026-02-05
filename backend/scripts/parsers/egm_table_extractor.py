"""
EGMTableExtractor - EGM 공시 HTML 테이블 기반 임원 정보 추출기

DART 공시 문서의 HTML 테이블 구조를 파싱하여 임원 정보를 정확하게 추출합니다.

지원하는 테이블 유형:
- 이사선임 세부내역: 성명, 출생년월, 임기, 신규선임여부, 주요경력
- 사외이사선임 세부내역: 성명, 출생년월, 임기, 신규선임여부, 주요경력, 타법인 재직
- 감사선임 세부내역: 성명, 출생년월, 주요경력

사용법:
    from scripts.parsers.egm_table_extractor import EGMTableExtractor

    extractor = EGMTableExtractor()
    officers = extractor.extract_from_html(html_content)
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EGMTableExtractor:
    """EGM 공시 테이블 기반 임원 정보 추출기"""

    # 테이블 탐지 마커 (우선순위 순)
    TABLE_MARKERS = {
        'director': [
            '이사선임 세부내역',
            '이사 선임 세부내역',
            '이사선임세부내역',
        ],
        'outside_director': [
            '사외이사선임 세부내역',
            '사외이사 선임 세부내역',
            '사외이사선임세부내역',
        ],
        'auditor': [
            '감사선임 세부내역',
            '감사 선임 세부내역',
            '감사선임세부내역',
        ],
    }

    # 컬럼 매핑 (정규화된 컬럼명 → 필드명)
    COLUMN_MAPPING = {
        '성명': 'name',
        '출생년월': 'birth_date',
        '임기': 'term_years',
        '신규선임여부': 'is_new',
        '신규선임 여부': 'is_new',
        '신규선임': 'is_new',
        '주요경력': 'career',
        '주요경력(현직포함)': 'career',
        '주요경력현직포함': 'career',
        '이사 등으로 재직 중인 다른 법인명(직위)': 'other_positions',
        '이사등으로 재직 중인 다른 법인명': 'other_positions',
        '다른법인재직': 'other_positions',
        '재직중인다른법인': 'other_positions',
    }

    # 제외할 이름 패턴 (액션 키워드 등)
    INVALID_NAMES = {
        '선임', '해임', '사임', '퇴임', '이사', '감사', '대표', '상무', '전무',
        '신규', '재선임', '중임', '성명', '출생년월', '임기', '-', '해당없음',
    }

    def __init__(self):
        self.stats = {
            'tables_found': 0,
            'officers_extracted': 0,
            'validation_failures': 0,
        }

    def extract_from_html(self, html_content: str) -> List[Dict]:
        """HTML에서 임원 정보 추출

        Args:
            html_content: HTML/XML 문서 내용

        Returns:
            추출된 임원 정보 리스트
            [
                {
                    'name': '박종오',
                    'birth_date': '1964-05',
                    'position': '사내이사',
                    'term_years': 3,
                    'is_new': True,
                    'career': '(현)㈜이엠앤아이 상무이사...',
                    'other_positions': None,
                    'table_type': 'director',
                    'extraction_confidence': 'HIGH',
                    'action': '선임',
                },
                ...
            ]
        """
        if not html_content:
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.error(f"HTML 파싱 실패: {e}")
            return []

        all_officers = []

        # 각 테이블 유형별 추출
        for table_type, markers in self.TABLE_MARKERS.items():
            officers = self._extract_table_by_marker(soup, markers, table_type)
            if officers:
                logger.debug(f"{table_type} 테이블에서 {len(officers)}명 추출")
            all_officers.extend(officers)

        # 중복 제거 (이름 + 출생년월 기준)
        unique_officers = self._deduplicate_officers(all_officers)

        self.stats['officers_extracted'] = len(unique_officers)
        logger.info(f"총 {len(unique_officers)}명 임원 추출 완료")

        return unique_officers

    def _extract_table_by_marker(
        self,
        soup: BeautifulSoup,
        markers: List[str],
        table_type: str
    ) -> List[Dict]:
        """마커 텍스트로 테이블 찾아서 추출"""
        officers = []

        for marker in markers:
            # 마커 텍스트를 포함하는 요소 찾기
            marker_elem = self._find_marker_element(soup, marker)

            if marker_elem:
                # 마커 이후 첫 번째 테이블 찾기
                table = marker_elem.find_next('table')
                if table:
                    self.stats['tables_found'] += 1
                    officers = self._parse_officer_table(table, table_type)
                    if officers:
                        logger.debug(f"'{marker}' 마커 테이블에서 {len(officers)}명 추출")
                        break

        return officers

    def _find_marker_element(self, soup: BeautifulSoup, marker: str) -> Optional[BeautifulSoup]:
        """마커 텍스트를 포함하는 요소 찾기"""
        # span, div, td, th 등에서 마커 텍스트 검색
        for tag_name in ['span', 'div', 'td', 'th', 'p', 'b', 'strong']:
            elements = soup.find_all(tag_name)
            for elem in elements:
                text = elem.get_text() or ''
                # 정규화된 텍스트로 비교
                normalized = self._normalize_text(text)
                marker_normalized = self._normalize_text(marker)
                if marker_normalized in normalized:
                    return elem
        return None

    def _parse_officer_table(
        self,
        table: BeautifulSoup,
        table_type: str
    ) -> List[Dict]:
        """테이블 파싱"""
        officers = []
        rows = table.find_all('tr')

        if len(rows) < 2:
            return officers

        # 헤더 행 파싱 (첫 번째 행)
        header_row = rows[0]
        headers = self._parse_header_row(header_row)

        if not headers or 'name' not in headers:
            # '성명' 컬럼이 없으면 다음 행도 헤더일 수 있음
            if len(rows) > 2:
                headers = self._parse_header_row(rows[1])
                rows = rows[1:]  # 헤더 행 조정

        if not headers or 'name' not in headers:
            logger.warning(f"테이블에서 '성명' 컬럼을 찾을 수 없음")
            return officers

        logger.debug(f"파싱된 헤더: {headers}")

        # 데이터 행 파싱 (첫 번째 행 이후)
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            officer_data = {'table_type': table_type}

            for i, cell in enumerate(cells):
                if i >= len(headers):
                    break

                field_name = headers[i]
                if not field_name:
                    continue

                cell_text = self._extract_cell_content(cell)
                officer_data[field_name] = cell_text

            # 유효성 검증 및 정제
            cleaned = self._validate_and_clean(officer_data, table_type)
            if cleaned:
                officers.append(cleaned)

        return officers

    def _parse_header_row(self, header_row) -> List[Optional[str]]:
        """헤더 행 파싱하여 필드명 리스트 반환"""
        headers = []
        for cell in header_row.find_all(['td', 'th']):
            header_text = self._clean_text(cell.get_text())
            field_name = self._map_column_to_field(header_text)
            headers.append(field_name)
        return headers

    def _map_column_to_field(self, header_text: str) -> Optional[str]:
        """컬럼 헤더를 필드명으로 매핑"""
        if not header_text:
            return None

        header_clean = self._normalize_text(header_text)

        for col_name, field_name in self.COLUMN_MAPPING.items():
            col_clean = self._normalize_text(col_name)
            if col_clean in header_clean or header_clean in col_clean:
                return field_name

        return None

    def _extract_cell_content(self, cell) -> str:
        """셀 내용 추출 (HTML 태그 처리)"""
        # <br> 태그를 줄바꿈으로 변환
        for br in cell.find_all('br'):
            br.replace_with('\n')

        # java 네임스페이스 br 태그도 처리
        for br in cell.find_all(lambda tag: 'br' in tag.name.lower() if tag.name else False):
            br.replace_with('\n')

        text = cell.get_text()

        # 정제
        text = text.strip()

        return text

    def _validate_and_clean(
        self,
        officer_data: Dict,
        table_type: str
    ) -> Optional[Dict]:
        """데이터 유효성 검증 및 정제"""
        name = officer_data.get('name', '').strip()

        # 이름 유효성 검사
        if not self._is_valid_name(name):
            self.stats['validation_failures'] += 1
            return None

        # 직책 결정
        position = self._determine_position(table_type, officer_data)

        # 출생년월 정규화
        birth_date = officer_data.get('birth_date', '')
        birth_date = self._normalize_birth_date(birth_date)

        # 신규선임 여부
        is_new_text = officer_data.get('is_new', '')
        is_new = self._parse_is_new(is_new_text)

        # 임기 파싱
        term_text = officer_data.get('term_years', '')
        term_years = self._parse_term_years(term_text)

        # 경력 정제
        career = officer_data.get('career', '')
        career = self._clean_career_text(career)

        # 타법인 재직 정보
        other_positions = officer_data.get('other_positions', '')
        if other_positions:
            other_positions = self._clean_text(other_positions)

        # 추출 신뢰도 계산
        confidence = self._calculate_confidence(
            name, birth_date, career, is_new, term_years
        )

        return {
            'name': name,
            'birth_date': birth_date,
            'position': position,
            'term_years': term_years,
            'is_new': is_new,
            'career': career,
            'other_positions': other_positions if other_positions else None,
            'table_type': table_type,
            'extraction_confidence': confidence,
            'action': '선임',  # 선임 세부내역 테이블에서 추출되면 선임
        }

    def _is_valid_name(self, name: str) -> bool:
        """이름 유효성 검사"""
        if not name:
            return False

        # 길이 검사 (2-5자)
        if len(name) < 2 or len(name) > 5:
            return False

        # 한글 이름인지 확인
        if not re.match(r'^[가-힣]{2,5}$', name):
            return False

        # 제외 목록 확인
        if name in self.INVALID_NAMES:
            return False

        return True

    def _determine_position(self, table_type: str, data: Dict) -> str:
        """직책 결정"""
        if table_type == 'outside_director':
            return '사외이사'
        elif table_type == 'auditor':
            return '감사'
        elif table_type == 'director':
            return '사내이사'
        else:
            return '이사'

    def _normalize_birth_date(self, birth_date: str) -> Optional[str]:
        """출생년월 정규화 (YYYY-MM 형식)"""
        if not birth_date:
            return None

        birth_date = birth_date.strip()

        # YYYY-MM 형식
        match = re.search(r'(\d{4})-(\d{1,2})', birth_date)
        if match:
            return f"{match.group(1)}-{match.group(2).zfill(2)}"

        # YYYY.MM 형식
        match = re.search(r'(\d{4})\.(\d{1,2})', birth_date)
        if match:
            return f"{match.group(1)}-{match.group(2).zfill(2)}"

        # YYYYMM 형식
        match = re.search(r'^(\d{4})(\d{2})$', birth_date.replace(' ', ''))
        if match:
            return f"{match.group(1)}-{match.group(2)}"

        return None

    def _parse_is_new(self, is_new_text: str) -> bool:
        """신규선임 여부 파싱"""
        if not is_new_text:
            return False

        is_new_text = is_new_text.strip().lower()

        # 신규 키워드 포함
        if '신규' in is_new_text:
            return True

        # 재선임/중임 키워드
        if '재선임' in is_new_text or '중임' in is_new_text:
            return False

        return False

    def _parse_term_years(self, term_text: str) -> Optional[int]:
        """임기 파싱 (년 단위)"""
        if not term_text:
            return None

        term_text = term_text.strip()

        match = re.search(r'(\d+)', term_text)
        if match:
            term = int(match.group(1))
            # 유효한 임기 범위 (1-10년)
            if 1 <= term <= 10:
                return term

        return None

    def _clean_career_text(self, career: str) -> str:
        """경력 텍스트 정제"""
        if not career:
            return ''

        # 기본 정제
        career = career.strip()

        # 연속 공백 정리
        career = re.sub(r'[ \t]+', ' ', career)

        # 연속 줄바꿈 정리
        career = re.sub(r'\n{3,}', '\n\n', career)

        # (현)/(전) 앞에 줄바꿈 추가 (이미 없는 경우)
        career = re.sub(r'([^\n])(\(현\))', r'\1\n\2', career)
        career = re.sub(r'([^\n])(\(전\))', r'\1\n\2', career)
        career = re.sub(r'([^\n])(현\))', r'\1\n\2', career)
        career = re.sub(r'([^\n])(전\))', r'\1\n\2', career)

        # 최대 길이 제한 (1000자)
        return career[:1000].strip()

    def _calculate_confidence(
        self,
        name: str,
        birth_date: Optional[str],
        career: str,
        is_new: bool,
        term_years: Optional[int]
    ) -> str:
        """추출 신뢰도 계산"""
        score = 0

        # 필수 필드
        if name:
            score += 40

        # 선택 필드
        if birth_date:
            score += 20
        if career and len(career) > 10:
            score += 25
        if term_years:
            score += 10
        # is_new는 True/False 모두 유효
        score += 5

        if score >= 80:
            return 'HIGH'
        elif score >= 50:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (비교용)"""
        if not text:
            return ''
        # 공백, 줄바꿈 제거
        return re.sub(r'\s+', '', text).strip()

    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ''
        # 연속 공백을 단일 공백으로
        return re.sub(r'\s+', ' ', text).strip()

    def _deduplicate_officers(self, officers: List[Dict]) -> List[Dict]:
        """중복 제거 (이름 + 출생년월 기준)"""
        seen = set()
        unique = []

        for officer in officers:
            # 키: 이름 + 출생년월 (출생년월 없으면 이름만)
            key = (officer.get('name'), officer.get('birth_date') or '')
            if key not in seen:
                seen.add(key)
                unique.append(officer)

        return unique

    def get_stats(self) -> Dict:
        """추출 통계 반환"""
        return self.stats.copy()

    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            'tables_found': 0,
            'officers_extracted': 0,
            'validation_failures': 0,
        }
