#!/usr/bin/env python3
"""
파이프라인 실행 보고서 생성

분기별 파이프라인 실행 후 종합 보고서를 생성합니다.

사용법:
    python -m scripts.pipeline.generate_report --quarter Q1 --year 2025
    python -m scripts.pipeline.generate_report --monthly  # 월간 보고서

출력:
    - 콘솔 출력 (터미널)
    - JSON 파일 (data/reports/)
    - Markdown 파일 (data/reports/)
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / 'data' / 'reports'


class PipelineReporter:
    """파이프라인 보고서 생성기"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

    async def generate_quarterly_report(
        self,
        quarter: str,
        year: int
    ) -> Dict[str, Any]:
        """분기별 보고서 생성

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도

        Returns:
            보고서 데이터
        """
        logger.info(f"=== {quarter} {year} 보고서 생성 ===")

        conn = await asyncpg.connect(self.database_url)

        try:
            report = {
                'report_type': 'quarterly',
                'quarter': quarter,
                'year': year,
                'generated_at': datetime.now().isoformat(),
                'summary': await self._get_summary_stats(conn),
                'financial_details': await self._get_financial_stats(conn, year),
                'officer_positions': await self._get_officer_stats(conn),
                'raymonds_index': await self._get_index_stats(conn, year),
                'data_quality': await self._get_quality_metrics(conn),
            }

            return report

        finally:
            await conn.close()

    async def _get_summary_stats(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        """요약 통계"""
        tables = [
            'companies', 'officers', 'officer_positions',
            'financial_details', 'convertible_bonds', 'cb_subscribers',
            'raymonds_index', 'risk_scores', 'disclosures'
        ]

        stats = {}
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count
            except:
                stats[table] = 0

        return stats

    async def _get_financial_stats(
        self,
        conn: asyncpg.Connection,
        year: int
    ) -> Dict[str, Any]:
        """재무 데이터 통계"""
        # 연도별 데이터 개수
        yearly = await conn.fetch("""
            SELECT fiscal_year, COUNT(*) as count
            FROM financial_details
            GROUP BY fiscal_year
            ORDER BY fiscal_year DESC
            LIMIT 5
        """)

        # 데이터 소스별 분포
        sources = await conn.fetch("""
            SELECT data_source, COUNT(*) as count
            FROM financial_details
            GROUP BY data_source
            ORDER BY count DESC
        """)

        # 해당 연도 주요 지표
        metrics = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN revenue > 0 THEN 1 END) as positive_revenue,
                COUNT(CASE WHEN net_income > 0 THEN 1 END) as profitable,
                AVG(CASE WHEN total_equity > 0 THEN net_income / total_equity * 100 END) as avg_roe
            FROM financial_details
            WHERE fiscal_year = $1
        """, year)

        return {
            'yearly_distribution': {r['fiscal_year']: r['count'] for r in yearly},
            'source_distribution': {r['data_source']: r['count'] for r in sources},
            'year_metrics': dict(metrics) if metrics else {},
        }

    async def _get_officer_stats(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        """임원 데이터 통계"""
        # 총 임원 수
        officer_count = await conn.fetchval("SELECT COUNT(*) FROM officers")

        # 현재 재직 중인 임원
        current_positions = await conn.fetchval("""
            SELECT COUNT(*) FROM officer_positions WHERE is_current = true
        """)

        # 포지션 수 분포
        position_dist = await conn.fetch("""
            SELECT
                CASE
                    WHEN cnt = 1 THEN '1'
                    WHEN cnt = 2 THEN '2'
                    WHEN cnt = 3 THEN '3'
                    WHEN cnt > 3 THEN '4+'
                END as count_range,
                COUNT(*) as officers
            FROM (
                SELECT o.id, COUNT(DISTINCT op.company_id) as cnt
                FROM officers o
                JOIN officer_positions op ON o.id = op.officer_id
                GROUP BY o.id
            ) sub
            GROUP BY count_range
            ORDER BY count_range
        """)

        return {
            'total_officers': officer_count,
            'current_positions': current_positions,
            'company_count_distribution': {r['count_range']: r['officers'] for r in position_dist},
        }

    async def _get_index_stats(
        self,
        conn: asyncpg.Connection,
        year: int
    ) -> Dict[str, Any]:
        """RaymondsIndex 통계"""
        # 등급 분포
        grades = await conn.fetch("""
            SELECT grade, COUNT(*) as count
            FROM raymonds_index
            WHERE fiscal_year = $1
            GROUP BY grade
            ORDER BY grade
        """, year)

        # 점수 분포
        score_ranges = await conn.fetch("""
            SELECT
                CASE
                    WHEN score >= 80 THEN '80-100'
                    WHEN score >= 60 THEN '60-79'
                    WHEN score >= 40 THEN '40-59'
                    ELSE '0-39'
                END as score_range,
                COUNT(*) as count
            FROM raymonds_index
            WHERE fiscal_year = $1
            GROUP BY score_range
            ORDER BY score_range DESC
        """, year)

        return {
            'grade_distribution': {r['grade']: r['count'] for r in grades},
            'score_distribution': {r['score_range']: r['count'] for r in score_ranges},
        }

    async def _get_quality_metrics(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        """데이터 품질 지표"""
        # NULL 비율 체크
        null_checks = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN revenue IS NULL THEN 1 END) as null_revenue,
                COUNT(CASE WHEN total_assets IS NULL THEN 1 END) as null_assets,
                COUNT(CASE WHEN net_income IS NULL THEN 1 END) as null_net_income
            FROM financial_details
        """)

        total = null_checks['total'] or 1

        return {
            'total_financial_records': null_checks['total'],
            'null_rates': {
                'revenue': null_checks['null_revenue'] / total * 100,
                'total_assets': null_checks['null_assets'] / total * 100,
                'net_income': null_checks['null_net_income'] / total * 100,
            }
        }

    def format_markdown(self, report: Dict[str, Any]) -> str:
        """Markdown 형식으로 변환"""
        lines = [
            f"# 데이터 파이프라인 보고서",
            f"",
            f"- 생성일시: {report['generated_at']}",
            f"- 분기: {report.get('quarter', 'N/A')} {report.get('year', 'N/A')}",
            f"",
            f"## 1. 데이터베이스 요약",
            f"",
        ]

        # 요약 테이블
        if 'summary' in report:
            lines.append("| 테이블 | 레코드 수 |")
            lines.append("|--------|----------|")
            for table, count in report['summary'].items():
                lines.append(f"| {table} | {count:,} |")
            lines.append("")

        # 재무 데이터
        if 'financial_details' in report:
            lines.append("## 2. 재무 데이터 현황")
            lines.append("")
            fd = report['financial_details']
            if 'yearly_distribution' in fd:
                lines.append("### 연도별 분포")
                for year, count in fd['yearly_distribution'].items():
                    lines.append(f"- {year}년: {count:,}건")
            lines.append("")

        # RaymondsIndex
        if 'raymonds_index' in report:
            lines.append("## 3. RaymondsIndex 현황")
            lines.append("")
            ri = report['raymonds_index']
            if 'grade_distribution' in ri:
                lines.append("### 등급 분포")
                lines.append("| 등급 | 기업 수 |")
                lines.append("|------|--------|")
                for grade, count in sorted(ri['grade_distribution'].items()):
                    lines.append(f"| {grade} | {count} |")
            lines.append("")

        # 데이터 품질
        if 'data_quality' in report:
            lines.append("## 4. 데이터 품질")
            lines.append("")
            dq = report['data_quality']
            if 'null_rates' in dq:
                lines.append("### NULL 비율")
                for field, rate in dq['null_rates'].items():
                    lines.append(f"- {field}: {rate:.2f}%")
            lines.append("")

        return "\n".join(lines)

    def save_report(
        self,
        report: Dict[str, Any],
        format: str = 'both'
    ) -> Dict[str, Path]:
        """보고서 저장

        Args:
            report: 보고서 데이터
            format: 저장 형식 (json, markdown, both)

        Returns:
            저장된 파일 경로
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        quarter = report.get('quarter', 'full')
        year = report.get('year', '')

        saved_files = {}

        if format in ['json', 'both']:
            json_path = REPORTS_DIR / f'pipeline_report_{quarter}_{year}_{timestamp}.json'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            saved_files['json'] = json_path
            logger.info(f"JSON 저장: {json_path}")

        if format in ['markdown', 'both']:
            md_content = self.format_markdown(report)
            md_path = REPORTS_DIR / f'pipeline_report_{quarter}_{year}_{timestamp}.md'
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            saved_files['markdown'] = md_path
            logger.info(f"Markdown 저장: {md_path}")

        return saved_files


async def main():
    parser = argparse.ArgumentParser(description='파이프라인 보고서 생성')
    parser.add_argument('--quarter', choices=['Q1', 'Q2', 'Q3', 'Q4'],
                        help='분기')
    parser.add_argument('--year', type=int, help='연도')
    parser.add_argument('--monthly', action='store_true', help='월간 보고서')
    parser.add_argument('--format', choices=['json', 'markdown', 'both'],
                        default='both', help='출력 형식')
    parser.add_argument('--save', action='store_true', help='파일로 저장')

    args = parser.parse_args()

    reporter = PipelineReporter()

    if args.quarter and args.year:
        report = await reporter.generate_quarterly_report(args.quarter, args.year)
    elif args.monthly:
        # 월간 보고서: 현재 연도 기준
        current_year = datetime.now().year
        report = await reporter.generate_quarterly_report('Q4', current_year - 1)
        report['report_type'] = 'monthly'
    else:
        parser.error('--quarter와 --year를 지정하거나 --monthly를 사용하세요')

    # 콘솔 출력
    print(reporter.format_markdown(report))

    # 파일 저장
    if args.save:
        reporter.save_report(report, format=args.format)


if __name__ == '__main__':
    asyncio.run(main())
