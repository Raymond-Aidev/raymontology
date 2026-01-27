#!/usr/bin/env python3
"""
RaymondsIndex 인플레이션된 점수 수정 스크립트

목적:
- total_score가 Sub-Index 가중평균과 크게 차이나는 레코드 수정
- 등급(grade)을 새 점수에 맞게 재계산

안전장치:
1. --dry-run: 실제 변경 없이 영향 범위만 확인
2. --backup: 변경 전 백업 테이블 생성
3. --threshold: 수정 대상 차이값 설정 (기본 5점)
4. 트랜잭션 기반 - 실패 시 롤백

영향 범위:
- raymonds_index 테이블의 total_score, grade 컬럼만 수정
- 다른 서비스(RaymondsRisk Web/App)가 읽는 데이터와 호환성 유지

사용법:
    # 1단계: 영향 범위 확인 (필수)
    python scripts/maintenance/fix_inflated_scores.py --dry-run

    # 2단계: 백업 후 실행
    python scripts/maintenance/fix_inflated_scores.py --backup

    # 3단계: 실행 (백업 없이 - 권장하지 않음)
    python scripts/maintenance/fix_inflated_scores.py --execute

변경 이력:
    2026-01-27: 초기 버전 (인플레이션 문제 해결)
"""

import asyncio
import asyncpg
import argparse
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
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
    'CEI': 0.20,  # Capital Efficiency Index
    'RII': 0.35,  # Reinvestment Intensity Index
    'CGI': 0.25,  # Cash Governance Index
    'MAI': 0.20,  # Momentum Alignment Index
}

# 등급 기준 (v2.1)
# v2.1 완화 (2026-01-27)
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


def calculate_weighted_average(
    cei: Optional[Decimal],
    rii: Optional[Decimal],
    cgi: Optional[Decimal],
    mai: Optional[Decimal]
) -> Optional[float]:
    """Sub-Index 가중평균 계산"""
    if any(v is None for v in [cei, rii, cgi, mai]):
        return None

    total = (
        float(cei) * WEIGHTS['CEI'] +
        float(rii) * WEIGHTS['RII'] +
        float(cgi) * WEIGHTS['CGI'] +
        float(mai) * WEIGHTS['MAI']
    )
    return round(total, 2)


def determine_grade(score: float) -> str:
    """점수 → 등급 변환"""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return 'C'


