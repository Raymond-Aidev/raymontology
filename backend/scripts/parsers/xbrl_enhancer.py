"""
XBRLEnhancer - IFRS ACODE 기반 재무 데이터 보완 모듈 (v3.2)

기존 FinancialParser가 텍스트 패턴 매칭으로 추출하지 못한 항목을
DART XML의 IFRS 표준 코드(ACODE)를 활용하여 보완합니다.

v3.2 확장 (2026-01-17):
- treasury_stock ACODE 매핑 확장 (dart_TreasuryShares, dart_AcquisitionOfTreasuryShares)
- 차입금 ACODE 매핑 확장:
  - short_term_borrowings: ifrs-full_ShorttermBorrowings, ifrs-full_CurrentPortionOfLongtermBorrowings
  - long_term_borrowings: dart_LongTermBorrowingsGross
  - bonds_payable: dart_BondsPayable, dart_CurrentPortionOfBonds
  - trade_payables: ifrs-full_TradeAndOtherCurrentPayables, dart_ShortTermTradePayables
- 전환사채 필드 신규 추가 (convertible_bonds, convertible_bonds_current)

v3.1 수정 (2026-01-16):
- 섹션별 단위 감지 추가 (단위: 백만원, 천원 등)
- 대기업 데이터 정확도 개선 (삼성전자, SK하이닉스 등)
- 기존 버그: XBRL 추출 시 단위를 무시하고 '원' 단위로 가정 → 수정

주요 대상 항목:
- 부채 세부: 단기차입금, 장기차입금, 매입채무, 사채, 전환사채
- 자본 세부: 자본금, 자본잉여금, 이익잉여금, 자기주식

사용법:
    from scripts.parsers.xbrl_enhancer import XBRLEnhancer

    enhancer = XBRLEnhancer()
    enhanced_values = enhancer.extract_from_xml(xml_content, target_year=2024)
"""

