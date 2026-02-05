#!/usr/bin/env python3
"""
EGM 분쟁 임원 수집 통합 파이프라인

임시주주총회 공시에서 경영분쟁으로 선임된 임원 정보를 추출하는 파이프라인입니다.

단계:
1. collect: DB에서 EGM 관련 공시 조회 및 egm_disclosures 테이블 등록
2. download: DART API에서 공시 본문 다운로드
3. parse: 공시 본문에서 분쟁 분류 및 임원 정보 추출
4. match: 추출된 임원을 기존 officers 테이블과 매칭
5. report: 처리 결과 보고서 생성

사용법:
    # 전체 파이프라인 실행
    python -m scripts.pipeline.run_egm_officer_pipeline

    # 특정 연도만
    python -m scripts.pipeline.run_egm_officer_pipeline --year 2024

    # 특정 단계부터 시작
    python -m scripts.pipeline.run_egm_officer_pipeline --start-from parse

    # 테스트 모드
    python -m scripts.pipeline.run_egm_officer_pipeline --limit 10 --dry-run

    # 강제 재파싱 (이미 파싱된 공시도 다시 처리)
    python -m scripts.pipeline.run_egm_officer_pipeline --force-reparse

환경 변수:
    DATABASE_URL: PostgreSQL 연결 문자열
    DART_API_KEY: DART OpenAPI 키
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg

# 상위 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.collection.collect_egm_disclosures import EGMDisclosureCollector
from scripts.parsers.egm_officer import EGMOfficerParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터 디렉토리
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'egm'

# 파이프라인 단계 정의
PIPELINE_STEPS = ['collect', 'download', 'parse', 'match', 'report']


class EGMOfficerPipeline:
    """EGM 분쟁 임원 수집 통합 파이프라인"""

    def __init__(self, database_url: str, dart_api_key: str = None):
        self.database_url = database_url
        self.dart_api_key = dart_api_key or os.getenv('DART_API_KEY', '')
        self.pool: Optional[asyncpg.Pool] = None

        self.stats = {
            'total_disclosures': 0,
            'downloaded': 0,
            'parsed': 0,
            'dispute_found': 0,
            'officers_extracted': 0,
            'officers_matched': 0,
            'errors': 0,
        }

        self.run_id = str(uuid.uuid4())[:8]
        self.start_time = None

    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(self.database_url)
        self.start_time = datetime.now()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.pool:
            await self.pool.close()

    async def log_pipeline_run(
        self,
        step: str,
        status: str,
        details: Dict = None
    ):
        """파이프라인 실행 로그 기록"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO pipeline_runs (
                        id, run_type, status, started_at, completed_at,
                        total_records, processed_records, error_count, error_details
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        status = $3,
                        completed_at = $5,
                        processed_records = $7,
                        error_count = $8,
                        error_details = $9
                """,
                    uuid.UUID(self.run_id + '00000000000000000000000000000000'[:32]),
                    f'egm_officer_{step}',
                    status,
                    self.start_time,
                    datetime.now() if status in ['completed', 'failed'] else None,
                    self.stats['total_disclosures'],
                    self.stats['parsed'],
                    self.stats['errors'],
                    json.dumps(details or {}),
                )
            except Exception as e:
                logger.warning(f"파이프라인 로그 기록 실패: {e}")

    async def step_collect(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None,
        dry_run: bool = False,
    ) -> List[Dict]:
        """Step 1: EGM 관련 공시 수집 (DB 조회 및 메타데이터 저장)"""
        logger.info("=== Step 1: 공시 수집 ===")

        async with EGMDisclosureCollector(self.database_url, self.dart_api_key) as collector:
            result = await collector.collect_all(
                start_year=start_year,
                end_year=end_year,
                limit=limit,
                list_only=False,
                dry_run=dry_run,
                skip_download=True,  # 다운로드는 다음 단계에서
            )

        self.stats['total_disclosures'] = result['total_found']
        logger.info(f"수집 완료: {result['db_inserted']}건 등록")

        return result

    async def step_download(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None,
        dry_run: bool = False,
    ) -> Dict:
        """Step 2: DART API에서 공시 본문 다운로드"""
        logger.info("=== Step 2: 공시 다운로드 ===")

        async with EGMDisclosureCollector(self.database_url, self.dart_api_key) as collector:
            result = await collector.collect_all(
                start_year=start_year,
                end_year=end_year,
                limit=limit,
                list_only=False,
                dry_run=dry_run,
                skip_download=False,
            )

        self.stats['downloaded'] = result['downloaded']
        logger.info(f"다운로드 완료: {result['downloaded']}건")

        return result

    async def step_parse(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None,
        dry_run: bool = False,
        force_reparse: bool = False,
    ) -> Dict:
        """Step 3: 공시 본문 파싱 (분쟁 분류 + 임원 추출)"""
        logger.info("=== Step 3: 공시 파싱 ===")

        if end_year is None:
            end_year = datetime.now().year

        # 파싱 대상 조회
        async with self.pool.acquire() as conn:
            # 상태 조건
            status_condition = "AND parse_status = 'PENDING'" if not force_reparse else ""

            query = f"""
                SELECT
                    id, disclosure_id, corp_code, corp_name, company_id,
                    disclosure_date
                FROM egm_disclosures
                WHERE EXTRACT(YEAR FROM disclosure_date) >= $1
                  AND EXTRACT(YEAR FROM disclosure_date) <= $2
                  {status_condition}
                ORDER BY disclosure_date DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            rows = await conn.fetch(query, start_year, end_year)
            logger.info(f"파싱 대상: {len(rows)}건")

        if dry_run:
            logger.info("[DRY-RUN] 파싱 건너뜀")
            return {'parsed': 0, 'skipped': len(rows)}

        # 파서 인스턴스
        parser = EGMOfficerParser(self.database_url)

        parsed_count = 0
        error_count = 0
        dispute_count = 0
        officer_count = 0

        for i, row in enumerate(rows):
            if (i + 1) % 50 == 0:
                logger.info(f"파싱 진행: {i+1}/{len(rows)}")

            disclosure_id = row['disclosure_id']
            year = row['disclosure_date'].year if row['disclosure_date'] else None

            # ZIP 파일 경로 확인
            zip_path = None
            if year:
                zip_path = DATA_DIR / str(year) / f"{disclosure_id}.zip"

            if not zip_path or not zip_path.exists():
                logger.debug(f"ZIP 파일 없음: {disclosure_id}")
                continue

            try:
                # 파싱 실행
                meta = {
                    'disclosure_id': disclosure_id,
                    'corp_code': row['corp_code'],
                    'corp_name': row['corp_name'],
                    'company_id': str(row['company_id']) if row['company_id'] else None,
                    'disclosure_date': row['disclosure_date'].isoformat() if row['disclosure_date'] else None,
                }

                result = await parser.parse(zip_path, meta)

                if result:
                    # DB 저장
                    async with self.pool.acquire() as conn:
                        await parser.save_to_db(conn, result)

                    parsed_count += 1

                    if result.get('is_dispute_related'):
                        dispute_count += 1

                    officer_count += len(result.get('dispute_officers', []))

            except Exception as e:
                logger.error(f"파싱 오류 {disclosure_id}: {e}")
                error_count += 1

        self.stats['parsed'] = parsed_count
        self.stats['dispute_found'] = dispute_count
        self.stats['officers_extracted'] = officer_count
        self.stats['errors'] += error_count

        logger.info(f"파싱 완료: {parsed_count}건 (분쟁: {dispute_count}, 임원: {officer_count}명)")

        return {
            'parsed': parsed_count,
            'dispute_found': dispute_count,
            'officers_extracted': officer_count,
            'errors': error_count,
        }

    async def step_match(
        self,
        dry_run: bool = False,
    ) -> Dict:
        """Step 4: 추출된 임원을 기존 officers 테이블과 매칭"""
        logger.info("=== Step 4: 임원 매칭 ===")

        async with self.pool.acquire() as conn:
            # 매칭되지 않은 분쟁 임원 조회
            unmatched = await conn.fetch("""
                SELECT
                    id, officer_name, birth_date, company_id, position
                FROM dispute_officers
                WHERE officer_id IS NULL
                  AND is_verified = FALSE
            """)

            logger.info(f"매칭 대상: {len(unmatched)}명")

            if dry_run:
                logger.info("[DRY-RUN] 매칭 건너뜀")
                return {'matched': 0, 'unmatched': len(unmatched)}

            matched_count = 0

            for row in unmatched:
                officer_name = row['officer_name']
                birth_date = row['birth_date']
                company_id = row['company_id']

                # 매칭 시도: 이름 + 회사 + 출생년월
                match_query = """
                    SELECT o.id, o.name, o.birth_date
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    WHERE o.name = $1
                """
                params = [officer_name]

                if company_id:
                    match_query += " AND op.company_id = $2"
                    params.append(company_id)

                if birth_date:
                    match_query += f" AND o.birth_date LIKE ${len(params)+1}"
                    params.append(f"{birth_date}%")

                match_query += " LIMIT 1"

                matched_officer = await conn.fetchrow(match_query, *params)

                if matched_officer:
                    # 매칭 정보 업데이트
                    confidence = "HIGH" if birth_date else "MEDIUM"

                    await conn.execute("""
                        UPDATE dispute_officers
                        SET officer_id = $1,
                            officer_match_confidence = $2,
                            updated_at = NOW()
                        WHERE id = $3
                    """, matched_officer['id'], confidence, row['id'])

                    matched_count += 1

            self.stats['officers_matched'] = matched_count
            logger.info(f"매칭 완료: {matched_count}명")

            return {'matched': matched_count, 'unmatched': len(unmatched) - matched_count}

    async def step_report(self) -> Dict:
        """Step 5: 처리 결과 보고서 생성"""
        logger.info("=== Step 5: 보고서 생성 ===")

        async with self.pool.acquire() as conn:
            # 통계 조회
            total_egm = await conn.fetchval("SELECT COUNT(*) FROM egm_disclosures")
            dispute_egm = await conn.fetchval(
                "SELECT COUNT(*) FROM egm_disclosures WHERE is_dispute_related = TRUE"
            )
            parsed_egm = await conn.fetchval(
                "SELECT COUNT(*) FROM egm_disclosures WHERE parse_status = 'PARSED'"
            )
            total_officers = await conn.fetchval("SELECT COUNT(*) FROM dispute_officers")
            matched_officers = await conn.fetchval(
                "SELECT COUNT(*) FROM dispute_officers WHERE officer_id IS NOT NULL"
            )

            # 연도별 분포
            yearly_stats = await conn.fetch("""
                SELECT
                    EXTRACT(YEAR FROM disclosure_date)::int as year,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_dispute_related THEN 1 ELSE 0 END) as disputes
                FROM egm_disclosures
                WHERE disclosure_date IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM disclosure_date)
                ORDER BY year DESC
            """)

        report = {
            'run_id': self.run_id,
            'generated_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'summary': {
                'total_egm_disclosures': total_egm,
                'dispute_related': dispute_egm,
                'parsed': parsed_egm,
                'total_dispute_officers': total_officers,
                'officers_matched': matched_officers,
            },
            'yearly_distribution': [
                {'year': r['year'], 'total': r['total'], 'disputes': r['disputes']}
                for r in yearly_stats
            ],
            'pipeline_stats': self.stats,
        }

        # 보고서 저장
        report_dir = DATA_DIR / 'reports'
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"egm_pipeline_{self.run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"보고서 저장: {report_path}")

        # 콘솔 출력
        print("\n" + "=" * 60)
        print("EGM 분쟁 임원 수집 파이프라인 결과")
        print("=" * 60)
        print(f"실행 ID: {self.run_id}")
        print(f"소요 시간: {report['duration_seconds']:.1f}초")
        print()
        print("[전체 현황]")
        print(f"  - EGM 공시: {total_egm:,}건")
        print(f"  - 경영분쟁 관련: {dispute_egm:,}건 ({dispute_egm/total_egm*100:.1f}%)" if total_egm else "  - 경영분쟁 관련: 0건")
        print(f"  - 파싱 완료: {parsed_egm:,}건")
        print(f"  - 분쟁 선임 임원: {total_officers:,}명")
        print(f"  - 기존 임원 매칭: {matched_officers:,}명")
        print()
        print("[연도별 분포]")
        for r in yearly_stats[:5]:
            print(f"  - {r['year']}: {r['total']:,}건 (분쟁: {r['disputes']:,}건)")
        print("=" * 60)

        return report

    async def run(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None,
        start_from: str = 'collect',
        dry_run: bool = False,
        force_reparse: bool = False,
    ) -> Dict:
        """전체 파이프라인 실행"""
        logger.info(f"=== EGM 분쟁 임원 수집 파이프라인 시작 (run_id: {self.run_id}) ===")
        logger.info(f"기간: {start_year} ~ {end_year or '현재'}")
        logger.info(f"시작 단계: {start_from}")
        if dry_run:
            logger.info("[DRY-RUN 모드]")

        await self.log_pipeline_run('start', 'running')

        try:
            # 단계 순서 결정
            start_idx = PIPELINE_STEPS.index(start_from) if start_from in PIPELINE_STEPS else 0

            for step in PIPELINE_STEPS[start_idx:]:
                if step == 'collect':
                    await self.step_collect(start_year, end_year, limit, dry_run)
                elif step == 'download':
                    await self.step_download(start_year, end_year, limit, dry_run)
                elif step == 'parse':
                    await self.step_parse(start_year, end_year, limit, dry_run, force_reparse)
                elif step == 'match':
                    await self.step_match(dry_run)
                elif step == 'report':
                    await self.step_report()

            await self.log_pipeline_run('complete', 'completed', self.stats)
            logger.info("=== 파이프라인 완료 ===")

        except Exception as e:
            logger.error(f"파이프라인 오류: {e}")
            await self.log_pipeline_run('error', 'failed', {'error': str(e)})
            raise

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description='EGM 분쟁 임원 수집 파이프라인')
    parser.add_argument('--year', type=int, help='특정 연도만 처리')
    parser.add_argument('--start-year', type=int, default=2022, help='시작 연도 (기본: 2022)')
    parser.add_argument('--end-year', type=int, help='종료 연도')
    parser.add_argument('--limit', type=int, help='최대 처리 건수')
    parser.add_argument('--start-from', choices=PIPELINE_STEPS, default='collect',
                        help='시작 단계 (기본: collect)')
    parser.add_argument('--dry-run', action='store_true', help='실제 DB 변경 없이 테스트')
    parser.add_argument('--force-reparse', action='store_true', help='이미 파싱된 공시도 재파싱')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

    start_year = args.year or args.start_year
    end_year = args.year if args.year else args.end_year

    async with EGMOfficerPipeline(database_url) as pipeline:
        await pipeline.run(
            start_year=start_year,
            end_year=end_year,
            limit=args.limit,
            start_from=args.start_from,
            dry_run=args.dry_run,
            force_reparse=args.force_reparse,
        )


if __name__ == '__main__':
    asyncio.run(main())
