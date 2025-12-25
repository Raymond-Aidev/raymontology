"""
DART 재무제표 파서 서비스 - RaymondsIndex용 상세 재무 데이터 수집

DART OpenAPI fnlttSinglAcnt 엔드포인트를 사용하여
현금흐름표 상세 항목(CAPEX, 배당금 등)을 수집합니다.
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class DARTFinancialParser:
    """
    DART API 재무제표 파서

    fnlttSinglAcnt (단일회사 전체 재무제표) 엔드포인트 사용
    """

    DART_API_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"

    # 계정과목 매핑 - 다양한 표현을 표준 필드로 변환
    ACCOUNT_MAPPING = {
        # ═══════════════════════════════════════════════════════════════
        # 재무상태표 (Balance Sheet)
        # ═══════════════════════════════════════════════════════════════
        'cash_and_equivalents': [
            '현금및현금성자산', '현금및현금등가물', '현금 및 현금성자산',
            '현금과현금성자산', 'I.현금및현금성자산', '1.현금및현금성자산'
        ],
        'short_term_investments': [
            '단기금융상품', '단기금융자산', '단기투자자산',
            '유동금융자산', '기타유동금융자산'
        ],
        'trade_receivables': [
            '매출채권', '매출채권및기타채권', '매출채권 및 기타채권',
            '단기매출채권', '매출채권및기타유동채권'
        ],
        'inventories': [
            '재고자산', '재고자산(순액)', '상품및제품',
            '원재료', '제품', '상품'
        ],
        'tangible_assets': [
            '유형자산', '유형자산(순액)', '토지,건물및기계장치',
            '토지', '건물', '기계장치', '구축물'
        ],
        'intangible_assets': [
            '무형자산', '무형자산(순액)', '영업권',
            '기타무형자산', '소프트웨어'
        ],
        'total_assets': [
            '자산총계', '자산 총계', '자산합계',
            '총자산', '합계(자산)'
        ],
        'current_liabilities': [
            '유동부채', '유동부채합계', '유동부채 합계',
            'I.유동부채', '1.유동부채'
        ],
        'non_current_liabilities': [
            '비유동부채', '비유동부채합계', '비유동부채 합계',
            'II.비유동부채', '2.비유동부채'
        ],
        'total_liabilities': [
            '부채총계', '부채 총계', '부채합계',
            '총부채', '합계(부채)'
        ],
        'total_equity': [
            '자본총계', '자본 총계', '자본합계',
            '총자본', '합계(자본)', '자기자본'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 손익계산서 (Income Statement)
        # ═══════════════════════════════════════════════════════════════
        'revenue': [
            '매출액', '수익(매출액)', '영업수익',
            '매출', '영업매출', '매출수익'
        ],
        'cost_of_sales': [
            '매출원가', '영업비용', '매출비용',
            '상품매출원가', '제품매출원가'
        ],
        'selling_admin_expenses': [
            '판매비와관리비', '판관비', '판매관리비',
            '판매비', '관리비', '판매비및관리비'
        ],
        'operating_income': [
            '영업이익', '영업이익(손실)', '영업손익',
            '사업이익'
        ],
        'net_income': [
            '당기순이익', '분기순이익', '반기순이익',
            '당기순이익(손실)', '연결당기순이익',
            '지배기업소유주지분순이익'
        ],

        # ═══════════════════════════════════════════════════════════════
        # 현금흐름표 (Cash Flow Statement) - RaymondsIndex 핵심
        # ═══════════════════════════════════════════════════════════════
        'operating_cash_flow': [
            '영업활동현금흐름', '영업활동으로인한현금흐름',
            '영업활동 현금흐름', '영업활동 순현금흐름',
            'I.영업활동현금흐름', '1.영업활동현금흐름'
        ],
        'investing_cash_flow': [
            '투자활동현금흐름', '투자활동으로인한현금흐름',
            '투자활동 현금흐름', '투자활동 순현금흐름',
            'II.투자활동현금흐름', '2.투자활동현금흐름'
        ],
        'financing_cash_flow': [
            '재무활동현금흐름', '재무활동으로인한현금흐름',
            '재무활동 현금흐름', '재무활동 순현금흐름',
            'III.재무활동현금흐름', '3.재무활동현금흐름'
        ],
        'capex': [
            '유형자산의취득', '유형자산의 취득', '유형자산취득',
            '유형자산의 증가', '설비투자', '시설투자',
            '토지의취득', '건물의취득', '기계장치의취득',
            '유형자산 취득으로 인한 현금유출'
        ],
        'intangible_acquisition': [
            '무형자산의취득', '무형자산의 취득', '무형자산취득',
            '무형자산의 증가', '개발비의 증가'
        ],
        'dividend_paid': [
            '배당금지급', '배당금의지급', '배당금 지급',
            '현금배당금', '현금배당금의지급', '배당금지급액'
        ],
        'treasury_stock_acquisition': [
            '자기주식취득', '자기주식의취득', '자기주식 취득',
            '자사주 취득', '자기주식의 취득'
        ],
        'stock_issuance': [
            '주식발행', '유상증자', '신주발행',
            '자본금의 증가', '주식의발행'
        ],
        'bond_issuance': [
            '사채발행', '사채의발행', '사채 발행',
            '회사채발행', '전환사채발행', '교환사채발행'
        ],
    }

    def __init__(self, api_key: str):
        """
        Args:
            api_key: DART OpenAPI 키
        """
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(3)  # 동시 요청 제한

    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()

    async def fetch_financial_statements(
        self,
        corp_code: str,
        year: int,
        report_code: str = '11011',  # 11011=사업보고서
        fs_div: str = 'CFS'  # CFS=연결, OFS=별도
    ) -> Optional[List[Dict]]:
        """
        DART API에서 재무제표 조회

        Args:
            corp_code: 기업 고유번호 (8자리)
            year: 사업연도
            report_code: 보고서코드 (11011=사업, 11012=반기, 11013=1분기, 11014=3분기)
            fs_div: 재무제표구분 (CFS=연결, OFS=별도)

        Returns:
            재무제표 항목 리스트 또는 None
        """
        if not self._session:
            raise RuntimeError("Session not initialized. Use 'async with'.")

        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': str(year),
            'reprt_code': report_code,
            'fs_div': fs_div
        }

        async with self._semaphore:
            try:
                await asyncio.sleep(0.5)  # Rate limiting

                async with self._session.get(self.DART_API_URL, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {corp_code}/{year}")
                        return None

                    data = await response.json()

                    status = data.get('status')
                    if status != '000':
                        # 013 = 데이터 없음 (정상적인 경우)
                        if status != '013':
                            logger.debug(f"DART API status {status} for {corp_code}/{year}: {data.get('message')}")
                        return None

                    return data.get('list', [])

            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {corp_code}/{year}")
                return None
            except Exception as e:
                logger.error(f"Error fetching {corp_code}/{year}: {e}")
                return None

    def parse_financial_details(
        self,
        statements: List[Dict],
        year: int,
        fs_type: str = 'CFS',
        quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        재무제표 항목을 파싱하여 financial_details 형식으로 변환

        Args:
            statements: DART API 응답 리스트
            year: 사업연도
            fs_type: 재무제표 유형 (CFS/OFS)
            quarter: 분기 (None=연간, 1=1분기, 2=반기, 3=3분기)

        Returns:
            financial_details 필드 딕셔너리
        """
        report_types = {None: 'annual', 1: 'q1', 2: 'semi', 3: 'q3'}
        result = {
            'fiscal_year': year,
            'fiscal_quarter': quarter,
            'report_type': report_types.get(quarter, 'annual'),
            'fs_type': fs_type,
            'data_source': 'DART'
        }

        # 계정과목별 금액 추출
        for statement in statements:
            account_name = statement.get('account_nm', '').strip()
            amount_str = statement.get('thstrm_amount', '')

            # 금액 파싱
            amount = self._parse_amount(amount_str)
            if amount is None:
                continue

            # 계정과목 매핑
            for field, aliases in self.ACCOUNT_MAPPING.items():
                for alias in aliases:
                    if alias in account_name or account_name in alias:
                        # 이미 값이 있는 경우, 더 구체적인 항목이면 덮어쓰지 않음
                        if field not in result or result[field] is None:
                            result[field] = amount
                        break

        # CAPEX는 음수로 저장 (유출이므로)
        if 'capex' in result and result['capex'] is not None and result['capex'] > 0:
            result['capex'] = -result['capex']

        return result

    def _parse_amount(self, amount_str: str) -> Optional[int]:
        """
        금액 문자열을 정수로 변환

        Args:
            amount_str: 금액 문자열 (예: "1,234,567" 또는 "-1,234,567")

        Returns:
            정수 금액 또는 None
        """
        if not amount_str or amount_str == '-' or amount_str.strip() == '':
            return None

        try:
            # 콤마, 공백 제거
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()

            # 괄호로 묶인 음수 처리: (123) -> -123
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]

            return int(cleaned)
        except (ValueError, AttributeError):
            return None

    async def collect_company_financials(
        self,
        corp_code: str,
        years: List[int] = None,
        prefer_consolidated: bool = True,
        quarter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        특정 기업의 여러 연도 재무 데이터 수집

        Args:
            corp_code: 기업 고유번호
            years: 수집 연도 리스트 (기본: [2022, 2023, 2024])
            prefer_consolidated: 연결재무제표 우선 (True)
            quarter: 분기 (None=연간, 1=1분기, 2=반기, 3=3분기)

        Returns:
            연도별 재무 데이터 리스트
        """
        if years is None:
            years = [2022, 2023, 2024]

        results = []
        report_code = get_report_code(quarter)

        for year in years:
            # 연결재무제표 먼저 시도
            fs_types = ['CFS', 'OFS'] if prefer_consolidated else ['OFS', 'CFS']

            for fs_type in fs_types:
                statements = await self.fetch_financial_statements(
                    corp_code=corp_code,
                    year=year,
                    report_code=report_code,
                    fs_div=fs_type
                )

                if statements:
                    parsed = self.parse_financial_details(statements, year, fs_type, quarter)
                    if self._has_essential_data(parsed):
                        results.append(parsed)
                        break  # 데이터 찾았으면 다음 연도로

        return results

    def _has_essential_data(self, data: Dict) -> bool:
        """
        RaymondsIndex 계산에 필수적인 데이터가 있는지 확인

        Args:
            data: 파싱된 재무 데이터

        Returns:
            필수 데이터 존재 여부
        """
        # 최소 필수 항목: 자산총계, 매출액, 영업활동현금흐름 중 하나
        essential_fields = ['total_assets', 'revenue', 'operating_cash_flow']
        return any(data.get(field) is not None for field in essential_fields)

    def validate_data_quality(self, data: Dict) -> float:
        """
        데이터 품질 점수 계산 (0.0 ~ 1.0)

        Args:
            data: 파싱된 재무 데이터

        Returns:
            품질 점수
        """
        # 가중치 부여된 필드
        weighted_fields = {
            # 재무상태표 (20%)
            'total_assets': 4, 'total_equity': 3, 'cash_and_equivalents': 3,
            # 손익계산서 (30%)
            'revenue': 6, 'operating_income': 5, 'net_income': 4,
            # 현금흐름표 - 핵심 (50%)
            'operating_cash_flow': 8, 'capex': 10, 'dividend_paid': 4,
            'investing_cash_flow': 5, 'financing_cash_flow': 3
        }

        total_weight = sum(weighted_fields.values())
        achieved_weight = sum(
            weight for field, weight in weighted_fields.items()
            if data.get(field) is not None
        )

        return round(achieved_weight / total_weight, 2)


# 헬퍼 함수
def get_report_code(quarter: Optional[int] = None) -> str:
    """
    분기별 보고서 코드 반환

    Args:
        quarter: 분기 (None=연간, 1=1분기, 2=반기, 3=3분기)

    Returns:
        DART 보고서 코드
    """
    codes = {
        None: '11011',  # 사업보고서 (연간)
        1: '11013',     # 1분기보고서
        2: '11012',     # 반기보고서
        3: '11014',     # 3분기보고서
    }
    return codes.get(quarter, '11011')
