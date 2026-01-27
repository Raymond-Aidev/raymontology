#!/usr/bin/env python3
"""
RaymondsIndex 데이터 무결성 검증 스크립트

목적:
- 배치 계산 후 데이터 정합성 자동 검증
- total_score vs Sub-Index 가중평균 일치 검증
- grade vs score 기준 일치 검증
- 이상치 및 NULL 데이터 탐지

사용법:
    # 전체 검증
    python scripts/maintenance/validate_index_scores.py

    # 특정 연도만 검증
    python scripts/maintenance/validate_index_scores.py --year 2024

    # JSON 리포트 출력
    python scripts/maintenance/validate_index_scores.py --format json

    # 파이프라인 통합용 (비정상 시 exit code 1)
    python scripts/maintenance/validate_index_scores.py --strict
"""

import asyncio
import asyncpg
import argparse
import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

# Sub-Index 가중치 (v2.1)
WEIGHTS = {
    'CEI': 0.20,
    'RII': 0.35,
    'CGI': 0.25,
    'MAI': 0.20,
}

# 등급 기준 (v2.1 완화 2026-01-27)
GRADE_THRESHOLDS = [
    (88, 'A++'),  # v2.1: 95 → 88
    (80, 'A+'),   # v2.1: 88 → 80
    (72, 'A'),    # v2.1: 80 → 72
    (64, 'A-'),   # v2.1: 72 → 64
    (55, 'B+'),   # v2.1: 64 → 55
    (45, 'B'),    # v2.1: 55 → 45
    (35, 'B-'),   # v2.1: 45 → 35
    (20, 'C+'),   # v2.1: 30 → 20
    (0, 'C'),
]


def expected_grade(score: float) -> str:
    """점수에 맞는 예상 등급 반환"""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return 'C'


