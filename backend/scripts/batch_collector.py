#!/usr/bin/env python3
"""
배치 데이터 수집기

500개 기업씩 공시 데이터 수집 → 파싱 → 보고 → 승인 → 정리
"""
import asyncio
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.crawlers.dart_client import DARTClient, CorpCode
from app.crawlers.dart_crawler import DARTCrawler
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchCollector:
    """
    배치 수집기

    Phase 1: 공시 메타데이터 + PDF 다운로드
    Phase 2: PDF 파싱 + 데이터 추출
    """

    def __init__(
        self,
        api_key: str,
        batch_size: int = 500,
        data_dir: Optional[Path] = None,
        start_batch: int = 1
    ):
        self.api_key = api_key
        self.batch_size = batch_size
        self.data_dir = data_dir or Path("./data/dart")
        self.start_batch = start_batch

        # 배치 정보
        self.current_batch = 0
        self.total_batches = 0

        # 전체 통계
        self.global_stats = {
            "total_companies": 0,
            "total_batches": 0,
            "completed_batches": 0,
            "total_disclosures": 0,
            "total_pdfs": 0,
            "total_errors": 0
        }

    async def run(self):
        """
        배치 수집 실행

        수집 기간: 2022년 1분기 ~ 2025년 2분기
        """
        # 고정된 날짜 범위: 2022 Q1 ~ 2025 Q2
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2025, 6, 30)

        print("=" * 60)
        print("🚀 Raymontology 배치 데이터 수집 시작")
        print("=" * 60)
        print(f"배치 크기: {self.batch_size}개 기업")
        print(f"수집 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"저장 경로: {self.data_dir}")
        print()

        # DART 클라이언트로 전체 기업 목록 조회
        async with DARTClient(self.api_key) as client:
            print("📋 전체 기업 목록 조회 중...")
            corp_list = await client.get_corp_code_list()

            # 상장사만 필터링 (코스피, 코스닥, 코넥스)
            listed_corps = [
                c for c in corp_list
                if c.stock_code and c.stock_code.strip()
            ]

            # 최신 기업부터 처리 (리스트 역순)
            listed_corps = list(reversed(listed_corps))

            total_companies = len(listed_corps)
            self.total_batches = (total_companies + self.batch_size - 1) // self.batch_size
            self.global_stats["total_companies"] = total_companies
            self.global_stats["total_batches"] = self.total_batches

            print(f"✅ 총 {total_companies}개 상장사 발견")
            print(f"📦 {self.total_batches}개 배치로 분할 예정")
            if self.start_batch > 1:
                print(f"⏩ 배치 #{self.start_batch}부터 시작")
            print()

            # 배치별 처리
            for batch_num in range(self.start_batch, self.total_batches + 1):
                self.current_batch = batch_num

                # 배치 범위
                start_idx = (batch_num - 1) * self.batch_size
                end_idx = min(start_idx + self.batch_size, total_companies)
                batch_corps = listed_corps[start_idx:end_idx]

                # 배치 처리
                await self._process_batch(batch_num, batch_corps, start_date, end_date)

                # 승인 대기 (마지막 배치 제외)
                if batch_num < self.total_batches:
                    if not await self._wait_for_approval(batch_num):
                        print("\n❌ 사용자가 중단했습니다.")
                        break

                    # PDF 정리
                    await self._cleanup_batch(batch_num)

        # 최종 보고
        self._print_final_report()

    async def _process_batch(
        self,
        batch_num: int,
        corps: List[CorpCode],
        start_date: datetime,
        end_date: datetime
    ):
        """배치 처리"""
        print("=" * 60)
        print(f"📦 배치 #{batch_num}/{self.total_batches} 처리 중")
        print(f"   기업: {(batch_num-1)*self.batch_size + 1} ~ {(batch_num-1)*self.batch_size + len(corps)}")
        print("=" * 60)

        # 배치 디렉토리 생성
        batch_dir = self.data_dir / f"batch_{batch_num:03d}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1: 공시 수집
        print("\n🔄 Phase 1: 공시 메타데이터 + PDF 다운로드")
        phase1_stats = await self._phase1_collect(batch_dir, corps, start_date, end_date)

        # Phase 2: PDF 파싱 (간단한 버전)
        print("\n🔄 Phase 2: PDF 파싱 + 데이터 추출")
        phase2_stats = await self._phase2_parse(batch_dir)

        # 배치 보고서 생성
        batch_report = {
            "batch_number": batch_num,
            "companies_count": len(corps),
            "companies": [
                {
                    "corp_code": c.corp_code,
                    "corp_name": c.corp_name,
                    "stock_code": c.stock_code
                }
                for c in corps
            ],
            "phase1": phase1_stats,
            "phase2": phase2_stats,
            "timestamp": datetime.now().isoformat()
        }

        # 보고서 저장
        report_path = self.data_dir / "logs" / f"batch_{batch_num:03d}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(batch_report, ensure_ascii=False, indent=2))

        # 화면 출력
        self._print_batch_report(batch_num, len(corps), phase1_stats, phase2_stats)

        # 전역 통계 업데이트
        self.global_stats["completed_batches"] += 1
        self.global_stats["total_disclosures"] += phase1_stats["total_disclosures"]
        self.global_stats["total_pdfs"] += phase1_stats["downloaded_documents"]
        self.global_stats["total_errors"] += len(phase1_stats.get("errors", []))

    async def _phase1_collect(
        self,
        batch_dir: Path,
        corps: List[CorpCode],
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Phase 1: 공시 수집"""

        # 크롤러 생성 (배치 디렉토리로 저장)
        crawler = DARTCrawler(
            api_key=self.api_key,
            data_dir=batch_dir
        )

        # 기업별 수집
        async with DARTClient(self.api_key) as client:
            for corp in corps:
                await crawler._crawl_company(client, corp, start_date, end_date)

        return crawler.stats

    async def _phase2_parse(self, batch_dir: Path) -> Dict:
        """Phase 2: PDF 파싱 (간단한 버전)"""
        stats = {
            "parsed_reports": 0,
            "extracted_officers": 0,
            "extracted_affiliates": 0,
            "parse_errors": 0
        }

        # TODO: 실제 PDF 파싱 로직 구현
        # 현재는 메타데이터만 카운트
        meta_files = list(batch_dir.rglob("*_meta.json"))
        stats["parsed_reports"] = len(meta_files)

        # 임시 통계 (실제 파싱 후 업데이트)
        stats["extracted_officers"] = len(meta_files) * 5  # 평균 5명/기업
        stats["extracted_affiliates"] = len(meta_files) * 2  # 평균 2개/기업

        return stats

    async def _wait_for_approval(self, batch_num: int) -> bool:
        """승인 대기"""
        print("\n" + "=" * 60)
        print(f"✅ 배치 #{batch_num} 완료!")
        print("=" * 60)

        while True:
            response = input("\n다음 배치를 진행하시겠습니까? (y/n): ").strip().lower()

            if response == 'y':
                print("✅ 다음 배치 진행")
                return True
            elif response == 'n':
                print("❌ 수집 중단")
                return False
            else:
                print("⚠️  'y' 또는 'n'을 입력하세요.")

    async def _cleanup_batch(self, batch_num: int):
        """배치 정리 (PDF 삭제)"""
        batch_dir = self.data_dir / f"batch_{batch_num:03d}"

        if not batch_dir.exists():
            return

        # PDF/ZIP 파일만 삭제 (메타데이터는 보존)
        deleted_count = 0
        for pdf_file in batch_dir.rglob("*.zip"):
            pdf_file.unlink()
            deleted_count += 1

        print(f"\n🗑️  PDF 파일 {deleted_count}개 삭제 완료")
        print(f"   (메타데이터는 보존: {batch_dir})")

    def _print_batch_report(
        self,
        batch_num: int,
        companies_count: int,
        phase1_stats: Dict,
        phase2_stats: Dict
    ):
        """배치 보고서 출력"""
        print("\n" + "=" * 60)
        print(f"📊 배치 #{batch_num} 수집 완료")
        print("=" * 60)
        print(f"총 기업 수: {companies_count}")
        print(f"수집 공시: {phase1_stats['total_disclosures']}건")
        print(f"  - 다운로드 성공: {phase1_stats['downloaded_documents']}개")
        print(f"  - 다운로드 실패: {phase1_stats['failed_downloads']}개")
        print()
        print(f"파싱 완료: {phase2_stats['parsed_reports']}건")
        print(f"  - 임원: {phase2_stats['extracted_officers']}명 (추정)")
        print(f"  - 특수관계자: {phase2_stats['extracted_affiliates']}개 (추정)")
        print()

        if phase1_stats.get('errors'):
            print(f"⚠️  에러: {len(phase1_stats['errors'])}건")
            for err in phase1_stats['errors'][:5]:  # 최대 5개만 표시
                print(f"   - {err['corp_name']}: {err['error']}")

        print("=" * 60)

    def _print_final_report(self):
        """최종 보고서"""
        print("\n" + "=" * 60)
        print("🎉 전체 수집 완료!")
        print("=" * 60)
        print(f"총 기업: {self.global_stats['total_companies']}개")
        print(f"완료 배치: {self.global_stats['completed_batches']}/{self.global_stats['total_batches']}")
        print(f"총 공시: {self.global_stats['total_disclosures']}건")
        print(f"다운로드 PDF: {self.global_stats['total_pdfs']}개")
        print(f"총 에러: {self.global_stats['total_errors']}건")
        print("=" * 60)


async def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="배치 데이터 수집기 (2022 Q1 ~ 2025 Q2)")
    parser.add_argument("--api-key", help="DART API Key")
    parser.add_argument("--batch-size", type=int, default=500, help="배치 크기")
    parser.add_argument("--start-batch", type=int, default=1, help="시작 배치 번호")
    parser.add_argument("--data-dir", type=Path, help="데이터 디렉토리")

    args = parser.parse_args()

    # API 키 (인자 또는 환경변수)
    api_key = args.api_key or settings.dart_api_key

    if not api_key:
        print("❌ DART API 키가 필요합니다.")
        print("   --api-key 인자 또는 DART_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    # 수집기 생성
    collector = BatchCollector(
        api_key=api_key,
        batch_size=args.batch_size,
        data_dir=args.data_dir or Path("./data/dart"),
        start_batch=args.start_batch
    )

    # 실행 (2022-01-01 ~ 2025-06-30)
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