import logging
import re
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class XBRLEnhancer:
    """IFRS ACODE 기반 재무 데이터 추출기"""

    # IFRS ACODE → DB 필드 매핑
    # 재무상태표에서 사용되는 주요 ACODE
    # v3.2 확장 (2026-01-17): treasury_stock, 차입금 ACODE 보완
    ACODE_MAPPING = {
        # ═══════════════════════════════════════════════════════════════
        # 자본 항목 (Equity)
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_IssuedCapital': 'capital_stock',
        'dart_CapitalSurplus': 'capital_surplus',
        'ifrs-full_SharePremium': 'capital_surplus',  # 대체 코드
        'ifrs-full_RetainedEarnings': 'retained_earnings',
        # treasury_stock (자기주식) - v3.2 확장
        'ifrs-full_TreasuryShares': 'treasury_stock',
        'dart_TreasuryShares': 'treasury_stock',  # DART 대체 코드
        'dart_AcquisitionOfTreasuryShares': 'treasury_stock',  # 취득 누계

        # ═══════════════════════════════════════════════════════════════
        # 부채 항목 (Liabilities)
        # ═══════════════════════════════════════════════════════════════
        # 유동부채 - 단기차입금 (v3.2 확장)
        'ifrs-full_TradeAndOtherCurrentPayablesToTradeSuppliers': 'trade_payables',
        'ifrs-full_TradeAndOtherCurrentPayables': 'trade_payables',  # 대체 코드
        'dart_ShortTermTradePayables': 'trade_payables',  # DART 코드
        'ifrs-full_OtherCurrentPayables': 'other_current_liabilities',
        'dart_ShortTermOtherPayables': 'other_current_liabilities',  # DART 코드
        'ifrs-full_CurrentLoansReceivedAndCurrentPortionOfNoncurrentLoansReceived': 'short_term_borrowings',
        'ifrs-full_ShorttermBorrowings': 'short_term_borrowings',  # v3.2 추가
        'ifrs-full_CurrentPortionOfLongtermBorrowings': 'short_term_borrowings',  # 유동성 장기부채
        'dart_CurrentPortionOfBonds': 'bonds_payable_current',  # 유동성 사채
        'dart_CurrentPortionOfConvertibleBonds': 'convertible_bonds_current',  # 유동성 전환사채
        'ifrs-full_CurrentLeaseLiabilities': 'lease_liabilities',
        'ifrs-full_CurrentTaxLiabilities': 'current_tax_liabilities',
        'ifrs-full_CurrentProvisions': 'provisions_current',

        # 비유동부채 - 장기차입금, 사채 (v3.2 확장)
        'ifrs-full_NoncurrentPortionOfNoncurrentLoansReceived': 'long_term_borrowings',
        'dart_LongTermBorrowingsGross': 'long_term_borrowings',  # DART 장기차입금
        'ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued': 'bonds_payable',
        'dart_BondsPayable': 'bonds_payable',  # DART 사채
        'dart_ConvertibleBonds': 'convertible_bonds',  # 전환사채
        'ifrs-full_NoncurrentLeaseLiabilities': 'lease_liabilities',
        'ifrs-full_DeferredTaxLiabilities': 'deferred_tax_liabilities',
        'ifrs-full_NoncurrentProvisions': 'provisions_non_current',
        'ifrs-full_OtherNoncurrentLiabilities': 'other_non_current_liabilities',
        'ifrs-full_OtherNoncurrentPayables': 'other_non_current_liabilities',
        'ifrs-full_NoncurrentRecognisedLiabilitiesDefinedBenefitPlan': 'net_defined_benefit_liabilities',

        # ═══════════════════════════════════════════════════════════════
        # 자산 항목 (Assets) - 보완용
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_CashAndCashEquivalents': 'cash_and_equivalents',
        'ifrs-full_ShorttermDepositsNotClassifiedAsCashEquivalents': 'short_term_investments',
        'ifrs-full_CurrentTradeReceivables': 'trade_and_other_receivables',
        'ifrs-full_Inventories': 'inventories',
        'ifrs-full_CurrentAssets': 'current_assets',
        'ifrs-full_NoncurrentAssets': 'non_current_assets',
        'ifrs-full_Assets': 'total_assets',
        'ifrs-full_PropertyPlantAndEquipment': 'tangible_assets',
        'ifrs-full_IntangibleAssetsOtherThanGoodwill': 'intangible_assets',
        'ifrs-full_DeferredTaxAssets': 'deferred_tax_assets',
        'ifrs-full_NoncurrentRecognisedAssetsDefinedBenefitPlan': 'net_defined_benefit_assets',
        'ifrs-full_RecognisedAssetsDefinedBenefitPlan': 'net_defined_benefit_assets',
        'ifrs-full_InvestmentsInSubsidiaries': 'investments_in_associates',
        'ifrs-full_InvestmentProperty': 'investment_property',

        # ═══════════════════════════════════════════════════════════════
        # 부채/자본 총계
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_Liabilities': 'total_liabilities',
        'ifrs-full_CurrentLiabilities': 'current_liabilities',
        'ifrs-full_NoncurrentLiabilities': 'non_current_liabilities',
        'ifrs-full_Equity': 'total_equity',
        'ifrs-full_EquityAttributableToOwnersOfParent': 'equity_attributable_to_parent',

        # ═══════════════════════════════════════════════════════════════
        # 손익계산서 (Income Statement)
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_Revenue': 'revenue',
        'ifrs-full_CostOfSales': 'cost_of_sales',
        'ifrs-full_GrossProfit': 'gross_profit',
        'dart_OperatingIncomeLoss': 'operating_income',  # 영업이익(손실) - DART 코드
        'ifrs-full_ProfitLoss': 'net_income',
        'ifrs-full_ProfitLossAttributableToOwnersOfParent': 'net_income',
        'ifrs-full_ProfitLossBeforeTax': 'income_before_tax',
        'ifrs-full_IncomeTaxExpenseContinuingOperations': 'tax_expense',
        'ifrs-full_FinanceCosts': 'interest_expense',
        'ifrs-full_FinanceIncome': 'finance_income',

        # ═══════════════════════════════════════════════════════════════
        # 현금흐름표 (Cash Flow Statement)
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_CashFlowsFromUsedInOperatingActivities': 'operating_cash_flow',
        'ifrs-full_CashFlowsFromUsedInInvestingActivities': 'investing_cash_flow',
        'ifrs-full_CashFlowsFromUsedInFinancingActivities': 'financing_cash_flow',
        'ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities': 'capex',
        'ifrs-full_PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities': 'intangible_acquisition',
        'ifrs-full_DividendsPaidClassifiedAsFinancingActivities': 'dividend_paid',
        'dart_ProceedsFromBonds': 'bond_issuance',
        'dart_ProceedsFromShortTermBorrowings': 'short_term_borrowings_proceeds',
    }

    # 연도 추출을 위한 ACONTEXT 패턴
    # CFY2024 = Current Fiscal Year 2024
    # PFY2023 = Previous Fiscal Year 2023
    # BPFY2022 = Before Previous Fiscal Year 2022
    YEAR_PATTERNS = {
        'CFY': 0,   # 당기
        'PFY': -1,  # 전기
        'BPFY': -2, # 전전기
    }

    # 재무제표 유형 (별도/연결)
    FS_TYPE_PATTERNS = {
        'SeparateMember': 'OFS',      # 별도재무제표
        'ConsolidatedMember': 'CFS',  # 연결재무제표
    }

    def __init__(self):
        # TE 태그 파싱을 위한 정규식
        self._te_pattern = re.compile(
            r'<TE\s+([^>]+)>\s*<P>([^<]*)</P>\s*</TE>',
            re.DOTALL
        )
        self._attr_pattern = re.compile(r'(\w+)="([^"]*)"')

        # 단위 감지 패턴 (v3.1 수정: 더 구체적인 패턴 먼저!)
        # "단위 : 백만원"이 "단위 : 원" 패턴에 매칭되는 버그 방지
        self._unit_patterns = [
            # 억원 (가장 먼저)
            (r'단\s*위\s*[:：]\s*억\s*원', 100_000_000),
            (r'\(단위\s*[:：]?\s*억원\)', 100_000_000),
            # 백만원
            (r'단\s*위\s*[:：]\s*백\s*만\s*원', 1_000_000),
            (r'\(단위\s*[:：]?\s*백만원\)', 1_000_000),
            # 천원
            (r'단\s*위\s*[:：]\s*천\s*원', 1_000),
            (r'\(단위\s*[:：]?\s*천원\)', 1_000),
            # 원 (마지막)
            (r'단\s*위\s*[:：]\s*원[^,]', 1),
            (r'\(단위\s*[:：]?\s*원\)', 1),
        ]

    def _detect_unit_from_content(self, content: str) -> int:
        """
        v3.1: 섹션 내용에서 단위 감지

        DART XML에서 '단위: 백만원', '(단위: 천원)' 등의 패턴을 찾아 배수 반환
        기본값: 1 (원)
        """
        for pattern, multiplier in self._unit_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.debug(f"Detected unit multiplier: {multiplier:,}")
                return multiplier
        return 1  # 기본값: 원

    def _detect_section_units(self, xml_content: str) -> Dict[str, int]:
        """
        v3.1: 각 재무제표 섹션별 단위 감지

        Returns:
            {'balance_sheet': 1000000, 'income_statement': 1000000, ...}
        """
        section_units = {}

        # 섹션별 TITLE 패턴과 단위 감지
        sections = [
            ('balance_sheet', [r'재\s*무\s*상\s*태\s*표', r'연\s*결\s*재\s*무\s*상\s*태\s*표']),
            ('income_statement', [r'손\s*익\s*계\s*산\s*서', r'포\s*괄\s*손\s*익\s*계\s*산\s*서', r'연\s*결\s*손\s*익']),
            ('cash_flow', [r'현\s*금\s*흐\s*름\s*표', r'연\s*결\s*현\s*금\s*흐\s*름']),
        ]

        for section_name, patterns in sections:
            for pattern in patterns:
                match = re.search(pattern, xml_content, re.IGNORECASE)
                if match:
                    # 섹션 시작부터 10000자 내에서 단위 감지
                    start_pos = match.start()
                    section_text = xml_content[start_pos:start_pos + 10000]
                    unit = self._detect_unit_from_content(section_text)
                    section_units[section_name] = unit
                    break
            else:
                section_units[section_name] = 1  # 기본값

        logger.debug(f"Section units detected: {section_units}")
        return section_units

    def _get_section_for_field(self, field_name: str) -> str:
        """필드명으로 해당 재무제표 섹션 결정"""
        balance_sheet_fields = {
            'capital_stock', 'capital_surplus', 'retained_earnings', 'treasury_stock',
            'trade_payables', 'short_term_borrowings', 'long_term_borrowings',
            'bonds_payable', 'lease_liabilities', 'deferred_tax_liabilities',
            'current_liabilities', 'non_current_liabilities', 'total_liabilities',
            'total_equity', 'equity_attributable_to_parent',
            'cash_and_equivalents', 'short_term_investments', 'inventories',
            'trade_and_other_receivables', 'current_assets', 'non_current_assets',
            'total_assets', 'tangible_assets', 'intangible_assets',
            'other_current_liabilities', 'provisions_current', 'provisions_non_current',
            'other_non_current_liabilities', 'current_tax_liabilities',
            'deferred_tax_assets', 'net_defined_benefit_assets', 'net_defined_benefit_liabilities',
            'investments_in_associates', 'investment_property',
        }
        income_statement_fields = {
            'revenue', 'cost_of_sales', 'gross_profit', 'operating_income',
            'net_income', 'income_before_tax', 'tax_expense',
            'interest_expense', 'finance_income',
        }
        cash_flow_fields = {
            'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
            'capex', 'intangible_acquisition', 'dividend_paid',
            'bond_issuance', 'short_term_borrowings_proceeds',
        }

        if field_name in balance_sheet_fields:
            return 'balance_sheet'
        elif field_name in income_statement_fields:
            return 'income_statement'
        elif field_name in cash_flow_fields:
            return 'cash_flow'
        return 'balance_sheet'  # 기본값

    def extract_from_xml(
        self,
        xml_content: str,
        target_year: int,
        fs_type: str = 'OFS'
    ) -> Dict[str, Optional[int]]:
        """
        XML에서 ACODE 기반으로 재무 데이터 추출 (v3.1: 단위 감지 적용)

        Args:
            xml_content: DART XML 문자열
            target_year: 대상 회계연도 (예: 2024)
            fs_type: 'OFS' (별도) 또는 'CFS' (연결)

        Returns:
            {field_name: value} 딕셔너리
        """
        result = {}

        # v3.1: 섹션별 단위 감지
        section_units = self._detect_section_units(xml_content)

        # 모든 <TE ACODE="...">...<P>값</P></TE> 추출
        for match in self._te_pattern.finditer(xml_content):
            attrs_str = match.group(1)
            value_str = match.group(2).strip()

            # 속성 파싱
            attrs = dict(self._attr_pattern.findall(attrs_str))

            acode = attrs.get('ACODE', '')
            acontext = attrs.get('ACONTEXT', '')

            # 매핑된 ACODE만 처리
            if acode not in self.ACODE_MAPPING:
                continue

            field_name = self.ACODE_MAPPING[acode]

            # 연도 및 재무제표 유형 확인
            year_match = self._extract_year_from_context(acontext, target_year)
            if year_match is None:
                continue

            fs_match = self._extract_fs_type_from_context(acontext)
            if fs_match != fs_type:
                continue

            # v3.1: 필드에 맞는 섹션의 단위 적용
            section = self._get_section_for_field(field_name)
            unit_multiplier = section_units.get(section, 1)

            # 금액 파싱 (단위 적용)
            amount = self._parse_amount(value_str, unit_multiplier)
            if amount is not None:
                # 이미 값이 있으면 덮어쓰지 않음 (첫 번째 값 우선)
                if field_name not in result:
                    result[field_name] = amount

        logger.debug(f"XBRL extracted {len(result)} fields for {target_year} ({fs_type})")
        return result

    def _extract_year_from_context(
        self,
        acontext: str,
        target_year: int
    ) -> Optional[int]:
        """
        ACONTEXT에서 회계연도 추출

        예: CFY2024eFY... → 2024년 (당기)
            PFY2023eFY... → 2023년 (전기)
        """
        # CFY2024, PFY2023, BPFY2022 패턴 찾기
        year_match = re.search(r'(CFY|PFY|BPFY)(\d{4})', acontext)
        if not year_match:
            return None

        prefix = year_match.group(1)
        stated_year = int(year_match.group(2))

        # target_year가 2024이고, acontext가 CFY2024면 매칭
        # target_year가 2024이고, acontext가 PFY2023이면 불일치
        if stated_year == target_year:
            return target_year

        return None

    def _extract_fs_type_from_context(self, acontext: str) -> str:
        """ACONTEXT에서 재무제표 유형 추출"""
        if 'SeparateMember' in acontext:
            return 'OFS'
        elif 'ConsolidatedMember' in acontext:
            return 'CFS'
        return 'OFS'  # 기본값

    def _parse_amount(self, value_str: str, unit_multiplier: int = 1) -> Optional[int]:
        """
        금액 문자열을 정수로 변환 (v3.1: 단위 적용)

        Args:
            value_str: 금액 문자열 (예: '1,234,567')
            unit_multiplier: 단위 배수 (1=원, 1000=천원, 1000000=백만원)

        Returns:
            정수 금액 (원 단위) 또는 None
        """
        if not value_str:
            return None

        # 빈 값이나 '-' 처리
        value_str = value_str.strip()
        if value_str in ['', '-', '－', '―']:
            return None

        try:
            # 괄호 = 음수
            is_negative = value_str.startswith('(') or value_str.startswith('-')

            # 숫자만 추출
            cleaned = re.sub(r'[^0-9.]', '', value_str)
            if not cleaned:
                return None

            # 소수점 처리
            if '.' in cleaned:
                amount = float(cleaned)
            else:
                amount = int(cleaned)

            # v3.1: 단위 적용
            result = int(amount * unit_multiplier)

            return -result if is_negative else result

        except (ValueError, TypeError):
            return None

    def enhance_parsed_data(
        self,
        xml_content: str,
        existing_data: Dict[str, Optional[int]],
        target_year: int,
        fs_type: str = 'OFS'
    ) -> Dict[str, Optional[int]]:
        """
        기존 파싱 결과를 XBRL 데이터로 보완

        기존에 NULL인 항목만 XBRL 값으로 채움

        Args:
            xml_content: DART XML 문자열
            existing_data: 기존 FinancialParser 결과
            target_year: 대상 회계연도
            fs_type: 재무제표 유형

        Returns:
            보완된 데이터 딕셔너리
        """
        # XBRL 데이터 추출
        xbrl_data = self.extract_from_xml(xml_content, target_year, fs_type)

        # 기존 데이터 복사
        result = existing_data.copy()

        # NULL인 항목만 보완
        enhanced_count = 0
        for field, value in xbrl_data.items():
            if result.get(field) is None and value is not None:
                result[field] = value
                enhanced_count += 1
                logger.debug(f"Enhanced {field}: {value}")

        if enhanced_count > 0:
            logger.info(f"XBRL enhanced {enhanced_count} fields")

        return result

    def get_all_xbrl_values(
        self,
        xml_content: str,
        target_year: int
    ) -> Dict[str, Dict[str, Optional[int]]]:
        """
        OFS와 CFS 모두에서 XBRL 값 추출

        Returns:
            {'OFS': {...}, 'CFS': {...}}
        """
        return {
            'OFS': self.extract_from_xml(xml_content, target_year, 'OFS'),
            'CFS': self.extract_from_xml(xml_content, target_year, 'CFS'),
        }


