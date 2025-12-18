#!/usr/bin/env python3
"""
사업보고서 엔터프라이즈 파서
- 재무제표 (Financial Statements)
- 계열사 현황 (Affiliates)
- 임원 현황 (Officers)
- CB 인수자 (CB Subscribers)
"""
import asyncio
import asyncpg
import logging
import sys
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnterpriseBusinessReportParser:
    """엔터프라이즈급 사업보고서 파서"""

    # 임원 직책 정규화 매핑
    POSITION_NORMALIZE = {
        '대표이사': '대표이사',
        '대표': '대표이사',
        'CEO': '대표이사',
        'Chief Executive Officer': '대표이사',
        '전무이사': '전무이사',
        '전무': '전무이사',
        '상무이사': '상무이사',
        '상무': '상무이사',
        '이사': '이사',
        '감사': '감사',
        '사외이사': '사외이사',
        '기타비상무이사': '기타비상무이사',
        '사내이사': '사내이사',
    }

    # 재무제표 계정과목 매핑
    ACCOUNT_MAPPING = {
        '자산총계': 'total_assets',
        '자산 총계': 'total_assets',
        '자산총액': 'total_assets',
        '부채총계': 'total_liabilities',
        '부채 총계': 'total_liabilities',
        '부채총액': 'total_liabilities',
        '자본총계': 'total_equity',
        '자본 총계': 'total_equity',
        '자본총액': 'total_equity',
        '매출액': 'revenue',
        '수익(매출액)': 'revenue',
        '영업수익': 'revenue',
        '영업이익': 'operating_profit',
        '영업이익(손실)': 'operating_profit',
        '당기순이익': 'net_income',
        '당기순이익(손실)': 'net_income',
        '분기순이익': 'net_income',
    }

    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'files_parsed': 0,
            'parse_errors': 0,
            'financial_statements_extracted': 0,
            'affiliates_extracted': 0,
            'officers_extracted': 0,
            'cb_subscribers_extracted': 0,
        }

    def normalize_position(self, position: str) -> str:
        """직책 정규화"""
        if not position:
            return '기타'

        position = position.strip()

        # 정확히 매칭되는 경우
        if position in self.POSITION_NORMALIZE:
            return self.POSITION_NORMALIZE[position]

        # 부분 매칭
        for key, value in self.POSITION_NORMALIZE.items():
            if key in position:
                return value

        return position

    def fuzzy_match_name(self, name1: str, name2: str, threshold: float = 0.85) -> bool:
        """이름 유사도 매칭 (85% 임계값)"""
        if not name1 or not name2:
            return False

        ratio = SequenceMatcher(None, name1, name2).ratio()
        return ratio >= threshold

    def parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 문자열 파싱 (백만원 단위 → 원 단위)"""
        if not amount_str or amount_str.strip() in ['-', '', 'N/A']:
            return None

        try:
            # 쉼표 제거
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()

            # 괄호 제거 (음수 표시)
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]

            # 숫자만 추출
            match = re.search(r'[-+]?\d+\.?\d*', cleaned)
            if match:
                value = float(match.group())
                # 백만원 단위를 원 단위로 변환
                value = int(value * 1000000)
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

    def extract_text_from_element(self, element, default: str = '') -> str:
        """XML 요소에서 텍스트 추출"""
        if element is None:
            return default

        text = element.text if element.text else default
        return text.strip()

    def parse_financial_statements(self, root: ET.Element, year: int, report_type: str) -> Optional[Dict]:
        """
        재무제표 데이터 추출

        사업보고서 XML 구조:
        - 재무제표는 <TABLE> 태그로 표현
        - 계정과목: <ACCOUNT_NM>
        - 금액: <THSTRM_AMOUNT> (당기), <FRMTRM_AMOUNT> (전기)
        """
        financial_data = {}

        try:
            # 재무상태표 (대차대조표) 섹션 찾기
            # 여러 가능한 섹션 제목
            fs_keywords = [
                '재무상태표',
                '대차대조표',
                '연결재무상태표',
                '개별재무상태표'
            ]

            # 손익계산서 섹션 찾기
            pl_keywords = [
                '손익계산서',
                '포괄손익계산서',
                '연결손익계산서',
                '개별손익계산서'
            ]

            # 모든 테이블 탐색
            for table in root.findall('.//TABLE'):
                table_name = self.extract_text_from_element(table.find('TABLE_NM'))

                # 재무상태표 데이터 추출
                if any(keyword in table_name for keyword in fs_keywords):
                    for row in table.findall('.//ROW'):
                        account_nm = self.extract_text_from_element(row.find('ACCOUNT_NM'))
                        amount = self.extract_text_from_element(row.find('THSTRM_AMOUNT'))

                        # 계정과목 매핑
                        for key, field in self.ACCOUNT_MAPPING.items():
                            if key in account_nm:
                                parsed_amount = self.parse_amount(amount)
                                if parsed_amount is not None:
                                    financial_data[field] = parsed_amount
                                break

                # 손익계산서 데이터 추출
                elif any(keyword in table_name for keyword in pl_keywords):
                    for row in table.findall('.//ROW'):
                        account_nm = self.extract_text_from_element(row.find('ACCOUNT_NM'))
                        amount = self.extract_text_from_element(row.find('THSTRM_AMOUNT'))

                        # 계정과목 매핑
                        for key, field in self.ACCOUNT_MAPPING.items():
                            if key in account_nm:
                                parsed_amount = self.parse_amount(amount)
                                if parsed_amount is not None:
                                    financial_data[field] = parsed_amount
                                break

            # 최소한의 데이터가 있는지 확인
            if len(financial_data) >= 2:
                # 분기 설정
                if report_type == '11011':
                    quarter = 'Q4'
                    statement_date = date(year, 12, 31)
                elif report_type == '11012':
                    quarter = 'Q2'
                    statement_date = date(year, 6, 30)
                else:
                    quarter = 'Q4'
                    statement_date = date(year, 12, 31)

                financial_data['fiscal_year'] = year
                financial_data['quarter'] = quarter
                financial_data['statement_date'] = statement_date
                financial_data['report_type'] = 'ANNUAL' if report_type == '11011' else 'QUARTERLY'

                return financial_data

            return None

        except Exception as e:
            logger.debug(f"Error parsing financial statements: {e}")
            return None

    def parse_affiliates(self, root: ET.Element) -> List[Dict]:
        """
        계열사 현황 데이터 추출

        사업보고서 XML 구조:
        - 계열회사 현황 섹션
        - 계열사명, 사업자등록번호, 지분율, 의결권비율 등
        """
        affiliates = []

        try:
            # 계열회사 현황 섹션 찾기
            affiliate_keywords = [
                '계열회사',
                '계열사',
                '종속회사',
                '관계회사'
            ]

            for table in root.findall('.//TABLE'):
                table_name = self.extract_text_from_element(table.find('TABLE_NM'))

                if any(keyword in table_name for keyword in affiliate_keywords):
                    for row in table.findall('.//ROW'):
                        # 계열사명
                        affiliate_name_elem = row.find('.//AFLT_NM')
                        if affiliate_name_elem is None:
                            affiliate_name_elem = row.find('.//COMPANY_NM')
                        if affiliate_name_elem is None:
                            continue

                        affiliate_name = self.extract_text_from_element(affiliate_name_elem)
                        if not affiliate_name or len(affiliate_name) < 2:
                            continue

                        # 사업자등록번호
                        bsns_no = self.extract_text_from_element(row.find('.//BSNS_NO'))

                        # 지분율
                        ownership_elem = row.find('.//H_RATE')
                        if ownership_elem is None:
                            ownership_elem = row.find('.//OWNERSHIP_RATIO')
                        ownership_ratio = self.parse_ratio(
                            self.extract_text_from_element(ownership_elem)
                        )

                        # 의결권비율
                        voting_elem = row.find('.//VOTE_RATE')
                        if voting_elem is None:
                            voting_elem = row.find('.//VOTING_RIGHTS')
                        voting_rights = self.parse_ratio(
                            self.extract_text_from_element(voting_elem)
                        )

                        # 상장여부
                        lst_yn_elem = row.find('.//LST_YN')
                        is_listed = False
                        if lst_yn_elem is not None:
                            lst_yn = self.extract_text_from_element(lst_yn_elem)
                            is_listed = lst_yn.upper() in ['Y', 'YES', '상장']

                        # 계열사 구분
                        relationship_type = self.extract_text_from_element(row.find('.//AFLT_GBN'))

                        # 총자산
                        total_assets = self.parse_amount(
                            self.extract_text_from_element(row.find('.//TOT_ASET'))
                        )

                        # 매출액
                        revenue = self.parse_amount(
                            self.extract_text_from_element(row.find('.//REVENUE'))
                        )

                        # 당기순이익
                        net_income = self.parse_amount(
                            self.extract_text_from_element(row.find('.//NET_INCOME'))
                        )

                        affiliates.append({
                            'affiliate_name': affiliate_name,
                            'business_number': bsns_no if bsns_no else None,
                            'relationship_type': relationship_type if relationship_type else None,
                            'is_listed': is_listed,
                            'ownership_ratio': ownership_ratio,
                            'voting_rights_ratio': voting_rights,
                            'total_assets': total_assets,
                            'revenue': revenue,
                            'net_income': net_income,
                        })

        except Exception as e:
            logger.debug(f"Error parsing affiliates: {e}")

        return affiliates

    def parse_officers(self, root: ET.Element) -> List[Dict]:
        """
        임원 현황 데이터 추출

        사업보고서 XML 구조:
        - 임원 현황 섹션
        - 성명, 직책, 등기임원여부, 상근여부, 담당업무 등
        """
        officers = []

        try:
            # 임원 현황 섹션 찾기
            officer_keywords = [
                '임원',
                '이사',
                '등기임원'
            ]

            for table in root.findall('.//TABLE'):
                table_name = self.extract_text_from_element(table.find('TABLE_NM'))

                if any(keyword in table_name for keyword in officer_keywords):
                    for row in table.findall('.//ROW'):
                        # 성명
                        name_elem = row.find('.//NAME')
                        if name_elem is None:
                            name_elem = row.find('.//OFFICER_NM')
                        if name_elem is None:
                            continue

                        name = self.extract_text_from_element(name_elem)
                        if not name or len(name) < 2:
                            continue

                        # 직책
                        position_elem = row.find('.//POSITION')
                        if position_elem is None:
                            position_elem = row.find('.//OFFICE')
                        position = self.extract_text_from_element(position_elem)
                        normalized_position = self.normalize_position(position)

                        # 등기임원 여부
                        registered_elem = row.find('.//RGST_YN')
                        is_registered = False
                        if registered_elem is not None:
                            rgst_yn = self.extract_text_from_element(registered_elem)
                            is_registered = rgst_yn.upper() in ['Y', 'YES', '등기']

                        # 상근 여부
                        fulltime_elem = row.find('.//FTIME_YN')
                        is_fulltime = False
                        if fulltime_elem is not None:
                            ftime_yn = self.extract_text_from_element(fulltime_elem)
                            is_fulltime = ftime_yn.upper() in ['Y', 'YES', '상근']

                        # 담당업무
                        duty = self.extract_text_from_element(row.find('.//DUTY'))

                        # 취임일
                        term_start_elem = row.find('.//APPOINT_DT')
                        if term_start_elem is None:
                            term_start_elem = row.find('.//TERM_START')
                        term_start = self.extract_text_from_element(term_start_elem)

                        # 임기만료일
                        term_end_elem = row.find('.//TERM_END_DT')
                        if term_end_elem is None:
                            term_end_elem = row.find('.//TERM_END')
                        term_end = self.extract_text_from_element(term_end_elem)

                        officers.append({
                            'name': name,
                            'position': position,
                            'normalized_position': normalized_position,
                            'is_registered': is_registered,
                            'is_fulltime': is_fulltime,
                            'duty': duty if duty else None,
                            'term_start': term_start if term_start else None,
                            'term_end': term_end if term_end else None,
                        })

        except Exception as e:
            logger.debug(f"Error parsing officers: {e}")

        return officers

    def parse_cb_subscribers(self, root: ET.Element) -> List[Dict]:
        """
        전환사채 인수자 데이터 추출

        사업보고서 XML 구조:
        - 전환사채 발행 및 인수 현황 섹션
        - 인수자명, 인수금액, 인수비율 등
        """
        subscribers = []

        try:
            # CB 인수 섹션 찾기
            cb_keywords = [
                '전환사채',
                'CB',
                '신주인수권부사채',
                'BW'
            ]

            for table in root.findall('.//TABLE'):
                table_name = self.extract_text_from_element(table.find('TABLE_NM'))

                if any(keyword in table_name for keyword in cb_keywords):
                    # 인수자 정보가 있는지 확인
                    if '인수' in table_name or '배정' in table_name:
                        for row in table.findall('.//ROW'):
                            # 인수자명
                            subscriber_name_elem = row.find('.//SUBSCRIBER_NM')
                            if subscriber_name_elem is None:
                                subscriber_name_elem = row.find('.//INVESTOR_NM')
                            if subscriber_name_elem is None:
                                continue

                            subscriber_name = self.extract_text_from_element(subscriber_name_elem)
                            if not subscriber_name or len(subscriber_name) < 2:
                                continue

                            # 인수금액
                            amount_elem = row.find('.//SUBSCRIPTION_AMOUNT')
                            if amount_elem is None:
                                amount_elem = row.find('.//AMOUNT')
                            subscription_amount = self.parse_amount(
                                self.extract_text_from_element(amount_elem)
                            )

                            # 인수비율
                            ratio_elem = row.find('.//SUBSCRIPTION_RATIO')
                            if ratio_elem is None:
                                ratio_elem = row.find('.//RATIO')
                            subscription_ratio = self.parse_ratio(
                                self.extract_text_from_element(ratio_elem)
                            )

                            # 관계
                            relationship_elem = row.find('.//RELATIONSHIP')
                            relationship = self.extract_text_from_element(relationship_elem)

                            subscribers.append({
                                'subscriber_name': subscriber_name,
                                'subscription_amount': subscription_amount,
                                'subscription_ratio': subscription_ratio,
                                'relationship': relationship if relationship else None,
                            })

        except Exception as e:
            logger.debug(f"Error parsing CB subscribers: {e}")

        return subscribers

    def parse_business_report(
        self,
        file_path: Path,
        corp_code: str,
        corp_name: str,
        year: int,
        report_type: str
    ) -> Dict:
        """사업보고서 XML 파일 파싱"""
        result = {
            'success': False,
            'financial_statements': None,
            'affiliates': [],
            'officers': [],
            'cb_subscribers': [],
            'error': None
        }

        try:
            # XML 파싱
            tree = ET.parse(file_path)
            root = tree.getroot()

            # 1. 재무제표 추출
            financial_data = self.parse_financial_statements(root, year, report_type)
            if financial_data:
                result['financial_statements'] = financial_data
                self.stats['financial_statements_extracted'] += 1

            # 2. 계열사 추출
            affiliates = self.parse_affiliates(root)
            if affiliates:
                result['affiliates'] = affiliates
                self.stats['affiliates_extracted'] += len(affiliates)

            # 3. 임원 추출
            officers = self.parse_officers(root)
            if officers:
                result['officers'] = officers
                self.stats['officers_extracted'] += len(officers)

            # 4. CB 인수자 추출
            cb_subscribers = self.parse_cb_subscribers(root)
            if cb_subscribers:
                result['cb_subscribers'] = cb_subscribers
                self.stats['cb_subscribers_extracted'] += len(cb_subscribers)

            result['success'] = True
            self.stats['files_parsed'] += 1

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error parsing {file_path.name}: {e}")
            self.stats['parse_errors'] += 1

        finally:
            self.stats['files_processed'] += 1

        return result

    async def get_or_create_officer(
        self,
        conn: asyncpg.Connection,
        name: str,
        company_id: str,
        position: str
    ) -> Tuple[str, bool]:
        """임원 조회 또는 생성 (fuzzy matching 포함)"""
        # 1. 정확한 매칭 시도
        officer_id = await conn.fetchval("""
            SELECT id FROM officers
            WHERE name = $1 AND current_company_id = $2
        """, name, company_id)

        if officer_id:
            return str(officer_id), False

        # 2. 같은 회사 내 유사 이름 검색
        similar_officers = await conn.fetch("""
            SELECT id, name FROM officers
            WHERE current_company_id = $1
        """, company_id)

        for officer in similar_officers:
            if self.fuzzy_match_name(name, officer['name']):
                return str(officer['id']), False

        # 3. 새 임원 생성
        officer_id = await conn.fetchval("""
            INSERT INTO officers (
                id, name, position, current_company_id, created_at, updated_at
            )
            VALUES (uuid_generate_v4(), $1, $2, $3, NOW(), NOW())
            RETURNING id
        """, name, position, company_id)

        return str(officer_id), True

    async def save_financial_statement(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict
    ):
        """재무제표 데이터 저장"""
        try:
            await conn.execute("""
                INSERT INTO financial_statements (
                    id, company_id, fiscal_year, quarter, statement_date, report_type,
                    total_assets, total_liabilities, total_equity,
                    revenue, operating_profit, net_income,
                    created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11,
                    NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, quarter, report_type)
                DO UPDATE SET
                    total_assets = EXCLUDED.total_assets,
                    total_liabilities = EXCLUDED.total_liabilities,
                    total_equity = EXCLUDED.total_equity,
                    revenue = EXCLUDED.revenue,
                    operating_profit = EXCLUDED.operating_profit,
                    net_income = EXCLUDED.net_income,
                    updated_at = NOW()
            """,
                company_id,
                data['fiscal_year'],
                data['quarter'],
                data['statement_date'],
                data['report_type'],
                data.get('total_assets'),
                data.get('total_liabilities'),
                data.get('total_equity'),
                data.get('revenue'),
                data.get('operating_profit'),
                data.get('net_income')
            )
        except Exception as e:
            logger.error(f"Error saving financial statement: {e}")

    async def save_affiliate(
        self,
        conn: asyncpg.Connection,
        parent_company_id: str,
        data: Dict,
        source_year: int
    ):
        """계열사 데이터 저장"""
        try:
            affiliate_name = data['affiliate_name']

            # 계열사 회사 ID 조회 또는 생성
            affiliate_company_id = await conn.fetchval("""
                SELECT id FROM companies WHERE name = $1
            """, affiliate_name)

            if not affiliate_company_id:
                affiliate_company_id = await conn.fetchval("""
                    INSERT INTO companies (
                        id, name, created_at, updated_at
                    )
                    VALUES (uuid_generate_v4(), $1, NOW(), NOW())
                    RETURNING id
                """, affiliate_name)

            # 계열사 관계 저장
            await conn.execute("""
                INSERT INTO affiliates (
                    id,
                    parent_company_id,
                    affiliate_company_id,
                    affiliate_name,
                    business_number,
                    relationship_type,
                    is_listed,
                    ownership_ratio,
                    voting_rights_ratio,
                    total_assets,
                    revenue,
                    net_income,
                    source_date,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW()
                )
                ON CONFLICT (parent_company_id, affiliate_company_id)
                DO UPDATE SET
                    affiliate_name = EXCLUDED.affiliate_name,
                    business_number = EXCLUDED.business_number,
                    relationship_type = EXCLUDED.relationship_type,
                    is_listed = EXCLUDED.is_listed,
                    ownership_ratio = EXCLUDED.ownership_ratio,
                    voting_rights_ratio = EXCLUDED.voting_rights_ratio,
                    total_assets = EXCLUDED.total_assets,
                    revenue = EXCLUDED.revenue,
                    net_income = EXCLUDED.net_income,
                    source_date = EXCLUDED.source_date,
                    updated_at = NOW()
            """,
                parent_company_id,
                affiliate_company_id,
                affiliate_name,
                data.get('business_number'),
                data.get('relationship_type'),
                data.get('is_listed', False),
                data.get('ownership_ratio'),
                data.get('voting_rights_ratio'),
                data.get('total_assets'),
                data.get('revenue'),
                data.get('net_income'),
                str(source_year)
            )
        except Exception as e:
            logger.error(f"Error saving affiliate {data['affiliate_name']}: {e}")

    async def save_officer(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict,
        source_year: int
    ):
        """임원 데이터 저장"""
        try:
            # 임원 조회 또는 생성
            officer_id, created = await self.get_or_create_officer(
                conn,
                data['name'],
                company_id,
                data['normalized_position']
            )

            # 임원 직책 이력 저장 (사업보고서 기반)
            # term_start 파싱
            term_start_date = None
            if data.get('term_start'):
                try:
                    # YYYYMMDD 형식 파싱
                    term_start_str = data['term_start'].replace('-', '').replace('.', '').strip()
                    if len(term_start_str) == 8:
                        term_start_date = datetime.strptime(term_start_str, '%Y%m%d').date()
                except:
                    pass

            # term_end 파싱
            term_end_date = None
            if data.get('term_end'):
                try:
                    term_end_str = data['term_end'].replace('-', '').replace('.', '').strip()
                    if len(term_end_str) == 8:
                        term_end_date = datetime.strptime(term_end_str, '%Y%m%d').date()
                except:
                    pass

            # 직책 이력 저장
            await conn.execute("""
                INSERT INTO officer_positions (
                    id,
                    officer_id,
                    company_id,
                    position,
                    term_start_date,
                    term_end_date,
                    is_current,
                    source_type,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, $6, 'business_report', NOW(), NOW()
                )
                ON CONFLICT (officer_id, company_id, COALESCE(term_start_date, '1900-01-01'::date), COALESCE(source_disclosure_id, '00000000-0000-0000-0000-000000000000'::uuid))
                DO UPDATE SET
                    position = EXCLUDED.position,
                    term_end_date = EXCLUDED.term_end_date,
                    is_current = EXCLUDED.is_current,
                    updated_at = NOW()
            """,
                officer_id,
                company_id,
                data['normalized_position'],
                term_start_date,
                term_end_date,
                term_end_date is None
            )
        except Exception as e:
            logger.error(f"Error saving officer {data['name']}: {e}")

    async def save_cb_subscriber(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        data: Dict,
        source_year: int
    ):
        """CB 인수자 데이터 저장"""
        try:
            # CB 조회 (해당 연도, 해당 회사)
            cb_id = await conn.fetchval("""
                SELECT id FROM convertible_bonds
                WHERE company_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, company_id)

            if not cb_id:
                logger.debug(f"No CB found for company {company_id}")
                return

            # CB 인수자 저장
            await conn.execute("""
                INSERT INTO cb_subscribers (
                    id,
                    cb_id,
                    subscriber_name,
                    subscriber_type,
                    subscription_amount,
                    subscription_ratio,
                    relationship,
                    created_at,
                    updated_at
                )
                VALUES (
                    uuid_generate_v4(),
                    $1, $2, $3, $4, $5, $6, NOW(), NOW()
                )
                ON CONFLICT (cb_id, subscriber_name)
                DO UPDATE SET
                    subscription_amount = EXCLUDED.subscription_amount,
                    subscription_ratio = EXCLUDED.subscription_ratio,
                    relationship = EXCLUDED.relationship,
                    updated_at = NOW()
            """,
                cb_id,
                data['subscriber_name'],
                None,  # subscriber_type는 별도 로직으로 판단
                data.get('subscription_amount'),
                data.get('subscription_ratio'),
                data.get('relationship')
            )
        except Exception as e:
            logger.error(f"Error saving CB subscriber {data['subscriber_name']}: {e}")


