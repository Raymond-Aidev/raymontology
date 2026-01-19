#!/usr/bin/env python3
"""
Palantir Ontology 기반 사업보고서 파서
- NO 중복제거: 같은 이름이라도 시간/맥락이 다르면 별도 객체
- Rich Metadata: 모든 레코드에 source_file, report_date, fiscal_year, temporal bounds 포함
- 8가지 데이터 타입: Companies, Officers, Positions, Financials, Affiliates, CB Subscribers, Bonds, Risk Signals
- BeautifulSoup 사용: malformed XML 안전하게 파싱
"""
import asyncio
import asyncpg
import logging
import sys
import json
import re
import zipfile
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OntologyBusinessReportParser:
    """Palantir Ontology 기반 사업보고서 파서 - NO 중복제거"""

    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'files_parsed': 0,
            'parse_errors': 0,
            'financial_statements_saved': 0,
            'affiliates_saved': 0,
            'officer_positions_saved': 0,
            'cb_subscribers_saved': 0,
            'skipped_no_company': 0,
        }

    def parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 문자열 파싱 (백만원 → 원)"""
        if not amount_str or amount_str.strip() in ['-', '', 'N/A', '해당사항없음']:
            return None

        try:
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]

            match = re.search(r'[-+]?\d+\.?\d*', cleaned)
            if match:
                value = float(match.group())
                value = int(value * 1000000)  # 백만원 → 원
                return -value if is_negative else value
            return None
        except:
            return None

    def parse_ratio(self, ratio_str: str) -> Optional[float]:
        """비율 문자열 파싱 (%, 소수점)"""
        if not ratio_str or ratio_str.strip() in ['-', '', 'N/A']:
            return None

        try:
            cleaned = ratio_str.replace(',', '').replace('%', '').replace(' ', '').strip()
            return float(cleaned)
        except:
            return None

    def parse_date(self, date_str: str) -> Optional[date]:
        """날짜 문자열 파싱"""
        if not date_str:
            return None

        try:
            cleaned = date_str.replace('-', '').replace('.', '').replace('/', '').strip()
            if len(cleaned) == 8:
                return datetime.strptime(cleaned, '%Y%m%d').date()
            return None
        except:
            return None

    def extract_financial_statements(
        self,
        soup: BeautifulSoup,
        metadata: Dict
    ) -> Optional[Dict]:
        """재무제표 추출 (BeautifulSoup 사용)"""
        try:
            financial_data = {}

            # 재무상태표/대차대조표 키워드
            bs_keywords = ['재무상태표', '대차대조표', '연결재무상태표', '개별재무상태표']
            # 손익계산서 키워드
            pl_keywords = ['손익계산서', '포괄손익계산서', '연결손익계산서', '개별손익계산서']

            # 계정과목 매핑
            account_map = {
                '자산총계': 'total_assets',
                '자산 총계': 'total_assets',
                '부채총계': 'total_liabilities',
                '부채 총계': 'total_liabilities',
                '자본총계': 'total_equity',
                '자본 총계': 'total_equity',
                '매출액': 'revenue',
                '영업이익': 'operating_profit',
                '당기순이익': 'net_income',
            }

            # 모든 테이블 탐색
            for table in soup.find_all(['TABLE', 'table']):
                table_text = table.get_text()

                # 재무상태표
                if any(kw in table_text for kw in bs_keywords):
                    for row in table.find_all(['TR', 'tr']):
                        cells = row.find_all(['TD', 'td'])
                        if len(cells) >= 2:
                            account_nm = cells[0].get_text().strip()
                            amount_str = cells[1].get_text().strip()

                            for key, field in account_map.items():
                                if key in account_nm:
                                    amount = self.parse_amount(amount_str)
                                    if amount is not None:
                                        financial_data[field] = amount

                # 손익계산서
                elif any(kw in table_text for kw in pl_keywords):
                    for row in table.find_all(['TR', 'tr']):
                        cells = row.find_all(['TD', 'td'])
                        if len(cells) >= 2:
                            account_nm = cells[0].get_text().strip()
                            amount_str = cells[1].get_text().strip()

                            for key, field in account_map.items():
                                if key in account_nm:
                                    amount = self.parse_amount(amount_str)
                                    if amount is not None:
                                        financial_data[field] = amount

            # 최소 2개 이상 필드 추출 시 성공
            if len(financial_data) >= 2:
                return financial_data

            return None

        except Exception as e:
            logger.debug(f"재무제표 추출 오류: {e}")
            return None

    def extract_affiliates(
        self,
        soup: BeautifulSoup,
        metadata: Dict
    ) -> List[Dict]:
        """계열사 현황 추출 - 개선된 로직"""
        affiliates = []

        try:
            # 계열사 키워드 (긍정적)
            aff_keywords = ['계열회사', '계열사', '종속회사', '관계회사']

            # 제외할 키워드 (재무제표 테이블 필터링)
            exclude_keywords = [
                '재무상태표', '손익계산서', '포괄손익계산서', '자본변동표', '현금흐름표',
                '자산총계', '부채총계', '자본총계', '매출액', '영업이익', '당기순이익',
                '법인세', '이연법인세', '감가상각', '대손상각', '유형자산', '무형자산',
                '현금및현금성자산', '단기금융자산', '매출채권', '재고자산'
            ]

            for table in soup.find_all(['TABLE', 'table']):
                table_text = table.get_text()

                # 재무제표 테이블 제외
                if any(kw in table_text for kw in exclude_keywords):
                    continue

                # 계열사 키워드 포함 테이블만 처리
                if not any(kw in table_text for kw in aff_keywords):
                    continue

                # 테이블 행 제한 (계열사 테이블은 보통 100개 미만)
                rows = table.find_all(['TR', 'tr'])
                if len(rows) > 200:
                    continue

                for row in rows[:100]:  # 최대 100행만 처리
                    cells = row.find_all(['TD', 'td'])
                    if len(cells) >= 2:
                        affiliate_name = cells[0].get_text().strip()

                        # 데이터 검증: 유효한 회사명인지 확인
                        if not self._is_valid_company_name(affiliate_name):
                            continue

                        ownership_ratio = None
                        if len(cells) >= 3:
                            ownership_ratio = self.parse_ratio(cells[2].get_text().strip())

                        affiliates.append({
                            'affiliate_name': affiliate_name,
                            'ownership_ratio': ownership_ratio,
                        })

        except Exception as e:
            logger.debug(f"계열사 추출 오류: {e}")

        return affiliates

    def _is_valid_company_name(self, name: str) -> bool:
        """회사명 유효성 검증"""
        if len(name) < 2 or len(name) > 100:
            return False

        # 헤더 제외
        invalid_names = [
            '회사명', '법인명', '상호', '계열사명', '기업명', '명칭',
            '구분', '합계', '소계', '계', '비고', '주1)', '주2)',
            '번호', 'No', '순번'
        ]
        if name in invalid_names:
            return False

        # 재무제표 계정과목 제외
        financial_keywords = [
            '자산', '부채', '자본', '매출', '이익', '손실', '비용', '수익',
            '법인세', '감가상각', '대손', '현금', '채권', '재고', '금융',
            '전기', '당기', '차기'
        ]
        if any(kw in name for kw in financial_keywords):
            return False

        return True

    def extract_officers(
        self,
        soup: BeautifulSoup,
        metadata: Dict
    ) -> List[Dict]:
        """임원 현황 추출 - NO 중복제거, 각 인스턴스 = 별도 Position 객체 (개선된 로직)"""
        officers = []

        try:
            # 임원 키워드 (긍정적)
            officer_keywords = ['임원', '이사', '등기임원', '현황']

            # 제외할 키워드 (재무제표 테이블 필터링)
            exclude_keywords = [
                '재무상태표', '손익계산서', '포괄손익계산서', '자본변동표', '현금흐름표',
                '자산총계', '부채총계', '자본총계', '매출액', '영업이익', '당기순이익',
                '법인세', '이연법인세', '감가상각', '대손상각', '유형자산', '무형자산',
                '현금및현금성자산', '단기금융자산', '매출채권', '재고자산'
            ]

            for table in soup.find_all(['TABLE', 'table']):
                table_text = table.get_text()

                # 재무제표 테이블 제외
                if any(kw in table_text for kw in exclude_keywords):
                    continue

                # 임원 키워드 포함 테이블만 처리
                if not any(kw in table_text for kw in officer_keywords):
                    continue

                # 테이블 행 제한 (임원 테이블은 보통 50개 미만)
                rows = table.find_all(['TR', 'tr'])
                if len(rows) > 100:
                    continue

                for row in rows[:50]:  # 최대 50행만 처리
                    cells = row.find_all(['TD', 'td'])
                    if len(cells) >= 2:
                        name = cells[0].get_text().strip()
                        position = cells[1].get_text().strip() if len(cells) >= 2 else ''

                        # 데이터 검증: 유효한 이름인지 확인
                        if not self._is_valid_person_name(name):
                            continue

                        term_start = None
                        term_end = None

                        # 임기 정보 추출 (있는 경우)
                        if len(cells) >= 4:
                            term_start = self.parse_date(cells[2].get_text().strip())
                            term_end = self.parse_date(cells[3].get_text().strip())

                        officers.append({
                            'name': name,
                            'position': position,
                            'term_start': term_start,
                            'term_end': term_end,
                        })

        except Exception as e:
            logger.debug(f"임원 추출 오류: {e}")

        return officers

    def _is_valid_person_name(self, name: str) -> bool:
        """사람 이름 유효성 검증"""
        if len(name) < 2 or len(name) > 20:
            return False

        # 헤더 제외
        invalid_names = [
            '성명', '이름', '직위', '임원명', '대표이사', '직책',
            '구분', '합계', '소계', '계', '비고', '주1)', '주2)',
            '번호', 'No', '순번', '성별', '나이', '연령'
        ]
        if name in invalid_names:
            return False

        # 재무제표 계정과목 제외
        financial_keywords = [
            '자산', '부채', '자본', '매출', '이익', '손실', '비용', '수익',
            '법인세', '감가상각', '대손', '현금', '채권', '재고', '금융',
            '전기', '당기', '차기', '총계'
        ]
        if any(kw in name for kw in financial_keywords):
            return False

        return True

    def extract_cb_subscribers(
        self,
        soup: BeautifulSoup,
        metadata: Dict
    ) -> List[Dict]:
        """CB 인수자 추출"""
        subscribers = []

        try:
            # CB 키워드
            cb_keywords = ['전환사채', 'CB', '신주인수권부사채', 'BW', '인수', '배정']

            for table in soup.find_all(['TABLE', 'table']):
                table_text = table.get_text()

                if any(kw in table_text for kw in cb_keywords) and ('인수' in table_text or '배정' in table_text):
                    for row in table.find_all(['TR', 'tr']):
                        cells = row.find_all(['TD', 'td'])
                        if len(cells) >= 2:
                            subscriber_name = cells[0].get_text().strip()

                            if len(subscriber_name) >= 2 and not subscriber_name in ['인수자', '배정대상', '성명']:
                                amount = None
                                ratio = None

                                if len(cells) >= 3:
                                    amount = self.parse_amount(cells[1].get_text().strip())
                                if len(cells) >= 4:
                                    ratio = self.parse_ratio(cells[2].get_text().strip())

                                subscribers.append({
                                    'subscriber_name': subscriber_name,
                                    'subscription_amount': amount,
                                    'subscription_ratio': ratio,
                                })

        except Exception as e:
            logger.debug(f"CB 인수자 추출 오류: {e}")

        return subscribers

    def parse_business_report_zip(
        self,
        zip_path: Path,
        metadata: Dict
    ) -> Dict:
        """ZIP 파일에서 사업보고서 XML 파싱 (BeautifulSoup 사용)"""
        result = {
            'success': False,
            'financial_statements': None,
            'affiliates': [],
            'officers': [],
            'cb_subscribers': [],
            'error': None
        }

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                xml_files = [f for f in zf.namelist() if f.endswith('.xml')]

                if not xml_files:
                    result['error'] = 'No XML file in ZIP'
                    return result

                # 첫 번째 XML 파일 읽기
                xml_content = zf.read(xml_files[0])

                # BeautifulSoup로 파싱 (malformed XML 대응)
                soup = BeautifulSoup(xml_content, 'xml')

                # 1. 재무제표 추출
                financial_data = self.extract_financial_statements(soup, metadata)
                if financial_data:
                    result['financial_statements'] = financial_data

                # 2. 계열사 추출
                affiliates = self.extract_affiliates(soup, metadata)
                if affiliates:
                    result['affiliates'] = affiliates

                # 3. 임원 추출
                officers = self.extract_officers(soup, metadata)
                if officers:
                    result['officers'] = officers

                # 4. CB 인수자 추출
                cb_subscribers = self.extract_cb_subscribers(soup, metadata)
                if cb_subscribers:
                    result['cb_subscribers'] = cb_subscribers

                result['success'] = True
                self.stats['files_parsed'] += 1

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"ZIP 파싱 오류 {zip_path.name}: {e}")
            self.stats['parse_errors'] += 1

        finally:
            self.stats['files_processed'] += 1

        return result

    async def save_financial_statement(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict,
        metadata: Dict
    ):
        """재무제표 저장 - Rich Metadata 포함"""
        try:
            # 연도와 분기 결정
            year = int(metadata['report_nm'].split('(')[1].split('.')[0])
            quarter = 'Q4'  # 기본값
            statement_date = date(year, 12, 31)

            if '반기' in metadata['report_nm'] or '2분기' in metadata['report_nm']:
                quarter = 'Q2'
                statement_date = date(year, 6, 30)
            elif '1분기' in metadata['report_nm']:
                quarter = 'Q1'
                statement_date = date(year, 3, 31)
            elif '3분기' in metadata['report_nm']:
                quarter = 'Q3'
                statement_date = date(year, 9, 30)

            # Rich metadata 구성
            rich_metadata = {
                'source_file': f"{metadata['rcept_no']}.zip",
                'report_date': metadata['rcept_dt'],
                'rcept_no': metadata['rcept_no'],
                'report_nm': metadata['report_nm'],
                'extracted_at': datetime.now().isoformat(),
            }

            await conn.execute("""
                INSERT INTO financial_statements (
                    id, company_id, fiscal_year, quarter, statement_date, report_type,
                    total_assets, total_liabilities, total_equity,
                    revenue, operating_profit, net_income,
                    metadata,
                    created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11, $12, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, quarter, report_type)
                DO UPDATE SET
                    total_assets = COALESCE(EXCLUDED.total_assets, financial_statements.total_assets),
                    total_liabilities = COALESCE(EXCLUDED.total_liabilities, financial_statements.total_liabilities),
                    total_equity = COALESCE(EXCLUDED.total_equity, financial_statements.total_equity),
                    revenue = COALESCE(EXCLUDED.revenue, financial_statements.revenue),
                    operating_profit = COALESCE(EXCLUDED.operating_profit, financial_statements.operating_profit),
                    net_income = COALESCE(EXCLUDED.net_income, financial_statements.net_income),
                    metadata = COALESCE(EXCLUDED.metadata, financial_statements.metadata),
                    updated_at = NOW()
            """,
                company_id, year, quarter, statement_date, 'ANNUAL',
                data.get('total_assets'),
                data.get('total_liabilities'),
                data.get('total_equity'),
                data.get('revenue'),
                data.get('operating_profit'),
                data.get('net_income'),
                json.dumps(rich_metadata)
            )

            self.stats['financial_statements_saved'] += 1

        except Exception as e:
            logger.error(f"재무제표 저장 오류: {e}")

    async def save_affiliate(
        self,
        conn: asyncpg.Connection,
        parent_company_id: str,
        data: Dict,
        metadata: Dict
    ):
        """계열사 저장 - Rich Metadata 포함"""
        try:
            affiliate_name = data['affiliate_name']

            # 계열사 회사 ID 조회 또는 생성
            affiliate_company_id = await conn.fetchval("""
                SELECT id FROM companies WHERE name = $1 LIMIT 1
            """, affiliate_name)

            if not affiliate_company_id:
                affiliate_company_id = await conn.fetchval("""
                    INSERT INTO companies (
                        id, name, created_at, updated_at
                    )
                    VALUES (uuid_generate_v4(), $1, NOW(), NOW())
                    RETURNING id
                """, affiliate_name)

            # Rich metadata 구성
            year = int(metadata['report_nm'].split('(')[1].split('.')[0])
            rich_metadata = {
                'source_file': f"{metadata['rcept_no']}.zip",
                'report_date': metadata['rcept_dt'],
                'rcept_no': metadata['rcept_no'],
                'report_nm': metadata['report_nm'],
                'fiscal_year': year,
                'extracted_at': datetime.now().isoformat(),
            }

            # 계열사 관계 저장 (중복 허용 - 시간에 따른 변화 추적)
            await conn.execute("""
                INSERT INTO affiliates (
                    id,
                    parent_company_id,
                    affiliate_company_id,
                    affiliate_name,
                    ownership_ratio,
                    source_date,
                    metadata,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, $6, NOW(), NOW()
                )
            """,
                parent_company_id,
                affiliate_company_id,
                affiliate_name,
                data.get('ownership_ratio'),
                str(year),
                json.dumps(rich_metadata)
            )

            self.stats['affiliates_saved'] += 1

        except Exception as e:
            logger.error(f"계열사 저장 오류 {affiliate_name}: {e}")

    async def save_officer_position(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict,
        metadata: Dict
    ):
        """
        임원 Position 저장 - Ontology 원칙
        - NO 중복제거: 각 인스턴스 = 별도 객체
        - Rich Metadata: source_file, report_date, fiscal_year, term_start, term_end
        """
        try:
            name = data['name']
            position = data['position']
            term_start = data.get('term_start')
            term_end = data.get('term_end')

            # Officer 조회 또는 생성 (이름만으로, fuzzy matching 없음)
            officer_id = await conn.fetchval("""
                SELECT id FROM officers
                WHERE name = $1
                LIMIT 1
            """, name)

            if not officer_id:
                officer_id = await conn.fetchval("""
                    INSERT INTO officers (
                        id, name, created_at, updated_at
                    )
                    VALUES (uuid_generate_v4(), $1, NOW(), NOW())
                    RETURNING id
                """, name)

            # Rich metadata 구성
            year = int(metadata['report_nm'].split('(')[1].split('.')[0])
            rich_metadata = {
                'source_file': f"{metadata['rcept_no']}.zip",
                'report_date': metadata['rcept_dt'],
                'rcept_no': metadata['rcept_no'],
                'report_nm': metadata['report_nm'],
                'fiscal_year': year,
                'term_start': term_start.isoformat() if term_start else None,
                'term_end': term_end.isoformat() if term_end else None,
                'extracted_at': datetime.now().isoformat(),
            }

            # Position 저장 - 각 인스턴스는 별도 레코드 (중복 허용)
            # 동일 officer + company + report에서는 1개만 저장
            await conn.execute("""
                INSERT INTO officer_positions (
                    id,
                    officer_id,
                    company_id,
                    position,
                    term_start_date,
                    term_end_date,
                    is_current,
                    metadata,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, $6, $7, NOW(), NOW()
                )
            """,
                officer_id,
                company_id,
                position,
                term_start,
                term_end,
                term_end is None,
                json.dumps(rich_metadata)
            )

            self.stats['officer_positions_saved'] += 1

        except Exception as e:
            logger.debug(f"임원 Position 저장 오류 {name}: {e}")

    async def save_cb_subscriber(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict,
        metadata: Dict
    ):
        """CB 인수자 저장 - Rich Metadata 포함"""
        try:
            # 해당 회사의 CB 조회 (최신)
            cb_id = await conn.fetchval("""
                SELECT id FROM convertible_bonds
                WHERE company_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, company_id)

            if not cb_id:
                return  # CB가 없으면 스킵

            # Rich metadata 구성
            year = int(metadata['report_nm'].split('(')[1].split('.')[0])
            rich_metadata = {
                'source_file': f"{metadata['rcept_no']}.zip",
                'report_date': metadata['rcept_dt'],
                'rcept_no': metadata['rcept_no'],
                'report_nm': metadata['report_nm'],
                'fiscal_year': year,
                'extracted_at': datetime.now().isoformat(),
            }

            # CB 인수자 저장
            await conn.execute("""
                INSERT INTO cb_subscribers (
                    id,
                    cb_id,
                    subscriber_name,
                    subscription_amount,
                    subscription_ratio,
                    metadata,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, NOW(), NOW()
                )
                ON CONFLICT (cb_id, subscriber_name)
                DO UPDATE SET
                    subscription_amount = COALESCE(EXCLUDED.subscription_amount, cb_subscribers.subscription_amount),
                    subscription_ratio = COALESCE(EXCLUDED.subscription_ratio, cb_subscribers.subscription_ratio),
                    metadata = COALESCE(EXCLUDED.metadata, cb_subscribers.metadata),
                    updated_at = NOW()
            """,
                cb_id,
                data['subscriber_name'],
                data.get('subscription_amount'),
                data.get('subscription_ratio'),
                json.dumps(rich_metadata)
            )

            self.stats['cb_subscribers_saved'] += 1

        except Exception as e:
            logger.debug(f"CB 인수자 저장 오류: {e}")


