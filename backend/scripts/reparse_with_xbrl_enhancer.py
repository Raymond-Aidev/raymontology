"""
XBRL Enhancer를 사용한 financial_details 재파싱 스크립트

v3.0 파서(FinancialParser + XBRLEnhancer)를 사용하여
2022-2025년 전체 데이터를 재파싱합니다.

사용법:
    python scripts/reparse_with_xbrl_enhancer.py [--year YEAR] [--sample N] [--dry-run]

옵션:
    --year YEAR   특정 연도만 재파싱 (예: --year 2024)
    --sample N    샘플 N건만 처리 (테스트용)
    --dry-run     실제 DB 업데이트 없이 추출 결과만 출력
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from scripts.parsers import FinancialParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


async def get_existing_records(conn, target_year: int = None) -> list:
    """기존 financial_details 레코드 조회"""
    query = """
        SELECT
            fd.id,
            fd.company_id,
            fd.fiscal_year,
            fd.report_type,
            c.corp_code,
            c.name as company_name
        FROM financial_details fd
        JOIN companies c ON fd.company_id = c.id
        WHERE 1=1
    """
    params = []

    if target_year:
        query += " AND fd.fiscal_year = $1"
        params.append(target_year)

    query += " ORDER BY fd.fiscal_year DESC, c.name"

    return await conn.fetch(query, *params)


async def find_report_zip(corp_code: str, fiscal_year: int, report_type: str) -> Path:
    """회사 코드와 연도로 보고서 ZIP 파일 찾기"""
    dart_dir = Path(__file__).parent.parent / 'data' / 'dart'

    # 제출 연도는 fiscal_year + 1 (사업보고서는 다음 해 3월에 제출)
    search_years = [fiscal_year + 1, fiscal_year]

    for batch_dir in sorted(dart_dir.glob('batch_*')):
        corp_dir = batch_dir / corp_code
        if not corp_dir.exists():
            continue

        for search_year in search_years:
            year_dir = corp_dir / str(search_year)
            if not year_dir.exists():
                continue

            # 사업보고서 찾기
            for meta_file in year_dir.glob('*_meta.json'):
                import json
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    report_nm = meta.get('report_nm', '')
                    if '사업보고서' in report_nm:
                        zip_path = meta_file.with_name(
                            meta_file.name.replace('_meta.json', '.zip')
                        )
                        if zip_path.exists():
                            return zip_path, meta
                except Exception:
                    continue

    return None, None


async def reparse_single_record(
    conn,
    parser: FinancialParser,
    record: dict,
    dry_run: bool = False
) -> dict:
    """단일 레코드 재파싱"""
    result = {
        'company_name': record['company_name'],
        'fiscal_year': record['fiscal_year'],
        'status': 'skipped',
        'enhanced_fields': 0,
        'details': {}
    }

    # ZIP 파일 찾기
    zip_path, meta = await find_report_zip(
        record['corp_code'],
        record['fiscal_year'],
        record['report_type']
    )

    if not zip_path:
        result['status'] = 'no_zip'
        return result

    try:
        # v3.0 파서로 파싱
        parse_result = await parser.parse(zip_path, meta)

        if not parse_result or not parse_result.get('success'):
            result['status'] = 'parse_failed'
            return result

        # 파싱된 데이터 추출
        parsed_data = parse_result.get('data', {})

        # XBRL로 보완된 필드 확인 (DB에 존재하는 컬럼만)
        xbrl_fields = [
            'capital_stock', 'capital_surplus', 'retained_earnings', 'treasury_stock',
            'trade_payables', 'short_term_borrowings', 'long_term_borrowings',
            'bonds_payable', 'lease_liabilities', 'other_current_liabilities',
            'other_non_current_liabilities', 'deferred_tax_liabilities',
        ]

        enhanced_count = 0
        for field in xbrl_fields:
            value = parsed_data.get(field)
            if value is not None:
                enhanced_count += 1
                result['details'][field] = value

        result['enhanced_fields'] = enhanced_count

        if not dry_run and enhanced_count > 0:
            # DB 업데이트
            update_fields = []
            update_values = []
            param_idx = 1

            for field in xbrl_fields:
                value = parsed_data.get(field)
                if value is not None:
                    update_fields.append(f"{field} = ${param_idx}")
                    update_values.append(value)
                    param_idx += 1

            if update_fields:
                # 업데이트 시간 및 소스 추가
                update_fields.append(f"updated_at = ${param_idx}")
                update_values.append(datetime.utcnow())
                param_idx += 1

                update_fields.append(f"data_source = ${param_idx}")
                update_values.append('LOCAL_DART_V3_XBRL')
                param_idx += 1

                update_values.append(record['id'])

                query = f"""
                    UPDATE financial_details
                    SET {', '.join(update_fields)}
                    WHERE id = ${param_idx}
                """

                await conn.execute(query, *update_values)
                result['status'] = 'updated'
        else:
            result['status'] = 'dry_run' if dry_run else 'no_changes'

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"Error parsing {record['company_name']}: {e}")

    return result


async def main():
    arg_parser = argparse.ArgumentParser(description='XBRL Enhancer 재파싱')
    arg_parser.add_argument('--year', type=int, help='특정 연도만 처리')
    arg_parser.add_argument('--sample', type=int, help='샘플 N건만 처리')
    arg_parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 테스트')
    args = arg_parser.parse_args()

    logger.info("=" * 60)
    logger.info("XBRL Enhancer 재파싱 시작")
    logger.info(f"  - 대상 연도: {args.year or '전체 (2022-2025)'}")
    logger.info(f"  - 샘플 수: {args.sample or '전체'}")
    logger.info(f"  - Dry Run: {args.dry_run}")
    logger.info("=" * 60)

    # asyncpg URL 형식 변환
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')

    conn = await asyncpg.connect(db_url)

    try:
        # 기존 레코드 조회
        records = await get_existing_records(conn, args.year)

        if args.sample:
            records = records[:args.sample]

        logger.info(f"처리 대상: {len(records)}건")

        # 파서 초기화 (XBRL Enhancer 활성화)
        parser = FinancialParser(enable_xbrl=True)

        # 통계
        stats = {
            'total': len(records),
            'updated': 0,
            'no_zip': 0,
            'parse_failed': 0,
            'no_changes': 0,
            'errors': 0,
            'total_enhanced_fields': 0
        }

        # 재파싱 실행
        for i, record in enumerate(records, 1):
            result = await reparse_single_record(conn, parser, record, args.dry_run)

            # 통계 업데이트
            if result['status'] == 'updated' or result['status'] == 'dry_run':
                stats['updated'] += 1
                stats['total_enhanced_fields'] += result['enhanced_fields']
            elif result['status'] == 'no_zip':
                stats['no_zip'] += 1
            elif result['status'] == 'parse_failed':
                stats['parse_failed'] += 1
            elif result['status'] == 'no_changes':
                stats['no_changes'] += 1
            elif result['status'] == 'error':
                stats['errors'] += 1

            # 진행 상황 출력
            if i % 100 == 0 or i == len(records):
                logger.info(f"진행: {i}/{len(records)} ({i*100/len(records):.1f}%)")

            # 향상된 필드가 있으면 상세 출력
            if result['enhanced_fields'] > 0 and (args.dry_run or i <= 10):
                logger.info(f"  {result['company_name']} ({result['fiscal_year']}): +{result['enhanced_fields']} fields")
                for field, value in list(result['details'].items())[:3]:
                    logger.info(f"    - {field}: {value:,}")

        # 최종 통계
        logger.info("")
        logger.info("=" * 60)
        logger.info("재파싱 완료")
        logger.info("=" * 60)
        logger.info(f"  총 처리: {stats['total']}건")
        logger.info(f"  업데이트: {stats['updated']}건")
        logger.info(f"  ZIP 없음: {stats['no_zip']}건")
        logger.info(f"  파싱 실패: {stats['parse_failed']}건")
        logger.info(f"  변경 없음: {stats['no_changes']}건")
        logger.info(f"  오류: {stats['errors']}건")
        logger.info(f"  보완된 필드 총계: {stats['total_enhanced_fields']}개")

        if args.dry_run:
            logger.info("")
            logger.info("⚠️ Dry Run 모드 - 실제 DB 업데이트 없음")
            logger.info("  실제 업데이트: python scripts/reparse_with_xbrl_enhancer.py")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
