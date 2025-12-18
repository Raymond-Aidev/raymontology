#!/usr/bin/env python3
"""
특수관계자/계열사 정보 수집 스크립트

사업보고서에서 계열사 및 자회사 정보를 파싱하여 DB에 저장
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Set
import logging
import json

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.affiliates import Affiliate
from app.models.companies import Company
from app.models.disclosures import Disclosure
from scripts.dart_parser import DARTXMLParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AffiliateCollector:
    """계열사 정보 수집기"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stats = {
            "total_files": 0,
            "parsed_files": 0,
            "total_affiliates_parsed": 0,
            "affiliates_saved": 0,
            "affiliates_matched": 0,
            "affiliates_unmatched": 0,
            "errors": 0
        }
        self.company_cache: Dict[str, str] = {}  # name -> company_id
        self.unmatched_affiliates: Set[str] = set()

    async def run(self):
        """계열사 정보 수집 실행"""
        print("=" * 60)
        print("🔗 특수관계자/계열사 정보 수집 시작")
        print("=" * 60)

        # 1. 회사 캐시 로드
        await self._load_company_cache()

        # 2. 사업보고서 파일 파싱
        print("\n📂 사업보고서 파일 파싱 중...")
        await self._parse_business_reports()

        # 3. 매칭되지 않은 계열사 출력
        if self.unmatched_affiliates:
            print(f"\n⚠️  매칭되지 않은 계열사 ({len(self.unmatched_affiliates)}개):")
            for name in sorted(list(self.unmatched_affiliates))[:20]:
                print(f"  - {name}")
            if len(self.unmatched_affiliates) > 20:
                print(f"  ... 외 {len(self.unmatched_affiliates) - 20}개")

        # 최종 통계
        self._print_stats()

    async def _load_company_cache(self):
        """회사 정보 캐시 로드"""
        print("\n💾 회사 정보 로딩 중...")

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Company.id, Company.name, Company.corp_code)
            )
            companies = result.all()

            for company_id, name, corp_code in companies:
                # 회사명으로 매칭
                self.company_cache[name] = str(company_id)

                # 회사명 변형도 캐시 (주식회사, (주) 등 제거)
                clean_name = name.replace("주식회사", "").replace("(주)", "").strip()
                if clean_name != name:
                    self.company_cache[clean_name] = str(company_id)

        print(f"  ✅ {len(companies)}개 회사 로드 완료 (캐시: {len(self.company_cache)}개 키)")

    async def _parse_business_reports(self):
        """사업보고서 파일들 파싱"""

        # 모든 배치 디렉토리 순회
        batch_dirs = sorted([
            d for d in self.data_dir.iterdir()
            if d.is_dir() and d.name.startswith('batch_')
        ])

        for batch_dir in batch_dirs:
            batch_num = int(batch_dir.name.split('_')[1])
            print(f"\n  배치 #{batch_num:03d} 처리 중...")

            # 각 회사별 처리
            for corp_dir in batch_dir.iterdir():
                if not corp_dir.is_dir():
                    continue

                corp_code = corp_dir.name

                # 각 연도별 처리
                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir():
                        continue

                    # ZIP 파일 찾기 (메타데이터에서 사업보고서만 필터링)
                    for meta_file in year_dir.glob("*_meta.json"):
                        try:
                            meta_data = json.loads(meta_file.read_text())

                            # 사업보고서만 처리 (report_nm에 "사업보고서"가 포함된 경우)
                            report_nm = meta_data.get("report_nm", "")
                            if "사업보고서" not in report_nm:
                                continue

                            rcept_no = meta_data.get("rcept_no")
                            zip_file = meta_file.parent / f"{rcept_no}.zip"

                            if zip_file.exists():
                                await self._process_file(
                                    zip_file=zip_file,
                                    corp_code=corp_code,
                                    meta_data=meta_data
                                )

                        except Exception as e:
                            logger.error(f"Failed to process {meta_file}: {e}")
                            self.stats["errors"] += 1

            # 배치별 통계
            print(f"    파싱: {self.stats['parsed_files']}개, "
                  f"계열사: {self.stats['affiliates_saved']}개 저장")

    async def _process_file(self, zip_file: Path, corp_code: str, meta_data: dict):
        """개별 파일 처리"""
        self.stats["total_files"] += 1

        try:
            # 1. XML 파싱
            parser = DARTXMLParser(zip_file)
            result = parser.parse()

            affiliates_data = result.get('affiliates', [])

            if not affiliates_data:
                return

            self.stats["parsed_files"] += 1
            self.stats["total_affiliates_parsed"] += len(affiliates_data)

            # 2. DB에 저장
            async with AsyncSessionLocal() as session:
                # 모회사 찾기
                parent_result = await session.execute(
                    select(Company).where(Company.corp_code == corp_code)
                )
                parent_company = parent_result.scalar_one_or_none()

                if not parent_company:
                    logger.warning(f"Parent company not found: {corp_code}")
                    return

                rcept_no = meta_data.get("rcept_no")
                rcept_dt = meta_data.get("rcept_dt")

                for aff_data in affiliates_data:
                    try:
                        affiliate_name = aff_data.name
                        relation_type = aff_data.relation_type

                        # 계열사 회사 매칭
                        affiliate_company_id = self.company_cache.get(affiliate_name)

                        if not affiliate_company_id:
                            # 매칭 실패 - 이름 정리 후 재시도
                            clean_name = affiliate_name.replace("주식회사", "").replace("(주)", "").strip()
                            affiliate_company_id = self.company_cache.get(clean_name)

                            if not affiliate_company_id:
                                self.unmatched_affiliates.add(affiliate_name)
                                self.stats["affiliates_unmatched"] += 1
                                # 매칭 안 되어도 저장 (나중에 수동 매칭 가능)
                        else:
                            self.stats["affiliates_matched"] += 1

                        # 중복 체크
                        existing_result = await session.execute(
                            select(Affiliate).where(
                                and_(
                                    Affiliate.parent_company_id == parent_company.id,
                                    Affiliate.affiliate_name == affiliate_name,
                                    Affiliate.source_date == rcept_dt
                                )
                            )
                        )
                        existing = existing_result.scalar_one_or_none()

                        if existing:
                            # 이미 존재하면 업데이트
                            existing.affiliate_company_id = affiliate_company_id if affiliate_company_id else existing.affiliate_company_id
                            existing.relationship_type = relation_type
                        else:
                            # 새로 생성
                            affiliate = Affiliate(
                                parent_company_id=parent_company.id,
                                affiliate_company_id=affiliate_company_id,
                                affiliate_name=affiliate_name,
                                relationship_type=relation_type,
                                source_disclosure_id=rcept_no,
                                source_date=rcept_dt,
                            )
                            session.add(affiliate)
                            self.stats["affiliates_saved"] += 1

                    except Exception as e:
                        logger.error(f"Failed to save affiliate {affiliate_name}: {e}")
                        self.stats["errors"] += 1

                # 커밋
                try:
                    await session.commit()
                except Exception as commit_error:
                    logger.error(f"Commit failed for {zip_file}: {commit_error}")
                    await session.rollback()
                    self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"Failed to parse {zip_file}: {e}")
            self.stats["errors"] += 1

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 계열사 정보 수집 완료")
        print("=" * 60)
        print(f"처리한 파일: {self.stats['total_files']:,}개")
        print(f"파싱된 파일: {self.stats['parsed_files']:,}개")
        print(f"파싱된 계열사: {self.stats['total_affiliates_parsed']:,}개")
        print(f"저장된 계열사: {self.stats['affiliates_saved']:,}개")
        print(f"매칭 성공: {self.stats['affiliates_matched']:,}개")
        print(f"매칭 실패: {self.stats['affiliates_unmatched']:,}개")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="계열사 정보 수집 스크립트")
    parser.add_argument("--data-dir", type=Path, default=Path("./data/dart"), help="데이터 디렉토리")

    args = parser.parse_args()

    collector = AffiliateCollector(args.data_dir)
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
