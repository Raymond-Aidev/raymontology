#!/usr/bin/env python3
"""
통합 파서 실행기

다운로드된 분기보고서를 통합 파서로 처리합니다.

사용법:
    python -m scripts.pipeline.run_unified_parser --quarter Q1 --year 2025
    python -m scripts.pipeline.run_unified_parser --quarter Q1 --year 2025 --type financial
    python -m scripts.pipeline.run_unified_parser --quarter Q1 --year 2025 --dry-run

옵션:
    --quarter: 분기 (Q1, Q2, Q3, Q4)
    --year: 연도
    --type: 파싱 유형 (financial, officer, all)
    --sample: 샘플 개수 (테스트용)
    --dry-run: 실제 저장 없이 파싱만
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import asyncpg

# 상대 경로 임포트를 위한 설정
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.parsers import DARTUnifiedParser, FinancialParser, OfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터 경로
QUARTERLY_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'quarterly'


class QuarterlyParser:
    """분기별 보고서 파서"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        self.unified_parser = DARTUnifiedParser(self.database_url)

        self.stats = {
            'started_at': None,
            'finished_at': None,
            'reports_found': 0,
            'reports_processed': 0,
            'financial_saved': 0,
            'officers_saved': 0,
            'errors': 0,
        }

    def find_quarterly_reports(
        self,
        quarter: str,
        year: int
    ) -> List[Dict]:
        """분기 보고서 검색

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도

        Returns:
            보고서 목록 [{'zip_path': Path, 'meta': dict}, ...]
        """
        data_dir = QUARTERLY_DATA_DIR / str(year) / quarter

        if not data_dir.exists():
            logger.warning(f"디렉토리 없음: {data_dir}")
            return []

        reports = []

        for meta_path in data_dir.glob('*_meta.json'):
            zip_path = meta_path.with_name(meta_path.name.replace('_meta.json', '.zip'))

            if not zip_path.exists():
                logger.warning(f"ZIP 없음: {zip_path}")
                continue

            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                reports.append({
                    'zip_path': zip_path,
                    'meta': meta,
                })

            except Exception as e:
                logger.warning(f"메타 파일 읽기 오류: {meta_path}: {e}")

        logger.info(f"{quarter} {year} 보고서: {len(reports)}개")
        return reports

    async def parse_quarterly(
        self,
        quarter: str,
        year: int,
        parse_type: str = 'all',
        sample: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """분기 보고서 파싱

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도
            parse_type: 파싱 유형 (financial, officer, all)
            sample: 샘플 개수 (테스트용)
            dry_run: True면 실제 저장 없이 파싱만

        Returns:
            파싱 통계
        """
        self.stats['started_at'] = datetime.now()
        logger.info(f"=== {quarter} {year} 파싱 시작 ===")

        # 보고서 검색
        reports = self.find_quarterly_reports(quarter, year)
        self.stats['reports_found'] = len(reports)

        if not reports:
            logger.warning("처리할 보고서가 없습니다")
            return self.stats

        if sample:
            reports = reports[:sample]
            logger.info(f"샘플 모드: {sample}개만 처리")

        # DB 연결
        conn = await asyncpg.connect(self.database_url)

        try:
            # 파서 초기화
            await self.unified_parser.initialize(conn)

            parse_financial = parse_type in ['financial', 'all']
            parse_officers = parse_type in ['officer', 'all']

            # 파싱 실행
            for i, report in enumerate(reports):
                if (i + 1) % 100 == 0:
                    logger.info(f"진행: {i+1}/{len(reports)} ({(i+1)/len(reports)*100:.1f}%)")

                zip_path = report['zip_path']
                meta = report['meta']

                try:
                    # 재무 데이터 파싱
                    if parse_financial:
                        result = await self.unified_parser.financial_parser.parse(zip_path, meta)
                        if result.get('success') and not dry_run:
                            saved = await self.unified_parser.financial_parser.save_to_db(conn, result)
                            if saved:
                                self.stats['financial_saved'] += 1

                    # 임원 데이터 파싱
                    if parse_officers:
                        result = await self.unified_parser.officer_parser.parse(zip_path, meta)
                        if result.get('success') and not dry_run:
                            saved = await self.unified_parser.officer_parser.save_to_db(conn, result)
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
        logger.info(f"{quarter} {year} 파싱 완료")
        logger.info(f"  - 소요 시간: {duration:.1f}초")
        logger.info(f"  - 보고서 검색: {self.stats['reports_found']:,}개")
        logger.info(f"  - 보고서 처리: {self.stats['reports_processed']:,}개")
        logger.info(f"  - 재무 저장: {self.stats['financial_saved']:,}개")
        logger.info(f"  - 임원 저장: {self.stats['officers_saved']:,}개")
        logger.info(f"  - 오류: {self.stats['errors']:,}개")
        logger.info(f"{'=' * 50}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description='분기보고서 파싱')
    parser.add_argument('--quarter', choices=['Q1', 'Q2', 'Q3', 'Q4'], required=True,
                        help='분기')
    parser.add_argument('--year', type=int, required=True, help='연도')
    parser.add_argument('--type', choices=['financial', 'officer', 'all'], default='all',
                        help='파싱 유형')
    parser.add_argument('--sample', type=int, help='샘플 개수 (테스트용)')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 파싱만')

    args = parser.parse_args()

    quarterly_parser = QuarterlyParser()
    await quarterly_parser.parse_quarterly(
        quarter=args.quarter,
        year=args.year,
        parse_type=args.type,
        sample=args.sample,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    asyncio.run(main())