# ═══════════════════════════════════════════════════════════════════════════
# CLI 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    import zipfile
    from pathlib import Path

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.parsers.xbrl_enhancer <zip_path> [year]")
        print("Example: python -m scripts.parsers.xbrl_enhancer data/dart/batch_003/01412822/2025/20250319000924.zip 2024")
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    target_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2024

    if not zip_path.exists():
        print(f"File not found: {zip_path}")
        sys.exit(1)

    # ZIP에서 XML 추출
    xml_content = None
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.xml') and not name.startswith('_'):
                # 가장 큰 XML 선택
                info = zf.getinfo(name)
                if xml_content is None or info.file_size > len(xml_content):
                    raw = zf.read(name)
                    try:
                        xml_content = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        xml_content = raw.decode('euc-kr', errors='replace')

    if not xml_content:
        print("No XML found in ZIP")
        sys.exit(1)

    # XBRL 추출
    enhancer = XBRLEnhancer()

    print(f"\n=== XBRL Extraction for {target_year} ===\n")

    for fs_type in ['OFS', 'CFS']:
        data = enhancer.extract_from_xml(xml_content, target_year, fs_type)
        print(f"\n[{fs_type}] {len(data)} fields extracted:")
        for field, value in sorted(data.items()):
            if value is not None:
                print(f"  {field}: {value:,}")
