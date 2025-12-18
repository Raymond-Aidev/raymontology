"""
DART Crawler

공시 데이터 수집 및 저장
"""
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from tqdm.asyncio import tqdm

from app.crawlers.dart_client import DARTClient, CorpCode, format_date
from app.config import settings

logger = logging.getLogger(__name__)


class DARTCrawler:
    """
    DART 공시 크롤러

    진행률 표시 및 에러 핸들링
    """

    def __init__(
        self,
        api_key: str,
        data_dir: Optional[Path] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0
    ):
        """
        Args:
            api_key: DART API 키
            data_dir: 데이터 저장 디렉토리 (기본: ./data/dart)
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
        """
        self.api_key = api_key
        self.data_dir = data_dir or Path("./data/dart")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 통계
        self.stats = {
            "total_companies": 0,
            "total_disclosures": 0,
            "downloaded_documents": 0,
            "failed_downloads": 0,
            "errors": []
        }

    async def crawl_all_companies(
        self,
        years: int = 3,
        batch_size: int = 10
    ) -> Dict:
        """
        전체 기업 공시 수집 (최근 N년)

        Args:
            years: 수집 기간 (년)
            batch_size: 동시 처리할 기업 수

        Returns:
            통계 정보
        """
        logger.info(f"Starting full crawl: {years} years")

        # 날짜 범위
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        async with DARTClient(self.api_key) as client:
            # 기업 코드 목록
            logger.info("Fetching corporation list...")
            corp_codes = await client.get_corp_code_list()
            self.stats["total_companies"] = len(corp_codes)

            logger.info(f"Found {len(corp_codes)} corporations")

            # 배치 처리
            for i in tqdm(
                range(0, len(corp_codes), batch_size),
                desc="Companies",
                unit="batch"
            ):
                batch = corp_codes[i:i + batch_size]

                # 동시 실행
                tasks = [
                    self._crawl_company(client, corp, start_date, end_date)
                    for corp in batch
                ]

                await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Crawl completed: {self.stats}")
        return self.stats

    async def crawl_recent(
        self,
        hours: int = 24,
        batch_size: int = 10
    ) -> Dict:
        """
        최근 N시간 공시 수집

        Args:
            hours: 수집 기간 (시간)
            batch_size: 동시 처리할 기업 수

        Returns:
            통계 정보
        """
        logger.info(f"Starting recent crawl: {hours} hours")

        # 날짜 범위
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)

        async with DARTClient(self.api_key) as client:
            # 기업 코드 목록
            corp_codes = await client.get_corp_code_list()
            self.stats["total_companies"] = len(corp_codes)

            # 배치 처리
            for i in tqdm(
                range(0, len(corp_codes), batch_size),
                desc="Recent disclosures",
                unit="batch"
            ):
                batch = corp_codes[i:i + batch_size]

                tasks = [
                    self._crawl_company(client, corp, start_date, end_date)
                    for corp in batch
                ]

                await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Recent crawl completed: {self.stats}")
        return self.stats

    async def crawl_company(
        self,
        corp_code: str,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        특정 기업 공시 수집

        Args:
            corp_code: 기업 고유번호
            start_date: 시작일
            end_date: 종료일

        Returns:
            수집한 공시 수
        """
        async with DARTClient(self.api_key) as client:
            # 기업 정보 찾기
            all_corps = await client.get_corp_code_list()
            corp = next((c for c in all_corps if c.corp_code == corp_code), None)

            if not corp:
                logger.error(f"Corporation not found: {corp_code}")
                return 0

            return await self._crawl_company(client, corp, start_date, end_date)

    async def _crawl_company(
        self,
        client: DARTClient,
        corp: CorpCode,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        기업 공시 수집 (내부 메서드)

        Args:
            client: DART 클라이언트
            corp: 기업 정보
            start_date: 시작일
            end_date: 종료일

        Returns:
            수집한 공시 수
        """
        count = 0

        try:
            # 공시 목록 조회
            result = await client.get_disclosure_list(
                corp_code=corp.corp_code,
                start_date=format_date(start_date),
                end_date=format_date(end_date),
                page_no=1,
                page_count=100
            )

            # 공시 리스트
            disclosures = result.get("list", [])
            if not disclosures:
                return 0

            # 각 공시 처리
            for disclosure in disclosures:
                success = await self._save_disclosure(client, corp, disclosure)
                if success:
                    count += 1
                    self.stats["total_disclosures"] += 1

        except Exception as e:
            logger.error(f"Failed to crawl {corp.corp_name}: {e}")
            self.stats["errors"].append({
                "corp_code": corp.corp_code,
                "corp_name": corp.corp_name,
                "error": str(e)
            })

        return count

    async def _save_disclosure(
        self,
        client: DARTClient,
        corp: CorpCode,
        disclosure: Dict
    ) -> bool:
        """
        공시 저장

        저장 구조:
        /data/dart/{corp_code}/{year}/{rcept_no}.zip
        /data/dart/{corp_code}/{year}/{rcept_no}_meta.json

        Args:
            client: DART 클라이언트
            corp: 기업 정보
            disclosure: 공시 정보

        Returns:
            성공 여부
        """
        rcept_no = disclosure.get("rcept_no")
        rcept_dt = disclosure.get("rcept_dt")  # YYYYMMDD

        if not rcept_no or not rcept_dt:
            return False

        # 연도 추출
        year = rcept_dt[:4]

        # 저장 경로
        corp_dir = self.data_dir / corp.corp_code / year
        corp_dir.mkdir(parents=True, exist_ok=True)

        doc_path = corp_dir / f"{rcept_no}.zip"
        meta_path = corp_dir / f"{rcept_no}_meta.json"

        # 이미 존재하면 스킵
        if doc_path.exists() and meta_path.exists():
            return True

        # 메타데이터 저장
        meta = {
            "rcept_no": rcept_no,
            "corp_code": corp.corp_code,
            "corp_name": corp.corp_name,
            "stock_code": corp.stock_code,
            "report_nm": disclosure.get("report_nm"),
            "rcept_dt": rcept_dt,
            "flr_nm": disclosure.get("flr_nm"),  # 공시 제출인명
            "rm": disclosure.get("rm"),  # 비고
            "crawled_at": datetime.now().isoformat(),
        }

        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

        # 문서 다운로드 (재시도 로직)
        for attempt in range(self.max_retries):
            try:
                success = await client.download_document(rcept_no, doc_path)

                if success:
                    self.stats["downloaded_documents"] += 1
                    return True

                # 실패 시 대기
                await asyncio.sleep(self.retry_delay)

            except Exception as e:
                logger.warning(
                    f"Download failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"{rcept_no} - {e}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        # 최종 실패
        self.stats["failed_downloads"] += 1
        return False


# ============================================================================
# CLI 실행
# ============================================================================

async def main():
    """CLI 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="DART Crawler")
    parser.add_argument("--api-key", required=True, help="DART API Key")
    parser.add_argument("--years", type=int, default=3, help="Years to crawl")
    parser.add_argument("--recent-hours", type=int, help="Recent hours to crawl")
    parser.add_argument("--data-dir", type=Path, default=Path("./data/dart"))

    args = parser.parse_args()

    # Crawler 생성
    crawler = DARTCrawler(
        api_key=args.api_key,
        data_dir=args.data_dir
    )

    # 실행
    if args.recent_hours:
        stats = await crawler.crawl_recent(hours=args.recent_hours)
    else:
        stats = await crawler.crawl_all_companies(years=args.years)

    # 결과 출력
    print("\n=== Crawl Statistics ===")
    print(f"Total Companies: {stats['total_companies']}")
    print(f"Total Disclosures: {stats['total_disclosures']}")
    print(f"Downloaded Documents: {stats['downloaded_documents']}")
    print(f"Failed Downloads: {stats['failed_downloads']}")
    print(f"Errors: {len(stats['errors'])}")


if __name__ == "__main__":
    asyncio.run(main())