class IndexScoreValidator:
    """RaymondsIndex 점수 검증기"""

    def __init__(self, database_url: str, year: Optional[int] = None, strict: bool = False):
        self.db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.year = year
        self.strict = strict
        self.issues = {
            'score_mismatch': [],  # total_score != weighted avg
            'grade_mismatch': [],  # grade != expected grade
            'null_subindex': [],   # Sub-Index가 NULL인데 score 있음
            'outliers': [],        # 이상치 (score < 0 or > 100)
            'duplicate': [],       # 중복 레코드
        }
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'score_mismatches': 0,
            'grade_mismatches': 0,
            'null_subindex': 0,
            'outliers': 0,
        }

    async def validate(self, conn: asyncpg.Connection) -> Dict[str, Any]:
        """전체 검증 실행"""
        logger.info("=" * 70)
        logger.info("RaymondsIndex 데이터 무결성 검증")
        logger.info("=" * 70)

        if self.year:
            logger.info(f"대상 연도: {self.year}")

        # 1. 기본 데이터 조회
        await self._load_data(conn)

        # 2. 점수 일치 검증
        await self._validate_score_calculation(conn)

        # 3. 등급 일치 검증
        await self._validate_grade(conn)

        # 4. NULL Sub-Index 검증
        await self._validate_null_subindex(conn)

        # 5. 이상치 검증
        await self._validate_outliers(conn)

        # 6. 중복 검증
        await self._validate_duplicates(conn)

        # 결과 집계
        self.stats['valid_records'] = (
            self.stats['total_records'] -
            self.stats['score_mismatches'] -
            self.stats['grade_mismatches'] -
            self.stats['null_subindex'] -
            self.stats['outliers']
        )

        return {
            'stats': self.stats,
            'issues': self.issues,
            'passed': len(self.issues['score_mismatch']) == 0 and
                     len(self.issues['grade_mismatch']) == 0 and
                     len(self.issues['outliers']) == 0,
        }

    async def _load_data(self, conn: asyncpg.Connection):
        """기본 데이터 로드"""
        query = "SELECT COUNT(*) FROM raymonds_index"
        if self.year:
            query += f" WHERE fiscal_year = {self.year}"

        self.stats['total_records'] = await conn.fetchval(query)
        logger.info(f"전체 레코드: {self.stats['total_records']:,}개")

    async def _validate_score_calculation(self, conn: asyncpg.Connection):
        """점수 계산 일치 검증"""
        logger.info("\n[1] 점수 계산 검증")

        query = """
            SELECT
                ri.id,
                c.name,
                ri.total_score,
                ri.cei_score, ri.rii_score, ri.cgi_score, ri.mai_score,
                ri.grade,
                ri.fiscal_year
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            WHERE ri.cei_score IS NOT NULL
              AND ri.rii_score IS NOT NULL
              AND ri.cgi_score IS NOT NULL
              AND ri.mai_score IS NOT NULL
        """
        if self.year:
            query += f" AND ri.fiscal_year = {self.year}"

        rows = await conn.fetch(query)

        mismatch_count = 0
        for row in rows:
            calculated = (
                float(row['cei_score']) * WEIGHTS['CEI'] +
                float(row['rii_score']) * WEIGHTS['RII'] +
                float(row['cgi_score']) * WEIGHTS['CGI'] +
                float(row['mai_score']) * WEIGHTS['MAI']
            )
            stored = float(row['total_score'])

            # 소수점 오차 허용 (0.1점)
            if abs(stored - calculated) > 0.1:
                mismatch_count += 1
                if mismatch_count <= 10:  # 최대 10개만 기록
                    self.issues['score_mismatch'].append({
                        'company': row['name'],
                        'stored': round(stored, 2),
                        'calculated': round(calculated, 2),
                        'diff': round(stored - calculated, 2),
                    })

        self.stats['score_mismatches'] = mismatch_count

        if mismatch_count == 0:
            logger.info("  ✓ 점수 계산 일치: 모든 레코드 정상")
        else:
            logger.warning(f"  ✗ 점수 불일치: {mismatch_count}개 레코드")
            for issue in self.issues['score_mismatch'][:5]:
                logger.warning(
                    f"    - {issue['company']}: {issue['stored']} vs {issue['calculated']} "
                    f"(차이: {issue['diff']:+.2f})"
                )

    async def _validate_grade(self, conn: asyncpg.Connection):
        """등급 일치 검증"""
        logger.info("\n[2] 등급 검증")

        query = """
            SELECT ri.id, c.name, ri.total_score, ri.grade
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            WHERE ri.total_score IS NOT NULL
        """
        if self.year:
            query += f" AND ri.fiscal_year = {self.year}"

        rows = await conn.fetch(query)

        mismatch_count = 0
        for row in rows:
            score = float(row['total_score'])
            exp_grade = expected_grade(score)

            if row['grade'] != exp_grade:
                mismatch_count += 1
                if mismatch_count <= 10:
                    self.issues['grade_mismatch'].append({
                        'company': row['name'],
                        'score': round(score, 2),
                        'stored_grade': row['grade'],
                        'expected_grade': exp_grade,
                    })

        self.stats['grade_mismatches'] = mismatch_count

        if mismatch_count == 0:
            logger.info("  ✓ 등급 일치: 모든 레코드 정상")
        else:
            logger.warning(f"  ✗ 등급 불일치: {mismatch_count}개 레코드")
            for issue in self.issues['grade_mismatch'][:5]:
                logger.warning(
                    f"    - {issue['company']}: {issue['score']}점 "
                    f"({issue['stored_grade']} → {issue['expected_grade']})"
                )

    async def _validate_null_subindex(self, conn: asyncpg.Connection):
        """NULL Sub-Index 검증"""
        logger.info("\n[3] NULL Sub-Index 검증")

        query = """
            SELECT COUNT(*) FROM raymonds_index
            WHERE total_score IS NOT NULL
              AND (cei_score IS NULL OR rii_score IS NULL
                   OR cgi_score IS NULL OR mai_score IS NULL)
        """
        if self.year:
            query += f" AND fiscal_year = {self.year}"

        count = await conn.fetchval(query)
        self.stats['null_subindex'] = count

        if count == 0:
            logger.info("  ✓ NULL Sub-Index 없음")
        else:
            logger.warning(f"  ⚠ NULL Sub-Index: {count}개 레코드")
            logger.info("    (신규 IPO 등 재무 데이터 부족 가능성)")

    async def _validate_outliers(self, conn: asyncpg.Connection):
        """이상치 검증"""
        logger.info("\n[4] 이상치 검증")

        query = """
            SELECT ri.id, c.name, ri.total_score, ri.grade
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            WHERE ri.total_score < 0 OR ri.total_score > 100
        """
        if self.year:
            query += f" AND ri.fiscal_year = {self.year}"

        rows = await conn.fetch(query)
        self.stats['outliers'] = len(rows)

        if len(rows) == 0:
            logger.info("  ✓ 이상치 없음 (0-100 범위 내)")
        else:
            logger.error(f"  ✗ 이상치 발견: {len(rows)}개 레코드")
            for row in rows[:5]:
                self.issues['outliers'].append({
                    'company': row['name'],
                    'score': float(row['total_score']),
                })
                logger.error(f"    - {row['name']}: {row['total_score']}")

    async def _validate_duplicates(self, conn: asyncpg.Connection):
        """중복 레코드 검증"""
        logger.info("\n[5] 중복 레코드 검증")

        query = """
            SELECT company_id, fiscal_year, COUNT(*) as cnt
            FROM raymonds_index
            GROUP BY company_id, fiscal_year
            HAVING COUNT(*) > 1
        """

        rows = await conn.fetch(query)

        if len(rows) == 0:
            logger.info("  ✓ 중복 레코드 없음")
        else:
            logger.warning(f"  ⚠ 중복 레코드: {len(rows)}개 그룹")
            for row in rows:
                self.issues['duplicate'].append({
                    'company_id': str(row['company_id']),
                    'fiscal_year': row['fiscal_year'],
                    'count': row['cnt'],
                })

    def print_summary(self, result: Dict[str, Any]):
        """검증 결과 요약 출력"""
        logger.info("\n" + "=" * 70)
        logger.info("검증 결과 요약")
        logger.info("=" * 70)
        logger.info(f"전체 레코드: {self.stats['total_records']:,}")
        logger.info(f"정상 레코드: {self.stats['valid_records']:,}")
        logger.info(f"점수 불일치: {self.stats['score_mismatches']}")
        logger.info(f"등급 불일치: {self.stats['grade_mismatches']}")
        logger.info(f"NULL Sub-Index: {self.stats['null_subindex']}")
        logger.info(f"이상치: {self.stats['outliers']}")

        if result['passed']:
            logger.info("\n✅ 검증 통과")
        else:
            logger.error("\n❌ 검증 실패 - 데이터 수정 필요")

    async def run(self) -> bool:
        """검증 실행"""
        conn = await asyncpg.connect(self.db_url)

        try:
            result = await self.validate(conn)
            self.print_summary(result)
            return result['passed']

        finally:
            await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='RaymondsIndex 데이터 무결성 검증')
    parser.add_argument('--year', type=int, help='특정 연도만 검증')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='출력 형식 (기본: text)')
    parser.add_argument('--strict', action='store_true',
                        help='검증 실패 시 exit code 1 반환 (파이프라인 통합용)')

    args = parser.parse_args()

    validator = IndexScoreValidator(
        DATABASE_URL,
        year=args.year,
        strict=args.strict
    )

    passed = await validator.run()

    if args.format == 'json':
        print(json.dumps({
            'stats': validator.stats,
            'issues': validator.issues,
            'passed': passed,
        }, indent=2, ensure_ascii=False))

    if args.strict and not passed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
