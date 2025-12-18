"""
Section Parser

사업보고서 섹션 분할 및 추출
"""
import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SectionParser:
    """
    사업보고서 섹션 파서

    정규표현식으로 주요 섹션 추출
    """

    # 섹션 패턴 정의 (로마자 + 한글)
    SECTION_PATTERNS = {
        # I. 회사의 개요
        "company_overview": [
            r"I+\.\s*회사의\s*개요",
            r"1\.\s*회사의\s*개요",
            r"【\s*회사의\s*개요\s*】",
        ],

        # II. 사업의 내용
        "business_description": [
            r"II+\.\s*사업의\s*내용",
            r"2\.\s*사업의\s*내용",
            r"【\s*사업의\s*내용\s*】",
        ],

        # III. 재무에 관한 사항
        "financial_info": [
            r"III+\.\s*재무에\s*관한\s*사항",
            r"3\.\s*재무에\s*관한\s*사항",
            r"【\s*재무에\s*관한\s*사항\s*】",
        ],

        # IV. 이사회 등 회사의 기관에 관한 사항
        "board_info": [
            r"IV+\.\s*이사회\s*등",
            r"4\.\s*이사회\s*등",
            r"【\s*이사회.*?】",
        ],

        # V. 임원 및 직원 등에 관한 사항
        "officers_info": [
            r"V+\.\s*임원\s*및\s*직원",
            r"5\.\s*임원\s*및\s*직원",
            r"【\s*임원.*?】",
        ],

        # 전환사채 관련
        "convertible_bonds": [
            r"전환사채\s*발행\s*현황",
            r"전환사채.*?내역",
            r"CB\s*발행",
        ],

        # 신주인수권부사채
        "bw_bonds": [
            r"신주인수권부사채\s*발행\s*현황",
            r"BW\s*발행",
        ],

        # 특수관계자 거래
        "related_party_transactions": [
            r"특수관계자\s*거래",
            r"특수관계인.*?거래",
            r"관계회사.*?거래",
        ],

        # 주주 현황
        "shareholders": [
            r"주주\s*현황",
            r"주식.*?소유\s*현황",
            r"최대주주.*?현황",
        ],

        # 배당 정책
        "dividend_policy": [
            r"배당\s*정책",
            r"배당.*?현황",
            r"이익배당",
        ],
    }

    def __init__(self):
        """섹션 파서 초기화"""
        # 패턴 컴파일
        self.compiled_patterns = {}
        for section_name, patterns in self.SECTION_PATTERNS.items():
            self.compiled_patterns[section_name] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]

    async def parse_sections(self, text: str) -> Dict[str, str]:
        """
        텍스트에서 섹션 추출

        Args:
            text: 전체 텍스트

        Returns:
            {
                "company_overview": "회사 개요 내용...",
                "officers_info": "임원 정보...",
                ...
            }
        """
        sections = {}

        for section_name, patterns in self.compiled_patterns.items():
            section_text = await self._extract_section(text, patterns, section_name)
            if section_text:
                sections[section_name] = section_text
                logger.info(f"Extracted section '{section_name}': {len(section_text)} chars")

        return sections

    async def _extract_section(
        self,
        text: str,
        patterns: List[re.Pattern],
        section_name: str
    ) -> Optional[str]:
        """
        특정 섹션 추출

        Args:
            text: 전체 텍스트
            patterns: 섹션 패턴 리스트
            section_name: 섹션 이름

        Returns:
            추출된 섹션 텍스트
        """
        # 모든 패턴 시도
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                start_pos = match.start()

                # 다음 섹션 찾기 (모든 섹션 패턴 검색)
                end_pos = len(text)
                for other_patterns in self.compiled_patterns.values():
                    for other_pattern in other_patterns:
                        # 현재 위치 이후에서 다음 섹션 찾기
                        next_match = other_pattern.search(text, start_pos + len(match.group()))
                        if next_match and next_match.start() < end_pos:
                            end_pos = next_match.start()

                # 섹션 텍스트 추출
                section_text = text[start_pos:end_pos].strip()

                # 최소 길이 확인
                if len(section_text) >= 50:
                    return section_text

        return None

    async def extract_officer_section(self, text: str) -> Optional[str]:
        """
        임원 현황 섹션 추출 (특화)

        Args:
            text: 전체 텍스트

        Returns:
            임원 현황 섹션
        """
        # 임원 현황 패턴 (더 구체적)
        officer_patterns = [
            r"임원\s*현황",
            r"임원.*?명부",
            r"등기임원.*?현황",
            r"미등기임원.*?현황",
        ]

        for pattern_str in officer_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)

            if match:
                # 섹션 시작 위치
                start_pos = match.start()

                # 끝 위치 찾기 (다음 섹션 또는 페이지 끝)
                end_patterns = [
                    r"직원\s*현황",
                    r"주주\s*현황",
                    r"VI+\.",
                    r"6\.",
                ]

                end_pos = len(text)
                for end_pattern_str in end_patterns:
                    end_pattern = re.compile(end_pattern_str, re.IGNORECASE)
                    end_match = end_pattern.search(text, start_pos + 100)
                    if end_match and end_match.start() < end_pos:
                        end_pos = end_match.start()

                section = text[start_pos:end_pos].strip()
                if len(section) >= 100:
                    return section

        return None

    async def extract_cb_section(self, text: str) -> Optional[str]:
        """
        전환사채 섹션 추출 (특화)

        Args:
            text: 전체 텍스트

        Returns:
            전환사채 섹션
        """
        # 전환사채 패턴
        cb_patterns = [
            r"전환사채\s*발행\s*현황",
            r"전환사채.*?내역",
            r"CB\s*발행.*?현황",
            r"전환권\s*행사",
        ]

        for pattern_str in cb_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)

            if match:
                # 앞뒤 500자씩 추출 (테이블 포함 가능성)
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(text), match.end() + 1000)

                section = text[start_pos:end_pos].strip()
                return section

        return None

    async def extract_related_party_section(self, text: str) -> Optional[str]:
        """
        특수관계자 거래 섹션 추출

        Args:
            text: 전체 텍스트

        Returns:
            특수관계자 거래 섹션
        """
        patterns = [
            r"특수관계자\s*거래",
            r"특수관계인.*?거래",
            r"관계회사.*?거래",
        ]

        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)

            if match:
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(text), match.end() + 2000)

                section = text[start_pos:end_pos].strip()
                return section

        return None

    async def extract_shareholder_section(self, text: str) -> Optional[str]:
        """
        주주 현황 섹션 추출

        Args:
            text: 전체 텍스트

        Returns:
            주주 현황 섹션
        """
        patterns = [
            r"주주\s*현황",
            r"주식.*?소유\s*현황",
            r"최대주주.*?현황",
            r"주요주주",
        ]

        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)

            if match:
                start_pos = match.start()

                # 다음 섹션까지 (최대 3000자)
                end_pos = min(len(text), match.end() + 3000)

                # 다음 대분류 섹션 찾기
                next_section_patterns = [
                    r"임원.*?현황",
                    r"직원.*?현황",
                    r"배당.*?정책",
                ]

                for next_pattern_str in next_section_patterns:
                    next_pattern = re.compile(next_pattern_str, re.IGNORECASE)
                    next_match = next_pattern.search(text, start_pos + 100)
                    if next_match and next_match.start() < end_pos:
                        end_pos = next_match.start()

                section = text[start_pos:end_pos].strip()
                if len(section) >= 100:
                    return section

        return None

    def find_table_blocks(self, text: str) -> List[Tuple[int, int]]:
        """
        테이블 블록 위치 찾기

        Args:
            text: 텍스트

        Returns:
            [(시작위치, 끝위치), ...]
        """
        # 테이블 패턴: 연속된 "|" 또는 "─" 라인
        table_pattern = re.compile(r"([│├─┼]+.*?\n)+", re.MULTILINE)

        blocks = []
        for match in table_pattern.finditer(text):
            blocks.append((match.start(), match.end()))

        return blocks

    def extract_text_between_headers(
        self,
        text: str,
        start_header: str,
        end_header: Optional[str] = None
    ) -> Optional[str]:
        """
        두 헤더 사이의 텍스트 추출

        Args:
            text: 전체 텍스트
            start_header: 시작 헤더 (정규표현식)
            end_header: 끝 헤더 (정규표현식, None이면 끝까지)

        Returns:
            추출된 텍스트
        """
        start_pattern = re.compile(start_header, re.IGNORECASE)
        start_match = start_pattern.search(text)

        if not start_match:
            return None

        start_pos = start_match.end()

        # 끝 위치
        if end_header:
            end_pattern = re.compile(end_header, re.IGNORECASE)
            end_match = end_pattern.search(text, start_pos)
            end_pos = end_match.start() if end_match else len(text)
        else:
            end_pos = len(text)

        extracted = text[start_pos:end_pos].strip()
        return extracted if len(extracted) >= 10 else None
