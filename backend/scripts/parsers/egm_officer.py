"""
EGMOfficerParser - 임시주주총회 공시 임원 파서

임시주주총회 공시에서 다음 정보를 추출:
1. 경영분쟁 여부 판정 (키워드 기반)
2. 안건 목록 파싱
3. 임원 선임/해임 정보 추출 (테이블 기반 + 정규식 폴백)
4. 선임 임원의 경력 정보 추출

v2.0 (2026-02-04): HTML 테이블 기반 추출 추가
- BeautifulSoup으로 이사선임/사외이사선임 세부내역 테이블 파싱
- 임원명, 출생년월, 임기, 경력 정보 정확하게 추출
- 기존 정규식 방식은 폴백으로 유지

사용법:
    from scripts.parsers.egm_officer import EGMOfficerParser

    parser = EGMOfficerParser()
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            result = await parser.parse_and_save(conn, zip_path, meta)
"""

import asyncpg
import json
import logging
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .base import BaseParser
from .egm_table_extractor import EGMTableExtractor

logger = logging.getLogger(__name__)


# =============================================================================
# 경영분쟁 분류 키워드
# =============================================================================

DISPUTE_STRONG_KEYWORDS = [
    '경영권 분쟁', '경영권분쟁', '적대적', '경영권 확보',
    '주주제안', '주주 제안', '소수주주', '반대주주',
    '해임 청구', '해임청구', '직무집행정지',
    '가처분', '소송', '소집허가', '위임장',
]

DISPUTE_MEDIUM_KEYWORDS = [
    '해임', '퇴임', '교체', '사임',
    '대표이사 변경', '이사회 구성',
    '지배구조', '경영진 교체',
    '긴급', '특별', '임시',
]

DISPUTE_WEAK_KEYWORDS = [
    '이사 선임', '감사 선임',
    '사외이사', '감사위원',
]


# =============================================================================
# DisputeClassifier - 경영분쟁 분류기
# =============================================================================

class DisputeClassifier:
    """경영분쟁 분류기"""

    def __init__(self):
        self.strong_keywords = DISPUTE_STRONG_KEYWORDS
        self.medium_keywords = DISPUTE_MEDIUM_KEYWORDS
        self.weak_keywords = DISPUTE_WEAK_KEYWORDS

    def classify(self, text: str) -> Tuple[bool, float, Optional[str], List[str]]:
        """경영분쟁 여부 판정

        Args:
            text: 공시 본문 텍스트

        Returns:
            (is_dispute, confidence, dispute_type, detected_keywords)
        """
        if not text:
            return False, 0.0, None, []

        score = 0.0
        detected_keywords = []

        # 강력 지표 (3.0점)
        for kw in self.strong_keywords:
            if kw in text:
                score += 3.0
                detected_keywords.append(kw)

        # 중간 지표 (2.0점)
        for kw in self.medium_keywords:
            if kw in text:
                score += 2.0
                detected_keywords.append(kw)

        # 약한 지표 (1.0점)
        for kw in self.weak_keywords:
            if kw in text:
                score += 1.0
                detected_keywords.append(kw)

        # 해임 + 선임 조합 시 추가 가중치
        if '해임' in text and '선임' in text:
            score += 2.0

        # 반대 의결 패턴
        if re.search(r'반대\s*\d+', text) or re.search(r'부결', text):
            score += 1.5

        # 정규화 (최대 15점 기준)
        confidence = min(score / 15.0, 1.0)
        is_dispute = confidence >= 0.2  # 임계값 20%

        # 분쟁 유형 분류
        dispute_type = None
        if is_dispute:
            if any(kw in text for kw in ['적대적', '경영권 확보', '경영권 분쟁']):
                dispute_type = 'HOSTILE_TAKEOVER'
            elif any(kw in text for kw in ['주주제안', '소수주주', '위임장']):
                dispute_type = 'SHAREHOLDER_ACTIVISM'
            elif any(kw in text for kw in ['가처분', '소송', '소집허가']):
                dispute_type = 'PROXY_FIGHT'
            else:
                dispute_type = 'MANAGEMENT_CONFLICT'

        # 중복 제거
        detected_keywords = list(set(detected_keywords))

        return is_dispute, round(confidence, 2), dispute_type, detected_keywords


