"""
DARTUnifiedParser - DART 통합 파서

모든 DART 데이터 파싱을 위한 단일 진입점.
기존 시행착오를 모두 반영한 검증된 로직으로 구성.

사용법:
    from scripts.parsers import DARTUnifiedParser

    async def main():
        parser = DARTUnifiedParser()
        await parser.parse_all(target_years=[2024])

    asyncio.run(main())

CLI 실행:
    python -m scripts.parsers.unified --year 2024 --sample 10
    python -m scripts.parsers.unified --year 2024 --type financial
    python -m scripts.parsers.unified --year 2024 --type officer
    python -m scripts.parsers.unified --validate
"""

import argparse
import asyncio
import asyncpg
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import BaseParser
from .financial import FinancialParser
from .officer import OfficerParser
from .validators import DataValidator, QualityReport

logger = logging.getLogger(__name__)


class DARTUnifiedParser:
    """DART 통합 파서 - 단일 진입점"""

    DART_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart'

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        self.financial_parser = FinancialParser(self.database_url)
        self.officer_parser = OfficerParser(self.database_url)
        self.validator = DataValidator()

        self.stats = {
            'started_at': None,
            'finished_at': None,
            'reports_found': 0,
            'reports_processed': 0,
            'financial_saved': 0,
            'officers_saved': 0,
            'errors': 0,
        }

    async def initialize(self, conn: asyncpg.Connection):
        """캐시 초기화"""
        await self.financial_parser.load_companies(conn)
        await self.officer_parser.load_companies(conn)
        logger.info("파서 초기화 완료")

    async def parse_all(
        self,
        target_years: Optional[List[int]] = None,
        report_type: str = '사업보고서',
        sample: Optional[int] = None,
        parse_financial: bool = True,
        parse_officers: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """전체 보고서 파싱

        Args:
            target_years: 대상 연도 [2023, 2024]
            report_type: 보고서 유형 ('사업보고서', '분기보고서' 등)
            sample: 샘플 개수 (테스트용)
            parse_financial: 재무 데이터 파싱 여부
            parse_officers: 임원 데이터 파싱 여부
            dry_run: True면 실제 저장 없이 파싱만

        Returns:
            통계 정보
        """
        self.stats['started_at'] = datetime.now()
        logger.info(f"DART 통합 파서 시작 - years={target_years}, type={report_type}")

        conn = await asyncpg.connect(self.database_url)

        try:
            # 초기화
            await self.initialize(conn)

            # 보고서 검색
            reports = self.financial_parser.find_reports(
                report_type=report_type,
                target_years=target_years
            )
            self.stats['reports_found'] = len(reports)

            if sample:
                reports = reports[:sample]
                logger.info(f"샘플 모드: {sample}개만 처리")

            # 진행 상황 출력
            for i, report in enumerate(reports):
                if (i + 1) % 100 == 0:
                    logger.info(f"진행: {i+1}/{len(reports)} ({(i+1)/len(reports)*100:.1f}%)")

                zip_path = report['zip_path']
                meta = report['meta']

                try:
                    # 재무 데이터 파싱
                    if parse_financial:
                        result = await self.financial_parser.parse(zip_path, meta)
                        if result['success'] and not dry_run:
                            saved = await self.financial_parser.save_to_db(conn, result)
                            if saved:
                                self.stats['financial_saved'] += 1

                    # 임원 데이터 파싱
                    if parse_officers:
                        result = await self.officer_parser.parse(zip_path, meta)
                        if result['success'] and not dry_run:
                            saved = await self.officer_parser.save_to_db(conn, result)
                            if saved:
                                self.stats['officers_saved'] += 1

                    self.stats['reports_processed'] += 1

                except Exception as e:
                    logger.error(f"처리 오류 {zip_path.name}: {e}")
                    self.stats['errors'] += 1

        finally:
            await conn.close()

        self.stats['finished_at'] = datetime.now()
        duration = (self.stats['finished_at'] - self.stats['started_at']).total_seconds()

        logger.info(f"\n{'=' * 50}")
        logger.info("DART 통합 파서 완료")
        logger.info(f"  - 소요 시간: {duration:.1f}초")
        logger.info(f"  - 보고서 검색: {self.stats['reports_found']:,}개")
        logger.info(f"  - 보고서 처리: {self.stats['reports_processed']:,}개")
        logger.info(f"  - 재무 저장: {self.stats['financial_saved']:,}개")
        logger.info(f"  - 임원 저장: {self.stats['officers_saved']:,}개")
        logger.info(f"  - 오류: {self.stats['errors']:,}개")
        logger.info(f"{'=' * 50}")

        return self.stats

    async def parse_financial_only(
        self,
        target_years: Optional[List[int]] = None,
        sample: Optional[int] = None
    ) -> Dict[str, Any]:
        """재무 데이터만 파싱"""
        return await self.parse_all(
            target_years=target_years,
            sample=sample,
            parse_financial=True,
            parse_officers=False
        )

    async def parse_officers_only(
        self,
        target_years: Optional[List[int]] = None,
        sample: Optional[int] = None
    ) -> Dict[str, Any]:
        """임원 데이터만 파싱"""
        return await self.parse_all(
            target_years=target_years,
            sample=sample,
            parse_financial=False,
            parse_officers=True
        )

    async def validate(self) -> QualityReport:
        """데이터 품질 검증"""
        conn = await asyncpg.connect(self.database_url)
        try:
            report = await self.validator.validate_all(conn)
            return report
        finally:
            await conn.close()

    async def get_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계"""
        conn = await asyncpg.connect(self.database_url)
        try:
            return await self.validator.get_summary_stats(conn)
        finally:
            await conn.close()


async def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(description='DART 통합 파서')
    parser.add_argument('--year', type=int, nargs='*', help='대상 연도 (예: 2023 2024)')
    parser.add_argument('--type', choices=['financial', 'officer', 'all'], default='all',
                        help='파싱 유형')
    parser.add_argument('--sample', type=int, help='샘플 개수 (테스트용)')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 파싱만')
    parser.add_argument('--validate', action='store_true', help='데이터 품질 검증만')
    parser.add_argument('--stats', action='store_true', help='데이터베이스 통계만')

    args = parser.parse_args()

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    unified_parser = DARTUnifiedParser()

    if args.validate:
        report = await unified_parser.validate()
        print(report.to_string())
        return

    if args.stats:
        stats = await unified_parser.get_stats()
        print("\n📊 데이터베이스 통계")
        print("=" * 40)
        for table, count in stats.items():
            print(f"  {table}: {count:,}")
        return

    # 파싱 실행
    parse_financial = args.type in ['financial', 'all']
    parse_officers = args.type in ['officer', 'all']

    await unified_parser.parse_all(
        target_years=args.year,
        sample=args.sample,
        parse_financial=parse_financial,
        parse_officers=parse_officers,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    asyncio.run(main())
