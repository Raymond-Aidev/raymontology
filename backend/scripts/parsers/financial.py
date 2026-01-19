"""
FinancialParser - DART 재무제표 파서 (v3.0)

검증된 v2.1 로직 + XBRL Enhancer 통합:
- 230+ 한글 계정과목 매핑 (텍스트 패턴)
- 3개 재무제표 섹션 독립 파싱 (재무상태표, 손익계산서, 현금흐름표)
- 섹션별 단위 감지
- ON CONFLICT UPSERT 패턴
- [v3.0] IFRS ACODE 기반 XBRL Enhancer로 누락 항목 보완

v3.0 개선 (2026-01-05):
- 기존 텍스트 패턴 매칭으로 추출 못한 항목을 XBRL ACODE로 보완
- 부채 세부 (단기차입금, 장기차입금, 매입채무, 사채 등) 추가 추출
- 자본 세부 (자본금, 자본잉여금, 이익잉여금, 자기주식) 추가 추출

사용법:
    from scripts.parsers import FinancialParser

    parser = FinancialParser()
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            await parser.parse_and_save(conn, zip_path, meta)
"""

import asyncpg
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import BaseParser
from .xbrl_enhancer import XBRLEnhancer

logger = logging.getLogger(__name__)


class FinancialParser(BaseParser):
    """DART 재무제표 파서 (v3.0 - XBRL Enhanced)"""

    # 계정과목 매핑 (한글 계정명 -> 필드명) - 230+ 항목
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
        # 재무상태표 - 자산/부채/자본 총계
        # ═══════════════════════════════════════════════════════════════
        'total_assets': [
            '자산총계', '자산 총계', '자산합계',
            '총자산', '합계(자산)', '자 산 총 계'
        ],
        'current_liabilities': [
            '유동부채', '유동부채합계', '유동부채 합계',
            'Ⅰ.유동부채', '1.유동부채', 'I.유동부채'
        ],
        'trade_payables': [
            '매입채무', '매입채무및기타채무', '매입채무 및 기타채무',
            '미지급금', '단기매입채무'
        ],
        'short_term_borrowings': [
            '단기차입금', '단기금융부채', '유동성장기부채',
            '단기 차입금', '유동차입금'
        ],
        'current_portion_long_term_debt': [
            '유동성장기차입금', '유동성장기부채', '1년이내만기도래장기부채',
            '유동성 장기차입금', '유동성장기금융부채'
        ],
        'other_current_liabilities': [
            '기타유동부채', '기타 유동부채', '기타유동금융부채',
            '미지급비용', '선수금', '선수수익'
        ],
        'current_tax_liabilities': [
            '당기법인세부채', '당기법인세 부채', '미지급법인세'
        ],
        'provisions_current': [
            '충당부채(유동)', '유동충당부채', '단기충당부채'
        ],
        'non_current_liabilities': [
            '비유동부채', '비유동부채합계', '비유동부채 합계',
            'Ⅱ.비유동부채', '2.비유동부채', 'II.비유동부채'
        ],
        'long_term_borrowings': [
            '장기차입금', '장기금융부채', '비유동차입금',
            '장기 차입금', '장기금융부채'
        ],
        'bonds_payable': [
            '사채', '회사채', '사채(비유동)',
            '장기사채', '비유동사채'
        ],
        'convertible_bonds': [
            '전환사채', '전환사채(비유동)', '전환사채부채요소',
            'CB', '신주인수권부사채'
        ],
        'lease_liabilities': [
            '리스부채', '리스부채(비유동)', '장기리스부채',
            '비유동리스부채', '금융리스부채'
        ],
        'deferred_tax_liabilities': [
            '이연법인세부채', '이연법인세 부채', '이연세금부채'
        ],
        'provisions_non_current': [
            '충당부채(비유동)', '비유동충당부채', '장기충당부채'
        ],
        'other_non_current_liabilities': [
            '기타비유동부채', '기타 비유동부채', '기타비유동금융부채'
        ],
        'total_liabilities': [
            '부채총계', '부채 총계', '부채합계',
            '총부채', '합계(부채)', '부 채 총 계'
        ],
        'total_equity': [
            '자본총계', '자본 총계', '자본합계',
            '총자본', '합계(자본)', '자기자본', '자 본 총 계'
        ],
        'capital_stock': [
            '자본금', '납입자본금', '보통주자본금',
            'Ⅰ.자본금', 'I.자본금', '1.자본금'
        ],
        'capital_surplus': [
            '자본잉여금', '자본 잉여금', '주식발행초과금',
            'Ⅱ.자본잉여금', 'II.자본잉여금'
        ],
        'retained_earnings': [
            '이익잉여금', '이익 잉여금', '미처분이익잉여금',
            'Ⅲ.이익잉여금', 'III.이익잉여금', '결손금'
        ],
        'treasury_stock': [
            '자기주식', '자기 주식', '자사주',
            '(-) 자기주식', '(-)자기주식'
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
        # v3.1: 재무비율 계산용 신규 계정과목
        'gross_profit': [
            '매출총이익', '매출총손익', '매출 총이익',
            '매출총이익(손실)', 'Ⅲ.매출총이익', 'III.매출총이익',
            '매 출 총 이 익'
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
        # v3.1: 재무비율 계산용 신규 계정과목
        'interest_income': [
            '이자수익', '이자이익', '이자수입', '금융수익',
            '이자 수익', '금융이익', '이자및배당금수익'
        ],
        'income_before_tax': [
            '법인세비용차감전순이익', '법인세차감전순이익', '세전이익',
            '법인세비용차감전이익', '세전순이익', '법인세비용차감전계속사업이익',
            '세 전 이 익', '법인세비용차감전순손익', '법인세비용차감전분기순이익'
        ],
        'tax_expense': [
            '법인세비용', '법인세', '소득세비용',
            '법인세비용(수익)', '당기법인세비용', '법인세등',
            '법인세비용(이익)', '계속사업법인세비용'
        ],
        'amortization': [
            '무형자산상각비', '상각비', '무형자산 상각',
            '무형자산상각', '무형자산감가상각비', '영업권상각비'
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
            '유형자산 취득으로 인한 현금유출', '유형자산의취득(자본적지출)',
            '유형자산및투자부동산의취득', '유형자산 및 투자부동산의 취득'
        ],
        # v3.1: 개별 유형자산 취득 (합산 대상)
        'capex_land': [
            '토지의취득', '토지의 취득', '토지취득', '토지 취득'
        ],
        'capex_building': [
            '건물의취득', '건물의 취득', '건물취득', '건물 취득'
        ],
        'capex_machinery': [
            '기계장치의취득', '기계장치의 취득', '기계장치취득', '기계장치 취득'
        ],
        'capex_equipment': [
            '시설장치의취득', '시설장치의 취득', '시설장치취득', '시설장치 취득',
            '설비의취득', '설비의 취득'
        ],
        'capex_vehicle': [
            '차량운반구의취득', '차량운반구의 취득', '차량운반구취득', '차량 취득'
        ],
        'capex_tools': [
            '공구와기구의취득', '공구와기구의 취득', '공구기구의취득',
            '비품의취득', '비품의 취득', '비품취득', '집기비품의취득'
        ],
        'capex_construction': [
            '건설중인자산의증가', '건설중인자산 증가', '건설중인자산의취득',
            '건설중인자산취득', 'CIP의증가'
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

    # 재무제표 섹션 설정
    STATEMENT_CONFIGS = [
        {
            'name': 'balance_sheet',
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
            'name': 'income_statement',
            'fields': [
                'revenue', 'cost_of_sales', 'gross_profit', 'selling_admin_expenses',
                'operating_income', 'net_income',
                'r_and_d_expense', 'depreciation_expense', 'interest_expense',
                'interest_income', 'income_before_tax', 'tax_expense', 'amortization'
            ]
        },
        {
            'name': 'cash_flow',
            'fields': [
                'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
                'capex', 'intangible_acquisition', 'dividend_paid',
                'treasury_stock_acquisition', 'stock_issuance', 'bond_issuance',
                # v3.1: 개별 CAPEX 항목 (합산용)
                'capex_land', 'capex_building', 'capex_machinery',
                'capex_equipment', 'capex_vehicle', 'capex_tools', 'capex_construction'
            ]
        }
    ]

    def __init__(self, database_url: Optional[str] = None, enable_xbrl: bool = True):
        super().__init__(database_url)
        self.company_cache = {}  # corp_code -> company_id
        self.enable_xbrl = enable_xbrl
        self.xbrl_enhancer = XBRLEnhancer() if enable_xbrl else None

    async def load_companies(self, conn: asyncpg.Connection):
        """회사 캐시 로드"""
        rows = await conn.fetch("SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL")
        self.company_cache = {r['corp_code']: str(r['id']) for r in rows}
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개")

    def _get_title_patterns(self, statement_name: str, fs_type: str = 'OFS') -> List[str]:
        """재무제표 TITLE 패턴 반환"""
        patterns = {
            'balance_sheet': {
                'OFS': [
                    r'<TITLE[^>]*>4-1\.\s*재\s*무\s*상\s*태\s*표</TITLE>',
                    r'<TITLE[^>]*>재\s*무\s*상\s*태\s*표</TITLE>',
                    r'<TITLE[^>]*>\d+-\d+\.\s*재\s*무\s*상\s*태\s*표</TITLE>',
                ],
                'CFS': [
                    r'<TITLE[^>]*>2-1\.\s*연\s*결\s*재\s*무\s*상\s*태\s*표</TITLE>',
                    r'<TITLE[^>]*>연\s*결\s*재\s*무\s*상\s*태\s*표</TITLE>',
                ]
            },
            'income_statement': {
                'OFS': [
                    r'<TITLE[^>]*>4-2\.\s*손\s*익\s*계\s*산\s*서</TITLE>',
                    r'<TITLE[^>]*>손\s*익\s*계\s*산\s*서</TITLE>',
                    r'<TITLE[^>]*>4-2\.\s*포\s*괄\s*손\s*익\s*계\s*산\s*서</TITLE>',
                ],
                'CFS': [
                    r'<TITLE[^>]*>2-2\.\s*연\s*결\s*손\s*익\s*계\s*산\s*서</TITLE>',
                    r'<TITLE[^>]*>연\s*결\s*손\s*익\s*계\s*산\s*서</TITLE>',
                ]
            },
            'cash_flow': {
                'OFS': [
                    r'<TITLE[^>]*>4-4\.\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                    r'<TITLE[^>]*>현\s*금\s*흐\s*름\s*표</TITLE>',
                ],
                'CFS': [
                    r'<TITLE[^>]*>2-4\.\s*연\s*결\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                    r'<TITLE[^>]*>연\s*결\s*현\s*금\s*흐\s*름\s*표</TITLE>',
                ]
            }
        }
        return patterns.get(statement_name, {}).get(fs_type, [])

    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """단일 보고서에서 재무 데이터 파싱 (v3.0: XBRL Enhanced)"""
        result = {
            'success': False,
            'data': {},
            'errors': [],
        }

        xml_content = self.extract_xml_from_zip(zip_path)
        if not xml_content:
            result['errors'].append('XML extraction failed')
            return result

        # fiscal_year 추출 (rcept_no 또는 report_nm에서)
        rcept_no = meta.get('rcept_no', '')
        report_nm = meta.get('report_nm', '')
        target_year = self._extract_fiscal_year(rcept_no, report_nm)

        # 별도재무제표(OFS) 우선, 없으면 연결(CFS)
        for fs_type in ['OFS', 'CFS']:
            # 1단계: 기존 텍스트 패턴 매칭
            parsed = self._extract_values_from_all_statements(xml_content, fs_type)

            # 2단계: XBRL Enhancer로 누락 항목 보완
            if self.enable_xbrl and self.xbrl_enhancer and target_year:
                enhanced = self.xbrl_enhancer.enhance_parsed_data(
                    xml_content, parsed, target_year, fs_type
                )
                # 보완된 항목 수 기록
                enhanced_count = sum(1 for k, v in enhanced.items() if v is not None and parsed.get(k) is None)
                if enhanced_count > 0:
                    logger.info(f"XBRL enhanced {enhanced_count} fields for {meta.get('corp_code')}")
                parsed = enhanced

            if parsed:
                # v3.1: 개별 CAPEX 합산
                parsed = self._aggregate_capex(parsed)
                result['data'] = parsed
                result['fs_type'] = fs_type
                result['success'] = True
                break

        # 메타 정보 추가
        if result['success']:
            result['meta'] = {
                'corp_code': meta.get('corp_code'),
                'rcept_no': meta.get('rcept_no'),
                'report_nm': meta.get('report_nm'),
            }
            result['target_year'] = target_year

        return result

    def _extract_fiscal_year(self, rcept_no: str, report_nm: str) -> Optional[int]:
        """보고서에서 대상 회계연도 추출"""
        import re

        # report_nm에서 연도 추출 (예: "사업보고서 (2024.12)")
        year_match = re.search(r'\((\d{4})\.\d+\)', report_nm)
        if year_match:
            return int(year_match.group(1))

        # rcept_no 앞 4자리 (제출연도 - 보통 회계연도 다음해)
        if rcept_no and len(rcept_no) >= 4:
            try:
                submit_year = int(rcept_no[:4])
                # 사업보고서는 보통 3월에 제출 → 전년도 회계연도
                return submit_year - 1
            except ValueError:
                pass

        return None

    def _aggregate_capex(self, parsed: Dict[str, int]) -> Dict[str, int]:
        """v3.1: 개별 유형자산 취득 항목을 합산하여 capex 계산

        DART 현금흐름표에서 CAPEX가 '유형자산의취득'이 아닌
        개별 자산(토지, 건물, 기계장치 등)으로 분리된 경우 합산
        """
        # capex가 이미 있으면 그대로 반환
        if parsed.get('capex') is not None:
            return parsed

        # 개별 CAPEX 항목 합산
        capex_fields = [
            'capex_land', 'capex_building', 'capex_machinery',
            'capex_equipment', 'capex_vehicle', 'capex_tools', 'capex_construction'
        ]

        total_capex = 0
        has_any_capex = False

        for field in capex_fields:
            value = parsed.get(field)
            if value is not None:
                # 현금유출은 보통 양수로 기록되지만, 현금흐름표에서는 (유출) = 양수
                total_capex += abs(value)
                has_any_capex = True
                logger.debug(f"CAPEX component: {field} = {value:,}")

        if has_any_capex:
            # 투자활동 현금유출이므로 음수로 표시할 수도 있지만,
            # 기존 CAPEX 필드와 일관성을 위해 양수 유지
            parsed['capex'] = total_capex
            logger.info(f"Aggregated CAPEX from {sum(1 for f in capex_fields if parsed.get(f))} components: {total_capex:,}")

        # 개별 필드 제거 (DB에 저장하지 않음)
        for field in capex_fields:
            parsed.pop(field, None)

        return parsed

    def _extract_values_from_all_statements(self, xml_content: str, fs_type: str = 'OFS') -> Dict[str, int]:
        """v2.0: 각 재무제표 섹션에서 독립적으로 값 추출"""
        values = {}

        for config in self.STATEMENT_CONFIGS:
            title_patterns = self._get_title_patterns(config['name'], fs_type)
            section_content = self._extract_statement_section(xml_content, title_patterns)

            if not section_content:
                logger.debug(f"No section found for {config['name']} ({fs_type})")
                continue

            # 해당 섹션에서 단위 감지
            unit_multiplier = self._detect_unit_from_content(section_content)
            logger.debug(f"{config['name']}: unit={unit_multiplier}")

            # 섹션 내 텍스트 추출
            clean_text = self._clean_xml_text(section_content)

            # 해당 섹션의 필드만 파싱
            for field in config['fields']:
                if field in values:
                    continue

                aliases = self.ACCOUNT_MAPPING.get(field, [])
                for alias in aliases:
                    alias_pattern = r'\s*'.join(re.escape(c) for c in alias)
                    # 주석번호 건너뛰기, 7자리 이상 금액 캡처
                    pattern = rf'{alias_pattern}(?:\s*\(주\d+\))?[^\d\-]*?([\-\(]?\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?[\)]?|[\-\(]?\d{{7,}}(?:\.\d+)?[\)]?)'

                    matches = re.findall(pattern, clean_text, re.IGNORECASE)
                    if matches:
                        amount = self._parse_amount(matches[0], unit_multiplier)
                        if amount is not None:
                            values[field] = amount
                            break

        return values

    async def save_to_db(self, conn: asyncpg.Connection, data: Dict[str, Any]) -> bool:
        """파싱 결과 DB 저장 (UPSERT) - v3.0: 추가 필드 포함"""
        if not data.get('success') or not data.get('data'):
            return False

        meta = data.get('meta', {})
        corp_code = meta.get('corp_code')

        if not corp_code or corp_code not in self.company_cache:
            logger.warning(f"Unknown corp_code: {corp_code}")
            return False

        company_id = self.company_cache[corp_code]
        values = data['data']

        # fiscal_year 추출 (parse()에서 이미 계산된 값 사용)
        fiscal_year = data.get('target_year')
        if not fiscal_year:
            rcept_no = meta.get('rcept_no', '')
            try:
                fiscal_year = int(rcept_no[:4]) - 1 if rcept_no else datetime.now().year
            except ValueError:
                fiscal_year = datetime.now().year

        # UPSERT 쿼리 (v3.1: 재무비율 계산용 4개 필드 추가)
        query = '''
            INSERT INTO financial_details (
                id, company_id, fiscal_year,
                current_assets, cash_and_equivalents, short_term_investments,
                trade_and_other_receivables, inventories,
                non_current_assets, tangible_assets, intangible_assets,
                total_assets,
                current_liabilities, trade_payables, short_term_borrowings,
                non_current_liabilities, long_term_borrowings, bonds_payable,
                total_liabilities,
                total_equity, capital_stock, capital_surplus, retained_earnings, treasury_stock,
                revenue, cost_of_sales, gross_profit, operating_income, net_income,
                interest_expense, interest_income, income_before_tax, tax_expense, amortization,
                operating_cash_flow, investing_cash_flow, financing_cash_flow,
                capex, intangible_acquisition, dividend_paid,
                fs_type, data_source, created_at, updated_at
            ) VALUES (
                $1, $2, $3,
                $4, $5, $6, $7, $8,
                $9, $10, $11, $12,
                $13, $14, $15, $16, $17, $18, $19,
                $20, $21, $22, $23, $24,
                $25, $26, $27, $28, $29,
                $30, $31, $32, $33, $34,
                $35, $36, $37, $38, $39, $40,
                $41, $42, NOW(), NOW()
            )
            ON CONFLICT (company_id, fiscal_year)
            DO UPDATE SET
                current_assets = COALESCE(EXCLUDED.current_assets, financial_details.current_assets),
                cash_and_equivalents = COALESCE(EXCLUDED.cash_and_equivalents, financial_details.cash_and_equivalents),
                short_term_investments = COALESCE(EXCLUDED.short_term_investments, financial_details.short_term_investments),
                trade_and_other_receivables = COALESCE(EXCLUDED.trade_and_other_receivables, financial_details.trade_and_other_receivables),
                inventories = COALESCE(EXCLUDED.inventories, financial_details.inventories),
                non_current_assets = COALESCE(EXCLUDED.non_current_assets, financial_details.non_current_assets),
                tangible_assets = COALESCE(EXCLUDED.tangible_assets, financial_details.tangible_assets),
                intangible_assets = COALESCE(EXCLUDED.intangible_assets, financial_details.intangible_assets),
                total_assets = COALESCE(EXCLUDED.total_assets, financial_details.total_assets),
                current_liabilities = COALESCE(EXCLUDED.current_liabilities, financial_details.current_liabilities),
                trade_payables = COALESCE(EXCLUDED.trade_payables, financial_details.trade_payables),
                short_term_borrowings = COALESCE(EXCLUDED.short_term_borrowings, financial_details.short_term_borrowings),
                non_current_liabilities = COALESCE(EXCLUDED.non_current_liabilities, financial_details.non_current_liabilities),
                long_term_borrowings = COALESCE(EXCLUDED.long_term_borrowings, financial_details.long_term_borrowings),
                bonds_payable = COALESCE(EXCLUDED.bonds_payable, financial_details.bonds_payable),
                total_liabilities = COALESCE(EXCLUDED.total_liabilities, financial_details.total_liabilities),
                total_equity = COALESCE(EXCLUDED.total_equity, financial_details.total_equity),
                capital_stock = COALESCE(EXCLUDED.capital_stock, financial_details.capital_stock),
                capital_surplus = COALESCE(EXCLUDED.capital_surplus, financial_details.capital_surplus),
                retained_earnings = COALESCE(EXCLUDED.retained_earnings, financial_details.retained_earnings),
                treasury_stock = COALESCE(EXCLUDED.treasury_stock, financial_details.treasury_stock),
                revenue = COALESCE(EXCLUDED.revenue, financial_details.revenue),
                cost_of_sales = COALESCE(EXCLUDED.cost_of_sales, financial_details.cost_of_sales),
                gross_profit = COALESCE(EXCLUDED.gross_profit, financial_details.gross_profit),
                operating_income = COALESCE(EXCLUDED.operating_income, financial_details.operating_income),
                net_income = COALESCE(EXCLUDED.net_income, financial_details.net_income),
                interest_expense = COALESCE(EXCLUDED.interest_expense, financial_details.interest_expense),
                interest_income = COALESCE(EXCLUDED.interest_income, financial_details.interest_income),
                income_before_tax = COALESCE(EXCLUDED.income_before_tax, financial_details.income_before_tax),
                tax_expense = COALESCE(EXCLUDED.tax_expense, financial_details.tax_expense),
                amortization = COALESCE(EXCLUDED.amortization, financial_details.amortization),
                operating_cash_flow = COALESCE(EXCLUDED.operating_cash_flow, financial_details.operating_cash_flow),
                investing_cash_flow = COALESCE(EXCLUDED.investing_cash_flow, financial_details.investing_cash_flow),
                financing_cash_flow = COALESCE(EXCLUDED.financing_cash_flow, financial_details.financing_cash_flow),
                capex = COALESCE(EXCLUDED.capex, financial_details.capex),
                intangible_acquisition = COALESCE(EXCLUDED.intangible_acquisition, financial_details.intangible_acquisition),
                dividend_paid = COALESCE(EXCLUDED.dividend_paid, financial_details.dividend_paid),
                fs_type = EXCLUDED.fs_type,
                data_source = EXCLUDED.data_source,
                updated_at = NOW()
        '''

        try:
            await conn.execute(
                query,
                str(uuid.uuid4()), company_id, fiscal_year,
                values.get('current_assets'), values.get('cash_and_equivalents'),
                values.get('short_term_investments'), values.get('trade_and_other_receivables'),
                values.get('inventories'),
                values.get('non_current_assets'), values.get('tangible_assets'),
                values.get('intangible_assets'), values.get('total_assets'),
                values.get('current_liabilities'), values.get('trade_payables'),
                values.get('short_term_borrowings'),
                values.get('non_current_liabilities'), values.get('long_term_borrowings'),
                values.get('bonds_payable'), values.get('total_liabilities'),
                values.get('total_equity'), values.get('capital_stock'),
                values.get('capital_surplus'), values.get('retained_earnings'),
                values.get('treasury_stock'),
                values.get('revenue'), values.get('cost_of_sales'),
                values.get('gross_profit'), values.get('operating_income'), values.get('net_income'),
                values.get('interest_expense'), values.get('interest_income'),
                values.get('income_before_tax'), values.get('tax_expense'), values.get('amortization'),
                values.get('operating_cash_flow'), values.get('investing_cash_flow'),
                values.get('financing_cash_flow'), values.get('capex'),
                values.get('intangible_acquisition'), values.get('dividend_paid'),
                data.get('fs_type', 'OFS'),
                'UNIFIED_PARSER_V3'
            )
            self.stats['records_created'] += 1
            return True
        except Exception as e:
            logger.error(f"DB save error: {e}")
            self.stats['errors'] += 1
            return False
