#!/usr/bin/env python3
"""
2025년 3분기보고서 파싱 스크립트

다운로드된 3분기보고서 XML에서 재무 데이터를 추출하여 financial_details 테이블에 저장합니다.
현금흐름표 데이터(영업CF, 투자CF, CAPEX 등)가 핵심입니다.

사용법:
    python scripts/parse_q3_reports_2025.py --sample 10  # 10개 회사만 테스트
    python scripts/parse_q3_reports_2025.py              # 전체 실행
"""
import asyncio
import asyncpg
import argparse
import json
import logging
import os
import re
import sys
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)
Q3_REPORTS_DIR = Path(__file__).parent.parent / 'data' / 'q3_reports_2025'


class Q3ReportParser:
    """2025년 3분기보고서 파서"""

    # 계정과목 매핑 (parse_local_financial_details.py와 동일)
    ACCOUNT_MAPPING = {
        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 유동자산
        # ═══════════════════════════════════════════════════════════════
        'current_assets': ['유동자산', '유동자산합계', 'Ⅰ.유동자산'],
        'cash_and_equivalents': [
            '현금및현금성자산', '현금및현금등가물', '현금 및 현금성자산',
            'Ⅰ.현금및현금성자산', '1.현금및현금성자산'
        ],
        'short_term_investments': ['단기금융상품', '단기금융자산', '단기투자자산'],
        'trade_and_other_receivables': [
            '매출채권및기타채권', '매출채권 및 기타채권', '매출채권'
        ],
        'inventories': ['재고자산', '재고자산(순액)', '상품및제품'],
        'other_financial_assets_current': [
            '기타금융자산', '기타유동금융자산', '기타 금융자산',
            '기타유동금융자산(유동)', '금융자산(유동)',
            '기타포괄손익공정가치측정금융자산', '상각후원가측정금융자산',
            '기타의금융자산', '기타금융자산(유동)', '유동기타금융자산',
            '기타의 금융자산', '단기기타금융자산', '기타 유동금융자산',
            '파생상품자산', '매매목적파생상품자산'
        ],
        'other_assets_current': [
            '기타자산', '기타유동자산', '기타 유동자산',
            '선급금', '선급비용', '기타자산(유동)',
            '기타의자산', '기타 자산', '유동기타자산',
            '선급금및선급비용', '선급금 및 선급비용', '선급금등',
            '기타의 자산', '단기기타자산', '선납세금',
            '계약자산', '기타의유동자산'
        ],
        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 비유동자산
        # ═══════════════════════════════════════════════════════════════
        'non_current_assets': ['비유동자산', '비유동자산합계', 'Ⅱ.비유동자산'],
        'fvpl_financial_assets': [
            '당기손익공정가치측정금융자산', '당기손익-공정가치측정금융자산',
            '당기손익인식금융자산', 'FVPL금융자산', '당기손익공정가치금융자산',
            '장기금융상품'
        ],
        'investments_in_associates': [
            '관계기업투자', '관계기업투자주식', '관계기업 및 공동기업투자',
            '관계기업에 대한 투자', '지분법적용투자주식', '관계기업투자자산'
        ],
        'tangible_assets': ['유형자산', '유형자산(순액)', 'Ⅱ.유형자산'],
        'intangible_assets': ['무형자산', '무형자산(순액)', 'Ⅲ.무형자산'],
        'right_of_use_assets': [
            '사용권자산', '사용권 자산', '리스사용권자산',
            '사용권자산(리스)', '리스자산'
        ],
        'other_financial_assets_non_current': [
            '기타비유동금융자산', '기타금융자산(비유동)', '장기금융자산',
            '기타 비유동금융자산', '비유동기타금융자산'
        ],
        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 자산/부채/자본 합계
        # ═══════════════════════════════════════════════════════════════
        'total_assets': ['자산총계', '자산 총계', '자산합계', '총자산'],
        'current_liabilities': ['유동부채', '유동부채합계', 'Ⅰ.유동부채'],
        'non_current_liabilities': ['비유동부채', '비유동부채합계', 'Ⅱ.비유동부채'],
        'total_liabilities': ['부채총계', '부채 총계', '부채합계'],
        'total_equity': ['자본총계', '자본 총계', '자본합계', '총자본'],

        # 손익계산서
        'revenue': ['매출액', '수익(매출액)', '영업수익', 'Ⅰ.매출액'],
        'cost_of_sales': ['매출원가', '영업비용', 'Ⅱ.매출원가'],
        'selling_admin_expenses': ['판매비와관리비', '판관비', 'Ⅲ.판매비와관리비'],
        'operating_income': ['영업이익', '영업이익(손실)', '영업손익'],
        'net_income': ['당기순이익', '분기순이익', '당기순이익(손실)'],

        # 현금흐름표 (핵심!)
        'operating_cash_flow': [
            '영업활동현금흐름', '영업활동으로인한현금흐름',
            '영업활동 현금흐름', 'Ⅰ.영업활동현금흐름',
            '영업활동으로 인한 현금흐름'
        ],
        'investing_cash_flow': [
            '투자활동현금흐름', '투자활동으로인한현금흐름',
            '투자활동 현금흐름', 'Ⅱ.투자활동현금흐름'
        ],
        'financing_cash_flow': [
            '재무활동현금흐름', '재무활동으로인한현금흐름',
            '재무활동 현금흐름', 'Ⅲ.재무활동현금흐름'
        ],
        'capex': [
            '유형자산의취득', '유형자산의 취득', '유형자산취득',
            '유형자산의 증가', '설비투자', '유형자산 취득으로 인한 현금유출',
            '유형자산의취득(자본적지출)'
        ],
        'intangible_acquisition': [
            '무형자산의취득', '무형자산의 취득', '무형자산취득'
        ],
        'dividend_paid': [
            '배당금지급', '배당금의지급', '배당금 지급',
            '현금배당금', '배당금지급액'
        ],
        'treasury_stock_acquisition': [
            '자기주식취득', '자기주식의취득', '자기주식 취득'
        ],
        'stock_issuance': ['주식발행', '유상증자', '신주발행'],
        'bond_issuance': ['사채발행', '사채의발행', '사채 발행'],
    }

    def __init__(self, data_dir: Path = Q3_REPORTS_DIR):
        self.data_dir = data_dir
        self.stats = {
            'total_files': 0,
            'parsed': 0,
            'saved': 0,
            'skipped': 0,
            'errors': 0
        }

    def find_q3_reports(self) -> List[Dict]:
        """다운로드된 3분기보고서 찾기"""
        reports = []

        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return reports

        for corp_dir in self.data_dir.iterdir():
            if not corp_dir.is_dir():
                continue

            corp_code = corp_dir.name

            for meta_file in corp_dir.glob('*_meta.json'):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    zip_file = meta_file.with_name(meta_file.name.replace('_meta.json', '.zip'))
                    if zip_file.exists():
                        reports.append({
                            'meta': meta,
                            'zip_path': zip_file,
                            'corp_code': corp_code
                        })
                except Exception as e:
                    logger.debug(f"Meta read error: {meta_file}: {e}")

        return reports

    def extract_xml_content(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 XML 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        raw_bytes = zf.read(name)
                        # 다중 인코딩 시도
                        for encoding in ['utf-8', 'euc-kr', 'cp949']:
                            try:
                                content = raw_bytes.decode(encoding)
                                if '재무' in content or '자산' in content:
                                    return content
                            except UnicodeDecodeError:
                                continue
                        return raw_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"ZIP extraction error: {zip_path}: {e}")
        return None

    def parse_financial_data(self, xml_content: str) -> Dict[str, Any]:
        """XML에서 재무 데이터 추출 (섹션별 단위 감지)"""
        result = {}

        # 재무상태표 섹션 추출 (먼저 - 현금 등 핵심 데이터)
        bs_section = self._extract_balance_sheet_section(xml_content)
        if bs_section:
            bs_unit = self._detect_unit_from_section(bs_section, 'bs')
            logger.debug(f"Balance sheet unit: {bs_unit}")
            bs_values = self._extract_values(bs_section, bs_unit)
            result.update(bs_values)
            logger.debug(f"Balance sheet values: {list(bs_values.keys())}")

        # 손익계산서 섹션 추출
        is_section = self._extract_income_statement_section(xml_content)
        if is_section:
            is_unit = self._detect_unit_from_section(is_section, 'is')
            logger.debug(f"Income statement unit: {is_unit}")
            is_values = self._extract_values(is_section, is_unit)
            for key, value in is_values.items():
                if key not in result:
                    result[key] = value
            logger.debug(f"Income statement values: {list(is_values.keys())}")

        # 현금흐름표 섹션 추출 (핵심!)
        cf_section = self._extract_cash_flow_section(xml_content)
        if cf_section:
            cf_unit = self._detect_unit_from_section(cf_section, 'cf')
            logger.debug(f"Cash flow unit: {cf_unit}")
            cf_values = self._extract_values(cf_section, cf_unit, is_cf=True)
            for key, value in cf_values.items():
                if key not in result:
                    result[key] = value
            logger.debug(f"Cash flow values: {list(cf_values.keys())}")

        # 데이터 검증: 현금이 음수이면 경고
        if result.get('cash_and_equivalents') and result['cash_and_equivalents'] < 0:
            logger.warning(f"Negative cash detected: {result['cash_and_equivalents']:,}")
            # 자산총계와 비교해서 비정상적으로 크면 단위 오류로 판단
            total_assets = result.get('total_assets', 0)
            if total_assets and abs(result['cash_and_equivalents']) > total_assets * 10:
                logger.warning(f"Cash seems to have wrong unit (cash={result['cash_and_equivalents']}, assets={total_assets})")
                # 단위 보정 시도하지 않음 (데이터 신뢰성 문제)

        return result

    def _extract_cash_flow_section(self, xml_content: str) -> Optional[str]:
        """현금흐름표 섹션 추출"""
        patterns = [
            r'<TITLE[^>]*>.*?현\s*금\s*흐\s*름\s*표.*?</TITLE>(.+?)(?=<TITLE|$)',
            r'<TITLE[^>]*>2-3\.\s*연결\s*현금흐름표</TITLE>(.+?)(?=<TITLE|$)',
            r'<TITLE[^>]*>4-3\.\s*현금흐름표</TITLE>(.+?)(?=<TITLE|$)',
            r'현\s*금\s*흐\s*름\s*표(.{5000,50000}?)(?=재\s*무\s*상\s*태\s*표|손\s*익\s*계\s*산\s*서|포\s*괄\s*손\s*익|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1) if match.lastindex else match.group(0)
                # 현금흐름 관련 키워드가 있는지 확인
                if '영업활동' in section or '투자활동' in section or '재무활동' in section:
                    return section

        return None

    def _extract_balance_sheet_section(self, xml_content: str) -> Optional[str]:
        """재무상태표 섹션 추출 (연결 우선)"""
        # 연결 재무상태표 우선 검색 (단위 포함 헤더까지)
        patterns = [
            # 연결 재무상태표 (우선)
            r'(<TITLE[^>]*>2-1\.\s*연결\s*재무상태표</TITLE>.+?)(?=<TITLE|$)',
            r'(<TITLE[^>]*>.*?연결\s*재\s*무\s*상\s*태\s*표.*?</TITLE>.+?)(?=<TITLE|$)',
            # 별도 재무상태표
            r'(<TITLE[^>]*>4-1\.\s*재무상태표</TITLE>.+?)(?=<TITLE|$)',
            r'(<TITLE[^>]*>.*?재\s*무\s*상\s*태\s*표.*?</TITLE>.+?)(?=<TITLE|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                # 자산총계가 있는지 확인 (재무상태표 맞는지 검증)
                if '자산총계' in section or '자산 총계' in section:
                    return section

        return None

    def _extract_income_statement_section(self, xml_content: str) -> Optional[str]:
        """손익계산서 섹션 추출"""
        patterns = [
            r'<TITLE[^>]*>.*?손\s*익\s*계\s*산\s*서.*?</TITLE>(.+?)(?=<TITLE|$)',
            r'<TITLE[^>]*>2-2\.\s*연결\s*손익계산서</TITLE>(.+?)(?=<TITLE|$)',
            r'<TITLE[^>]*>4-2\.\s*손익계산서</TITLE>(.+?)(?=<TITLE|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _detect_unit_from_section(self, section: str, section_type: str = 'bs') -> int:
        """섹션별 단위 감지 (개선된 버전)

        개선사항:
        1. 섹션 시작 부근에서만 단위 감지 (첫 2000자)
        2. 섹션별로 다른 단위 적용
        3. 다양한 단위 패턴 지원 (단위:, 단위 :, 단위;)
        """
        # 섹션 시작 부분만 검색 (2000자)
        search_area = section[:2000] if len(section) > 2000 else section

        # 백만원 패턴 (우선순위 높음)
        if re.search(r'단위\s*[:\s:;]\s*백만\s*원', search_area):
            logger.debug(f"Unit detected: 백만원 for {section_type}")
            return 1_000_000
        # 천원 패턴
        elif re.search(r'단위\s*[:\s:;]\s*천\s*원', search_area):
            logger.debug(f"Unit detected: 천원 for {section_type}")
            return 1_000
        # 원 패턴 (천원/백만원 아닌 경우)
        elif re.search(r'단위\s*[:\s:;]\s*원[^천백]', search_area) or re.search(r'단위\s*[:\s:;]\s*원\)', search_area):
            logger.debug(f"Unit detected: 원 for {section_type}")
            return 1

        # 기본값: 천원 (가장 일반적)
        logger.debug(f"Unit not detected, using default 천원 for {section_type}")
        return 1_000

    def _detect_unit(self, xml_content: str) -> int:
        """단위 감지 (레거시 호환용)"""
        return self._detect_unit_from_section(xml_content, 'default')

    def _extract_values(self, section: str, unit_multiplier: int, is_cf: bool = False) -> Dict[str, int]:
        """섹션에서 계정과목별 금액 추출"""
        values = {}

        # 태그 제거
        clean_text = re.sub(r'<[^>]+>', ' ', section)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        for field, aliases in self.ACCOUNT_MAPPING.items():
            for alias in aliases:
                # 공백 무시 패턴
                alias_pattern = r'\s*'.join(re.escape(c) for c in alias)
                pattern = rf'{alias_pattern}[^\d\-]*?([\-\(]?\d[\d,\.]*[\)]?)'

                matches = re.findall(pattern, clean_text, re.IGNORECASE)
                if matches:
                    amount = self._parse_amount(matches[0], unit_multiplier)
                    if amount is not None:
                        values[field] = amount
                        break

        # CAPEX는 음수로 저장 (현금 유출)
        if 'capex' in values and values['capex'] > 0:
            values['capex'] = -values['capex']

        return values

    def _parse_amount(self, amount_str: str, multiplier: int = 1) -> Optional[int]:
        """금액 문자열 파싱"""
        if not amount_str:
            return None

        try:
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()

            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('-'):
                is_negative = True
                cleaned = cleaned[1:]

            cleaned = re.sub(r'[^\d\.]', '', cleaned)
            if not cleaned:
                return None

            if '.' in cleaned:
                value = int(float(cleaned))
            else:
                value = int(cleaned)

            value = value * multiplier
            return -value if is_negative else value

        except (ValueError, TypeError):
            return None


class Q3FinancialDetailsCollector:
    """3분기보고서 데이터 수집 및 저장"""

    def __init__(self, db_url: str):
        self.db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.parser = Q3ReportParser()
        self.stats = {
            'companies': 0,
            'parsed': 0,
            'saved': 0,
            'errors': 0
        }

    async def get_company_by_corp_code(self, conn, corp_code: str) -> Optional[Dict]:
        """corp_code로 회사 조회"""
        row = await conn.fetchrow("""
            SELECT id, name, ticker, market
            FROM companies
            WHERE corp_code = $1
        """, corp_code)
        return dict(row) if row else None

    async def save_financial_details(self, conn, company_id: str, data: Dict) -> bool:
        """재무 데이터 저장"""
        try:
            await conn.execute("""
                INSERT INTO financial_details (
                    id, company_id, fiscal_year, fiscal_quarter, report_type,
                    current_assets, cash_and_equivalents, short_term_investments,
                    trade_and_other_receivables, inventories,
                    other_financial_assets_current, other_assets_current,
                    non_current_assets, fvpl_financial_assets, investments_in_associates,
                    tangible_assets, intangible_assets, right_of_use_assets,
                    other_financial_assets_non_current,
                    total_assets, current_liabilities, non_current_liabilities,
                    total_liabilities, total_equity,
                    revenue, cost_of_sales, selling_admin_expenses,
                    operating_income, net_income,
                    operating_cash_flow, investing_cash_flow, financing_cash_flow,
                    capex, intangible_acquisition, dividend_paid,
                    treasury_stock_acquisition, stock_issuance, bond_issuance,
                    fs_type, data_source, source_rcept_no, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), $1, $2, $3, $4,
                    $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18,
                    $19, $20, $21, $22, $23,
                    $24, $25, $26, $27, $28,
                    $29, $30, $31, $32, $33, $34, $35, $36, $37,
                    $38, $39, $40, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, fiscal_quarter, fs_type)
                DO UPDATE SET
                    current_assets = COALESCE(EXCLUDED.current_assets, financial_details.current_assets),
                    cash_and_equivalents = COALESCE(EXCLUDED.cash_and_equivalents, financial_details.cash_and_equivalents),
                    short_term_investments = COALESCE(EXCLUDED.short_term_investments, financial_details.short_term_investments),
                    trade_and_other_receivables = COALESCE(EXCLUDED.trade_and_other_receivables, financial_details.trade_and_other_receivables),
                    inventories = COALESCE(EXCLUDED.inventories, financial_details.inventories),
                    other_financial_assets_current = COALESCE(EXCLUDED.other_financial_assets_current, financial_details.other_financial_assets_current),
                    other_assets_current = COALESCE(EXCLUDED.other_assets_current, financial_details.other_assets_current),
                    non_current_assets = COALESCE(EXCLUDED.non_current_assets, financial_details.non_current_assets),
                    fvpl_financial_assets = COALESCE(EXCLUDED.fvpl_financial_assets, financial_details.fvpl_financial_assets),
                    investments_in_associates = COALESCE(EXCLUDED.investments_in_associates, financial_details.investments_in_associates),
                    tangible_assets = COALESCE(EXCLUDED.tangible_assets, financial_details.tangible_assets),
                    intangible_assets = COALESCE(EXCLUDED.intangible_assets, financial_details.intangible_assets),
                    right_of_use_assets = COALESCE(EXCLUDED.right_of_use_assets, financial_details.right_of_use_assets),
                    other_financial_assets_non_current = COALESCE(EXCLUDED.other_financial_assets_non_current, financial_details.other_financial_assets_non_current),
                    total_assets = COALESCE(EXCLUDED.total_assets, financial_details.total_assets),
                    current_liabilities = COALESCE(EXCLUDED.current_liabilities, financial_details.current_liabilities),
                    non_current_liabilities = COALESCE(EXCLUDED.non_current_liabilities, financial_details.non_current_liabilities),
                    total_liabilities = COALESCE(EXCLUDED.total_liabilities, financial_details.total_liabilities),
                    total_equity = COALESCE(EXCLUDED.total_equity, financial_details.total_equity),
                    revenue = COALESCE(EXCLUDED.revenue, financial_details.revenue),
                    cost_of_sales = COALESCE(EXCLUDED.cost_of_sales, financial_details.cost_of_sales),
                    selling_admin_expenses = COALESCE(EXCLUDED.selling_admin_expenses, financial_details.selling_admin_expenses),
                    operating_income = COALESCE(EXCLUDED.operating_income, financial_details.operating_income),
                    net_income = COALESCE(EXCLUDED.net_income, financial_details.net_income),
                    operating_cash_flow = COALESCE(EXCLUDED.operating_cash_flow, financial_details.operating_cash_flow),
                    investing_cash_flow = COALESCE(EXCLUDED.investing_cash_flow, financial_details.investing_cash_flow),
                    financing_cash_flow = COALESCE(EXCLUDED.financing_cash_flow, financial_details.financing_cash_flow),
                    capex = COALESCE(EXCLUDED.capex, financial_details.capex),
                    intangible_acquisition = COALESCE(EXCLUDED.intangible_acquisition, financial_details.intangible_acquisition),
                    dividend_paid = COALESCE(EXCLUDED.dividend_paid, financial_details.dividend_paid),
                    treasury_stock_acquisition = COALESCE(EXCLUDED.treasury_stock_acquisition, financial_details.treasury_stock_acquisition),
                    stock_issuance = COALESCE(EXCLUDED.stock_issuance, financial_details.stock_issuance),
                    bond_issuance = COALESCE(EXCLUDED.bond_issuance, financial_details.bond_issuance),
                    updated_at = NOW()
            """,
                uuid.UUID(company_id),
                data.get('fiscal_year', 2025),
                data.get('fiscal_quarter', 3),  # 3분기
                data.get('report_type', 'q3'),
                # 재무상태표 - 유동자산
                data.get('current_assets'),
                data.get('cash_and_equivalents'),
                data.get('short_term_investments'),
                data.get('trade_and_other_receivables'),
                data.get('inventories'),
                data.get('other_financial_assets_current'),  # NEW
                data.get('other_assets_current'),  # NEW
                # 재무상태표 - 비유동자산
                data.get('non_current_assets'),
                data.get('fvpl_financial_assets'),  # NEW
                data.get('investments_in_associates'),  # NEW
                data.get('tangible_assets'),
                data.get('intangible_assets'),
                data.get('right_of_use_assets'),  # NEW
                data.get('other_financial_assets_non_current'),  # NEW
                # 재무상태표 - 합계
                data.get('total_assets'),
                data.get('current_liabilities'),
                data.get('non_current_liabilities'),
                data.get('total_liabilities'),
                data.get('total_equity'),
                # 손익계산서
                data.get('revenue'),
                data.get('cost_of_sales'),
                data.get('selling_admin_expenses'),
                data.get('operating_income'),
                data.get('net_income'),
                # 현금흐름표
                data.get('operating_cash_flow'),
                data.get('investing_cash_flow'),
                data.get('financing_cash_flow'),
                data.get('capex'),
                data.get('intangible_acquisition'),
                data.get('dividend_paid'),
                data.get('treasury_stock_acquisition'),
                data.get('stock_issuance'),
                data.get('bond_issuance'),
                # 메타
                data.get('fs_type', 'CFS'),
                'LOCAL_Q3_2025',
                data.get('source_rcept_no')
            )
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    async def run(self, limit: Optional[int] = None):
        """전체 파싱 실행"""
        conn = await asyncpg.connect(self.db_url)

        try:
            # 1. 3분기보고서 찾기
            reports = self.parser.find_q3_reports()
            if limit:
                reports = reports[:limit]

            self.stats['companies'] = len(reports)

            logger.info("=" * 80)
            logger.info("2025년 3분기보고서 파싱 시작")
            logger.info("=" * 80)
            logger.info(f"대상 보고서: {len(reports)}개")
            logger.info("=" * 80)

            # 2. 파싱 및 저장
            for i, report in enumerate(reports, 1):
                try:
                    corp_code = report['corp_code']
                    meta = report['meta']

                    # 회사 정보 조회
                    company = await self.get_company_by_corp_code(conn, corp_code)
                    if not company:
                        logger.debug(f"Company not found: {corp_code}")
                        continue

                    # XML 추출 및 파싱
                    xml_content = self.parser.extract_xml_content(report['zip_path'])
                    if not xml_content:
                        self.stats['errors'] += 1
                        continue

                    data = self.parser.parse_financial_data(xml_content)
                    if not data:
                        self.stats['errors'] += 1
                        continue

                    self.stats['parsed'] += 1

                    # 추가 메타데이터
                    data['fiscal_year'] = 2025
                    data['fiscal_quarter'] = 3
                    data['report_type'] = 'q3'
                    data['fs_type'] = 'CFS'  # 연결재무제표 우선
                    data['source_rcept_no'] = meta.get('rcept_no')

                    # 저장
                    success = await self.save_financial_details(
                        conn, str(company['id']), data
                    )
                    if success:
                        self.stats['saved'] += 1
                        has_cf = 'operating_cash_flow' in data and data['operating_cash_flow'] is not None
                        has_capex = 'capex' in data and data['capex'] is not None
                        logger.info(
                            f"[{i}/{len(reports)}] {company['name']}: "
                            f"OCF={'✓' if has_cf else '✗'}, "
                            f"CAPEX={'✓' if has_capex else '✗'}"
                        )

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing {report.get('corp_code')}: {e}")

                # 진행 상황
                if i % 100 == 0:
                    logger.info(
                        f"Progress: {i}/{len(reports)} - "
                        f"Parsed: {self.stats['parsed']}, "
                        f"Saved: {self.stats['saved']}, "
                        f"Errors: {self.stats['errors']}"
                    )

            # 3. 결과 출력
            logger.info("=" * 80)
            logger.info("파싱 완료")
            logger.info("=" * 80)
            logger.info(f"대상: {self.stats['companies']}개")
            logger.info(f"파싱: {self.stats['parsed']}건")
            logger.info(f"저장: {self.stats['saved']}건")
            logger.info(f"오류: {self.stats['errors']}건")
            logger.info("=" * 80)

        finally:
            await conn.close()


async def verify_results():
    """결과 검증"""
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 2025년 3분기 데이터 확인
        result = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN operating_cash_flow IS NOT NULL THEN 1 ELSE 0 END) as ocf_cnt,
                SUM(CASE WHEN capex IS NOT NULL THEN 1 ELSE 0 END) as capex_cnt,
                SUM(CASE WHEN dividend_paid IS NOT NULL THEN 1 ELSE 0 END) as div_cnt
            FROM financial_details
            WHERE fiscal_year = 2025 AND fiscal_quarter = 3
        """)

        logger.info("\n[2025년 3분기 데이터 현황]")
        if result:
            logger.info(f"  총 레코드: {result['total']:,}건")
            logger.info(f"  영업현금흐름: {result['ocf_cnt']:,}건")
            logger.info(f"  CAPEX: {result['capex_cnt']:,}건")
            logger.info(f"  배당금: {result['div_cnt']:,}건")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='2025년 3분기보고서 파싱')
    parser.add_argument('--sample', type=int, help='샘플 회사 수')
    parser.add_argument('--verify-only', action='store_true', help='결과 검증만')

    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_results())
        return

    collector = Q3FinancialDetailsCollector(DATABASE_URL)
    asyncio.run(collector.run(limit=args.sample))
    asyncio.run(verify_results())


if __name__ == "__main__":
    main()
