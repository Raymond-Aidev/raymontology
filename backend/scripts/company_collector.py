#!/usr/bin/env python3
"""
회사 정보 수집 스크립트

메타데이터 파일에서 회사 정보를 수집하고 DART API로 보강하여 DB에 저장
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Set
import logging
import json
import aiohttp

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.companies import Company
from app.models.disclosures import Disclosure  # Import to resolve relationship

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompanyCollector:
    """회사 정보 수집기"""

    def __init__(self, data_dir: Path, dart_api_key: str = None, skip_api: bool = False):
        self.data_dir = data_dir
        self.dart_api_key = dart_api_key
        self.skip_api = skip_api
        self.stats = {
            "total_meta_files": 0,
            "unique_companies": 0,
            "saved_companies": 0,
            "api_enriched": 0,
            "errors": 0
        }

    async def run(self):
        """회사 정보 수집 실행"""
        print("=" * 60)
        print("🏢 회사 정보 수집 시작")
        print("=" * 60)

        # 1. 메타데이터에서 회사 정보 수집
        companies = await self._collect_from_metadata()

        print(f"\n고유 회사: {len(companies)}개")

        # 2. DART API로 추가 정보 가져오기 (선택적)
        if not self.skip_api and self.dart_api_key:
            print("\n🔍 DART API로 회사 상세 정보 가져오는 중...")
            await self._enrich_with_dart_api(companies)
        else:
            print("\n⏭️  API enrichment 건너뛰기")

        # 3. DB에 저장
        print("\n💾 데이터베이스에 저장 중...")
        await self._save_to_db(companies)

        # 최종 통계
        self._print_stats()

    async def _collect_from_metadata(self) -> Dict[str, Dict]:
        """메타데이터 파일에서 회사 정보 수집"""
        print("\n📂 메타데이터 파일 스캔 중...")

        companies = {}  # corp_code를 키로 사용

        # 모든 배치 디렉토리 순회
        batch_dirs = sorted([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith('batch_')])

        for batch_dir in batch_dirs:
            batch_num = int(batch_dir.name.split('_')[1])
            print(f"  배치 #{batch_num:03d} 처리 중...", end=' ')

            count = 0
            for meta_file in batch_dir.rglob("*_meta.json"):
                self.stats["total_meta_files"] += 1
                try:
                    meta_data = json.loads(meta_file.read_text())
                    corp_code = meta_data.get("corp_code")

                    if corp_code and corp_code not in companies:
                        companies[corp_code] = {
                            "corp_code": corp_code,
                            "name": meta_data.get("corp_name"),
                            "ticker": meta_data.get("stock_code") or None,
                        }
                        count += 1

                except Exception as e:
                    logger.error(f"Failed to read {meta_file}: {e}")
                    self.stats["errors"] += 1

            print(f"{count}개 회사 발견")

        self.stats["unique_companies"] = len(companies)
        return companies

    async def _enrich_with_dart_api(self, companies: Dict[str, Dict]):
        """DART API로 회사 정보 보강"""

        # DART API - 회사 개황 정보
        # https://opendart.fss.or.kr/api/company.json?crtfc_key={api_key}&corp_code={corp_code}

        async with aiohttp.ClientSession() as session:
            enriched = 0
            total = len(companies)

            for i, (corp_code, company_data) in enumerate(companies.items(), 1):
                if i % 100 == 0:
                    print(f"  진행: {i}/{total} ({enriched}개 보강됨)")

                try:
                    url = f"https://opendart.fss.or.kr/api/company.json"
                    params = {
                        "crtfc_key": self.dart_api_key,
                        "corp_code": corp_code
                    }

                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()

                            if data.get("status") == "000":
                                # API 응답 성공
                                company_data["name_en"] = data.get("corp_name_eng")
                                company_data["sector"] = data.get("induty_code")  # 업종 코드
                                company_data["business_number"] = data.get("jurir_no")

                                # 시장 구분 (상장/비상장)
                                if company_data["ticker"]:
                                    # stock_code가 있으면 상장사
                                    # KOSPI, KOSDAQ 구분은 별도로 필요
                                    company_data["market"] = "KOSPI/KOSDAQ"  # 일단 임시
                                else:
                                    company_data["market"] = "비상장"

                                enriched += 1
                                self.stats["api_enriched"] += 1

                            # API 제한 방지 (초당 10건)
                            await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Failed to enrich {corp_code}: {e}")
                    self.stats["errors"] += 1

            print(f"  완료: {enriched}/{total}개 보강됨")

    async def _save_to_db(self, companies: Dict[str, Dict]):
        """DB에 저장"""

        async with AsyncSessionLocal() as session:
            saved = 0

            for corp_code, company_data in companies.items():
                try:
                    # 기존 회사 확인
                    result = await session.execute(
                        select(Company).where(Company.corp_code == corp_code)
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # 업데이트
                        existing.name = company_data["name"]
                        existing.ticker = company_data.get("ticker")
                        existing.name_en = company_data.get("name_en")
                        existing.sector = company_data.get("sector")
                        existing.business_number = company_data.get("business_number")
                        existing.market = company_data.get("market")
                    else:
                        # 새로 생성
                        company = Company(
                            corp_code=corp_code,
                            name=company_data["name"],
                            ticker=company_data.get("ticker"),
                            name_en=company_data.get("name_en"),
                            sector=company_data.get("sector"),
                            business_number=company_data.get("business_number"),
                            market=company_data.get("market"),
                        )
                        session.add(company)

                    saved += 1

                    # 주기적으로 커밋 (메모리 관리)
                    if saved % 50 == 0:
                        try:
                            await session.commit()
                            print(f"  {saved}개 저장됨...")
                        except Exception as commit_error:
                            logger.error(f"Commit failed at {saved}: {commit_error}")
                            await session.rollback()
                            # 에러 발생 시 개별적으로 저장 시도
                            continue

                except Exception as e:
                    logger.error(f"Failed to save {corp_code}: {e}")
                    self.stats["errors"] += 1

            # 최종 커밋
            try:
                await session.commit()
            except Exception as final_error:
                logger.error(f"Final commit failed: {final_error}")
                await session.rollback()
            self.stats["saved_companies"] = saved
            print(f"  ✅ 총 {saved}개 회사 저장 완료")

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 회사 정보 수집 완료")
        print("=" * 60)
        print(f"메타데이터 파일: {self.stats['total_meta_files']:,}개")
        print(f"고유 회사: {self.stats['unique_companies']:,}개")
        print(f"API 보강: {self.stats['api_enriched']:,}개")
        print(f"저장된 회사: {self.stats['saved_companies']:,}개")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="회사 정보 수집 스크립트")
    parser.add_argument("--data-dir", type=Path, default=Path("./data/dart"), help="데이터 디렉토리")
    parser.add_argument("--api-key", type=str, required=True, help="DART API 키")
    parser.add_argument("--skip-api", action="store_true", help="API 보강 건너뛰기")

    args = parser.parse_args()

    collector = CompanyCollector(args.data_dir, args.api_key, args.skip_api)
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