# =============================================================================
# OfficerExtractor - 임원 정보 추출기 (v2.0: 테이블 기반 + 정규식 폴백)
# =============================================================================

class OfficerExtractor:
    """임원 정보 추출기

    v2.0 변경사항:
    - HTML 테이블 기반 추출을 우선 시도
    - 테이블에서 추출 실패 시 정규식 폴백
    - 이름 유효성 검증 강화 (액션 키워드 필터링)
    """

    # 제외할 이름 (액션 키워드 등)
    INVALID_NAMES = {
        '선임', '해임', '사임', '퇴임', '이사', '감사', '대표', '상무', '전무',
        '신규', '재선임', '중임', '성명', '출생년월', '임기', '-', '해당없음',
    }

    def __init__(self):
        self.table_extractor = EGMTableExtractor()

    # 안건 패턴
    AGENDA_PATTERNS = [
        # 제N호 의안: 이사 OOO 선임의 건
        r'제\s*(\d+)\s*호\s*의안\s*[:：]?\s*(.+?)(?=제\s*\d+\s*호|$)',
        # N. 안건명
        r'(\d+)\s*[\.:\s]\s*(.+?)(의\s*건|안\s*건)(?=\d+\s*\.|$|\n\n)',
        # 【제N호 의안】
        r'【\s*제\s*(\d+)\s*호\s*의안\s*】\s*(.+?)(?=【|$)',
    ]

    # 임원 선임/해임 패턴
    OFFICER_PATTERNS = [
        # 이사 OOO 선임
        r'(사외이사|사내이사|이사|감사|감사위원|대표이사)\s+([가-힣]{2,5})\s*(선임|해임|사임|중도퇴임)',
        # OOO 이사 선임
        r'([가-힣]{2,5})\s+(사외이사|사내이사|이사|감사|감사위원|대표이사)\s*(선임|해임|사임|중도퇴임)',
        # 후보자: OOO
        r'후보자\s*[:：]\s*([가-힣]{2,5})',
        # 성명: OOO
        r'성\s*명\s*[:：]\s*([가-힣]{2,5})',
    ]

    # 경력 추출 패턴
    CAREER_PATTERNS = [
        # 주요경력: ...
        r'주요\s*경력\s*[:：]?\s*(.+?)(?=학\s*력|출생|생년|$)',
        # 경력사항: ...
        r'경력\s*사항\s*[:：]?\s*(.+?)(?=학\s*력|출생|생년|$)',
        # 약력: ...
        r'약\s*력\s*[:：]?\s*(.+?)(?=학\s*력|출생|생년|$)',
    ]

    # 투표 결과 패턴
    VOTE_PATTERNS = [
        # 찬성 85.3%, 반대 14.7%
        r'찬성\s*[:：]?\s*([\d\.]+)\s*%.*?반대\s*[:：]?\s*([\d\.]+)\s*%',
        # 가결 (85.3%)
        r'(가결|부결)\s*[\(（]?\s*([\d\.]+)\s*%?\s*[\)）]?',
        # 찬성 1,234,567주
        r'찬성\s*[:：]?\s*([\d,]+)\s*주',
    ]

    def extract_agenda_items(self, text: str) -> List[Dict]:
        """안건 목록 추출"""
        agenda_items = []

        for pattern in self.AGENDA_PATTERNS:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            for match in matches:
                if len(match) >= 2:
                    number = match[0]
                    title = match[1].strip()

                    # 임원 관련 안건 필터링
                    if self._is_officer_related(title):
                        result = self._extract_vote_result(text, title)
                        agenda_items.append({
                            'number': number,
                            'title': title[:200],  # 최대 200자
                            'result': result.get('result'),
                            'vote_for': result.get('vote_for'),
                            'vote_against': result.get('vote_against'),
                        })

        return agenda_items

    def extract_officer_changes(self, xml_content: str, text: str) -> List[Dict]:
        """임원 선임/해임 정보 추출 (테이블 기반 + 정규식 폴백)

        Args:
            xml_content: 원본 XML/HTML 내용 (테이블 파싱용)
            text: 정제된 텍스트 (정규식 폴백용)

        Returns:
            추출된 임원 정보 리스트
        """
        officers = []

        # Phase 1: HTML 테이블 기반 추출 (우선)
        try:
            table_officers = self.table_extractor.extract_from_html(xml_content)
            if table_officers:
                logger.info(f"테이블에서 {len(table_officers)}명 임원 추출")
                officers.extend(table_officers)
        except Exception as e:
            logger.warning(f"테이블 추출 실패, 정규식 폴백 사용: {e}")

        # Phase 2: 정규식 폴백 (테이블에서 추출 못한 경우)
        if len(officers) == 0:
            logger.debug("테이블 추출 결과 없음, 정규식 폴백 사용")
            regex_officers = self._extract_by_regex(text)
            officers.extend(regex_officers)

        # 중복 제거 및 검증
        unique_officers = self._deduplicate_and_validate(officers)

        return unique_officers

    def _extract_by_regex(self, text: str) -> List[Dict]:
        """정규식 기반 추출 (폴백)"""
        officers = []

        for pattern in self.OFFICER_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                officer = self._parse_officer_match(match)
                if officer:
                    # 경력 추출 시도
                    career = self._extract_career(text, officer['name'])
                    officer['career'] = career

                    # 투표 결과 추출
                    vote = self._extract_vote_result(text, officer['name'])
                    officer['vote_result'] = vote.get('result')
                    officer['vote_for'] = vote.get('vote_for')
                    officer['vote_against'] = vote.get('vote_against')

                    # 폴백 표시
                    officer['extraction_confidence'] = 'LOW'
                    officer['table_type'] = None

                    officers.append(officer)

        return officers

    def _deduplicate_and_validate(self, officers: List[Dict]) -> List[Dict]:
        """중복 제거 및 검증"""
        seen = set()
        validated = []

        for officer in officers:
            name = officer.get('name', '')

            # 이름 유효성 검사
            if not name or len(name) < 2:
                continue
            if name in self.INVALID_NAMES:
                logger.debug(f"유효하지 않은 이름 제외: {name}")
                continue

            # 중복 키: 이름 + 출생년월
            key = (name, officer.get('birth_date') or '')
            if key not in seen:
                seen.add(key)
                validated.append(officer)

        return validated

    def _is_officer_related(self, title: str) -> bool:
        """임원 관련 안건인지 확인"""
        officer_keywords = ['이사', '감사', '선임', '해임', '사임', '퇴임', '임원']
        return any(kw in title for kw in officer_keywords)

    def _parse_officer_match(self, match: tuple) -> Optional[Dict]:
        """매칭된 임원 정보 파싱"""
        if len(match) < 2:
            return None

        # 패턴에 따라 위치가 다름
        name = None
        position = None
        action = None

        for item in match:
            if not item:
                continue
            item = item.strip()

            # 이름 (2-5자 한글)
            if re.match(r'^[가-힣]{2,5}$', item):
                name = item
            # 직책
            elif item in ['사외이사', '사내이사', '이사', '감사', '감사위원', '대표이사']:
                position = item
            # 액션
            elif item in ['선임', '해임', '사임', '중도퇴임']:
                action = item

        if not name:
            return None

        return {
            'name': name,
            'position': position,
            'action': action or '선임',
        }

    def _extract_career(self, text: str, officer_name: str) -> Optional[str]:
        """임원 경력 추출"""
        # 이름 주변 텍스트에서 경력 찾기
        name_pos = text.find(officer_name)
        if name_pos == -1:
            return None

        # 이름 이후 500자 내에서 경력 패턴 검색
        search_text = text[name_pos:name_pos + 500]

        for pattern in self.CAREER_PATTERNS:
            match = re.search(pattern, search_text, re.DOTALL)
            if match:
                career = match.group(1).strip()
                # 정제
                career = re.sub(r'\s+', ' ', career)
                career = career[:500]  # 최대 500자
                return career

        return None

    def _extract_vote_result(self, text: str, context: str) -> Dict:
        """투표 결과 추출"""
        result = {
            'result': None,
            'vote_for': None,
            'vote_against': None,
        }

        # 컨텍스트 주변에서 검색
        context_pos = text.find(context)
        if context_pos != -1:
            search_text = text[context_pos:context_pos + 300]
        else:
            search_text = text

        for pattern in self.VOTE_PATTERNS:
            match = re.search(pattern, search_text)
            if match:
                groups = match.groups()
                if '가결' in groups[0] if groups else False:
                    result['result'] = '가결'
                elif '부결' in groups[0] if groups else False:
                    result['result'] = '부결'

                if len(groups) >= 2:
                    try:
                        result['vote_for'] = f"{groups[1]}%"
                    except:
                        pass

        return result


