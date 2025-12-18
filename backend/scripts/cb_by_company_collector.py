#!/usr/bin/env python3
"""
회사별 전환사채 공시 수집 스크립트

각 회사의 corp_code를 사용하여 CB 관련 공시를 검색하고 수집
"""
import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime, timedelta
import json

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Company

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBByCompanyCollector:
    """회사별 전환사채 공시 수집기"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        self.stats = {
            "companies_processed": 0,
            "companies_with_cb": 0,
            "total_cb_disclosures": 0,
            "errors": 0
        }
        self.cb_disclosures = []

    async def search_company_cb_disclosures(
        self,
        corp_code: str,
        corp_name: str,
        begin_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        특정 회사의 CB 관련 공시 검색

        Args:
            corp_code: 회사 고유번호
            corp_name: 회사명 (로깅용)
            begin_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
        """
        url = f"{self.base_url}/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": begin_date,
            "end_de": end_date,
            "page_no": 1,
            "page_count": 100
        }

        disclosures = []

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if data.get("status") != "000":
                        if data.get("status") != "013":  # 데이터 없음은 에러 아님
                            logger.error(f"API Error for {corp_name}: {data.get('message')}")
                            self.stats["errors"] += 1
                        return []

                    items = data.get("list", [])

                    # CB 관련 공시 필터링
                    cb_keywords = [
                        "전환사채", "신주인수권부사채", "교환사채",
                        "CB", "BW", "EB",
                        "전환권", "신주인수권"
                    ]

                    for item in items:
                        report_nm = item.get("report_nm", "")
                        if any(keyword in report_nm for keyword in cb_keywords):
                            disclosures.append({
                                **item,
                                "corp_name": corp_name,
                                "search_corp_code": corp_code
                            })

                    if disclosures:
                        logger.info(f"{corp_name}: {len(disclosures)}건 CB 공시 발견")

            except Exception as e:
                logger.error(f"Error fetching disclosures for {corp_name}: {e}")
                self.stats["errors"] += 1

        return disclosures

    async def run(self, years: int = 5, limit: int = None):
        """회사별 CB 공시 수집 실행"""
        print("=" * 60)
        print("💰 회사별 전환사채 공시 수집 시작")
        print("=" * 60)

        # 검색 기간 설정
        end_date = datetime.now()
        begin_date = end_date - timedelta(days=365 * years)
        begin_str = begin_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        print(f"\n📅 검색 기간: {begin_str} ~ {end_str}")

        # DB에서 회사 목록 가져오기
        print("\n📋 회사 목록 로딩 중...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Company))
            companies = result.scalars().all()

            if limit:
                companies = companies[:limit]

        print(f"  ✅ {len(companies)}개 회사 로드 완료\n")

        # 각 회사별로 CB 공시 검색
        print("🔍 회사별 CB 공시 검색 중...")

        for i, company in enumerate(companies, 1):
            self.stats["companies_processed"] += 1

            if i % 100 == 0:
                print(f"  진행: {i}/{len(companies)} ({i/len(companies)*100:.1f}%)")

            disclosures = await self.search_company_cb_disclosures(
                corp_code=company.corp_code,
                corp_name=company.name,
                begin_date=begin_str,
                end_date=end_str
            )

            if disclosures:
                self.stats["companies_with_cb"] += 1
                self.stats["total_cb_disclosures"] += len(disclosures)
                self.cb_disclosures.extend(disclosures)

            # Rate limit (초당 1건)
            await asyncio.sleep(1.0)

        # 통계 출력
        self._print_stats()

        return self.cb_disclosures

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 회사별 CB 공시 수집 완료")
        print("=" * 60)
        print(f"처리한 회사: {self.stats['companies_processed']:,}개")
        print(f"CB 발행 회사: {self.stats['companies_with_cb']:,}개")
        print(f"발견된 CB 공시: {self.stats['total_cb_disclosures']:,}건")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)

        if self.cb_disclosures:
            print("\n📋 최근 CB 공시 샘플 (최근 20건):")
            for item in sorted(self.cb_disclosures, key=lambda x: x['rcept_dt'], reverse=True)[:20]:
                print(f"  - {item['corp_name']}: {item['report_nm']} ({item['rcept_dt']})")


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="회사별 전환사채 공시 수집 스크립트")
    parser.add_argument("--api-key", required=True, help="DART API 키")
    parser.add_argument("--years", type=int, default=5, help="검색 기간 (년)")
    parser.add_argument("--limit", type=int, default=None, help="처리할 회사 수 제한 (테스트용)")

    args = parser.parse_args()

    collector = CBByCompanyCollector(args.api_key)
    disclosures = await collector.run(years=args.years, limit=args.limit)

    # 공시 목록 저장
    if disclosures:
        # 파일명 결정 (limit 있으면 _test, 없으면 _full)
        if args.limit:
            output_file = Path("data/cb_disclosures_by_company_test.json")
        else:
            output_file = Path("data/cb_disclosures_by_company_full.json")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(disclosures, f, ensure_ascii=False, indent=2)

        print(f"\n💾 공시 목록 저장: {output_file}")
        print(f"   총 {len(disclosures)}건의 CB 공시 저장 완료")


if __name__ == "__main__":
    asyncio.run(main())
