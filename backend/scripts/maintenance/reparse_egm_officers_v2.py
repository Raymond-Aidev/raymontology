#!/usr/bin/env python3
"""
EGM 공시 임원 재파싱 스크립트 (v2.0 테이블 기반 파서)

기존 dispute_officers 데이터를 삭제하고 새로운 테이블 기반 파서로 재파싱합니다.

사용법:
    # 특정 기업만 재파싱 (테스트)
    python -m scripts.maintenance.reparse_egm_officers_v2 --corp-name "이엠앤아이"

    # 전체 재파싱
    python -m scripts.maintenance.reparse_egm_officers_v2

    # Dry run (실제 저장 없이 테스트)
    python -m scripts.maintenance.reparse_egm_officers_v2 --dry-run

환경 변수:
    DATABASE_URL: PostgreSQL 연결 문자열
"""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'egm'


async def main():
    parser = argparse.ArgumentParser(description='EGM 공시 임원 재파싱 (v2.0)')
    parser.add_argument('--corp-name', type=str, help='특정 기업명만 재파싱')
    parser.add_argument('--limit', type=int, help='최대 재파싱 개수')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 테스트')
    parser.add_argument('--keep-existing', action='store_true', help='기존 임원 데이터 유지')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 필요합니다")

    # 파서 import
    from scripts.parsers.egm_officer import EGMOfficerParser

    pool = await asyncpg.create_pool(database_url)
    egm_parser = EGMOfficerParser()

    stats = {
        'total': 0,
        'parsed': 0,
        'officers_extracted': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'skipped': 0,
        'failed': 0,
    }

    try:
        async with pool.acquire() as conn:
            # 대상 공시 조회
            query = """
                SELECT
                    e.id,
                    e.disclosure_id,
                    e.company_id,
                    e.corp_code,
                    e.corp_name,
                    e.disclosure_date,
                    e.is_dispute_related
                FROM egm_disclosures e
                WHERE e.parse_status = 'PARSED'
            """

            if args.corp_name:
                query += f" AND e.corp_name LIKE '%{args.corp_name}%'"

            query += " ORDER BY e.disclosure_date DESC"

            if args.limit:
                query += f" LIMIT {args.limit}"

            rows = await conn.fetch(query)
            stats['total'] = len(rows)

            logger.info(f"재파싱 대상: {len(rows)}건")

            if args.dry_run:
                logger.info("=== Dry Run 모드 ===")

            # 기존 임원 데이터 삭제 (dry-run이 아닐 때)
            if not args.dry_run and not args.keep_existing:
                if args.corp_name:
                    # 특정 기업만 삭제
                    egm_ids = [r['id'] for r in rows]
                    if egm_ids:
                        deleted = await conn.execute("""
                            DELETE FROM dispute_officers
                            WHERE egm_disclosure_id = ANY($1)
                        """, egm_ids)
                        logger.info(f"기존 임원 데이터 삭제: {deleted}")
                else:
                    # 전체 삭제
                    deleted = await conn.execute("DELETE FROM dispute_officers")
                    logger.info(f"기존 임원 데이터 삭제: {deleted}")

            # 재파싱 실행
            for i, row in enumerate(rows):
                if (i + 1) % 20 == 0:
                    logger.info(f"진행: {i+1}/{len(rows)} ({(i+1)/len(rows)*100:.1f}%)")

                disclosure_id = row['disclosure_id']
                year = str(row['disclosure_date'].year) if row['disclosure_date'] else '2024'
                zip_path = DATA_DIR / year / f"{disclosure_id}.zip"

                if not zip_path.exists():
                    stats['skipped'] += 1
                    continue

                meta = {
                    'disclosure_id': disclosure_id,
                    'company_id': str(row['company_id']) if row['company_id'] else None,
                    'corp_code': row['corp_code'],
                    'corp_name': row['corp_name'],
                }

                try:
                    # 파싱 실행
                    result = await egm_parser.parse(zip_path, meta)

                    if result.get('success'):
                        officer_changes = result.get('officer_changes', [])

                        # 통계 수집
                        for officer in officer_changes:
                            stats['officers_extracted'] += 1
                            conf = officer.get('extraction_confidence', 'MEDIUM')
                            if conf == 'HIGH':
                                stats['high_confidence'] += 1
                            elif conf == 'MEDIUM':
                                stats['medium_confidence'] += 1
                            else:
                                stats['low_confidence'] += 1

                        if args.dry_run:
                            # Dry run: 결과 출력
                            if officer_changes:
                                logger.info(f"\n[{row['corp_name']}] {disclosure_id}")
                                for officer in officer_changes:
                                    name = officer.get('name', '?')
                                    birth = officer.get('birth_date', '-')
                                    position = officer.get('position', '-')
                                    career = officer.get('career', '')
                                    career_preview = career[:50] + '...' if len(career) > 50 else career
                                    conf = officer.get('extraction_confidence', 'MEDIUM')
                                    logger.info(f"  - {name} ({birth}) {position} [{conf}]")
                                    if career_preview:
                                        logger.info(f"    경력: {career_preview}")
                        else:
                            # 실제 저장
                            saved = await egm_parser.save_to_db(conn, result)
                            if saved:
                                stats['parsed'] += 1

                except Exception as e:
                    logger.error(f"파싱 오류 {disclosure_id}: {e}")
                    stats['failed'] += 1

            # 결과 출력
            logger.info(f"\n{'='*50}")
            logger.info(f"=== 재파싱 완료 (v2.0 테이블 기반 파서) ===")
            logger.info(f"{'='*50}")
            logger.info(f"총 대상: {stats['total']}건")
            logger.info(f"파싱 완료: {stats['parsed']}건")
            logger.info(f"스킵 (ZIP 없음): {stats['skipped']}건")
            logger.info(f"실패: {stats['failed']}건")
            logger.info(f"\n임원 추출 통계:")
            logger.info(f"  - 총 추출: {stats['officers_extracted']}명")
            logger.info(f"  - HIGH 신뢰도: {stats['high_confidence']}명")
            logger.info(f"  - MEDIUM 신뢰도: {stats['medium_confidence']}명")
            logger.info(f"  - LOW 신뢰도: {stats['low_confidence']}명")

            if stats['officers_extracted'] > 0:
                high_ratio = stats['high_confidence'] / stats['officers_extracted'] * 100
                logger.info(f"  - HIGH 비율: {high_ratio:.1f}%")

    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