# =============================================================================
# EGMOfficerParser - 메인 파서
# =============================================================================

class EGMOfficerParser(BaseParser):
    """임시주주총회 공시 임원 파서"""

    def __init__(self, database_url: Optional[str] = None):
        super().__init__(database_url)
        self.dispute_classifier = DisputeClassifier()
        self.officer_extractor = OfficerExtractor()
        self.company_cache = {}  # corp_code -> company_id

    async def load_companies(self, conn: asyncpg.Connection):
        """회사 정보 로드"""
        rows = await conn.fetch(
            "SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL"
        )
        self.company_cache = {r['corp_code']: str(r['id']) for r in rows}
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개")

    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """공시 본문 파싱

        Args:
            zip_path: ZIP 파일 경로
            meta: 메타데이터 (disclosure_id, corp_code 등)

        Returns:
            파싱 결과 딕셔너리
        """
        result = {
            'success': False,
            'is_dispute': False,
            'dispute_confidence': 0.0,
            'dispute_type': None,
            'dispute_keywords': [],
            'agenda_items': [],
            'officer_changes': [],
            'officers_appointed': 0,
            'officers_dismissed': 0,
            'parse_errors': [],
            'raw_content_sample': None,
        }

        try:
            # XML 추출
            xml_content = self.extract_xml_from_zip(zip_path)
            if not xml_content:
                result['parse_errors'].append('XML extraction failed')
                return result

            # 텍스트 추출
            text = self._clean_xml_text(xml_content)

            # 원문 샘플 저장 (처음 2000자)
            result['raw_content_sample'] = text[:2000] if text else None

            # 경영분쟁 분류
            is_dispute, confidence, dispute_type, keywords = self.dispute_classifier.classify(text)
            result['is_dispute'] = is_dispute
            result['dispute_confidence'] = confidence
            result['dispute_type'] = dispute_type
            result['dispute_keywords'] = keywords

            # 안건 파싱
            result['agenda_items'] = self.officer_extractor.extract_agenda_items(text)

            # 임원 변동 추출 (v2.0: XML 원본도 전달하여 테이블 파싱)
            officer_changes = self.officer_extractor.extract_officer_changes(xml_content, text)
            result['officer_changes'] = officer_changes

            # 선임/해임 수 집계
            result['officers_appointed'] = sum(1 for o in officer_changes if o.get('action') == '선임')
            result['officers_dismissed'] = sum(1 for o in officer_changes if o.get('action') in ['해임', '사임', '중도퇴임'])

            result['success'] = True
            result['meta'] = meta

        except Exception as e:
            result['parse_errors'].append(str(e))
            logger.error(f"파싱 오류: {e}")

        return result

    async def save_to_db(self, conn: asyncpg.Connection, data: Dict[str, Any]) -> bool:
        """파싱 결과 DB 저장

        1. egm_disclosures 테이블 업데이트
        2. dispute_officers 테이블에 신규 임원 삽입

        Args:
            conn: DB 연결
            data: 파싱 결과

        Returns:
            성공 여부
        """
        if not data.get('success'):
            return False

        meta = data.get('meta', {})
        disclosure_id = meta.get('disclosure_id')

        if not disclosure_id:
            logger.error("disclosure_id 없음")
            return False

        try:
            # 1. egm_disclosures 업데이트
            egm_date = None
            # 안건에서 날짜 추출 시도 (추후 구현)

            await conn.execute("""
                UPDATE egm_disclosures SET
                    is_dispute_related = $2,
                    dispute_confidence = $3,
                    dispute_type = $4,
                    dispute_keywords = $5,
                    agenda_items = $6,
                    officer_changes = $7,
                    officers_appointed = $8,
                    officers_dismissed = $9,
                    raw_content = $10,
                    parse_status = $11,
                    parse_confidence = $12,
                    parse_errors = $13,
                    needs_manual_review = $14,
                    updated_at = NOW()
                WHERE disclosure_id = $1
            """,
                disclosure_id,
                data['is_dispute'],
                Decimal(str(data['dispute_confidence'])),
                data['dispute_type'],
                json.dumps(data['dispute_keywords'], ensure_ascii=False),
                json.dumps(data['agenda_items'], ensure_ascii=False),
                json.dumps(data['officer_changes'], ensure_ascii=False),
                data['officers_appointed'],
                data['officers_dismissed'],
                data.get('raw_content_sample'),
                'PARSED',
                Decimal(str(data['dispute_confidence'])),
                json.dumps(data['parse_errors'], ensure_ascii=False),
                data['is_dispute'] and data['dispute_confidence'] < 0.5,  # 신뢰도 낮으면 수동 검토
            )

            # 2. dispute_officers 저장 (분쟁 관련 + 선임된 임원만)
            if data['is_dispute'] and data['officer_changes']:
                # egm_disclosures.id 조회
                egm_record = await conn.fetchrow(
                    "SELECT id, company_id FROM egm_disclosures WHERE disclosure_id = $1",
                    disclosure_id
                )

                if egm_record:
                    for officer in data['officer_changes']:
                        if officer.get('action') == '선임':
                            await self._save_dispute_officer(
                                conn, egm_record, officer, data['is_dispute']
                            )

            self.stats['records_created'] += 1
            return True

        except Exception as e:
            logger.error(f"DB 저장 실패 {disclosure_id}: {e}")
            self.stats['errors'] += 1
            return False

    async def _save_dispute_officer(
        self,
        conn: asyncpg.Connection,
        egm_record: asyncpg.Record,
        officer: Dict,
        is_dispute: bool
    ):
        """분쟁 임원 저장 (v2.0: birth_date 추가)"""
        try:
            # 선임 맥락 결정
            context = 'DISPUTE_NEW' if is_dispute else 'REGULAR'
            if officer.get('replaced_officer'):
                context = 'DISPUTE_REPLACEMENT'

            # 추출 신뢰도 (테이블 추출 시 제공됨)
            confidence = officer.get('extraction_confidence', 'MEDIUM')

            await conn.execute("""
                INSERT INTO dispute_officers (
                    id, officer_name, birth_date, position, company_id, egm_disclosure_id,
                    career_from_disclosure, appointment_context,
                    vote_result, vote_for_ratio, vote_against_ratio,
                    extraction_confidence, extraction_source, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """,
                uuid.uuid4(),
                officer['name'],
                officer.get('birth_date'),  # v2.0: 출생년월 추가
                officer.get('position'),
                egm_record['company_id'],
                egm_record['id'],
                officer.get('career'),
                context,
                officer.get('vote_result'),
                officer.get('vote_for'),
                officer.get('vote_against'),
                confidence,
                officer.get('table_type', 'regex'),  # 추출 소스
            )
            logger.debug(f"임원 저장: {officer['name']} ({officer.get('position')}) - {confidence}")
        except Exception as e:
            logger.error(f"임원 저장 실패 {officer.get('name')}: {e}")

    async def parse_and_save(
        self,
        conn: asyncpg.Connection,
        zip_path: Path,
        meta: Dict[str, Any]
    ) -> bool:
        """파싱 및 저장 통합 실행"""
        result = await self.parse(zip_path, meta)
        return await self.save_to_db(conn, result)
