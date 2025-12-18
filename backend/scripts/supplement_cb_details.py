#!/usr/bin/env python3
"""
전환사채 세부정보 보완 스크립트

누락된 maturity_date, conversion_price, issue_date 등을
원본 공시에서 재파싱하여 보완합니다.
"""
import asyncio
import aiohttp
import asyncpg
import asyncpg.exceptions
import re
import warnings
import zipfile
import io
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY')
DART_BASE_URL = "https://opendart.fss.or.kr/api"

def get_db_url() -> str:
    url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
    if url.startswith('postgresql+asyncpg://'):
        url = url.replace('postgresql+asyncpg://', 'postgresql://')
    return url


class CBDetailSupplementer:
    """CB 세부정보 보완 클래스"""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")
        self.api_key = api_key
        self.stats = {
            'total_checked': 0,
            'updated': 0,
            'skipped': 0,
            'download_failed': 0,
            'parse_failed': 0
        }

    async def download_disclosure(self, session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
        """공시 문서 다운로드"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }
            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
                if response.status != 200:
                    return None
                raw_content = await response.read()
                return self._decode_content(raw_content)
        except Exception as e:
            logger.error(f"다운로드 실패 {rcept_no}: {e}")
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
            for encoding in encodings:
                try:
                    return raw_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
        return None

    def _extract_acode(self, content: str, acode: str) -> Optional[str]:
        """ACODE 속성으로 값 추출"""
        pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_aunit(self, content: str, aunit: str) -> Optional[str]:
        """AUNIT 속성으로 값 추출"""
        pattern = rf'<TU[^>]*AUNIT="{aunit}"[^>]*>([^<]*)</TU>'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        return None

    def _parse_korean_date(self, date_str: str) -> Optional[datetime]:
        """한국어 날짜 파싱 (다양한 형식 지원)"""
        if not date_str or date_str == '-':
            return None
        try:
            # 형식 1: 2027년 9월 6일
            match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?', date_str)
            if match:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 2000 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d).date()

            # 형식 2: 2027 9 6 (공백 구분)
            match = re.search(r'(\d{4})\s+(\d{1,2})\s+(\d{1,2})', date_str)
            if match:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 2000 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d).date()

            # 형식 3: 2027.09.06 또는 2027-09-06
            match = re.search(r'(\d{4})[\.\-](\d{1,2})[\.\-](\d{1,2})', date_str)
            if match:
                y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 2000 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d).date()
        except ValueError:
            pass
        return None

    def _parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 파싱"""
        if not amount_str or amount_str == '-':
            return None
        try:
            cleaned = re.sub(r'[^\d]', '', amount_str)
            if cleaned:
                return int(cleaned)
        except ValueError:
            pass
        return None

    def _extract_table_value(self, content: str, keywords: List[str]) -> Optional[str]:
        """HTML 테이블에서 키워드로 값 추출"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        for keyword in keywords:
            # TD에서 키워드 검색
            for td in soup.find_all('td'):
                text = td.get_text(strip=True)
                if keyword in text:
                    # 같은 행의 다음 TD들 확인
                    next_td = td.find_next_sibling('td')
                    while next_td:
                        next_text = next_td.get_text(strip=True)
                        if next_text and next_text != '-':
                            return next_text
                        next_td = next_td.find_next_sibling('td')
                    # 다음 행 확인
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        next_tr = parent_tr.find_next_sibling('tr')
                        if next_tr:
                            first_td = next_tr.find('td')
                            if first_td:
                                return first_td.get_text(strip=True)
        return None

    def _extract_maturity_from_html(self, content: str) -> Optional[datetime]:
        """HTML에서 만기일 추출"""
        # 패턴 1: "만기일" 또는 "사채만기일" 키워드 뒤의 날짜
        patterns = [
            r'만기일[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
            r'만기[^<]*</TD>\s*<TD[^>]*>[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
            r'사채\s*만기일?[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
            # 정정공시 형식: 변경 후 열에서 추출
            r'만기[^<]*</TD>\s*<TD[^>]*>[^<]*</TD>\s*<TD[^>]*>[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                date = self._parse_korean_date(match.group(1))
                if date:
                    return date

        # 패턴 2: 직접 날짜 추출 (만기 키워드 근처)
        maturity_idx = content.find('만기')
        if maturity_idx > 0:
            # 만기 키워드 뒤 500자 내에서 날짜 찾기
            search_area = content[maturity_idx:maturity_idx + 500]
            # 2027 7 29 형식
            match = re.search(r'>(\d{4})\s+(\d{1,2})\s+(\d{1,2})<', search_area)
            if match:
                try:
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 2020 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                        return datetime(y, m, d).date()
                except ValueError:
                    pass

        return None

    def _extract_conversion_price_from_html(self, content: str) -> Optional[int]:
        """HTML에서 전환가액 추출"""
        patterns = [
            r'전환가액[^<]*</TD>\s*<TD[^>]*>([0-9,]+)',
            r'행사가액[^<]*</TD>\s*<TD[^>]*>([0-9,]+)',
            r'전환가격[^<]*</TD>\s*<TD[^>]*>([0-9,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return self._parse_amount(match.group(1))
        return None

    def _extract_issue_date_from_html(self, content: str) -> Optional[datetime]:
        """HTML에서 발행일/납입일 추출"""
        patterns = [
            r'납입일[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
            r'발행일[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
            r'청약일[^<]*</TD>\s*<TD[^>]*>([^<]+)</TD>',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                date = self._parse_korean_date(match.group(1))
                if date:
                    return date
        return None

    def parse_cb_details(self, content: str) -> Dict:
        """CB 세부정보 파싱"""
        result = {
            'maturity_date': None,
            'issue_date': None,
            'conversion_price': None,
            'interest_rate': None,
            'conversion_start_date': None,
            'conversion_end_date': None,
            'issue_amount': None
        }

        # 1. ACODE/AUNIT 기반 파싱 (우선)
        result['maturity_date'] = self._parse_korean_date(self._extract_aunit(content, 'EXP_DT'))
        pym_dt = self._extract_aunit(content, 'PYM_DT')
        sbsc_dt = self._extract_aunit(content, 'SBSC_DT')
        result['issue_date'] = self._parse_korean_date(pym_dt) or self._parse_korean_date(sbsc_dt)
        result['conversion_price'] = self._parse_amount(self._extract_acode(content, 'EXE_PRC'))

        prft_rate = self._extract_acode(content, 'PRFT_RATE')
        if prft_rate and prft_rate != '-':
            try:
                result['interest_rate'] = float(prft_rate)
            except ValueError:
                pass

        result['conversion_start_date'] = self._parse_korean_date(self._extract_aunit(content, 'SB_BGN_DT'))
        result['conversion_end_date'] = self._parse_korean_date(self._extract_aunit(content, 'SB_END_DT'))
        result['issue_amount'] = self._parse_amount(self._extract_acode(content, 'DNM_SUM'))

        # 2. HTML 테이블 기반 파싱 (Fallback)
        if not result['maturity_date']:
            result['maturity_date'] = self._extract_maturity_from_html(content)
        if not result['conversion_price']:
            result['conversion_price'] = self._extract_conversion_price_from_html(content)
        if not result['issue_date']:
            result['issue_date'] = self._extract_issue_date_from_html(content)

        return result

    async def get_cbs_missing_details(self, pool: asyncpg.Pool) -> List[Dict]:
        """세부정보가 누락된 CB 목록 조회"""
        query = """
            SELECT cb.id, cb.bond_name, cb.issue_amount, cb.maturity_date,
                   cb.conversion_price, cb.issue_date, cb.source_disclosure_id,
                   c.name as company_name
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            WHERE (cb.maturity_date IS NULL OR cb.conversion_price IS NULL OR cb.issue_date IS NULL)
              AND cb.bond_name NOT LIKE '%영구%'
              AND cb.bond_name NOT LIKE '%무기한%'
              AND cb.source_disclosure_id IS NOT NULL
            ORDER BY cb.id
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def update_cb_details(self, pool: asyncpg.Pool, cb_id: str, details: Dict) -> bool:
        """CB 세부정보 업데이트"""
        updates = []
        params = [cb_id]
        param_idx = 2

        for field in ['maturity_date', 'issue_date', 'conversion_price',
                      'interest_rate', 'conversion_start_date', 'conversion_end_date']:
            if details.get(field) is not None:
                updates.append(f"{field} = ${param_idx}")
                params.append(details[field])
                param_idx += 1

        if not updates:
            return False

        query = f"UPDATE convertible_bonds SET {', '.join(updates)} WHERE id = $1"
        async with pool.acquire() as conn:
            await conn.execute(query, *params)
        return True

    async def supplement_cb_details(self, limit: int = None):
        """CB 세부정보 보완 실행"""
        pool = await asyncpg.create_pool(get_db_url(), min_size=2, max_size=5)

        try:
            cbs = await self.get_cbs_missing_details(pool)
            total = len(cbs)
            logger.info(f"세부정보 누락 CB: {total}건")

            if limit:
                cbs = cbs[:limit]
                logger.info(f"처리 제한: {limit}건")

            async with aiohttp.ClientSession() as session:
                for i, cb in enumerate(cbs, 1):
                    self.stats['total_checked'] += 1
                    cb_id = cb['id']
                    rcept_no = cb['source_disclosure_id']
                    company = cb['company_name']
                    bond_name = cb['bond_name']

                    logger.info(f"[{i}/{len(cbs)}] {company} - {bond_name} (rcept: {rcept_no})")

                    # 공시 다운로드
                    content = await self.download_disclosure(session, rcept_no)
                    if not content:
                        self.stats['download_failed'] += 1
                        logger.warning(f"  다운로드 실패: {rcept_no}")
                        continue

                    # 파싱
                    details = self.parse_cb_details(content)

                    # 누락된 필드만 업데이트
                    update_details = {}
                    if cb['maturity_date'] is None and details['maturity_date']:
                        update_details['maturity_date'] = details['maturity_date']
                    if cb['conversion_price'] is None and details['conversion_price']:
                        update_details['conversion_price'] = details['conversion_price']
                    if cb['issue_date'] is None and details['issue_date']:
                        update_details['issue_date'] = details['issue_date']
                    if details.get('interest_rate'):
                        update_details['interest_rate'] = details['interest_rate']
                    if details.get('conversion_start_date'):
                        update_details['conversion_start_date'] = details['conversion_start_date']
                    if details.get('conversion_end_date'):
                        update_details['conversion_end_date'] = details['conversion_end_date']

                    if update_details:
                        try:
                            await self.update_cb_details(pool, cb_id, update_details)
                            self.stats['updated'] += 1
                            logger.info(f"  업데이트: {list(update_details.keys())}")
                        except asyncpg.exceptions.UniqueViolationError as e:
                            # issue_date 업데이트로 인한 유니크 제약 위반 - issue_date 제외하고 재시도
                            if 'issue_date' in update_details:
                                del update_details['issue_date']
                                if update_details:
                                    try:
                                        await self.update_cb_details(pool, cb_id, update_details)
                                        self.stats['updated'] += 1
                                        logger.info(f"  업데이트 (issue_date 제외): {list(update_details.keys())}")
                                    except Exception:
                                        self.stats['skipped'] += 1
                                        logger.warning(f"  유니크 제약 위반으로 스킵")
                                else:
                                    self.stats['skipped'] += 1
                                    logger.warning(f"  유니크 제약 위반으로 스킵")
                            else:
                                self.stats['skipped'] += 1
                                logger.warning(f"  유니크 제약 위반으로 스킵: {e}")
                    else:
                        self.stats['skipped'] += 1
                        logger.info(f"  파싱 실패 또는 업데이트할 항목 없음")

                    # Rate limit
                    await asyncio.sleep(0.3)

        finally:
            await pool.close()

        # 결과 출력
        logger.info("\n===== 보완 결과 =====")
        logger.info(f"총 확인: {self.stats['total_checked']}건")
        logger.info(f"업데이트: {self.stats['updated']}건")
        logger.info(f"스킵: {self.stats['skipped']}건")
        logger.info(f"다운로드 실패: {self.stats['download_failed']}건")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='CB 세부정보 보완')
    parser.add_argument('--limit', type=int, help='처리 제한 수')
    args = parser.parse_args()

    api_key = DART_API_KEY
    if not api_key:
        logger.error("DART_API_KEY 환경변수를 설정하세요")
        return

    supplementer = CBDetailSupplementer(api_key)
    await supplementer.supplement_cb_details(limit=args.limit)


if __name__ == '__main__':
    asyncio.run(main())
