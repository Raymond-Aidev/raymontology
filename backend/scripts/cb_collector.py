#!/usr/bin/env python3
"""
전환사채(CB) 정보 수집 스크립트

사업보고서에서 전환사채, 신주인수권부사채(BW), 교환사채(EB) 정보를 파싱하여 DB에 저장
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List
import logging
import json
from datetime import datetime

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models.convertible_bonds import ConvertibleBond
from app.models.companies import Company
from app.models.disclosures import Disclosure
from scripts.dart_parser import DARTXMLParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBCollector:
    """전환사채 정보 수집기"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stats = {
            "total_files": 0,
            "parsed_files": 0,
            "total_bonds_parsed": 0,
            "bonds_saved": 0,
            "bonds_updated": 0,
            "errors": 0
        }

    async def run(self):
        """전환사채 정보 수집 실행"""
        print("=" * 60)
        print("💰 전환사채(CB) 정보 수집 시작")
        print("=" * 60)

        # 사업보고서 파일 파싱
        print("\n📂 사업보고서 파일 파싱 중...")
        await self._parse_business_reports()

        # 최종 통계
        self._print_stats()

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

                            # 사업보고서만 처리
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
                  f"CB: {self.stats['bonds_saved']}개 저장")

    async def _process_file(self, zip_file: Path, corp_code: str, meta_data: dict):
        """개별 파일 처리"""
        self.stats["total_files"] += 1

        try:
            # 1. XML 파싱
            parser = DARTXMLParser(zip_file)
            result = parser.parse()

            bonds_data = result.get('convertible_bonds', [])

            if not bonds_data:
                return

            self.stats["parsed_files"] += 1
            self.stats["total_bonds_parsed"] += len(bonds_data)

            # 2. DB에 저장
            async with AsyncSessionLocal() as session:
                # 발행 회사 찾기
                company_result = await session.execute(
                    select(Company).where(Company.corp_code == corp_code)
                )
                company = company_result.scalar_one_or_none()

                if not company:
                    logger.warning(f"Company not found: {corp_code}")
                    return

                rcept_no = meta_data.get("rcept_no")
                rcept_dt = meta_data.get("rcept_dt")

                for bond_data in bonds_data:
                    try:
                        # 날짜 형식 변환 (YYYY-MM-DD)
                        issue_date = None
                        maturity_date = None

                        if bond_data.issue_date:
                            issue_date = self._parse_date(bond_data.issue_date)
                        if bond_data.maturity_date:
                            maturity_date = self._parse_date(bond_data.maturity_date)

                        # 채권명 추정 (발행일 기준)
                        bond_name = f"전환사채 {issue_date}" if issue_date else "전환사채"

                        # 중복 체크 (회사 + 발행일 기준)
                        existing_result = await session.execute(
                            select(ConvertibleBond).where(
                                and_(
                                    ConvertibleBond.company_id == company.id,
                                    ConvertibleBond.issue_date == issue_date,
                                    ConvertibleBond.source_date == rcept_dt
                                )
                            )
                        )
                        existing = existing_result.scalar_one_or_none()

                        if existing:
                            # 기존 레코드 업데이트
                            if bond_data.issue_amount:
                                existing.issue_amount = bond_data.issue_amount
                            if bond_data.conversion_price:
                                existing.conversion_price = bond_data.conversion_price
                            if bond_data.conversion_ratio:
                                existing.conversion_ratio = bond_data.conversion_ratio
                            if maturity_date:
                                existing.maturity_date = maturity_date

                            self.stats["bonds_updated"] += 1
                        else:
                            # 새로 생성
                            cb = ConvertibleBond(
                                company_id=company.id,
                                bond_name=bond_name,
                                bond_type="CB",  # 기본값
                                issue_date=issue_date,
                                maturity_date=maturity_date,
                                issue_amount=bond_data.issue_amount,
                                conversion_price=bond_data.conversion_price,
                                conversion_ratio=bond_data.conversion_ratio,
                                source_disclosure_id=rcept_no,
                                source_date=rcept_dt,
                                status="active"  # 기본값
                            )
                            session.add(cb)
                            self.stats["bonds_saved"] += 1

                    except Exception as e:
                        logger.error(f"Failed to save CB for {company.name}: {e}")
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

    def _parse_date(self, date_str: str) -> str:
        """날짜 문자열 파싱 (YYYY-MM-DD 형식으로 변환)"""
        try:
            # 다양한 형식 지원
            formats = [
                "%Y-%m-%d",
                "%Y.%m.%d",
                "%Y/%m/%d",
                "%Y%m%d"
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            return date_str
        except Exception as e:
            logger.error(f"Failed to parse date {date_str}: {e}")
            return date_str

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 전환사채(CB) 정보 수집 완료")
        print("=" * 60)
        print(f"처리한 파일: {self.stats['total_files']:,}개")
        print(f"파싱된 파일: {self.stats['parsed_files']:,}개")
        print(f"파싱된 CB: {self.stats['total_bonds_parsed']:,}개")
        print(f"저장된 CB: {self.stats['bonds_saved']:,}개")
        print(f"업데이트된 CB: {self.stats['bonds_updated']:,}개")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="전환사채(CB) 정보 수집 스크립트")
    parser.add_argument("--data-dir", type=Path, default=Path("./data/dart"), help="데이터 디렉토리")

    args = parser.parse_args()

    collector = CBCollector(args.data_dir)
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
