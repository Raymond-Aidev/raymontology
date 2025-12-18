"""
Named Entity Recognition (NER) Extractor

임원, 전환사채 등 개체명 추출 (정규표현식 + 패턴 매칭)
"""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NERExtractor:
    """
    개체명 추출기

    정규표현식 기반 (CPU 효율적, Railway 최적화)
    필요시 KoBERT 추가 가능
    """

    def __init__(self):
        """NER 추출기 초기화"""
        # 직책 패턴
        self.position_patterns = [
            r"대표이사",
            r"사내이사",
            r"사외이사",
            r"감사",
            r"감사위원",
            r"상무이사",
            r"전무이사",
            r"부사장",
            r"사장",
            r"회장",
            r"부회장",
            r"이사",
            r"CFO",
            r"CEO",
            r"COO",
            r"CTO",
        ]

        # 금액 패턴
        self.amount_patterns = [
            r"(\d{1,3}(?:,\d{3})*)\s*억\s*원",
            r"(\d{1,3}(?:,\d{3})*)\s*만\s*원",
            r"(\d{1,3}(?:,\d{3})*)\s*원",
        ]

    async def extract_officers(self, text: str) -> List[Dict]:
        """
        임원 정보 추출

        Args:
            text: 임원 현황 섹션 텍스트

        Returns:
            [
                {
                    "name": "홍길동",
                    "position": "대표이사",
                    "term_start": "2023-03-01",
                    "term_end": "2026-02-28",
                    "responsibilities": "경영 총괄"
                },
                ...
            ]
        """
        officers = []

        # 테이블 라인 파싱 (가장 일반적인 형식)
        table_officers = await self._extract_officers_from_table(text)
        officers.extend(table_officers)

        # 일반 텍스트에서 추출
        if not officers:
            text_officers = await self._extract_officers_from_text(text)
            officers.extend(text_officers)

        logger.info(f"Extracted {len(officers)} officers")
        return officers

    async def _extract_officers_from_table(self, text: str) -> List[Dict]:
        """
        테이블 형식에서 임원 추출

        테이블 형식:
        성명 | 직위 | 등기임원 여부 | 임기 | 담당업무
        홍길동 | 대표이사 | 등기 | 2023.03~2026.02 | 경영총괄
        """
        officers = []

        # 라인별 처리
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # 라인에 직책 키워드가 있는지 확인
            position = None
            for pos_pattern in self.position_patterns:
                if re.search(pos_pattern, line, re.IGNORECASE):
                    position = pos_pattern
                    break

            if not position:
                continue

            # 이름 추출 (한글 2-4자)
            name_match = re.search(r'([가-힣]{2,4})', line)
            if not name_match:
                continue

            name = name_match.group(1)

            # 이미 추출된 임원인지 확인 (중복 제거)
            if any(o['name'] == name and o['position'] == position for o in officers):
                continue

            # 임기 추출
            term_start, term_end = self._extract_term(line)

            # 담당업무 추출 (간단한 휴리스틱)
            responsibilities = self._extract_responsibilities(line)

            officer = {
                "name": name,
                "position": position,
                "term_start": term_start,
                "term_end": term_end,
                "responsibilities": responsibilities,
            }

            officers.append(officer)
            logger.debug(f"Extracted officer from table: {officer}")

        return officers

    async def _extract_officers_from_text(self, text: str) -> List[Dict]:
        """
        일반 텍스트에서 임원 추출

        형식: "홍길동 대표이사는 2023년 3월부터..."
        """
        officers = []

        # 패턴: [이름] [직책]
        for pos_pattern in self.position_patterns:
            pattern = re.compile(
                rf'([가-힣]{{2,4}})\s*({pos_pattern})',
                re.IGNORECASE
            )

            for match in pattern.finditer(text):
                name = match.group(1)
                position = match.group(2)

                # 중복 확인
                if any(o['name'] == name and o['position'] == position for o in officers):
                    continue

                # 문맥에서 임기 추출 (앞뒤 200자)
                context_start = max(0, match.start() - 200)
                context_end = min(len(text), match.end() + 200)
                context = text[context_start:context_end]

                term_start, term_end = self._extract_term(context)

                officer = {
                    "name": name,
                    "position": position,
                    "term_start": term_start,
                    "term_end": term_end,
                    "responsibilities": None,
                }

                officers.append(officer)

        return officers

    def _extract_term(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        임기 추출

        형식:
        - 2023.03 ~ 2026.02
        - 2023년 3월 ~ 2026년 2월
        - 2023-03-01 ~ 2026-02-28
        """
        # 패턴 1: YYYY.MM ~ YYYY.MM
        pattern1 = re.compile(r'(\d{4})\.(\d{1,2})\s*[~～\-]\s*(\d{4})\.(\d{1,2})')
        match1 = pattern1.search(text)
        if match1:
            start = f"{match1.group(1)}-{match1.group(2).zfill(2)}-01"
            # 종료일은 다음달 1일 - 1일
            end_year = int(match1.group(3))
            end_month = int(match1.group(4))
            # 간단히 마지막날로 처리
            end = f"{end_year}-{str(end_month).zfill(2)}-28"
            return start, end

        # 패턴 2: YYYY-MM-DD ~ YYYY-MM-DD
        pattern2 = re.compile(r'(\d{4})-(\d{2})-(\d{2})\s*[~～\-]\s*(\d{4})-(\d{2})-(\d{2})')
        match2 = pattern2.search(text)
        if match2:
            start = f"{match2.group(1)}-{match2.group(2)}-{match2.group(3)}"
            end = f"{match2.group(4)}-{match2.group(5)}-{match2.group(6)}"
            return start, end

        # 패턴 3: YYYY년 MM월
        pattern3 = re.compile(r'(\d{4})년\s*(\d{1,2})월')
        match3 = pattern3.search(text)
        if match3:
            start = f"{match3.group(1)}-{match3.group(2).zfill(2)}-01"
            return start, None

        return None, None

    def _extract_responsibilities(self, text: str) -> Optional[str]:
        """
        담당업무 추출

        간단한 키워드 매칭
        """
        responsibilities_keywords = [
            "경영총괄", "경영관리", "재무", "회계", "영업", "마케팅",
            "생산", "연구개발", "R&D", "인사", "법무", "전략",
        ]

        for keyword in responsibilities_keywords:
            if keyword in text:
                return keyword

        return None

    async def extract_convertible_bonds(self, text: str) -> List[Dict]:
        """
        전환사채(CB) 정보 추출

        Args:
            text: 전환사채 섹션 텍스트

        Returns:
            [
                {
                    "issue_date": "2023-01-01",
                    "maturity_date": "2025-01-01",
                    "amount": 10000000000,  # 원 단위
                    "conversion_price": 5000,
                    "holder": "투자조합1호",
                    "conversion_rate": 100.0
                },
                ...
            ]
        """
        cbs = []

        # 테이블 파싱 시도
        table_cbs = await self._extract_cb_from_table(text)
        cbs.extend(table_cbs)

        # 텍스트 파싱
        if not cbs:
            text_cbs = await self._extract_cb_from_text(text)
            cbs.extend(text_cbs)

        logger.info(f"Extracted {len(cbs)} convertible bonds")
        return cbs

    async def _extract_cb_from_table(self, text: str) -> List[Dict]:
        """
        테이블에서 CB 추출

        형식:
        발행일 | 만기일 | 발행금액 | 전환가격 | 보유자
        """
        cbs = []
        lines = text.split('\n')

        for line in lines:
            # 금액 패턴이 있는 라인만 처리
            if not re.search(r'\d{1,3}(?:,\d{3})*\s*억', line):
                continue

            # 발행일 추출
            issue_date = self._extract_date(line)

            # 금액 추출
            amount = self._extract_amount(line)

            # 전환가격 추출
            conversion_price = self._extract_conversion_price(line)

            # 보유자 추출
            holder = self._extract_holder(line)

            if amount:
                cb = {
                    "issue_date": issue_date,
                    "maturity_date": None,  # 별도 파싱 필요
                    "amount": amount,
                    "conversion_price": conversion_price,
                    "holder": holder,
                    "conversion_rate": 100.0,  # 기본값
                }
                cbs.append(cb)

        return cbs

    async def _extract_cb_from_text(self, text: str) -> List[Dict]:
        """
        일반 텍스트에서 CB 추출
        """
        cbs = []

        # "XX억원 규모의 전환사채" 패턴
        pattern = re.compile(
            r'(\d{1,3}(?:,\d{3})*)\s*억\s*원.*?전환사채',
            re.IGNORECASE
        )

        for match in pattern.finditer(text):
            amount_str = match.group(1).replace(',', '')
            amount = int(amount_str) * 100000000  # 억원 → 원

            # 문맥에서 날짜 추출
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            context = text[context_start:context_end]

            issue_date = self._extract_date(context)

            cb = {
                "issue_date": issue_date,
                "maturity_date": None,
                "amount": amount,
                "conversion_price": None,
                "holder": None,
                "conversion_rate": 100.0,
            }
            cbs.append(cb)

        return cbs

    def _extract_date(self, text: str) -> Optional[str]:
        """
        날짜 추출 (YYYY-MM-DD 형식으로 반환)
        """
        # YYYY.MM.DD
        pattern1 = re.compile(r'(\d{4})\.(\d{1,2})\.(\d{1,2})')
        match1 = pattern1.search(text)
        if match1:
            return f"{match1.group(1)}-{match1.group(2).zfill(2)}-{match1.group(3).zfill(2)}"

        # YYYY-MM-DD
        pattern2 = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
        match2 = pattern2.search(text)
        if match2:
            return match2.group(0)

        # YYYY년 MM월 DD일
        pattern3 = re.compile(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일')
        match3 = pattern3.search(text)
        if match3:
            return f"{match3.group(1)}-{match3.group(2).zfill(2)}-{match3.group(3).zfill(2)}"

        return None

    def _extract_amount(self, text: str) -> Optional[int]:
        """
        금액 추출 (원 단위로 반환)
        """
        # XX억원
        pattern1 = re.compile(r'(\d{1,3}(?:,\d{3})*)\s*억\s*원')
        match1 = pattern1.search(text)
        if match1:
            amount_str = match1.group(1).replace(',', '')
            return int(amount_str) * 100000000

        # XX만원
        pattern2 = re.compile(r'(\d{1,3}(?:,\d{3})*)\s*만\s*원')
        match2 = pattern2.search(text)
        if match2:
            amount_str = match2.group(1).replace(',', '')
            return int(amount_str) * 10000

        # XX원
        pattern3 = re.compile(r'(\d{1,3}(?:,\d{3})*)\s*원')
        match3 = pattern3.search(text)
        if match3:
            amount_str = match3.group(1).replace(',', '')
            return int(amount_str)

        return None

    def _extract_conversion_price(self, text: str) -> Optional[int]:
        """
        전환가격 추출
        """
        # 전환가격: XX원
        pattern = re.compile(r'전환가[격가]?\s*:?\s*(\d{1,3}(?:,\d{3})*)\s*원')
        match = pattern.search(text)
        if match:
            price_str = match.group(1).replace(',', '')
            return int(price_str)

        return None

    def _extract_holder(self, text: str) -> Optional[str]:
        """
        보유자 추출 (간단한 패턴)
        """
        # "보유자: XXX" 또는 "XXX 투자조합"
        holder_patterns = [
            r'보유자\s*:?\s*([가-힣\w\s]{2,20})',
            r'([가-힣\w]{2,20}투자조합)',
            r'([가-힣\w]{2,20}펀드)',
        ]

        for pattern_str in holder_patterns:
            pattern = re.compile(pattern_str)
            match = pattern.search(text)
            if match:
                return match.group(1).strip()

        return None

    async def extract_related_parties(self, text: str) -> List[Dict]:
        """
        특수관계자 추출

        Args:
            text: 특수관계자 섹션 텍스트

        Returns:
            [{"name": "...", "relationship": "...", "transaction_amount": ...}, ...]
        """
        parties = []

        # 간단한 패턴 매칭
        lines = text.split('\n')

        for line in lines:
            # 금액이 있는 라인만 처리
            amount = self._extract_amount(line)
            if not amount:
                continue

            # 관계 키워드
            relationship = None
            if "계열사" in line:
                relationship = "계열사"
            elif "특수관계인" in line:
                relationship = "특수관계인"
            elif "관계회사" in line:
                relationship = "관계회사"

            # 회사명/개인명 추출 (휴리스틱)
            name_match = re.search(r'([가-힣]{2,20}(?:주식회사|유한회사)?)', line)
            name = name_match.group(1) if name_match else None

            if name and relationship:
                party = {
                    "name": name,
                    "relationship": relationship,
                    "transaction_amount": amount,
                }
                parties.append(party)

        logger.info(f"Extracted {len(parties)} related parties")
        return parties
