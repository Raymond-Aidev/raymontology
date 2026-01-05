"""
XBRLEnhancer - IFRS ACODE 기반 재무 데이터 보완 모듈

기존 FinancialParser가 텍스트 패턴 매칭으로 추출하지 못한 항목을
DART XML의 IFRS 표준 코드(ACODE)를 활용하여 보완합니다.

주요 대상 항목 (기존 0% 커버리지):
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
    ACODE_MAPPING = {
        # ═══════════════════════════════════════════════════════════════
        # 자본 항목 (Equity)
        # ═══════════════════════════════════════════════════════════════
        'ifrs-full_IssuedCapital': 'capital_stock',
        'dart_CapitalSurplus': 'capital_surplus',
        'ifrs-full_SharePremium': 'capital_surplus',  # 대체 코드
        'ifrs-full_RetainedEarnings': 'retained_earnings',
        'ifrs-full_TreasuryShares': 'treasury_stock',

        # ═══════════════════════════════════════════════════════════════
        # 부채 항목 (Liabilities)
        # ═══════════════════════════════════════════════════════════════
        # 유동부채
        'ifrs-full_TradeAndOtherCurrentPayablesToTradeSuppliers': 'trade_payables',
        'ifrs-full_OtherCurrentPayables': 'other_current_liabilities',
        'ifrs-full_CurrentLoansReceivedAndCurrentPortionOfNoncurrentLoansReceived': 'short_term_borrowings',
        'ifrs-full_CurrentLeaseLiabilities': 'lease_liabilities',
        'ifrs-full_CurrentTaxLiabilities': 'current_tax_liabilities',
        'ifrs-full_CurrentProvisions': 'provisions_current',

        # 비유동부채
        'ifrs-full_NoncurrentPortionOfNoncurrentLoansReceived': 'long_term_borrowings',
        'ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued': 'bonds_payable',
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

    def extract_from_xml(
        self,
        xml_content: str,
        target_year: int,
        fs_type: str = 'OFS'
    ) -> Dict[str, Optional[int]]:
        """
        XML에서 ACODE 기반으로 재무 데이터 추출

        Args:
            xml_content: DART XML 문자열
            target_year: 대상 회계연도 (예: 2024)
            fs_type: 'OFS' (별도) 또는 'CFS' (연결)

        Returns:
            {field_name: value} 딕셔너리
        """
        result = {}

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

            # 금액 파싱
            amount = self._parse_amount(value_str)
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

    def _parse_amount(self, value_str: str) -> Optional[int]:
        """
        금액 문자열을 정수로 변환

        DART XBRL은 단위가 '원'으로 통일되어 있음
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
                amount = int(float(cleaned))
            else:
                amount = int(cleaned)

            return -amount if is_negative else amount

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
