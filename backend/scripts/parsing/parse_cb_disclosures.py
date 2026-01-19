#!/usr/bin/env python3
"""
전환사채 공시 파싱

전환사채 공시 문서에서:
1. CB 발행 상세 정보 (발행일, 만기일, 이자율, 전환가액 등)
2. CB 인수자(발행 대상자) 정보 (이름, 관계, 인수금액 등)
3. PostgreSQL 업데이트
"""
import asyncio
import aiohttp
import asyncpg
import json
import logging
import re
import warnings
import zipfile
import io
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

sys.path.insert(0, str(Path(__file__).parent.parent))

# warnings 설정 (한 번만 실행)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 상수 정의
MAX_BOND_NAME_LENGTH = 200
MAX_SUBSCRIBER_NAME_LENGTH = 200
MAX_RELATIONSHIP_LENGTH = 200
MAX_RATIONALE_LENGTH = 500
MAX_USE_OF_PROCEEDS_LENGTH = 500

# 설정 (환경변수 필수)
DART_API_KEY = os.getenv('DART_API_KEY')
DART_BASE_URL = "https://opendart.fss.or.kr/api"

def get_db_url() -> str:
    """DB URL 반환 (asyncpg 호환 형식으로 변환)"""
    url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
    # SQLAlchemy 형식을 asyncpg 형식으로 변환
    if url.startswith('postgresql+asyncpg://'):
        url = url.replace('postgresql+asyncpg://', 'postgresql://')
    return url