async def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("사업보고서 엔터프라이즈 파싱")
    logger.info("=" * 80)

    # 사업보고서 디렉토리
    reports_dir = Path(__file__).parent.parent / 'data' / 'business_reports'

    if not reports_dir.exists():
        logger.error(f"Business reports directory not found: {reports_dir}")
        return

    # 메타데이터 로드
    metadata_file = reports_dir / 'business_reports_metadata.json'
    if not metadata_file.exists():
        logger.error(f"Metadata file not found: {metadata_file}")
        return

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    logger.info(f"Total business reports: {len(metadata)}")

    # PostgreSQL 연결
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 파서 생성
        parser = EnterpriseBusinessReportParser()

        # 모든 사업보고서 파싱
        for i, (key, meta) in enumerate(metadata.items()):
            file_path = reports_dir / meta['filename']

            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            # 파싱
            result = parser.parse_business_report(
                file_path,
                meta['corp_code'],
                meta['corp_name'],
                meta['year'],
                meta['report_type']
            )

            if result['success']:
                # 회사 ID 조회
                company_id = await conn.fetchval("""
                    SELECT id FROM companies WHERE corp_code = $1
                """, meta['corp_code'])

                if not company_id:
                    logger.warning(f"Company not found: {meta['corp_name']} ({meta['corp_code']})")
                    continue

                # 1. 재무제표 저장
                if result['financial_statements']:
                    await parser.save_financial_statement(
                        conn, company_id, result['financial_statements']
                    )

                # 2. 계열사 저장
                for affiliate in result['affiliates']:
                    await parser.save_affiliate(
                        conn, company_id, affiliate, meta['year']
                    )

                # 3. 임원 저장
                for officer in result['officers']:
                    await parser.save_officer(
                        conn, company_id, officer, meta['year']
                    )

                # 4. CB 인수자 저장
                for subscriber in result['cb_subscribers']:
                    await parser.save_cb_subscriber(
                        conn, company_id, subscriber, meta['year']
                    )

            # 진행 상황 출력
            if (i + 1) % 100 == 0:
                logger.info(
                    f"Progress: {i + 1}/{len(metadata)} - "
                    f"Parsed: {parser.stats['files_parsed']}, "
                    f"FS: {parser.stats['financial_statements_extracted']}, "
                    f"Affiliates: {parser.stats['affiliates_extracted']}, "
                    f"Officers: {parser.stats['officers_extracted']}, "
                    f"CB Subscribers: {parser.stats['cb_subscribers_extracted']}, "
                    f"Errors: {parser.stats['parse_errors']}"
                )

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("사업보고서 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 파일: {parser.stats['files_processed']:,}")
        logger.info(f"파싱 성공: {parser.stats['files_parsed']:,}")
        logger.info(f"파싱 오류: {parser.stats['parse_errors']:,}")
        logger.info(f"재무제표 추출: {parser.stats['financial_statements_extracted']:,}")
        logger.info(f"계열사 추출: {parser.stats['affiliates_extracted']:,}")
        logger.info(f"임원 추출: {parser.stats['officers_extracted']:,}")
        logger.info(f"CB 인수자 추출: {parser.stats['cb_subscribers_extracted']:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
