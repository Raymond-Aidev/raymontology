"""
DART API Client

전자공시시스템(DART) OpenAPI 클라이언트
Rate Limiting: 초당 10 요청
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import zipfile
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CorpCode:
    """기업 코드"""
    def __init__(self, corp_code: str, corp_name: str, stock_code: Optional[str] = None):
        self.corp_code = corp_code  # 8자리 고유번호
        self.corp_name = corp_name
        self.stock_code = stock_code  # 6자리 종목코드

    def __repr__(self):
        return f"<CorpCode({self.corp_code}, {self.corp_name}, {self.stock_code})>"


class DARTClient:
    """
    DART API 클라이언트

    OpenAPI: https://opendart.fss.or.kr/
    """

    BASE_URL = "https://opendart.fss.or.kr/api"
    MAX_REQUESTS_PER_SECOND = 2  # DART 서버 안정성을 위해 낮춤

    def __init__(self, api_key: str):
        """
        Args:
            api_key: DART API 키 (https://opendart.fss.or.kr/에서 발급)
        """
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate Limiting
        self._request_times: List[float] = []
        self._semaphore = asyncio.Semaphore(self.MAX_REQUESTS_PER_SECOND)

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        """Rate Limiting 적용"""
        now = asyncio.get_event_loop().time()

        # 1초 이전 요청 제거
        self._request_times = [t for t in self._request_times if now - t < 1.0]

        # 초당 요청 제한 확인
        if len(self._request_times) >= self.MAX_REQUESTS_PER_SECOND:
            sleep_time = 1.0 - (now - self._request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self._request_times.append(now)

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        API 요청

        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터

        Returns:
            응답 JSON

        Raises:
            Exception: API 에러
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        # Rate Limiting
        async with self._semaphore:
            await self._rate_limit()

            # API 키 추가
            if params is None:
                params = {}
            params["crtfc_key"] = self.api_key

            url = f"{self.BASE_URL}/{endpoint}"

            try:
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()

                    # JSON 응답
                    data = await response.json()

                    # 에러 체크
                    status = data.get("status")
                    if status != "000":
                        message = data.get("message", "Unknown error")
                        raise Exception(f"DART API Error {status}: {message}")

                    return data

            except aiohttp.ClientError as e:
                logger.error(f"HTTP Error: {e}")
                raise

    async def get_corp_code_list(self) -> List[CorpCode]:
        """
        전체 기업 코드 목록 조회

        Returns:
            CorpCode 리스트
        """
        endpoint = "corpCode.xml"

        try:
            # XML zip 파일 다운로드
            if not self.session:
                raise RuntimeError("Session not initialized")

            async with self._semaphore:
                await self._rate_limit()

                url = f"{self.BASE_URL}/{endpoint}"
                params = {"crtfc_key": self.api_key}

                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    zip_data = await response.read()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                xml_content = zf.read("CORPCODE.xml").decode("utf-8")

            # XML 파싱 (간단한 텍스트 파싱)
            corp_codes = []
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_content)
            for item in root.findall("list"):
                corp_code = item.findtext("corp_code", "")
                corp_name = item.findtext("corp_name", "")
                stock_code = item.findtext("stock_code", None)

                # 종목코드가 없으면 비상장
                if stock_code and stock_code.strip():
                    corp_codes.append(CorpCode(corp_code, corp_name, stock_code))

            logger.info(f"Retrieved {len(corp_codes)} corporations")
            return corp_codes

        except Exception as e:
            logger.error(f"Failed to get corp code list: {e}")
            raise

    async def get_disclosure_list(
        self,
        corp_code: str,
        start_date: str,
        end_date: str,
        page_no: int = 1,
        page_count: int = 100
    ) -> Dict:
        """
        공시 목록 조회

        Args:
            corp_code: 기업 고유번호 (8자리)
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            page_no: 페이지 번호 (기본 1)
            page_count: 페이지당 건수 (기본 100, 최대 100)

        Returns:
            {
                "status": "000",
                "list": [
                    {
                        "rcept_no": "접수번호",
                        "corp_name": "회사명",
                        "report_nm": "보고서명",
                        "rcept_dt": "접수일자",
                        ...
                    }
                ]
            }
        """
        endpoint = "list.json"

        params = {
            "corp_code": corp_code,
            "bgn_de": start_date,
            "end_de": end_date,
            "page_no": page_no,
            "page_count": page_count,
        }

        return await self._request(endpoint, params)

    async def get_disclosure_detail(self, rcept_no: str) -> Dict:
        """
        공시 상세 정보 조회

        Args:
            rcept_no: 접수번호

        Returns:
            공시 상세 정보
        """
        endpoint = "document.json"
        params = {"rcept_no": rcept_no}

        return await self._request(endpoint, params)

    async def download_document(
        self,
        rcept_no: str,
        save_path: Path
    ) -> bool:
        """
        공시 문서 다운로드 (ZIP 파일)

        Args:
            rcept_no: 접수번호
            save_path: 저장 경로

        Returns:
            성공 여부
        """
        try:
            # DART OpenAPI 문서 다운로드 endpoint
            url = f"{self.BASE_URL}/document.xml"
            params = {
                "crtfc_key": self.api_key,
                "rcept_no": rcept_no
            }

            if not self.session:
                raise RuntimeError("Session not initialized")

            async with self._semaphore:
                await self._rate_limit()

                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    content = await response.read()

            # 파일 저장
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(content)

            logger.info(f"Downloaded document: {rcept_no} -> {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download document {rcept_no}: {e}")
            return False

    async def search_company(self, company_name: str) -> List[CorpCode]:
        """
        회사명으로 검색

        Args:
            company_name: 회사명 (부분 일치)

        Returns:
            매칭되는 CorpCode 리스트
        """
        all_corps = await self.get_corp_code_list()

        # 부분 일치 검색
        results = [
            corp for corp in all_corps
            if company_name in corp.corp_name
        ]

        return results


# ============================================================================
# 헬퍼 함수
# ============================================================================

def format_date(date: datetime) -> str:
    """datetime을 DART API 형식(YYYYMMDD)으로 변환"""
    return date.strftime("%Y%m%d")


def parse_date(date_str: str) -> datetime:
    """DART API 형식(YYYYMMDD)을 datetime으로 변환"""
    return datetime.strptime(date_str, "%Y%m%d")
