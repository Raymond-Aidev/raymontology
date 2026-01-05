#!/usr/bin/env python3
"""
파싱된 데이터 품질 검증

분기별로 파싱된 데이터의 품질을 검증합니다.

사용법:
    python -m scripts.pipeline.validate_parsed_data --quarter Q1 --year 2025
    python -m scripts.pipeline.validate_parsed_data --full  # 전체 데이터 검증

출력:
    - 품질 보고서 (콘솔)
    - JSON 보고서 (data/reports/quality_report_{date}.json)
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import asyncpg

# 상대 경로 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.parsers import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 보고서 저장 경로
REPORTS_DIR = Path(__file__).parent.parent.parent / 'data' / 'reports'


class DataQualityChecker:
    """데이터 품질 검증기"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        self.validator = DataValidator()

    async def validate_quarter(
        self,
        quarter: str,
        year: int
    ) -> Dict[str, Any]:
        """분기별 데이터 검증

        특정 분기에 추가된 데이터만 검증합니다.

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도

        Returns:
            검증 결과
        """
        logger.info(f"=== {quarter} {year} 데이터 검증 ===")

        conn = await asyncpg.connect(self.database_url)

        try:
            # 분기별 data_source 패턴
            source_pattern = self._get_source_pattern(quarter, year)

            result = {
                'quarter': quarter,
                'year': year,
                'validated_at': datetime.now().isoformat(),
                'financial': await self._validate_financial_quarter(conn, source_pattern),
                'officers': await self._validate_officer_quarter(conn, year),
            }

            return result

        finally:
            await conn.close()

    def _get_source_pattern(self, quarter: str, year: int) -> str:
        """분기별 data_source 패턴"""
        quarter_map = {
            'Q1': f'LOCAL_Q1_{year}',
            'Q2': f'LOCAL_Q2_{year}',
            'Q3': f'LOCAL_Q3_{year}',
            'Q4': f'LOCAL_DART',  # 사업보고서
        }
        return quarter_map.get(quarter, 'LOCAL_DART')

    async def _validate_financial_quarter(
        self,
        conn: asyncpg.Connection,
        source_pattern: str
    ) -> Dict[str, Any]:
        """재무 데이터 분기별 검증"""
        # 해당 분기 데이터 개수
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM financial_details
            WHERE data_source LIKE $1
        """, f'{source_pattern}%')

        if count == 0:
            return {'total': 0, 'status': 'no_data'}

        # 이상값 검사
        anomalies = await conn.fetch("""
            SELECT fd.id, c.name as company_name, fd.fiscal_year, fd.revenue, fd.total_assets
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.data_source LIKE $1
              AND (fd.revenue < 0 OR fd.total_assets < 0)
            LIMIT 10
        """, f'{source_pattern}%')

        return {
            'total': count,
            'anomalies': len(anomalies),
            'anomaly_samples': [dict(r) for r in anomalies[:5]],
            'status': 'ok' if len(anomalies) == 0 else 'warning',
        }

    async def _validate_officer_quarter(
        self,
        conn: asyncpg.Connection,
        year: int
    ) -> Dict[str, Any]:
        """임원 데이터 분기별 검증"""
        # 해당 연도 데이터 개수 (source_report_date 기준)
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM officer_positions
            WHERE EXTRACT(YEAR FROM source_report_date) = $1
        """, year)

        if count == 0:
            return {'total': 0, 'status': 'no_data'}

        # 중복 의심 (동일 회사 3개 초과 포지션)
        duplicates = await conn.fetch("""
            SELECT o.name, c.name as company, COUNT(*) as cnt
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            WHERE EXTRACT(YEAR FROM op.source_report_date) = $1
            GROUP BY o.name, c.name
            HAVING COUNT(*) > 3
            ORDER BY cnt DESC
            LIMIT 10
        """, year)

        return {
            'total': count,
            'duplicate_suspects': len(duplicates),
            'duplicate_samples': [dict(r) for r in duplicates[:5]],
            'status': 'ok' if len(duplicates) == 0 else 'warning',
        }

    async def validate_full(self) -> Dict[str, Any]:
        """전체 데이터 검증"""
        logger.info("=== 전체 데이터 품질 검증 ===")

        conn = await asyncpg.connect(self.database_url)

        try:
            report = await self.validator.validate_all(conn)
            stats = await self.validator.get_summary_stats(conn)

            return {
                'validated_at': datetime.now().isoformat(),
                'summary_stats': stats,
                'quality_report': report.to_dict(),
            }

        finally:
            await conn.close()

    def save_report(self, result: Dict[str, Any], filename: Optional[str] = None):
        """검증 결과 저장"""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'quality_report_{timestamp}.json'

        report_path = REPORTS_DIR / filename

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"보고서 저장: {report_path}")
        return report_path


async def main():
    parser = argparse.ArgumentParser(description='데이터 품질 검증')
    parser.add_argument('--quarter', choices=['Q1', 'Q2', 'Q3', 'Q4'],
                        help='분기')
    parser.add_argument('--year', type=int, help='연도')
    parser.add_argument('--full', action='store_true', help='전체 데이터 검증')
    parser.add_argument('--save', action='store_true', help='결과를 JSON으로 저장')

    args = parser.parse_args()

    checker = DataQualityChecker()

    if args.full:
        result = await checker.validate_full()
        # 품질 보고서 출력
        if 'quality_report' in result and 'results' in result['quality_report']:
            from scripts.parsers import DataValidator
            validator = DataValidator()
            conn = await asyncpg.connect(checker.database_url)
            try:
                report = await validator.validate_all(conn)
                print(report.to_string())
            finally:
                await conn.close()
    elif args.quarter and args.year:
        result = await checker.validate_quarter(args.quarter, args.year)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        parser.error('--quarter와 --year를 함께 지정하거나 --full을 사용하세요')

    if args.save:
        checker.save_report(result)


if __name__ == '__main__':
    asyncio.run(main())
