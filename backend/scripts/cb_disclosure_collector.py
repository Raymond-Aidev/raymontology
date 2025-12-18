#!/usr/bin/env python3
"""
전환사채 관련 공시 수집 스크립트

DART API를 통해 전환사채 발행/전환 관련 공시를 직접 검색하여 수집
"""
import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime, timedelta

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.companies import Company

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBDisclosureCollector:
    """전환사채 공시 수집기"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        self.stats = {
            "cb_disclosures": 0,
            "bw_disclosures": 0,
            "eb_disclosures": 0,
            "companies_found": set()
        }

    async def search_cb_disclosures(self, keyword: str, begin_date: str, end_date: str) -> List[Dict]:
        """
        특정 키워드로 공시 검색

        Args:
            keyword: 검색 키워드 (전환사채, 신주인수권부사채 등)
            begin_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
        """
        url = f"{self.base_url}/list.json"
        params = {
            "crtfc_key": self.api_key,
            "bgn_de": begin_date,
            "end_de": end_date,
            "page_no": 1,
            "page_count": 100
        }

        disclosures = []

        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["page_no"] = page

                try:
                    async with session.get(url, params=params) as response:
                        data = await response.json()

                        if data.get("status") != "000":
                            logger.error(f"API Error: {data.get('message')}")
                            break

                        items = data.get("list", [])
                        if not items:
                            break

                        # 키워드 필터링
                        for item in items:
                            report_nm = item.get("report_nm", "")
                            if keyword in report_nm:
                                disclosures.append(item)
                                self.stats["companies_found"].add(item.get("corp_name"))

                        cb_count = len([i for i in items if keyword in i.get('report_nm', '')])
                        logger.info(f"페이지 {page}: {len(items)}개 공시, {cb_count}개 CB 관련")

                        # 다음 페이지
                        page += 1

                        # 최대 10페이지
                        if page > 10:
                            break

                        # Rate limit
                        await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    break

        return disclosures

    async def run(self, years: int = 3):
        """CB 공시 수집 실행"""
        print("=" * 60)
        print("💰 전환사채 발행 공시 수집 시작")
        print("=" * 60)

        # 검색 기간 설정 (최근 N년)
        end_date = datetime.now()
        begin_date = end_date - timedelta(days=365 * years)

        begin_str = begin_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        print(f"\n📅 검색 기간: {begin_str} ~ {end_str}")

        # 1. 전환사채 공시 검색
        print("\n🔍 전환사채 발행 공시 검색 중...")
        cb_disclosures = await self.search_cb_disclosures("전환사채", begin_str, end_str)
        self.stats["cb_disclosures"] = len(cb_disclosures)
        print(f"  ✅ 전환사채 공시: {len(cb_disclosures)}건")

        # 2. 신주인수권부사채 공시 검색
        print("\n🔍 신주인수권부사채 발행 공시 검색 중...")
        bw_disclosures = await self.search_cb_disclosures("신주인수권부사채", begin_str, end_str)
        self.stats["bw_disclosures"] = len(bw_disclosures)
        print(f"  ✅ 신주인수권부사채 공시: {len(bw_disclosures)}건")

        # 3. 교환사채 공시 검색
        print("\n🔍 교환사채 발행 공시 검색 중...")
        eb_disclosures = await self.search_cb_disclosures("교환사채", begin_str, end_str)
        self.stats["eb_disclosures"] = len(eb_disclosures)
        print(f"  ✅ 교환사채 공시: {len(eb_disclosures)}건")

        # 통계 출력
        self._print_stats(cb_disclosures + bw_disclosures + eb_disclosures)

        return cb_disclosures + bw_disclosures + eb_disclosures

    def _print_stats(self, disclosures: List[Dict]):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 전환사채 공시 검색 완료")
        print("=" * 60)
        print(f"전환사채 공시: {self.stats['cb_disclosures']:,}건")
        print(f"신주인수권부사채 공시: {self.stats['bw_disclosures']:,}건")
        print(f"교환사채 공시: {self.stats['eb_disclosures']:,}건")
        print(f"총 공시: {len(disclosures):,}건")
        print(f"발견된 회사: {len(self.stats['companies_found'])}개")
        print("=" * 60)

        if disclosures:
            print("\n📋 최근 CB 공시 샘플 (최근 10건):")
            for item in disclosures[:10]:
                print(f"  - {item['corp_name']}: {item['report_nm']} ({item['rcept_dt']})")


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="전환사채 공시 수집 스크립트")
    parser.add_argument("--api-key", required=True, help="DART API 키")
    parser.add_argument("--years", type=int, default=3, help="검색 기간 (년)")

    args = parser.parse_args()

    collector = CBDisclosureCollector(args.api_key)
    disclosures = await collector.run(years=args.years)

    # 공시 목록 저장
    if disclosures:
        output_file = Path("data/cb_disclosures.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(disclosures, f, ensure_ascii=False, indent=2)

        print(f"\n💾 공시 목록 저장: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