class InflatedScoreFixer:
    """인플레이션된 점수 수정기"""

    def __init__(self, database_url: str, threshold: float = 5.0):
        """
        Args:
            database_url: PostgreSQL 연결 URL
            threshold: 수정 대상 판정 기준 (저장값 - 계산값 차이)
        """
        self.db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.threshold = threshold
        self.stats = {
            'total_checked': 0,
            'inflated_found': 0,
            'deflated_found': 0,
            'null_subindex': 0,
            'updated': 0,
            'errors': 0,
        }

    async def analyze(self, conn: asyncpg.Connection) -> List[Dict]:
        """
        불일치 레코드 분석

        Returns:
            수정이 필요한 레코드 목록
        """
        logger.info("=" * 70)
        logger.info("불일치 레코드 분석 시작")
        logger.info(f"판정 기준: |stored - calculated| > {self.threshold}")
        logger.info("=" * 70)

        query = """
            SELECT
                ri.id,
                ri.company_id,
                ri.fiscal_year,
                ri.total_score,
                ri.grade,
                ri.cei_score,
                ri.rii_score,
                ri.cgi_score,
                ri.mai_score,
                c.name as company_name,
                c.ticker
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            ORDER BY ri.total_score DESC
        """

        rows = await conn.fetch(query)
        mismatched = []

        for row in rows:
            self.stats['total_checked'] += 1

            # Sub-Index가 NULL인 경우
            if any(row[col] is None for col in ['cei_score', 'rii_score', 'cgi_score', 'mai_score']):
                self.stats['null_subindex'] += 1
                continue

            # 가중평균 계산
            calculated = calculate_weighted_average(
                row['cei_score'], row['rii_score'],
                row['cgi_score'], row['mai_score']
            )

            if calculated is None:
                continue

            stored = float(row['total_score']) if row['total_score'] else 0
            diff = stored - calculated

            # 불일치 판정
            if abs(diff) > self.threshold:
                if diff > 0:
                    self.stats['inflated_found'] += 1
                else:
                    self.stats['deflated_found'] += 1

                new_grade = determine_grade(calculated)

                mismatched.append({
                    'id': str(row['id']),
                    'company_id': str(row['company_id']),
                    'company_name': row['company_name'],
                    'ticker': row['ticker'],
                    'fiscal_year': row['fiscal_year'],
                    'stored_score': stored,
                    'calculated_score': calculated,
                    'diff': round(diff, 2),
                    'current_grade': row['grade'],
                    'new_grade': new_grade,
                    'grade_changed': row['grade'] != new_grade,
                    'cei': float(row['cei_score']),
                    'rii': float(row['rii_score']),
                    'cgi': float(row['cgi_score']),
                    'mai': float(row['mai_score']),
                })

        return mismatched

    async def create_backup(self, conn: asyncpg.Connection) -> str:
        """
        백업 테이블 생성

        Returns:
            백업 테이블명
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f'raymonds_index_backup_{timestamp}'

        logger.info(f"백업 테이블 생성: {backup_table}")

        await conn.execute(f"""
            CREATE TABLE {backup_table} AS
            SELECT * FROM raymonds_index
            WHERE id IN (
                SELECT ri.id FROM raymonds_index ri
                WHERE ri.cei_score IS NOT NULL
                  AND ri.rii_score IS NOT NULL
                  AND ri.cgi_score IS NOT NULL
                  AND ri.mai_score IS NOT NULL
                  AND ABS(
                      ri.total_score - (
                          ri.cei_score * 0.20 +
                          ri.rii_score * 0.35 +
                          ri.cgi_score * 0.25 +
                          ri.mai_score * 0.20
                      )
                  ) > {self.threshold}
            )
        """)

        count = await conn.fetchval(f"SELECT COUNT(*) FROM {backup_table}")
        logger.info(f"백업 완료: {count}개 레코드")

        return backup_table

    async def fix_records(
        self,
        conn: asyncpg.Connection,
        records: List[Dict],
        dry_run: bool = True
    ) -> int:
        """
        불일치 레코드 수정

        Args:
            conn: DB 연결
            records: 수정 대상 레코드
            dry_run: True면 실제 수정 안 함

        Returns:
            수정된 레코드 수
        """
        if dry_run:
            logger.info("\n[DRY-RUN 모드] 실제 변경 없음")
            return 0

        logger.info(f"\n수정 시작: {len(records)}개 레코드")
        updated = 0

        for record in records:
            try:
                await conn.execute("""
                    UPDATE raymonds_index
                    SET total_score = $1,
                        grade = $2
                    WHERE id = $3::uuid
                """,
                    record['calculated_score'],
                    record['new_grade'],
                    record['id']
                )
                updated += 1
                self.stats['updated'] += 1

                if updated % 100 == 0:
                    logger.info(f"진행: {updated}/{len(records)}")

            except Exception as e:
                logger.error(f"수정 실패 {record['company_name']}: {e}")
                self.stats['errors'] += 1

        return updated

    def print_analysis_report(self, mismatched: List[Dict]):
        """분석 결과 출력"""
        logger.info("\n" + "=" * 70)
        logger.info("분석 결과")
        logger.info("=" * 70)
        logger.info(f"전체 검사: {self.stats['total_checked']:,}개")
        logger.info(f"Sub-Index NULL: {self.stats['null_subindex']:,}개 (수정 불가)")
        logger.info(f"인플레이션 (stored > calc): {self.stats['inflated_found']:,}개")
        logger.info(f"디플레이션 (stored < calc): {self.stats['deflated_found']:,}개")
        logger.info(f"수정 대상 합계: {len(mismatched):,}개")

        if mismatched:
            # 인플레이션 TOP 10
            inflated = sorted([r for r in mismatched if r['diff'] > 0],
                            key=lambda x: x['diff'], reverse=True)[:10]

            if inflated:
                logger.info("\n[인플레이션 TOP 10]")
                logger.info("-" * 70)
                for r in inflated:
                    grade_change = f"{r['current_grade']} → {r['new_grade']}" if r['grade_changed'] else r['current_grade']
                    logger.info(
                        f"  {r['company_name'][:20]:20s} | "
                        f"저장:{r['stored_score']:6.2f} → 계산:{r['calculated_score']:6.2f} | "
                        f"차이:{r['diff']:+7.2f} | {grade_change}"
                    )

            # 등급 변경 요약
            grade_changes = {}
            for r in mismatched:
                if r['grade_changed']:
                    key = f"{r['current_grade']} → {r['new_grade']}"
                    grade_changes[key] = grade_changes.get(key, 0) + 1

            if grade_changes:
                logger.info("\n[등급 변경 요약]")
                logger.info("-" * 70)
                for change, count in sorted(grade_changes.items(), key=lambda x: -x[1]):
                    logger.info(f"  {change}: {count}건")

    async def run(
        self,
        dry_run: bool = True,
        create_backup: bool = False,
        execute: bool = False
    ):
        """
        메인 실행

        Args:
            dry_run: 분석만 수행 (기본값)
            create_backup: 백업 테이블 생성
            execute: 실제 수정 실행
        """
        conn = await asyncpg.connect(self.db_url)

        try:
            # 1. 분석
            mismatched = await self.analyze(conn)
            self.print_analysis_report(mismatched)

            if not mismatched:
                logger.info("\n수정 대상 레코드 없음")
                return

            # 2. 백업 (옵션)
            if create_backup or execute:
                backup_table = await self.create_backup(conn)
                logger.info(f"복원 방법: INSERT INTO raymonds_index SELECT * FROM {backup_table}")

            # 3. 수정
            if execute:
                logger.info("\n" + "=" * 70)
                logger.info("수정 실행")
                logger.info("=" * 70)

                # 트랜잭션 시작
                async with conn.transaction():
                    updated = await self.fix_records(conn, mismatched, dry_run=False)
                    logger.info(f"\n수정 완료: {updated}개 레코드")
            else:
                await self.fix_records(conn, mismatched, dry_run=True)
                logger.info("\n" + "=" * 70)
                logger.info("실제 수정을 실행하려면: --execute 옵션 사용")
                logger.info("백업과 함께 실행하려면: --backup --execute")
                logger.info("=" * 70)

        finally:
            await conn.close()

        # 최종 통계
        logger.info("\n[최종 통계]")
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value:,}")


async def main():
    parser = argparse.ArgumentParser(
        description='RaymondsIndex 인플레이션된 점수 수정',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  1. 영향 범위 확인 (필수 첫 단계):
     python scripts/maintenance/fix_inflated_scores.py --dry-run

  2. 백업 후 실행 (권장):
     python scripts/maintenance/fix_inflated_scores.py --backup --execute

  3. 특정 임계값으로 분석:
     python scripts/maintenance/fix_inflated_scores.py --threshold 10 --dry-run

⚠️ 주의: --execute 없이 실행하면 분석만 수행됩니다.
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='분석만 수행, 실제 변경 없음 (기본값)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='수정 전 백업 테이블 생성'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제 수정 실행 (⚠️ 주의)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=5.0,
        help='수정 대상 판정 기준 (|stored - calc| > threshold, 기본: 5.0)'
    )

    args = parser.parse_args()

    # 실행 모드 결정
    if args.execute:
        dry_run = False
        logger.warning("⚠️  실제 수정 모드로 실행합니다!")
    else:
        dry_run = True
        logger.info("분석 모드 (--execute 없음)")

    fixer = InflatedScoreFixer(DATABASE_URL, threshold=args.threshold)
    await fixer.run(
        dry_run=dry_run,
        create_backup=args.backup,
        execute=args.execute
    )


if __name__ == "__main__":
    asyncio.run(main())