class CBDisclosureParser:
    """전환사채 공시 파서"""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")
        self.api_key = api_key
        self.stats = {
            'disclosures_processed': 0,
            'cb_inserted': 0,
            'cb_updated': 0,
            'cb_skipped': 0,
            'subscribers_created': 0,
            'download_failed': 0,
            'parse_failed': 0,
            'errors': 0
        }

    async def download_disclosure(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str
    ) -> Optional[str]:
        """공시 문서 다운로드"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
                if response.status != 200:
                    logger.debug(f"HTTP {response.status} for {rcept_no}")
                    return None

                raw_content = await response.read()
                return self._decode_content(raw_content)

        except aiohttp.ClientError as e:
            logger.error(f"다운로드 실패 {rcept_no}: {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류 {rcept_no}: {e}")
            return None

    def _decode_content(self, raw_content: bytes) -> Optional[str]:
        """ZIP 또는 XML 콘텐츠 디코딩"""
        encodings = ['euc-kr', 'utf-8', 'cp949']

        # ZIP 파일 시도
        try:
            with zipfile.ZipFile(io.BytesIO(raw_content)) as zf:
                xml_filename = zf.namelist()[0]
                xml_bytes = zf.read(xml_filename)

                for encoding in encodings:
                    try:
                        return xml_bytes.decode(encoding)
                    except UnicodeDecodeError:
                        continue
        except zipfile.BadZipFile:
            # ZIP이 아닌 경우 직접 디코딩
            for encoding in encodings:
                try:
                    return raw_content.decode(encoding)
                except UnicodeDecodeError:
                    continue

        return None

    def _extract_acode(self, content: str, acode: str) -> Optional[str]:
        """ACODE 속성으로 값 추출 (중첩 태그 처리)"""
        # 1차 시도: 중첩 태그 없는 단순 패턴
        pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
        match = re.search(pattern, content)
        if match and match.group(1).strip():
            return match.group(1).strip()

        # 2차 시도: 중첩 태그(SPAN 등) 포함 패턴
        pattern2 = rf'<TE[^>]*ACODE="{acode}"[^>]*>(.*?)</TE>'
        match2 = re.search(pattern2, content, re.DOTALL)
        if match2:
            # HTML 태그 제거하고 텍스트만 추출
            text = re.sub(r'<[^>]+>', '', match2.group(1))
            # 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                return text

        return None

    def _extract_aunit(self, content: str, aunit: str) -> Optional[str]:
        """AUNIT 속성으로 값 추출"""
        pattern = rf'<TU[^>]*AUNIT="{aunit}"[^>]*>([^<]*)</TU>'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        return None

    def _parse_korean_date(self, date_str: str) -> Optional[datetime]:
        """한국어 날짜 파싱 (예: 2028년 03월 10일)"""
        if not date_str or date_str == '-':
            return None
        try:
            match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?', date_str)
            if match:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 2000 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d).date()
        except ValueError:
            pass
        return None

    def _parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 파싱 (쉼표 제거)"""
        if not amount_str or amount_str == '-':
            return None
        try:
            cleaned = re.sub(r'[^\d]', '', amount_str)
            if cleaned:
                return int(cleaned)
        except ValueError:
            pass
        return None

    def parse_cb_info(self, content: str, disclosure: Dict) -> Optional[Dict]:
        """CB 발행 정보 파싱 (DART XML ACODE 기반)"""
        result = {
            'bond_name': None,
            'bond_type': 'CB',
            'issue_date': None,
            'maturity_date': None,
            'issue_amount': None,
            'interest_rate': None,
            'conversion_price': None,
            'conversion_start_date': None,
            'conversion_end_date': None,
            'use_of_proceeds': None,
            'source_disclosure_id': disclosure.get('rcept_no'),
            'source_date': disclosure.get('rcept_dt')
        }

        # 채권 유형 판단
        report_nm = disclosure.get('report_nm', '')
        if '신주인수권부사채' in report_nm or 'BW' in report_nm:
            result['bond_type'] = 'BW'
        elif '교환사채' in report_nm or 'EB' in report_nm:
            result['bond_type'] = 'EB'

        # 사채종류 (PL_KND) + 회차 (SEQ_NO)
        pl_knd = self._extract_acode(content, 'PL_KND')
        seq_no = self._extract_acode(content, 'SEQ_NO')
        if pl_knd:
            bond_name = f"제{seq_no}회 {pl_knd}" if seq_no and seq_no != '-' else pl_knd
            result['bond_name'] = bond_name[:MAX_BOND_NAME_LENGTH]
        else:
            result['bond_name'] = '전환사채'

        # 권면총액 (DNM_SUM)
        result['issue_amount'] = self._parse_amount(self._extract_acode(content, 'DNM_SUM'))

        # 표면이율 (PRFT_RATE)
        prft_rate = self._extract_acode(content, 'PRFT_RATE')
        if prft_rate and prft_rate != '-':
            try:
                result['interest_rate'] = float(prft_rate)
            except ValueError:
                pass

        # 전환가액 (EXE_PRC)
        result['conversion_price'] = self._parse_amount(self._extract_acode(content, 'EXE_PRC'))

        # 만기일 (EXP_DT)
        result['maturity_date'] = self._parse_korean_date(self._extract_aunit(content, 'EXP_DT'))

        # 납입일/발행일 (PYM_DT 또는 SBSC_DT)
        pym_dt = self._extract_aunit(content, 'PYM_DT')
        sbsc_dt = self._extract_aunit(content, 'SBSC_DT')
        result['issue_date'] = self._parse_korean_date(pym_dt) or self._parse_korean_date(sbsc_dt)

        # 전환청구기간
        result['conversion_start_date'] = self._parse_korean_date(self._extract_aunit(content, 'SB_BGN_DT'))
        result['conversion_end_date'] = self._parse_korean_date(self._extract_aunit(content, 'SB_END_DT'))

        # 자금사용목적
        fnd_use = self._extract_acode(content, 'FND_USE1')
        if not fnd_use or fnd_use == '-':
            fnd_use = self._extract_aunit(content, 'FND1_PPS')
        if fnd_use and fnd_use != '-':
            result['use_of_proceeds'] = fnd_use[:MAX_USE_OF_PROCEEDS_LENGTH]

        # Fallback: regex 패턴 (ACODE가 없는 경우)
        if not result['issue_amount']:
            result['issue_amount'] = self._extract_amount_fallback(content)

        # 최소한 발행금액이 있어야 유효
        return result if result['issue_amount'] else None

    def _extract_amount_fallback(self, content: str) -> Optional[int]:
        """발행금액 추출 (Fallback)"""
        patterns = [
            r'권면\s*(?:총액|금액)[^\d]*([0-9,]+)',
            r'발행\s*(?:총액|금액)[^\d]*([0-9,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                amount = self._parse_amount(match.group(1))
                if amount:
                    return amount
        return None

    def parse_subscribers(self, content: str, disclosure: Dict) -> List[Dict]:
        """CB 인수자 정보 파싱 (ACODE 기반) - 모든 인수자와 금액 추출"""
        subscribers = []
        rcept_no = disclosure.get('rcept_no')
        seen_names = set()

        # 1. 모든 ISSU_NM과 ISSU_AMT 쌍을 regex로 추출 (순서대로)
        # 패턴: TR 내에서 ISSU_NM과 ISSU_AMT가 있는 경우
        all_subscribers = self._extract_all_subscribers_regex(content, rcept_no)

        for sub in all_subscribers:
            name = sub.get('subscriber_name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                subscribers.append(sub)

        # 2. 첫 번째 인수자의 관계 정보 및 법인 정보 추가
        if subscribers:
            first_sub = subscribers[0]
            rlt = self._extract_acode(content, 'RLT')
            issu_slt = self._extract_acode(content, 'ISSU_SLT')

            if rlt and rlt != '-':
                first_sub['relationship_to_company'] = rlt[:MAX_RELATIONSHIP_LENGTH]
                first_sub['is_related_party'] = 'Y'
            if issu_slt and issu_slt != '-':
                first_sub['selection_rationale'] = issu_slt[:MAX_RATIONALE_LENGTH]

            # 법인/단체 기본정보 추가
            entity_info = self._extract_entity_info(content, first_sub['subscriber_name'])
            first_sub.update(entity_info)

        # 3. Fallback: BeautifulSoup 기반 테이블 파싱
        if not subscribers:
            subscribers = self._extract_subscribers_from_table(content, rcept_no)

        return subscribers

    def _extract_all_subscribers_regex(self, content: str, rcept_no: str) -> List[Dict]:
        """모든 인수자와 인수금액 쌍을 regex로 추출"""
        subscribers = []

        # TR 단위로 ISSU_NM과 ISSU_AMT 찾기
        # 패턴: <TR...>...<TE...ACODE="ISSU_NM"...>이름</TE>...<TE...ACODE="ISSU_AMT"...>금액</TE>...</TR>
        tr_pattern = r'<TR[^>]*>(.*?)</TR>'
        tr_matches = re.findall(tr_pattern, content, re.DOTALL | re.IGNORECASE)

        for tr_content in tr_matches:
            # 이 TR 안에 ISSU_NM이 있는지 확인
            name_match = re.search(r'<TE[^>]*ACODE="ISSU_NM"[^>]*>(.*?)</TE>', tr_content, re.DOTALL | re.IGNORECASE)
            if not name_match:
                continue

            # 이름 추출 (HTML 태그 제거)
            name_raw = name_match.group(1)
            name = re.sub(r'<[^>]+>', '', name_raw)
            name = re.sub(r'&[^;]+;', ' ', name)  # &cr; 등을 공백으로
            name = re.sub(r'\s+', ' ', name).strip()

            if not name or name == '-' or len(name) < 2:
                continue

            # 금액 추출
            amt_match = re.search(r'<TE[^>]*ACODE="ISSU_AMT"[^>]*>([^<]*)</TE>', tr_content, re.IGNORECASE)
            amount = None
            if amt_match:
                amount = self._parse_amount(amt_match.group(1))

            subscribers.append({
                'subscriber_name': name[:MAX_SUBSCRIBER_NAME_LENGTH],
                'relationship_to_company': None,
                'subscription_amount': amount,
                'selection_rationale': None,
                'is_related_party': 'N',
                'source_disclosure_id': rcept_no,
                'representative_name': None,
                'representative_share': None,
                'gp_name': None,
                'gp_share': None,
                'largest_shareholder_name': None,
                'largest_shareholder_share': None,
            })

        return subscribers

    def _extract_first_subscriber(self, content: str, rcept_no: str) -> Optional[Dict]:
        """첫 번째 인수자 추출"""
        issu_nm = self._extract_acode(content, 'ISSU_NM')
        if not issu_nm or issu_nm == '-' or len(issu_nm) < 2:
            return None

        rlt = self._extract_acode(content, 'RLT')
        issu_amt = self._extract_acode(content, 'ISSU_AMT')
        issu_slt = self._extract_acode(content, 'ISSU_SLT')

        # 법인/단체 기본정보 추출 (대표이사, 업무집행자, 최대주주)
        entity_info = self._extract_entity_info(content, issu_nm)

        return {
            'subscriber_name': issu_nm[:MAX_SUBSCRIBER_NAME_LENGTH],
            'relationship_to_company': rlt[:MAX_RELATIONSHIP_LENGTH] if rlt and rlt != '-' else None,
            'subscription_amount': self._parse_amount(issu_amt),
            'selection_rationale': issu_slt[:MAX_RATIONALE_LENGTH] if issu_slt and issu_slt != '-' else None,
            'is_related_party': 'Y' if (rlt and rlt != '-') else 'N',
            'source_disclosure_id': rcept_no,
            # 법인/단체 정보
            'representative_name': entity_info.get('representative_name'),
            'representative_share': entity_info.get('representative_share'),
            'gp_name': entity_info.get('gp_name'),
            'gp_share': entity_info.get('gp_share'),
            'largest_shareholder_name': entity_info.get('largest_shareholder_name'),
            'largest_shareholder_share': entity_info.get('largest_shareholder_share'),
        }

    def _extract_entity_info(self, content: str, subscriber_name: str) -> Dict:
        """법인/단체 기본정보 추출 (대표이사, 업무집행자, 최대주주)"""
        result = {
            'representative_name': None,
            'representative_share': None,
            'gp_name': None,
            'gp_share': None,
            'largest_shareholder_name': None,
            'largest_shareholder_share': None,
        }

        try:
            # BAS_NAME이 subscriber_name과 일치하는 행 찾기
            # 먼저 BAS_NAME 추출
            bas_name = self._extract_acode(content, 'BAS_NAME')

            # BAS_NAME이 subscriber_name과 일치하거나, subscriber_name이 포함되어 있으면
            if not bas_name or (subscriber_name not in bas_name and bas_name not in subscriber_name):
                # 다른 방식으로 찾기 - TABLE-GROUP 내에서 찾기
                pass

            # 대표이사(대표조합원) - BAS_NAM1
            bas_nam1 = self._extract_acode(content, 'BAS_NAM1')
            if bas_nam1 and bas_nam1 != '-' and len(bas_nam1) >= 2:
                result['representative_name'] = bas_nam1[:200]

            # 대표이사 지분율 - BAS_RAT1
            bas_rat1 = self._extract_acode(content, 'BAS_RAT1')
            if bas_rat1 and bas_rat1 != '-':
                result['representative_share'] = self._parse_share(bas_rat1)

            # 업무집행자(업무집행조합원) - BAS_NAM2
            bas_nam2 = self._extract_acode(content, 'BAS_NAM2')
            if bas_nam2 and bas_nam2 != '-' and len(bas_nam2) >= 2:
                result['gp_name'] = bas_nam2[:200]

            # 업무집행자 지분율 - BAS_RAT2
            bas_rat2 = self._extract_acode(content, 'BAS_RAT2')
            if bas_rat2 and bas_rat2 != '-':
                result['gp_share'] = self._parse_share(bas_rat2)

            # 최대주주(최대출자자) - BAS_NAM3
            bas_nam3 = self._extract_acode(content, 'BAS_NAM3')
            if bas_nam3 and bas_nam3 != '-' and len(bas_nam3) >= 2:
                result['largest_shareholder_name'] = bas_nam3[:200]

            # 최대주주 지분율 - BAS_RAT3
            bas_rat3 = self._extract_acode(content, 'BAS_RAT3')
            if bas_rat3 and bas_rat3 != '-':
                result['largest_shareholder_share'] = self._parse_share(bas_rat3)

        except Exception as e:
            logger.warning(f"법인정보 추출 실패: {e}")

        return result

    def _parse_share(self, share_str: str) -> Optional[float]:
        """지분율 파싱 (%)"""
        if not share_str or share_str == '-':
            return None
        try:
            # % 제거하고 숫자만 추출
            cleaned = re.sub(r'[^\d.]', '', share_str)
            if cleaned:
                return float(cleaned)
        except ValueError:
            pass
        return None

    def _extract_additional_subscribers(self, content: str, rcept_no: str, first_sub: Optional[Dict]) -> List[Dict]:
        """추가 인수자 추출 (복수 인수자)"""
        subscribers = []
        first_name = first_sub['subscriber_name'] if first_sub else None

        issu_pattern = r'<TR[^>]*>.*?ACODE="ISSU_NM"[^>]*>([^<]+)</TE>.*?</TR>'
        matches = re.findall(issu_pattern, content, re.DOTALL)

        for match in matches:
            name = match.strip()
            if name and name != '-' and len(name) >= 2 and name != first_name:
                subscribers.append({
                    'subscriber_name': name[:MAX_SUBSCRIBER_NAME_LENGTH],
                    'relationship_to_company': None,
                    'subscription_amount': None,
                    'selection_rationale': None,
                    'is_related_party': 'N',
                    'source_disclosure_id': rcept_no
                })

        return subscribers

    def _extract_subscribers_from_table(self, content: str, rcept_no: str) -> List[Dict]:
        """BeautifulSoup 기반 테이블 파싱 (Fallback)"""
        subscribers = []

        try:
            soup = BeautifulSoup(content, 'html.parser')
            table_groups = soup.find_all('table-group', {'aclass': re.compile(r'CB_ISSU', re.I)})
            if not table_groups:
                table_groups = soup.find_all('table-group')

            seen_names = set()
            for tg in table_groups:
                tg_text = tg.get_text()
                if '대상자' not in tg_text and '인수' not in tg_text:
                    continue

                for row in tg.find_all('tr'):
                    te_tags = row.find_all('te')
                    for te in te_tags:
                        if te.get('acode', '') != 'ISSU_NM':
                            continue

                        name = te.get_text(strip=True)
                        if not name or name == '-' or len(name) < 2 or name in seen_names:
                            continue

                        seen_names.add(name)

                        # 같은 row에서 금액 찾기
                        amt = None
                        for te2 in te_tags:
                            if te2.get('acode') == 'ISSU_AMT':
                                amt = self._parse_amount(te2.get_text(strip=True))
                                break

                        subscribers.append({
                            'subscriber_name': name[:MAX_SUBSCRIBER_NAME_LENGTH],
                            'relationship_to_company': None,
                            'subscription_amount': amt,
                            'selection_rationale': None,
                            'is_related_party': 'N',
                            'source_disclosure_id': rcept_no
                        })

        except Exception as e:
            logger.warning(f"테이블 파싱 실패 ({rcept_no}): {e}")

        return subscribers

    async def process_disclosure(
        self,
        session: aiohttp.ClientSession,
        conn: asyncpg.Connection,
        disclosure: Dict
    ) -> Tuple[bool, int]:
        """개별 공시 처리"""
        rcept_no = disclosure.get('rcept_no')
        corp_code = disclosure.get('corp_code')

        # 회사 조회
        company = await conn.fetchrow(
            "SELECT id FROM companies WHERE corp_code = $1", corp_code
        )
        if not company:
            return False, 0

        # 이미 처리된 공시인지 확인 (중복 처리 방지)
        existing = await conn.fetchval(
            "SELECT 1 FROM convertible_bonds WHERE source_disclosure_id = $1", rcept_no
        )
        if existing:
            self.stats['cb_skipped'] += 1
            return False, 0

        # 공시 다운로드
        content = await self.download_disclosure(session, rcept_no)
        if not content:
            self.stats['download_failed'] += 1
            return False, 0

        # CB 정보 파싱
        cb_info = self.parse_cb_info(content, disclosure)
        if not cb_info:
            self.stats['parse_failed'] += 1
            return False, 0

        # CB 저장 또는 업데이트
        try:
            cb_id = await self._upsert_cb(conn, company['id'], cb_info, rcept_no)
            if not cb_id:
                return False, 0

            # 인수자 저장
            subscribers = self.parse_subscribers(content, disclosure)
            new_subs = await self._insert_subscribers(conn, cb_id, subscribers, rcept_no)

            self.stats['disclosures_processed'] += 1
            return True, new_subs

        except Exception as e:
            logger.error(f"공시 {rcept_no} 처리 실패: {e}")
            self.stats['errors'] += 1
            return False, 0

    async def _upsert_cb(
        self, conn: asyncpg.Connection, company_id, cb_info: Dict, rcept_no: str
    ) -> Optional[str]:
        """CB 저장 또는 업데이트 (UPSERT)"""
        # INSERT with ON CONFLICT - xmax로 INSERT/UPDATE 구분
        result = await conn.fetchrow("""
            INSERT INTO convertible_bonds (
                id, company_id, bond_name, issue_date, maturity_date,
                issue_amount, interest_rate, conversion_price,
                conversion_start_date, conversion_end_date,
                use_of_proceeds, status, source_disclosure_id,
                created_at, updated_at
            ) VALUES (
                uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active', $11,
                NOW(), NOW()
            )
            ON CONFLICT (company_id, bond_name, issue_date) DO UPDATE SET
                maturity_date = COALESCE(EXCLUDED.maturity_date, convertible_bonds.maturity_date),
                issue_amount = COALESCE(EXCLUDED.issue_amount, convertible_bonds.issue_amount),
                interest_rate = COALESCE(EXCLUDED.interest_rate, convertible_bonds.interest_rate),
                conversion_price = COALESCE(EXCLUDED.conversion_price, convertible_bonds.conversion_price),
                conversion_start_date = COALESCE(EXCLUDED.conversion_start_date, convertible_bonds.conversion_start_date),
                conversion_end_date = COALESCE(EXCLUDED.conversion_end_date, convertible_bonds.conversion_end_date),
                source_disclosure_id = COALESCE(EXCLUDED.source_disclosure_id, convertible_bonds.source_disclosure_id),
                updated_at = NOW()
            RETURNING id, (xmax = 0) as inserted
        """,
            company_id,
            cb_info['bond_name'],
            cb_info['issue_date'],
            cb_info['maturity_date'],
            cb_info['issue_amount'],
            cb_info['interest_rate'],
            cb_info['conversion_price'],
            cb_info.get('conversion_start_date'),
            cb_info.get('conversion_end_date'),
            cb_info['use_of_proceeds'],
            rcept_no
        )

        if result:
            if result['inserted']:
                self.stats['cb_inserted'] += 1
            else:
                self.stats['cb_updated'] += 1
            return result['id']
        return None

    async def _insert_subscribers(
        self, conn: asyncpg.Connection, cb_id, subscribers: List[Dict], rcept_no: str
    ) -> int:
        """인수자 저장 (중복 체크 포함)"""
        new_count = 0

        for sub in subscribers:
            try:
                # 기존 인수자 확인 (cb_id + subscriber_name 조합으로 중복 체크)
                existing = await conn.fetchval("""
                    SELECT 1 FROM cb_subscribers
                    WHERE cb_id = $1 AND subscriber_name = $2
                """, cb_id, sub['subscriber_name'])

                if existing:
                    continue

                await conn.execute("""
                    INSERT INTO cb_subscribers (
                        id, cb_id, subscriber_name, relationship_to_company,
                        subscription_amount, selection_rationale, is_related_party,
                        source_disclosure_id, created_at, updated_at,
                        representative_name, representative_share,
                        gp_name, gp_share,
                        largest_shareholder_name, largest_shareholder_share
                    ) VALUES (
                        uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, NOW(), NOW(),
                        $8, $9, $10, $11, $12, $13
                    )
                """,
                    cb_id,
                    sub['subscriber_name'],
                    sub['relationship_to_company'],
                    sub['subscription_amount'],
                    sub['selection_rationale'],
                    sub['is_related_party'],
                    rcept_no,
                    sub.get('representative_name'),
                    sub.get('representative_share'),
                    sub.get('gp_name'),
                    sub.get('gp_share'),
                    sub.get('largest_shareholder_name'),
                    sub.get('largest_shareholder_share'),
                )
                new_count += 1
            except asyncpg.UniqueViolationError:
                pass  # 중복 - 무시
            except Exception as e:
                logger.warning(f"인수자 저장 실패: {e}")

        self.stats['subscribers_created'] += new_count
        return new_count


async def main():
    """메인 함수"""
    import argparse

    parser_arg = argparse.ArgumentParser(description="전환사채 공시 파싱")
    parser_arg.add_argument("--input", default="data/cb_disclosures_by_company_full.json", help="입력 JSON 파일")
    parser_arg.add_argument("--limit", type=int, default=500, help="처리할 공시 수")
    parser_arg.add_argument("--skip", type=int, default=0, help="건너뛸 공시 수")
    parser_arg.add_argument("--delay", type=float, default=1.0, help="API 호출 간격 (초)")

    args = parser_arg.parse_args()

    # API 키 확인
    if not DART_API_KEY:
        logger.error("DART_API_KEY 환경변수가 설정되지 않았습니다")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("전환사채 공시 파싱 시작")
    logger.info("=" * 80)

    # 공시 목록 로드
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent.parent / args.input

    if not input_path.exists():
        logger.error(f"입력 파일이 없습니다: {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        disclosures = json.load(f)

    logger.info(f"총 공시: {len(disclosures)}건")

    # 발행결정 공시만 필터링
    original_count = len(disclosures)
    disclosures = [d for d in disclosures if '발행결정' in d.get('report_nm', '')]
    logger.info(f"발행결정 공시: {len(disclosures)}건 (전체 {original_count}건 중)")

    # 범위 지정
    disclosures = disclosures[args.skip:args.skip + args.limit]
    logger.info(f"처리 대상: {len(disclosures)}건 (skip: {args.skip})")

    if not disclosures:
        logger.info("처리할 공시가 없습니다")
        return

    parser = CBDisclosureParser(DART_API_KEY)
    db_url = get_db_url()
    conn = await asyncpg.connect(db_url)

    try:
        async with aiohttp.ClientSession() as session:
            for i, disclosure in enumerate(disclosures):
                await parser.process_disclosure(session, conn, disclosure)

                if (i + 1) % 50 == 0:
                    _log_progress(parser, i + 1, len(disclosures))

                if args.delay > 0:
                    await asyncio.sleep(args.delay)

        # 최종 통계
        _log_final_stats(parser)
        await _log_db_stats(conn)

    finally:
        await conn.close()


def _log_progress(parser: CBDisclosureParser, current: int, total: int):
    """진행 상황 로깅"""
    stats = parser.stats
    logger.info(
        f"진행: {current}/{total} - "
        f"처리: {stats['disclosures_processed']}, "
        f"신규: {stats['cb_inserted']}, "
        f"업데이트: {stats['cb_updated']}, "
        f"건너뜀: {stats['cb_skipped']}, "
        f"인수자: {stats['subscribers_created']}"
    )


def _log_final_stats(parser: CBDisclosureParser):
    """최종 통계 로깅"""
    stats = parser.stats
    logger.info("\n" + "=" * 80)
    logger.info("전환사채 공시 파싱 완료")
    logger.info("=" * 80)
    logger.info(f"처리된 공시: {stats['disclosures_processed']}건")
    logger.info(f"CB 신규 생성: {stats['cb_inserted']}개")
    logger.info(f"CB 업데이트: {stats['cb_updated']}개")
    logger.info(f"CB 건너뜀 (이미 처리됨): {stats['cb_skipped']}개")
    logger.info(f"다운로드 실패: {stats['download_failed']}건")
    logger.info(f"파싱 실패: {stats['parse_failed']}건")
    logger.info(f"인수자 저장: {stats['subscribers_created']}명")
    logger.info(f"오류: {stats['errors']}건")


async def _log_db_stats(conn: asyncpg.Connection):
    """DB 현황 로깅"""
    stats = await conn.fetchrow("""
        SELECT
            COUNT(*) as total_cb,
            COUNT(issue_date) as has_issue_date,
            COUNT(conversion_price) as has_conv_price,
            (SELECT COUNT(*) FROM cb_subscribers) as total_subscribers
        FROM convertible_bonds
    """)
    logger.info(f"\nDB 현황:")
    logger.info(f"  전환사채: 총 {stats['total_cb']}개")
    logger.info(f"  - issue_date 있음: {stats['has_issue_date']}개")
    logger.info(f"  - conversion_price 있음: {stats['has_conv_price']}개")
    logger.info(f"  인수자: 총 {stats['total_subscribers']}명")


if __name__ == "__main__":
    asyncio.run(main())