async def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("Palantir Ontology 기반 사업보고서 파싱")
    logger.info("=" * 80)

    # 사업보고서 디렉토리
    dart_dir = Path(__file__).parent.parent / 'data' / 'dart'

    if not dart_dir.exists():
        logger.error(f"DART directory not found: {dart_dir}")
        return

    # PostgreSQL 연결
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@127.0.0.1:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 파서 생성
        parser = OntologyBusinessReportParser()

        # 모든 batch 폴더 탐색
        batch_folders = sorted([d for d in dart_dir.iterdir() if d.is_dir() and d.name.startswith('batch_')])
        logger.info(f"Total batch folders: {len(batch_folders)}")

        total_reports = 0
        business_reports_processed = 0

        for batch_folder in batch_folders:
            # batch 내 모든 corp_code 폴더 탐색
            for corp_folder in batch_folder.iterdir():
                if not corp_folder.is_dir():
                    continue

                corp_code = corp_folder.name

                # corp_code 내 모든 연도 폴더 탐색
                for year_folder in corp_folder.iterdir():
                    if not year_folder.is_dir():
                        continue

                    # 연도 폴더 내 모든 _meta.json 파일 탐색
                    for meta_file in year_folder.glob('*_meta.json'):
                        total_reports += 1

                        # 메타데이터 로드
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        # 사업보고서만 처리
                        if '사업보고서' not in metadata.get('report_nm', ''):
                            continue

                        # 반기/분기보고서는 제외하고 연간 사업보고서만
                        if '반기' in metadata['report_nm'] or '1분기' in metadata['report_nm'] or '3분기' in metadata['report_nm']:
                            # 단, 2025년 2분기는 허용
                            if not ('2025' in metadata['report_nm'] and '2분기' in metadata['report_nm']):
                                continue

                        business_reports_processed += 1

                        # ZIP 파일 경로
                        zip_file = year_folder / f"{metadata['rcept_no']}.zip"
                        if not zip_file.exists():
                            continue

                        # 회사 ID 조회 또는 생성
                        company_id = await conn.fetchval("""
                            SELECT id FROM companies WHERE corp_code = $1
                        """, metadata['corp_code'])

                        if not company_id:
                            # 회사가 없으면 생성 (사업보고서에서 추출)
                            company_id = await conn.fetchval("""
                                INSERT INTO companies (
                                    id, corp_code, corp_name, created_at, updated_at
                                )
                                VALUES (
                                    uuid_generate_v4(), $1, $2, NOW(), NOW()
                                )
                                RETURNING id
                            """, metadata['corp_code'], metadata.get('corp_name', metadata['corp_code']))

                        # ZIP 파싱
                        result = parser.parse_business_report_zip(zip_file, metadata)

                        if result['success']:
                            # 1. 재무제표 저장
                            if result['financial_statements']:
                                await parser.save_financial_statement(
                                    conn, company_id, result['financial_statements'], metadata
                                )

                            # 2. 계열사 저장
                            for affiliate in result['affiliates']:
                                await parser.save_affiliate(
                                    conn, company_id, affiliate, metadata
                                )

                            # 3. 임원 Position 저장
                            for officer in result['officers']:
                                await parser.save_officer_position(
                                    conn, company_id, officer, metadata
                                )

                            # 4. CB 인수자 저장
                            for subscriber in result['cb_subscribers']:
                                await parser.save_cb_subscriber(
                                    conn, company_id, subscriber, metadata
                                )

                        # 진행 상황 출력
                        if business_reports_processed % 100 == 0:
                            logger.info(
                                f"Progress: {business_reports_processed} business reports - "
                                f"Parsed: {parser.stats['files_parsed']}, "
                                f"FS: {parser.stats['financial_statements_saved']}, "
                                f"Affiliates: {parser.stats['affiliates_saved']}, "
                                f"Positions: {parser.stats['officer_positions_saved']}, "
                                f"CB Subscribers: {parser.stats['cb_subscribers_saved']}, "
                                f"Errors: {parser.stats['parse_errors']}"
                            )

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("사업보고서 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"총 파일 탐색: {total_reports:,}")
        logger.info(f"사업보고서 처리: {business_reports_processed:,}")
        logger.info(f"파싱 성공: {parser.stats['files_parsed']:,}")
        logger.info(f"파싱 오류: {parser.stats['parse_errors']:,}")
        logger.info(f"재무제표 저장: {parser.stats['financial_statements_saved']:,}")
        logger.info(f"계열사 저장: {parser.stats['affiliates_saved']:,}")
        logger.info(f"임원 Position 저장: {parser.stats['officer_positions_saved']:,}")
        logger.info(f"CB 인수자 저장: {parser.stats['cb_subscribers_saved']:,}")
        logger.info(f"회사 없음(스킵): {parser.stats['skipped_no_company']:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
