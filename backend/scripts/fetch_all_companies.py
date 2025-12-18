#!/usr/bin/env python3
"""
DART API를 사용하여 전체 상장 기업 목록을 가져오는 스크립트

DART API corpCode.xml 엔드포인트를 사용하여 모든 기업 정보를 가져옵니다.
https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}
"""
import asyncio
import sys
from pathlib import Path
import logging
import zipfile
import io
import xml.etree.ElementTree as ET
import aiohttp

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


class AllCompanyFetcher:
    """전체 기업 목록 수집기"""

    def __init__(self, dart_api_key: str):
        self.dart_api_key = dart_api_key
        self.stats = {
            "total_companies": 0,
            "listed_companies": 0,  # 상장사
            "saved_companies": 0,
            "updated_companies": 0,
            "errors": 0
        }

    async def run(self):
        """전체 기업 목록 수집 실행"""
        print("=" * 60)
        print("🏢 DART 전체 기업 목록 수집 시작")
        print("=" * 60)

        # 1. DART API에서 기업 목록 다운로드
        companies = await self._fetch_from_dart_api()

        if not companies:
            print("❌ 기업 목록을 가져오지 못했습니다.")
            return

        print(f"\n총 {len(companies)}개 기업 정보 수집됨")

        # 상장사만 필터링 (ticker가 있는 경우)
        listed_companies = {
            corp_code: data
            for corp_code, data in companies.items()
            if data.get("ticker")
        }

        print(f"상장사: {len(listed_companies)}개")
        self.stats["listed_companies"] = len(listed_companies)

        # 2. DB에 저장 (상장사 우선, 전체도 가능)
        print("\n💾 데이터베이스에 저장 중...")
        await self._save_to_db(listed_companies)

        # 최종 통계
        self._print_stats()

    async def _fetch_from_dart_api(self) -> dict:
        """DART API에서 전체 기업 목록 다운로드"""
        print("\n📥 DART API에서 기업 목록 다운로드 중...")

        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": self.dart_api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"API 요청 실패: {response.status}")
                        return {}

                    # ZIP 파일 다운로드
                    zip_data = await response.read()
                    print(f"  다운로드 완료: {len(zip_data)} bytes")

                    # ZIP 압축 해제
                    companies = {}
                    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                        # CORPCODE.xml 파일 읽기
                        xml_filename = zf.namelist()[0]
                        print(f"  압축 해제: {xml_filename}")

                        with zf.open(xml_filename) as xml_file:
                            # XML 파싱
                            tree = ET.parse(xml_file)
                            root = tree.getroot()

                            for company in root.findall('list'):
                                corp_code = company.find('corp_code').text
                                corp_name = company.find('corp_name').text
                                stock_code_elem = company.find('stock_code')
                                stock_code = stock_code_elem.text if stock_code_elem is not None else None
                                modify_date = company.find('modify_date').text

                                # stock_code가 있으면 상장사 (공백이 아닌 실제 값이 있는 경우만)
                                ticker = None
                                if stock_code:
                                    ticker = stock_code.strip()

                                if ticker:  # 상장사만 저장
                                    companies[corp_code] = {
                                        "corp_code": corp_code,
                                        "name": corp_name,
                                        "ticker": ticker,
                                        "modify_date": modify_date
                                    }

                                self.stats["total_companies"] += 1

                    print(f"  ✅ {len(companies)}개 기업 파싱 완료")
                    return companies

        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {}

    async def _save_to_db(self, companies: dict):
        """DB에 저장"""

        async with AsyncSessionLocal() as session:
            saved = 0
            updated = 0

            for corp_code, company_data in companies.items():
                try:
                    # 기존 회사 확인
                    result = await session.execute(
                        select(Company).where(Company.corp_code == corp_code)
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # 업데이트 (기존 데이터 유지하면서 보완)
                        if not existing.name:
                            existing.name = company_data["name"]
                        if not existing.ticker:
                            existing.ticker = company_data.get("ticker")
                        updated += 1
                    else:
                        # 새로 생성
                        company = Company(
                            corp_code=corp_code,
                            name=company_data["name"],
                            ticker=company_data.get("ticker"),
                        )
                        session.add(company)
                        saved += 1

                    # 주기적으로 커밋 (메모리 관리)
                    if (saved + updated) % 100 == 0:
                        try:
                            await session.commit()
                            print(f"  {saved + updated}개 처리됨 (신규: {saved}, 업데이트: {updated})...")
                        except Exception as commit_error:
                            logger.error(f"Commit failed at {saved + updated}: {commit_error}")
                            await session.rollback()
                            continue

                except Exception as e:
                    logger.error(f"Failed to save {corp_code}: {e}")
                    self.stats["errors"] += 1

            # 최종 커밋
            try:
                await session.commit()
                print(f"  ✅ 총 {saved + updated}개 회사 저장 완료 (신규: {saved}, 업데이트: {updated})")
            except Exception as final_error:
                logger.error(f"Final commit failed: {final_error}")
                await session.rollback()

            self.stats["saved_companies"] = saved
            self.stats["updated_companies"] = updated

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 기업 목록 수집 완료")
        print("=" * 60)
        print(f"다운로드된 기업: {self.stats['total_companies']:,}개")
        print(f"상장 기업: {self.stats['listed_companies']:,}개")
        print(f"신규 저장: {self.stats['saved_companies']:,}개")
        print(f"업데이트: {self.stats['updated_companies']:,}개")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="DART 전체 기업 목록 수집")
    parser.add_argument("--api-key", type=str, required=True, help="DART API 키")

    args = parser.parse_args()

    fetcher = AllCompanyFetcher(args.api_key)
    await fetcher.run()


if __name__ == "__main__":
    asyncio.run(main())
