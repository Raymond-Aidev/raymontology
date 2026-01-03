#!/usr/bin/env python3
"""
로컬 DART XML에서 재무 데이터 추출 - RaymondsIndex용

data/dart/ 폴더의 사업보고서 XML에서 financial_details 테이블에 필요한 데이터 파싱:
- 재무상태표: 현금, 자산, 부채, 자본
- 손익계산서: 매출, 영업이익, 순이익
- 현금흐름표: 영업CF, 투자CF, CAPEX, 배당금 (핵심)

사용법:
    python scripts/parse_local_financial_details.py --sample 10  # 10개 회사만 테스트
    python scripts/parse_local_financial_details.py              # 전체 실행
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
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
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
DART_DATA_DIR = Path(__file__).parent.parent / 'data' / 'dart'


class LocalDARTFinancialParser:
    """로컬 DART XML 재무제표 파서"""

    # 계정과목 매핑 (한글 계정명 -> 필드명)
    ACCOUNT_MAPPING = {
        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 유동자산 (Current Assets)
        # ═══════════════════════════════════════════════════════════════
        'current_assets': [
            '유동자산', '유동자산합계', '유동자산 합계',
            'Ⅰ.유동자산', 'I.유동자산', '1.유동자산'
        ],
        'cash_and_equivalents': [
            '현금및현금성자산', '현금및현금등가물', '현금 및 현금성자산',
            'Ⅰ.현금및현금성자산', '1.현금및현금성자산', '현금과현금성자산',
            'I. 현금및현금성자산', '현금및 현금성자산'
        ],
        'short_term_investments': [
            '단기금융상품', '단기금융자산', '단기투자자산',
            '유동금융자산', '단기 금융상품'
        ],
        'trade_and_other_receivables': [
            '매출채권및기타채권', '매출채권 및 기타채권', '매출채권및기타유동채권',
            '매출채권 및 기타유동채권', '매출채권', '단기매출채권'
        ],
        'inventories': [
            '재고자산', '재고자산(순액)', '상품및제품',
            '재고 자산', '유동재고자산'
        ],
        'current_tax_assets': [
            '당기법인세자산', '당기법인세 자산', '미수법인세',
            '법인세자산', '당기법인세환급자산'
        ],
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
        # 재무상태표 - 비유동자산 (Non-Current Assets)
        # ═══════════════════════════════════════════════════════════════
        'non_current_assets': [
            '비유동자산', '비유동자산합계', '비유동자산 합계',
            'Ⅱ.비유동자산', 'II.비유동자산', '2.비유동자산'
        ],
        'fvpl_financial_assets': [
            '당기손익공정가치측정금융자산', '당기손익-공정가치측정금융자산',
            '당기손익인식금융자산', 'FVPL금융자산', '당기손익공정가치금융자산'
        ],
        'investments_in_associates': [
            '관계기업투자', '관계기업투자주식', '관계기업 및 공동기업투자',
            '관계기업에 대한 투자', '지분법적용투자주식', '관계기업투자자산'
        ],
        'tangible_assets': [
            '유형자산', '유형자산(순액)', '토지,건물및기계장치',
            '유형 자산', '비유동유형자산', 'Ⅱ.유형자산'
        ],
        'intangible_assets': [
            '무형자산', '무형자산(순액)', '기타무형자산',
            '무형 자산', 'Ⅲ.무형자산', '영업권및무형자산'
        ],
        'right_of_use_assets': [
            '사용권자산', '사용권 자산', '리스사용권자산',
            '사용권자산(리스)', '리스자산'
        ],
        'net_defined_benefit_assets': [
            '순확정급여자산', '확정급여자산', '퇴직급여자산',
            '순확정급여자산(부채)', '확정급여제도자산'
        ],
        'deferred_tax_assets': [
            '이연법인세자산', '이연법인세 자산', '이연세금자산',
            '이연법인세자산(비유동)'
        ],
        'other_financial_assets_non_current': [
            '기타비유동금융자산', '기타금융자산(비유동)', '장기금융자산',
            '기타 비유동금융자산', '비유동기타금융자산'
        ],
        'other_assets_non_current': [
            '기타비유동자산', '기타자산(비유동)', '기타 비유동자산',
            '장기선급금', '장기선급비용'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 자산총계
        # ═══════════════════════════════════════════════════════════════
        'total_assets': [
            '자산총계', '자산 총계', '자산합계',
            '총자산', '합계(자산)', '자 산 총 계'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 - 부채/자본
        # ═══════════════════════════════════════════════════════════════
        'current_liabilities': [
            '유동부채', '유동부채합계', '유동부채 합계',
            'Ⅰ.유동부채', '1.유동부채', 'I.유동부채'
        ],
        'non_current_liabilities': [
            '비유동부채', '비유동부채합계', '비유동부채 합계',
            'Ⅱ.비유동부채', '2.비유동부채', 'II.비유동부채'
        ],
        'total_liabilities': [
            '부채총계', '부채 총계', '부채합계',
            '총부채', '합계(부채)', '부 채 총 계'
        ],
        'total_equity': [
            '자본총계', '자본 총계', '자본합계',
            '총자본', '합계(자본)', '자기자본', '자 본 총 계'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 손익계산서 (Income Statement)
        # ═══════════════════════════════════════════════════════════════
        'revenue': [
            '매출액', '수익(매출액)', '영업수익',
            '매출', '영업매출', '매출수익', '영 업 수 익',
            'Ⅰ.매출액', 'I.매출액', '1.매출액'
        ],
        'cost_of_sales': [
            '매출원가', '영업비용', '매출비용',
            '상품매출원가', '제품매출원가', '매 출 원 가',
            'Ⅱ.매출원가', 'II.매출원가', '2.매출원가'
        ],
        'selling_admin_expenses': [
            '판매비와관리비', '판관비', '판매관리비',
            '판매비', '관리비', '판매비및관리비',
            'Ⅲ.판매비와관리비', 'III.판매비와관리비'
        ],
        'operating_income': [
            '영업이익', '영업이익(손실)', '영업손익',
            '사업이익', '영 업 이 익', '영업이익(손실)'
        ],
        'net_income': [
            '당기순이익', '분기순이익', '반기순이익',
            '당기순이익(손실)', '연결당기순이익', '당기순손익',
            '지배기업소유주지분순이익', '당 기 순 이 익'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 손익계산서 - v2.0 신규 항목 (R&D, 감가상각, 이자, 법인세)
        # ═══════════════════════════════════════════════════════════════
        'r_and_d_expense': [
            '연구개발비', '연구비', '개발비', '경상연구개발비',
            '연구및개발비', 'R&D비용', '연구개발관련비용',
            '경상개발비', '연구개발비용', '연구개발활동비'
        ],
        'depreciation_expense': [
            '감가상각비', '감가상각비용', '유형자산감가상각비',
            '사용권자산감가상각비', '무형자산상각비', '상각비',
            '감가상각및상각비', '감가상각비 및 상각비', '감가상각누계액'
        ],
        'interest_expense': [
            '이자비용', '금융비용', '이자지급', '차입금이자',
            '사채이자', '금융원가', '이자비용(금융비용)',
            '금융이자비용', '차입금이자비용'
        ],
        'tax_expense': [
            '법인세비용', '법인세', '소득세비용',
            '법인세비용(수익)', '당기법인세비용', '법인세등',
            '법인세비용(이익)', '계속사업법인세비용'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 현금흐름표 (Cash Flow Statement) - RaymondsIndex 핵심
        # ═══════════════════════════════════════════════════════════════
        'operating_cash_flow': [
            '영업활동현금흐름', '영업활동으로인한현금흐름',
            '영업활동 현금흐름', '영업활동 순현금흐름',
            'Ⅰ.영업활동현금흐름', 'I.영업활동현금흐름',
            '1.영업활동현금흐름', '영업활동으로 인한 현금흐름',
            '영업활동현금유입', '영업활동으로부터의현금흐름'
        ],
        'investing_cash_flow': [
            '투자활동현금흐름', '투자활동으로인한현금흐름',
            '투자활동 현금흐름', '투자활동 순현금흐름',
            'Ⅱ.투자활동현금흐름', 'II.투자활동현금흐름',
            '2.투자활동현금흐름', '투자활동으로 인한 현금흐름'
        ],
        'financing_cash_flow': [
            '재무활동현금흐름', '재무활동으로인한현금흐름',
            '재무활동 현금흐름', '재무활동 순현금흐름',
            'Ⅲ.재무활동현금흐름', 'III.재무활동현금흐름',
            '3.재무활동현금흐름', '재무활동으로 인한 현금흐름'
        ],
        'capex': [
            '유형자산의취득', '유형자산의 취득', '유형자산취득',
            '유형자산의 증가', '설비투자', '시설투자',
            '토지의취득', '건물의취득', '기계장치의취득',
            '유형자산 취득으로 인한 현금유출', '유형자산의취득(자본적지출)'
        ],
        'intangible_acquisition': [
            '무형자산의취득', '무형자산의 취득', '무형자산취득',
            '무형자산의 증가', '개발비의 증가', '무형자산 취득'
        ],
        'dividend_paid': [
            '배당금지급', '배당금의지급', '배당금 지급',
            '현금배당금', '현금배당금의지급', '배당금지급액',
            '배당금의 지급', '배당금 지급액'
        ],
        'treasury_stock_acquisition': [
            '자기주식취득', '자기주식의취득', '자기주식 취득',
            '자사주 취득', '자기주식의 취득', '자기주식취득(처분)'
        ],
        'stock_issuance': [
            '주식발행', '유상증자', '신주발행',
            '자본금의 증가', '주식의발행', '주식발행에 따른 현금유입'
        ],
        'bond_issuance': [
            '사채발행', '사채의발행', '사채 발행',
            '회사채발행', '전환사채발행', '교환사채발행', '사채의 발행'
        ],
    }

    def __init__(self, data_dir: Path = DART_DATA_DIR):
        self.data_dir = data_dir
        self.stats = {
            'total_files': 0,
            'parsed': 0,
            'saved': 0,
            'skipped': 0,
            'errors': 0
        }

    def find_business_reports(self, corp_code: str = None) -> List[Dict]:
        """사업보고서 파일 찾기"""
        reports = []

        for batch_dir in self.data_dir.iterdir():
            if not batch_dir.is_dir() or batch_dir.name.startswith('.'):
                continue

            for corp_dir in batch_dir.iterdir():
                if not corp_dir.is_dir():
                    continue

                if corp_code and corp_dir.name != corp_code:
                    continue

                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir():
                        continue

                    for meta_file in year_dir.glob('*_meta.json'):
                        try:
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                meta = json.load(f)

                            # 사업보고서만 필터링
                            report_nm = meta.get('report_nm', '')
                            if '사업보고서' in report_nm:
                                zip_file = meta_file.with_name(
                                    meta_file.name.replace('_meta.json', '.zip')
                                )
                                if zip_file.exists():
                                    reports.append({
                                        'meta': meta,
                                        'zip_path': zip_file,
                                        'year_dir': year_dir.name
                                    })
                        except Exception as e:
                            logger.debug(f"Meta read error: {meta_file}: {e}")

        return reports

    def extract_xml_content(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 사업보고서 XML 추출 (v2.0)

        ZIP에 여러 XML이 있을 수 있음:
        - 사업보고서 (ACODE=11011) - 우선
        - 감사보고서 (ACODE=00760)
        - 연결감사보고서 (ACODE=00761)

        사업보고서(11011)를 찾아서 반환, 없으면 가장 큰 XML 반환
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                xml_files = [n for n in zf.namelist() if n.endswith('.xml')]

                # 1. 사업보고서(11011) 찾기
                for name in xml_files:
                    raw_bytes = zf.read(name)
                    content = self._decode_xml(raw_bytes)
                    if content and 'ACODE="11011"' in content:
                        logger.debug(f"Found business report (11011): {name}")
                        return content

                # 2. 사업보고서가 없으면 가장 큰 XML 반환 (일반적으로 사업보고서가 가장 큼)
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

    def _decode_xml(self, raw_bytes: bytes) -> Optional[str]:
        """XML 바이트를 문자열로 디코딩 (다중 인코딩 지원)"""
        for encoding in ['utf-8', 'euc-kr', 'cp949']:
            try:
                content = raw_bytes.decode(encoding)
                if '재무' in content or '자산' in content or '부채' in content:
                    return content
            except UnicodeDecodeError:
                continue
        # 모두 실패시 utf-8 with replace
        return raw_bytes.decode('utf-8', errors='replace')

    def parse_financial_tables(self, xml_content: str) -> Dict[str, Dict[str, int]]:
        """XML에서 재무제표 테이블 파싱

        v2.0: 각 재무제표(재무상태표, 손익계산서, 현금흐름표)를 독립적으로 파싱
        - 각 섹션에서 해당 섹션의 단위를 개별 감지하여 적용
        - 요약재무정보(백만원)가 아닌 본문 재무제표(원/천원)에서 파싱

        요청사항: 재무상태표와 연결재무상태표 둘 다 있으면 재무상태표(별도) 사용
        """
        result = {}

        # 별도재무제표 우선 (OFS), 없으면 연결재무제표 (CFS)
        for fs_type in ['OFS', 'CFS']:
            if fs_type == 'CFS' and result:
                continue  # 별도 데이터가 있으면 연결은 스킵

            parsed = self._extract_values_from_all_statements(xml_content, fs_type)
            if parsed:
                result[fs_type] = parsed

        return result

    def _extract_values_from_all_statements(self, xml_content: str, fs_type: str = 'OFS') -> Dict[str, int]:
        """v2.0: 각 재무제표 섹션에서 독립적으로 값 추출

        핵심 개선:
        1. 재무상태표, 손익계산서, 현금흐름표를 각각 독립적으로 파싱
        2. 각 섹션의 단위를 개별 감지하여 적용 (요약재무정보 혼동 방지)
        3. 계정과목을 해당 섹션에서만 검색
        """
        values = {}

        # 재무제표 섹션 정의
        # (섹션 이름, TITLE 패턴들, 해당 섹션에서 추출할 필드들)
        statement_configs = [
            {
                'name': 'balance_sheet',  # 재무상태표
                'title_patterns': self._get_bs_title_patterns(fs_type),
                'fields': [
                    'current_assets', 'cash_and_equivalents', 'short_term_investments',
                    'trade_and_other_receivables', 'inventories', 'current_tax_assets',
                    'other_financial_assets_current', 'other_assets_current',
                    'non_current_assets', 'fvpl_financial_assets', 'investments_in_associates',
                    'tangible_assets', 'intangible_assets', 'right_of_use_assets',
                    'net_defined_benefit_assets', 'deferred_tax_assets',
                    'other_financial_assets_non_current', 'other_assets_non_current',
                    'total_assets', 'current_liabilities', 'trade_payables',
                    'short_term_borrowings', 'current_portion_long_term_debt',
                    'other_current_liabilities', 'current_tax_liabilities', 'provisions_current',
                    'non_current_liabilities', 'long_term_borrowings', 'bonds_payable',
                    'convertible_bonds', 'lease_liabilities', 'deferred_tax_liabilities',
                    'provisions_non_current', 'other_non_current_liabilities',
                    'total_liabilities', 'total_equity', 'capital_stock',
                    'capital_surplus', 'retained_earnings', 'treasury_stock'
                ]
            },
            {
                'name': 'income_statement',  # 손익계산서
                'title_patterns': self._get_is_title_patterns(fs_type),
                'fields': [
                    'revenue', 'cost_of_sales', 'selling_admin_expenses',
                    'operating_income', 'net_income',
                    'r_and_d_expense', 'depreciation_expense', 'interest_expense', 'tax_expense'
                ]
            },
            {
                'name': 'cash_flow',  # 현금흐름표
                'title_patterns': self._get_cf_title_patterns(fs_type),
                'fields': [
                    'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
                    'capex', 'intangible_acquisition', 'dividend_paid',
                    'treasury_stock_acquisition', 'stock_issuance', 'bond_issuance'
                ]
            }
        ]

        for config in statement_configs:
            section_content = self._extract_statement_section(xml_content, config['title_patterns'])

            if not section_content:
                logger.debug(f"No section found for {config['name']} ({fs_type})")
                continue

            # 해당 섹션에서 단위 감지 (섹션 내용 기반)
            unit_multiplier = self._detect_unit_from_content(section_content)
            logger.debug(f"{config['name']}: unit={unit_multiplier}")

            # 섹션 내 텍스트 추출 (태그 제거)
            clean_text = self._clean_xml_text(section_content)

            # 해당 섹션의 필드만 파싱
            for field in config['fields']:
                if field in values:
                    continue  # 이미 추출된 경우 스킵

                aliases = self.ACCOUNT_MAPPING.get(field, [])
                for alias in aliases:
                    # 공백 무시하고 검색
                    alias_pattern = r'\s*'.join(re.escape(c) for c in alias)
                    # v2.2: 주석번호 "(주숫자)" 형태 건너뛰기 - 큰 금액(최소 7자리 이상) 캡처
                    pattern = rf'{alias_pattern}(?:\s*\(주\d+\))?[^\d\-]*?([\-\(]?\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?[\)]?|[\-\(]?\d{{7,}}(?:\.\d+)?[\)]?)'

                    matches = re.findall(pattern, clean_text, re.IGNORECASE)
                    if matches:
                        # 첫 번째 매칭 값 사용 (당기)
                        amount = self._parse_amount(matches[0], unit_multiplier)
                        if amount is not None:
                            values[field] = amount
                            break

        return values

    def _get_bs_title_patterns(self, fs_type: str) -> List[str]:
        """재무상태표 TITLE 패턴 (공백 유연 처리)

        실제 TITLE 예시:
        - '2-1. 연결 재무상태표' (공백 있음)
        - '4-1. 재무상태표'
        """
        if fs_type == 'OFS':
            return [
                r'<TITLE[^>]*>4-1\.\s*재\s*무\s*상\s*태\s*표</TITLE>',
                r'<TITLE[^>]*>재\s*무\s*상\s*태\s*표</TITLE>',
            ]
        else:
            return [
                r'<TITLE[^>]*>2-1\.\s*연결\s*재\s*무\s*상\s*태\s*표</TITLE>',
                r'<TITLE[^>]*>연결\s*재\s*무\s*상\s*태\s*표</TITLE>',
                r'<TITLE[^>]*>2\.\s*연결\s*재무제표</TITLE>',  # 상위 섹션 전체 (v2.1)
            ]

    def _get_is_title_patterns(self, fs_type: str) -> List[str]:
        """손익계산서 TITLE 패턴 (공백 유연 처리)

        실제 TITLE 예시:
        - '2-2. 연결 손익계산서' (공백 있음)
        - '4-2. 손익계산서'
        """
        if fs_type == 'OFS':
            return [
                r'<TITLE[^>]*>4-2\.\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>4-2\.\s*포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',
            ]
        else:
            return [
                r'<TITLE[^>]*>2-2\.\s*연결\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>2-2\.\s*연결\s*포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',  # 2-2번도 포괄손익 가능
                r'<TITLE[^>]*>2-3\.\s*연결\s*포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>연결\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>연결\s*포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',
                r'<TITLE[^>]*>2\.\s*연결\s*재무제표</TITLE>',  # 상위 섹션 전체 (v2.1)
            ]

    def _get_cf_title_patterns(self, fs_type: str) -> List[str]:
        """현금흐름표 TITLE 패턴 (공백 유연 처리)

        실제 TITLE 예시:
        - '2-5. 연결 현금흐름표' (공백 있음)
        - '4-5. 현금흐름표'
        """
        if fs_type == 'OFS':
            return [
                r'<TITLE[^>]*>4-5\.\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                r'<TITLE[^>]*>현\s*금\s*흐\s*름\s*표</TITLE>',
            ]
        else:
            return [
                r'<TITLE[^>]*>2-5\.\s*연결\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                r'<TITLE[^>]*>연결\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                r'<TITLE[^>]*>2\.\s*연결\s*재무제표</TITLE>',  # 상위 섹션 전체 (v2.1)
            ]

    def _extract_statement_section(self, xml_content: str, title_patterns: List[str]) -> Optional[str]:
        """특정 재무제표 섹션 추출 (v2.2)

        개선:
        - "2. 연결재무제표" 같은 상위 섹션 패턴일 경우, 하위 재무제표 전체를 포함하도록
          "3. 연결재무제표 주석" 또는 "4. 재무제표" 전까지 추출
        """
        for pattern in title_patterns:
            # "2. 연결재무제표" 상위 섹션 패턴 확인
            is_parent_section = r'연결\s*재무제표</TITLE>' in pattern and '상태표' not in pattern

            if is_parent_section:
                # 상위 섹션: "3. 연결재무제표 주석" 또는 "4. 재무제표" 전까지 추출
                section_pattern = rf'({pattern})(.+?)(?=<TITLE[^>]*>\s*3\.\s*연결재무제표\s*주석|<TITLE[^>]*>\s*4\.\s*재무제표|$)'
            else:
                # 일반 하위 섹션: 다음 TITLE 까지
                section_pattern = rf'({pattern})(.+?)(?=<TITLE|$)'

            match = re.search(section_pattern, xml_content, re.DOTALL)
            if match:
                return match.group(2)
        return None

    def _detect_unit_from_content(self, section_content: str) -> int:
        """섹션 내용에서 단위 감지 (v2.0)

        우선순위:
        1. 섹션 앞부분의 (단위: 원/천원/백만원) 텍스트
        2. AUNIT 속성
        3. 기본값 1 (원)
        """
        # 섹션 앞부분 3000자에서 단위 찾기
        search_area = section_content[:3000]

        # 1. 텍스트 단위 패턴 (우선순위 순서: 백만원 > 천원 > 원)
        if re.search(r'\(단위\s*[:\s:]\s*백만\s*원\)', search_area):
            return 1_000_000
        elif re.search(r'\(단위\s*[:\s:]\s*천\s*원\)', search_area):
            return 1_000
        elif re.search(r'\(단위\s*[:\s:]\s*원\)', search_area):
            return 1

        # 2. AUNIT 속성 확인
        aunit_match = re.search(r'AUNIT="(\w+)"\s+AUNITVALUE="(\d+)"', search_area)
        if aunit_match:
            aunit = aunit_match.group(1).upper()
            aunit_value = int(aunit_match.group(2))
            if aunit == 'WON':
                return aunit_value  # 보통 1
            elif aunit == 'THOUSAND':
                return 1_000 * aunit_value
            elif aunit == 'MILLION':
                return 1_000_000 * aunit_value

        # 3. ENG 속성에서 단위 확인 (예: "(Unit : KRW)")
        if re.search(r'Unit\s*:\s*KRW', search_area, re.IGNORECASE):
            return 1  # 원 단위

        # 4. 기본값: 원 (v2.0에서는 원을 기본으로 변경 - 사업보고서 본문은 대부분 원)
        logger.debug("Using default unit: 1 (원)")
        return 1

    def _extract_values_from_xml(self, xml_content: str, table_patterns: List[str], fs_type: str = 'OFS') -> Dict[str, int]:
        """[DEPRECATED] 기존 메서드 - 하위 호환성 유지용

        v2.0에서는 _extract_values_from_all_statements 사용
        """
        return self._extract_values_from_all_statements(xml_content, fs_type)

    def _extract_section_content(self, xml_content: str, fs_type: str) -> Optional[str]:
        """재무제표 섹션 내용 추출 (다양한 문서 구조 지원)"""
        if fs_type == 'OFS':
            # 별도 재무상태표 패턴들
            section_patterns = [
                r'<TITLE[^>]*>4-1\.\s*재무상태표</TITLE>(.+?)(?=<TITLE|$)',
                r'<TITLE[^>]*>재\s*무\s*상\s*태\s*표</TITLE>(.+?)(?=<TITLE|$)',
            ]
        else:
            # 연결 재무상태표 패턴들
            section_patterns = [
                r'<TITLE[^>]*>2-1\.\s*연결\s*재무상태표</TITLE>(.+?)(?=<TITLE|$)',
                r'<TITLE[^>]*>연결\s*재\s*무\s*상\s*태\s*표</TITLE>(.+?)(?=<TITLE|$)',
            ]

        # 1. TITLE 태그 패턴 시도
        for pattern in section_patterns:
            match = re.search(pattern, xml_content, re.DOTALL)
            if match:
                return match.group(1)

        # 2. TITLE 태그 없는 문서: 재무상태표 + 큰 숫자가 있는 섹션 찾기
        # 각 "재 무 상 태 표" 위치에서 검색
        keyword = r'재\s*무\s*상\s*태\s*표' if fs_type == 'OFS' else r'연결\s*재\s*무\s*상\s*태\s*표'
        matches = list(re.finditer(keyword, xml_content))

        for m in matches:
            # 해당 위치부터 다음 TITLE 또는 다음 재무상태표까지
            section_end = len(xml_content)

            # 다음 TITLE 태그 찾기
            next_title = re.search(r'<TITLE', xml_content[m.end():])
            if next_title:
                section_end = m.end() + next_title.start()

            section = xml_content[m.start():section_end]

            # 이 섹션에 실제 재무 데이터가 있는지 확인 (7자리 이상 숫자)
            big_numbers = re.findall(r'[\d,]{7,}', section)
            if len(big_numbers) >= 5:  # 충분한 데이터 행이 있음
                return section

        return None

    def _detect_unit_from_section(self, xml_content: str, fs_type: str) -> int:
        """재무상태표 섹션에서 단위 감지

        우선순위:
        1. 재무상태표 근처의 (단위: 원/천원/백만원) 텍스트 - 가장 정확
        2. AUNIT 속성 (AUNIT="WON" AUNITVALUE="1")
        3. 문서 전체에서 단위 패턴 찾기
        4. 기본값 1000 (천원이 가장 흔함)
        """

        def _parse_unit_text(text: str) -> Optional[int]:
            """텍스트에서 단위 추출 (다양한 패턴 지원)"""
            # 패턴들: (단위: 원), (단위 : 천원), 단위:백만원 등
            # 백만원 먼저 체크 (천원이 백만원에 포함됨)
            if re.search(r'단위\s*[:\s:]\s*백만\s*원', text):
                return 1_000_000
            elif re.search(r'단위\s*[:\s:]\s*천\s*원', text):
                return 1_000
            elif re.search(r'단위\s*[:\s:]\s*원[^천백]', text) or re.search(r'단위\s*[:\s:]\s*원\)', text) or re.search(r'단위\s*[:\s:]\s*원$', text):
                return 1
            return None

        # 1. 재무상태표 TITLE 섹션에서 단위 찾기
        # DART 문서 구조: "4-1. 재무상태표" (별도), "2-1. 연결 재무상태표" (연결)
        if fs_type == 'OFS':
            title_patterns = [
                r'<TITLE[^>]*>4-1\.\s*재무상태표</TITLE>',  # 가장 정확
                r'<TITLE[^>]*>재\s*무\s*상\s*태\s*표</TITLE>',
                r'재\s*무\s*상\s*태\s*표',
            ]
        else:
            title_patterns = [
                r'<TITLE[^>]*>2-1\.\s*연결\s*재무상태표</TITLE>',
                r'<TITLE[^>]*>연결\s*재\s*무\s*상\s*태\s*표</TITLE>',
                r'연결\s*재\s*무\s*상\s*태\s*표',
            ]

        for title_pattern in title_patterns:
            # 제목 후 2000자 내에서 단위 찾기
            match = re.search(rf'({title_pattern})(.{{0,2000}})', xml_content, re.DOTALL)
            if match:
                section = match.group(2)

                # 텍스트 단위 확인 (최우선)
                unit = _parse_unit_text(section)
                if unit:
                    logger.debug(f"Found unit from text near title: {unit}")
                    return unit

                # AUNIT 속성 확인
                aunit_match = re.search(r'AUNIT="(\w+)"\s+AUNITVALUE="(\d+)"', section)
                if aunit_match:
                    aunit = aunit_match.group(1).upper()
                    aunit_value = int(aunit_match.group(2))
                    if aunit == 'WON':
                        logger.debug(f"Found AUNIT WON with value: {aunit_value}")
                        return aunit_value  # 보통 1
                    elif aunit == 'THOUSAND':
                        return 1_000 * aunit_value
                    elif aunit == 'MILLION':
                        return 1_000_000 * aunit_value

        # 2. 문서 전체에서 단위 패턴 찾기 (첫 번째 매칭)
        all_units = re.findall(r'단위\s*[:\s:]\s*(백만\s*원|천\s*원|원)', xml_content)
        if all_units:
            first_unit = all_units[0].replace(' ', '')
            if '백만원' in first_unit:
                logger.debug("Found 백만원 in document")
                return 1_000_000
            elif '천원' in first_unit:
                logger.debug("Found 천원 in document")
                return 1_000
            elif first_unit == '원':
                logger.debug("Found 원 in document")
                return 1

        # 3. 기본값: 천원 (가장 일반적)
        logger.debug("Using default unit: 1000 (천원)")
        return 1_000

    def _clean_xml_text(self, xml_content: str) -> str:
        """XML 태그 제거하고 텍스트만 추출"""
        # 태그 제거
        text = re.sub(r'<[^>]+>', ' ', xml_content)
        # 다중 공백 축소
        text = re.sub(r'\s+', ' ', text)
        return text

    def _parse_amount(self, amount_str: str, multiplier: int = 1) -> Optional[int]:
        """금액 문자열 파싱"""
        if not amount_str:
            return None

        try:
            # 공백, 콤마 제거
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()

            # 괄호 = 음수
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('-'):
                is_negative = True
                cleaned = cleaned[1:]

            # 숫자만 추출
            cleaned = re.sub(r'[^\d\.]', '', cleaned)
            if not cleaned:
                return None

            # 소수점 처리
            if '.' in cleaned:
                value = int(float(cleaned))
            else:
                value = int(cleaned)

            value = value * multiplier
            return -value if is_negative else value

        except (ValueError, TypeError):
            return None

    def get_fiscal_year_from_report(self, meta: Dict, xml_content: str) -> int:
        """보고서에서 결산년도 추출"""
        # meta에서 report_nm 분석 (예: "사업보고서 (2023.12)")
        report_nm = meta.get('report_nm', '')
        match = re.search(r'\((\d{4})\.\d{2}\)', report_nm)
        if match:
            return int(match.group(1))

        # XML에서 기간 정보 추출
        period_match = re.search(r'제\s*\d+\s*기\s*(\d{4})\.\d{2}\.\d{2}\s*부터\s*(\d{4})\.\d{2}\.\d{2}\s*까지', xml_content)
        if period_match:
            return int(period_match.group(2))

        # rcept_dt에서 년도 추출 (마지막 수단)
        rcept_dt = meta.get('rcept_dt', '')
        if len(rcept_dt) >= 4:
            year = int(rcept_dt[:4])
            # 1-3월 제출이면 전년도 결산
            if len(rcept_dt) >= 6:
                month = int(rcept_dt[4:6])
                if month <= 4:
                    year -= 1
            return year

        return 2023  # 기본값


class FinancialDetailsCollectorLocal:
    """로컬 DART 데이터 + API 보완 수집기"""

    def __init__(self, db_url: str, dart_api_key: str = None):
        self.db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.parser = LocalDARTFinancialParser()
        self.dart_api_key = dart_api_key or os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
        self.stats = {
            'companies': 0,
            'local_parsed': 0,
            'api_fetched': 0,
            'saved': 0,
            'errors': 0
        }

    async def get_companies(self, conn, limit: Optional[int] = None) -> List[Dict]:
        """상장사 목록 조회"""
        query = """
            SELECT id, corp_code, name, ticker, market
            FROM companies
            WHERE corp_code IS NOT NULL
              AND market IS NOT NULL
              AND market NOT IN ('ETF', '기타')
            ORDER BY name
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def save_financial_details(self, conn, company_id: str, data: Dict) -> bool:
        """재무 데이터 저장"""
        try:
            await conn.execute("""
                INSERT INTO financial_details (
                    id, company_id, fiscal_year, fiscal_quarter, report_type,
                    -- 유동자산
                    current_assets, cash_and_equivalents, short_term_investments,
                    trade_and_other_receivables, inventories, current_tax_assets,
                    other_financial_assets_current, other_assets_current,
                    -- 비유동자산
                    non_current_assets, fvpl_financial_assets, investments_in_associates,
                    tangible_assets, intangible_assets, right_of_use_assets,
                    net_defined_benefit_assets, deferred_tax_assets,
                    other_financial_assets_non_current, other_assets_non_current,
                    -- 자산/부채/자본 총계
                    total_assets, current_liabilities, non_current_liabilities,
                    total_liabilities, total_equity,
                    -- 손익계산서
                    revenue, cost_of_sales, selling_admin_expenses,
                    operating_income, net_income,
                    -- 손익계산서 v2.0 신규
                    r_and_d_expense, depreciation_expense, interest_expense, tax_expense,
                    -- 현금흐름표
                    operating_cash_flow, investing_cash_flow, financing_cash_flow,
                    capex, intangible_acquisition, dividend_paid,
                    treasury_stock_acquisition, stock_issuance, bond_issuance,
                    -- 메타
                    fs_type, data_source, source_rcept_no, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), $1, $2, $3, $4,
                    $5, $6, $7, $8, $9, $10, $11, $12,
                    $13, $14, $15, $16, $17, $18, $19, $20, $21, $22,
                    $23, $24, $25, $26, $27,
                    $28, $29, $30, $31, $32,
                    $33, $34, $35, $36,
                    $37, $38, $39, $40, $41, $42, $43, $44, $45,
                    $46, $47, $48, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, fiscal_quarter, fs_type)
                DO UPDATE SET
                    current_assets = COALESCE(EXCLUDED.current_assets, financial_details.current_assets),
                    cash_and_equivalents = COALESCE(EXCLUDED.cash_and_equivalents, financial_details.cash_and_equivalents),
                    short_term_investments = COALESCE(EXCLUDED.short_term_investments, financial_details.short_term_investments),
                    trade_and_other_receivables = COALESCE(EXCLUDED.trade_and_other_receivables, financial_details.trade_and_other_receivables),
                    inventories = COALESCE(EXCLUDED.inventories, financial_details.inventories),
                    current_tax_assets = COALESCE(EXCLUDED.current_tax_assets, financial_details.current_tax_assets),
                    other_financial_assets_current = COALESCE(EXCLUDED.other_financial_assets_current, financial_details.other_financial_assets_current),
                    other_assets_current = COALESCE(EXCLUDED.other_assets_current, financial_details.other_assets_current),
                    non_current_assets = COALESCE(EXCLUDED.non_current_assets, financial_details.non_current_assets),
                    fvpl_financial_assets = COALESCE(EXCLUDED.fvpl_financial_assets, financial_details.fvpl_financial_assets),
                    investments_in_associates = COALESCE(EXCLUDED.investments_in_associates, financial_details.investments_in_associates),
                    tangible_assets = COALESCE(EXCLUDED.tangible_assets, financial_details.tangible_assets),
                    intangible_assets = COALESCE(EXCLUDED.intangible_assets, financial_details.intangible_assets),
                    right_of_use_assets = COALESCE(EXCLUDED.right_of_use_assets, financial_details.right_of_use_assets),
                    net_defined_benefit_assets = COALESCE(EXCLUDED.net_defined_benefit_assets, financial_details.net_defined_benefit_assets),
                    deferred_tax_assets = COALESCE(EXCLUDED.deferred_tax_assets, financial_details.deferred_tax_assets),
                    other_financial_assets_non_current = COALESCE(EXCLUDED.other_financial_assets_non_current, financial_details.other_financial_assets_non_current),
                    other_assets_non_current = COALESCE(EXCLUDED.other_assets_non_current, financial_details.other_assets_non_current),
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
                    r_and_d_expense = COALESCE(EXCLUDED.r_and_d_expense, financial_details.r_and_d_expense),
                    depreciation_expense = COALESCE(EXCLUDED.depreciation_expense, financial_details.depreciation_expense),
                    interest_expense = COALESCE(EXCLUDED.interest_expense, financial_details.interest_expense),
                    tax_expense = COALESCE(EXCLUDED.tax_expense, financial_details.tax_expense),
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
                data.get('fiscal_year'),
                data.get('fiscal_quarter'),
                data.get('report_type', 'annual'),
                # 유동자산
                data.get('current_assets'),
                data.get('cash_and_equivalents'),
                data.get('short_term_investments'),
                data.get('trade_and_other_receivables'),
                data.get('inventories'),
                data.get('current_tax_assets'),
                data.get('other_financial_assets_current'),
                data.get('other_assets_current'),
                # 비유동자산
                data.get('non_current_assets'),
                data.get('fvpl_financial_assets'),
                data.get('investments_in_associates'),
                data.get('tangible_assets'),
                data.get('intangible_assets'),
                data.get('right_of_use_assets'),
                data.get('net_defined_benefit_assets'),
                data.get('deferred_tax_assets'),
                data.get('other_financial_assets_non_current'),
                data.get('other_assets_non_current'),
                # 자산/부채/자본 총계
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
                # 손익계산서 v2.0 신규
                data.get('r_and_d_expense'),
                data.get('depreciation_expense'),
                data.get('interest_expense'),
                data.get('tax_expense'),
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
                data.get('data_source', 'LOCAL_DART'),
                data.get('source_rcept_no')
            )
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    async def fetch_from_api(self, corp_code: str, year: int) -> Optional[Dict]:
        """DART API에서 재무데이터 조회 (로컬에 없는 경우)"""
        import aiohttp

        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': self.dart_api_key,
            'corp_code': corp_code,
            'bsns_year': str(year),
            'reprt_code': '11011',  # 사업보고서
            'fs_div': 'CFS'  # 연결재무제표
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    if data.get('status') != '000':
                        # 연결이 없으면 별도 시도
                        if data.get('status') == '013':
                            params['fs_div'] = 'OFS'
                            async with session.get(url, params=params, timeout=30) as resp2:
                                if resp2.status == 200:
                                    data = await resp2.json()
                                    if data.get('status') != '000':
                                        return None
                        else:
                            return None

                    return self._parse_api_response(data.get('list', []), year, params['fs_div'])

        except Exception as e:
            logger.debug(f"API fetch error for {corp_code}/{year}: {e}")
            return None

    def _parse_api_response(self, statements: List[Dict], year: int, fs_type: str) -> Dict:
        """API 응답 파싱"""
        result = {
            'fiscal_year': year,
            'fiscal_quarter': None,
            'report_type': 'annual',
            'fs_type': fs_type,
            'data_source': 'DART_API'
        }

        account_map = {
            '자산총계': 'total_assets',
            '부채총계': 'total_liabilities',
            '자본총계': 'total_equity',
            '매출액': 'revenue',
            '영업이익': 'operating_income',
            '당기순이익': 'net_income',
            '현금및현금성자산': 'cash_and_equivalents',
            '유형자산': 'tangible_assets',
            '무형자산': 'intangible_assets',
            '영업활동현금흐름': 'operating_cash_flow',
            '투자활동현금흐름': 'investing_cash_flow',
            '재무활동현금흐름': 'financing_cash_flow',
        }

        for stmt in statements:
            account_nm = stmt.get('account_nm', '').strip()
            amount_str = stmt.get('thstrm_amount', '')

            if not amount_str or amount_str == '-':
                continue

            try:
                amount = int(amount_str.replace(',', ''))
                for key, field in account_map.items():
                    if key in account_nm:
                        result[field] = amount
                        break
            except ValueError:
                continue

        return result

    async def collect_company_data(self, conn, company: Dict, years: List[int]) -> int:
        """회사별 데이터 수집 (로컬 우선, API 보완)"""
        saved_count = 0
        corp_code = company['corp_code']

        # 로컬 사업보고서 찾기
        local_reports = self.parser.find_business_reports(corp_code)

        for year in years:
            data = None
            source = None

            # 1. 로컬에서 해당 연도 데이터 찾기
            for report in local_reports:
                xml_content = self.parser.extract_xml_content(report['zip_path'])
                if not xml_content:
                    continue

                fiscal_year = self.parser.get_fiscal_year_from_report(report['meta'], xml_content)
                if fiscal_year != year:
                    continue

                parsed = self.parser.parse_financial_tables(xml_content)
                if parsed:
                    fs_type = 'CFS' if 'CFS' in parsed else 'OFS'
                    data = parsed.get(fs_type, {})
                    data['fiscal_year'] = year
                    data['fiscal_quarter'] = None
                    data['report_type'] = 'annual'
                    data['fs_type'] = fs_type
                    data['data_source'] = 'LOCAL_DART'
                    data['source_rcept_no'] = report['meta'].get('rcept_no')
                    source = 'local'
                    break

            # 2. 로컬에 없으면 API로 조회
            if not data or not self._has_essential_fields(data):
                api_data = await self.fetch_from_api(corp_code, year)
                if api_data:
                    if data:
                        # 로컬 데이터에 API 데이터 보완
                        for key, value in api_data.items():
                            if value is not None and data.get(key) is None:
                                data[key] = value
                    else:
                        data = api_data
                    source = 'api' if not source else 'local+api'
                    self.stats['api_fetched'] += 1

            # 3. 저장
            if data and self._has_essential_fields(data):
                success = await self.save_financial_details(conn, str(company['id']), data)
                if success:
                    saved_count += 1
                    self.stats['saved'] += 1
                    if source == 'local':
                        self.stats['local_parsed'] += 1

        return saved_count

    def _has_essential_fields(self, data: Dict) -> bool:
        """필수 필드가 있는지 확인"""
        essential = ['total_assets', 'revenue', 'operating_cash_flow']
        return any(data.get(f) is not None for f in essential)

    async def run(self, limit: Optional[int] = None, years: List[int] = None):
        """전체 수집 실행"""
        if years is None:
            years = [2022, 2023, 2024]

        conn = await asyncpg.connect(self.db_url)

        try:
            companies = await self.get_companies(conn, limit)
            self.stats['companies'] = len(companies)

            logger.info("=" * 80)
            logger.info("로컬 DART 데이터 + API 보완 수집 시작")
            logger.info("=" * 80)
            logger.info(f"대상 회사: {len(companies)}개")
            logger.info(f"수집 연도: {years}")
            logger.info("=" * 80)

            for i, company in enumerate(companies, 1):
                try:
                    saved = await self.collect_company_data(conn, company, years)
                    if saved > 0:
                        logger.info(f"[{i}/{len(companies)}] {company['name']}: {saved}건 저장")

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing {company['name']}: {e}")

                # 진행 상황
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(companies)} - Local: {self.stats['local_parsed']}, API: {self.stats['api_fetched']}, Saved: {self.stats['saved']}")

                # API 호출 시 rate limiting
                await asyncio.sleep(0.3)

            # 결과
            logger.info("=" * 80)
            logger.info("수집 완료")
            logger.info("=" * 80)
            logger.info(f"회사 수: {self.stats['companies']}")
            logger.info(f"로컬 파싱: {self.stats['local_parsed']}건")
            logger.info(f"API 보완: {self.stats['api_fetched']}건")
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
        yearly = await conn.fetch("""
            SELECT fiscal_year, COUNT(*) as cnt,
                   SUM(CASE WHEN capex IS NOT NULL THEN 1 ELSE 0 END) as capex_cnt,
                   SUM(CASE WHEN operating_cash_flow IS NOT NULL THEN 1 ELSE 0 END) as ocf_cnt
            FROM financial_details
            GROUP BY fiscal_year
            ORDER BY fiscal_year
        """)

        logger.info("\n[수집 결과]")
        for row in yearly:
            logger.info(f"  {row['fiscal_year']}년: {row['cnt']}건 (CAPEX: {row['capex_cnt']}, OCF: {row['ocf_cnt']})")

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='로컬 DART 재무 데이터 수집')
    parser.add_argument('--sample', type=int, help='샘플 회사 수')
    parser.add_argument('--year', type=int, help='특정 연도만')
    parser.add_argument('--verify-only', action='store_true', help='결과 검증만')

    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_results())
        return

    years = [args.year] if args.year else [2022, 2023, 2024]

    collector = FinancialDetailsCollectorLocal(DATABASE_URL)
    asyncio.run(collector.run(limit=args.sample, years=years))
    asyncio.run(verify_results())


if __name__ == "__main__":
    main()
