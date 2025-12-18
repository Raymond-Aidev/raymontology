#!/usr/bin/env python3
"""
배치 파싱 스크립트

다운로드한 DART ZIP 파일들을 파싱해서 DB에 저장
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict
import logging
import json

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company
from app.models.disclosures import Disclosure  # Import to resolve relationship
from dart_parser import parse_dart_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchParser:
    """배치 파싱기"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stats = {
            "total_files": 0,
            "parsed_files": 0,
            "total_executives": 0,
            "saved_executives": 0,
            "errors": 0
        }

    async def run(self, start_batch: int = 1, end_batch: int = None):
        """배치 파싱 실행"""
        print("=" * 60)
        print("🔄 배치 파싱 시작")
        print("=" * 60)

        # 배치 디렉토리 찾기
        batch_dirs = sorted([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith('batch_')])

        if end_batch:
            batch_dirs = [d for d in batch_dirs if start_batch <= int(d.name.split('_')[1]) <= end_batch]
        else:
            batch_dirs = [d for d in batch_dirs if int(d.name.split('_')[1]) >= start_batch]

        print(f"처리 대상: {len(batch_dirs)}개 배치")
        print()

        for batch_dir in batch_dirs:
            batch_num = int(batch_dir.name.split('_')[1])
            await self._process_batch(batch_num, batch_dir)

        # 최종 통계
        self._print_stats()

    async def _process_batch(self, batch_num: int, batch_dir: Path):
        """배치 처리"""
        print(f"\n📦 배치 #{batch_num:03d} 처리 중...")

        # 사업보고서 및 감사보고서 ZIP 파일 찾기 (메타데이터에서 확인)
        business_reports = []

        for meta_file in batch_dir.rglob("*_meta.json"):
            try:
                meta_data = json.loads(meta_file.read_text())
                report_nm = meta_data.get("report_nm", "")
                # 사업보고서 또는 감사보고서 (둘 다 임원 정보 포함)
                if "사업보고서" in report_nm or "감사보고서" in report_nm:
                    # _meta.json을 .zip으로 변경
                    zip_file = Path(str(meta_file).replace('_meta.json', '.zip'))
                    if zip_file.exists():
                        business_reports.append({
                            "zip_path": zip_file,
                            "corp_code": meta_data["corp_code"],
                            "corp_name": meta_data["corp_name"],
                            "stock_code": meta_data.get("stock_code"),
                            "rcept_no": meta_data["rcept_no"],
                            "rcept_dt": meta_data["rcept_dt"]
                        })
            except Exception as e:
                logger.error(f"Failed to read meta file {meta_file}: {e}")

        print(f"  보고서: {len(business_reports)}건")

        # 파싱 및 저장
        batch_stats = {
            "files": len(business_reports),
            "executives": 0,
            "saved": 0
        }

        async with AsyncSessionLocal() as session:
            for report in business_reports:
                self.stats["total_files"] += 1

                try:
                    # ZIP 파싱
                    parsed_data = parse_dart_file(report["zip_path"])

                    executives = parsed_data.get("executives", [])
                    batch_stats["executives"] += len(executives)
                    self.stats["total_executives"] += len(executives)

                    # DB 저장
                    saved_count = await self._save_executives(
                        session,
                        executives,
                        report
                    )

                    batch_stats["saved"] += saved_count
                    self.stats["saved_executives"] += saved_count
                    self.stats["parsed_files"] += 1

                except Exception as e:
                    logger.error(f"Failed to process {report['zip_path']}: {e}")
                    self.stats["errors"] += 1

            # 커밋
            await session.commit()

        print(f"  ✅ 임원 {batch_stats['executives']}명 발견, {batch_stats['saved']}명 저장")

    async def _save_executives(
        self,
        session: AsyncSession,
        executives: List,
        report: Dict
    ) -> int:
        """임원 정보 저장"""
        saved_count = 0

        # 회사 찾기 (stock_code 기준)
        company = None
        if report.get("stock_code"):
            result = await session.execute(
                select(Company).where(Company.ticker == report["stock_code"])
            )
            company = result.scalar_one_or_none()

        for exec_data in executives:
            try:
                # 동일 이름 + 직위 + 회사로 중복 체크 (first() 사용하여 여러 행 허용)
                company_id = company.id if company else None
                result = await session.execute(
                    select(Officer).where(
                        Officer.name == exec_data.name,
                        Officer.position == exec_data.position,
                        Officer.current_company_id == company_id
                    ).limit(1)  # 첫 번째 레코드만 가져옴
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 업데이트 (properties에 최신 정보 추가)
                    properties = existing.properties or {}
                    properties.update({
                        "gender": exec_data.gender,
                        "birth_year_month": exec_data.birth_year_month,
                        "is_registered": exec_data.is_registered,
                        "is_fulltime": exec_data.is_fulltime,
                        "stock_count": exec_data.stock_count,
                        "ownership_ratio": exec_data.ownership_ratio,
                        "last_updated_from": report["rcept_no"],
                        "last_updated_date": report["rcept_dt"]
                    })
                    existing.properties = properties
                    existing.current_company_id = company.id if company else existing.current_company_id
                else:
                    # 새로 생성
                    officer = Officer(
                        name=exec_data.name,
                        position=exec_data.position,
                        current_company_id=company.id if company else None,
                        properties={
                            "gender": exec_data.gender,
                            "birth_year_month": exec_data.birth_year_month,
                            "is_registered": exec_data.is_registered,
                            "is_fulltime": exec_data.is_fulltime,
                            "stock_count": exec_data.stock_count,
                            "ownership_ratio": exec_data.ownership_ratio,
                            "source_report": report["rcept_no"],
                            "source_date": report["rcept_dt"]
                        }
                    )
                    session.add(officer)

                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save executive {exec_data.name}: {e}")

        return saved_count

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 파싱 완료 통계")
        print("=" * 60)
        print(f"처리 파일: {self.stats['parsed_files']:,} / {self.stats['total_files']:,}")
        print(f"발견 임원: {self.stats['total_executives']:,}명")
        print(f"저장 임원: {self.stats['saved_executives']:,}명")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="배치 파싱 스크립트")
    parser.add_argument("--data-dir", type=Path, default=Path("./data/dart"), help="데이터 디렉토리")
    parser.add_argument("--start-batch", type=int, default=1, help="시작 배치")
    parser.add_argument("--end-batch", type=int, help="종료 배치")

    args = parser.parse_args()

    parser_instance = BatchParser(args.data_dir)
    await parser_instance.run(args.start_batch, args.end_batch)


if __name__ == "__main__":
    asyncio.run(main())
