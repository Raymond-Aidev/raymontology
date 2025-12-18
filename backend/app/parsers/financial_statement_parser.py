"""
재무제표 파서

DART OpenAPI의 단일회사 전체 재무제표 API 사용:
- fnlttSinglAcntAll (단일회사 전체 재무제표)

참고: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class FinancialStatementParser:
    """재무제표 파서"""

    # 계정과목 매핑 (표준화)
    ACCOUNT_MAPPING = {
        # 현금 및 현금성 자산
        "현금및현금성자산": "cash_and_equivalents",
        "현금및현금등가물": "cash_and_equivalents",
        "현금": "cash_and_equivalents",

        # 단기 금융 상품
        "단기금융상품": "short_term_investments",
        "단기투자자산": "short_term_investments",
        "단기금융자산": "short_term_investments",

        # 매출채권
        "매출채권": "accounts_receivable",
        "매출채권및기타채권": "accounts_receivable",
        "매출채권과기타채권": "accounts_receivable",
        "단기매출채권": "accounts_receivable",

        # 재고자산
        "재고자산": "inventory",
        "상품": "inventory",
        "제품": "inventory",
        "재공품": "inventory",

        # 유동자산
        "유동자산": "current_assets",
        "유동자산합계": "current_assets",

        # 비유동자산
        "비유동자산": "non_current_assets",
        "비유동자산합계": "non_current_assets",

        # 자산총계
        "자산총계": "total_assets",
        "자산총액": "total_assets",

        # 매입채무
        "매입채무": "accounts_payable",
        "매입채무및기타채무": "accounts_payable",
        "단기매입채무": "accounts_payable",

        # 단기차입금
        "단기차입금": "short_term_debt",
        "단기借入金": "short_term_debt",

        # 유동부채
        "유동부채": "current_liabilities",
        "유동부채합계": "current_liabilities",

        # 장기차입금
        "장기차입금": "long_term_debt",
        "장기借入金": "long_term_debt",

        # 비유동부채
        "비유동부채": "non_current_liabilities",
        "비유동부채합계": "non_current_liabilities",

        # 부채총계
        "부채총계": "total_liabilities",
        "부채총액": "total_liabilities",

        # 자본금
        "자본금": "capital_stock",
        "資本金": "capital_stock",

        # 이익잉여금
        "이익잉여금": "retained_earnings",
        "利益剩餘金": "retained_earnings",
        "미처분이익잉여금": "retained_earnings",

        # 자본총계
        "자본총계": "total_equity",
        "자본총액": "total_equity",
        "자본합계": "total_equity",

        # 매출액
        "매출액": "revenue",
        "수익": "revenue",
        "영업수익": "revenue",
        "売上高": "revenue",

        # 매출원가
        "매출원가": "cost_of_sales",
        "매출총원가": "cost_of_sales",
        "売上原価": "cost_of_sales",

        # 매출총이익
        "매출총이익": "gross_profit",
        "매출총익": "gross_profit",

        # 판매비와 관리비
        "판매비와관리비": "operating_expenses",
        "판매비및관리비": "operating_expenses",
        "판매비와일반관리비": "operating_expenses",

        # 영업이익
        "영업이익": "operating_profit",
        "영업손익": "operating_profit",
        "營業利益": "operating_profit",

        # 당기순이익
        "당기순이익": "net_income",
        "당기순이익(손실)": "net_income",
        "분기순이익": "net_income",
        "반기순이익": "net_income",
        "當期純利益": "net_income",

        # 현금흐름
        "영업활동으로인한현금흐름": "operating_cash_flow",
        "영업활동현금흐름": "operating_cash_flow",
        "투자활동으로인한현금흐름": "investing_cash_flow",
        "투자활동현금흐름": "investing_cash_flow",
        "재무활동으로인한현금흐름": "financing_cash_flow",
        "재무활동현금흐름": "financing_cash_flow",
    }

    @classmethod
    def parse_amount(cls, amount_str: str) -> Optional[int]:
        """
        금액 문자열을 정수로 변환

        Args:
            amount_str: 금액 문자열 (예: "1,234,567", "-1234567")

        Returns:
            정수 금액 (단위: 원) 또는 None
        """
        if not amount_str or amount_str.strip() in ["", "-", "0", "N/A"]:
            return None

        try:
            # 쉼표 제거 후 정수 변환
            cleaned = amount_str.replace(",", "").strip()
            return int(float(cleaned))
        except (ValueError, AttributeError):
            logger.warning(f"금액 파싱 실패: {amount_str}")
            return None

    @classmethod
    def normalize_account_name(cls, account_name: str) -> Optional[str]:
        """
        계정과목명을 표준 컬럼명으로 변환

        Args:
            account_name: 원본 계정과목명

        Returns:
            표준 컬럼명 또는 None
        """
        # 공백 및 특수문자 제거
        cleaned = account_name.replace(" ", "").replace(".", "").strip()

        # 직접 매칭
        if cleaned in cls.ACCOUNT_MAPPING:
            return cls.ACCOUNT_MAPPING[cleaned]

        # 부분 매칭 (포함)
        for key, value in cls.ACCOUNT_MAPPING.items():
            if key in cleaned or cleaned in key:
                return value

        return None

    @classmethod
    def parse_dart_api_response(cls, api_data: List[Dict]) -> Dict[str, Optional[int]]:
        """
        DART API 응답 데이터를 파싱하여 재무제표 딕셔너리 반환

        Args:
            api_data: DART API 응답 리스트
                [
                    {
                        "account_nm": "현금및현금성자산",
                        "thstrm_amount": "1234567890"
                    },
                    ...
                ]

        Returns:
            {
                "cash_and_equivalents": 1234567890,
                "revenue": 5000000000,
                ...
            }
        """
        result = {}

        for item in api_data:
            account_name = item.get("account_nm", "")
            amount_str = item.get("thstrm_amount", "")  # 당기금액

            # 계정과목 정규화
            normalized = cls.normalize_account_name(account_name)
            if not normalized:
                continue

            # 금액 파싱
            amount = cls.parse_amount(amount_str)

            # 결과에 추가 (이미 있으면 덮어쓰지 않음 - 첫 번째 값 우선)
            if normalized not in result:
                result[normalized] = amount

        return result

    @classmethod
    def extract_period_info(cls, api_data: List[Dict]) -> Tuple[int, Optional[str], str]:
        """
        API 응답에서 회계연도 및 분기 정보 추출

        Args:
            api_data: DART API 응답 리스트

        Returns:
            (fiscal_year, quarter, report_type)
            예: (2024, "Q2", "분기보고서")
        """
        if not api_data:
            raise ValueError("API 데이터가 비어있습니다")

        first_item = api_data[0]

        # 회계연도
        fiscal_year = int(first_item.get("bsns_year", 0))

        # 분기
        reprt_code = first_item.get("reprt_code", "")
        quarter_mapping = {
            "11011": None,      # 사업보고서 (연간)
            "11012": "Q1",      # 1분기보고서
            "11013": "Q2",      # 반기보고서
            "11014": "Q3",      # 3분기보고서
        }
        quarter = quarter_mapping.get(reprt_code)

        # 보고서 유형
        report_type_mapping = {
            "11011": "사업보고서",
            "11012": "분기보고서",
            "11013": "반기보고서",
            "11014": "분기보고서",
        }
        report_type = report_type_mapping.get(reprt_code, "사업보고서")

        return fiscal_year, quarter, report_type
