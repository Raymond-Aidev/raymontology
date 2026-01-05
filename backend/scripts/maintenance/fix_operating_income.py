"""
operating_income NULL 레코드 재파싱 스크립트

문제: 2024년 데이터 중 751건의 operating_income이 NULL
원인: XBRL Enhancer에 dart_OperatingIncomeLoss ACODE 매핑이 없었음
해결: 매핑 추가 후 해당 레코드들 재파싱

사용법:
    python scripts/maintenance/fix_operating_income.py --dry-run   # 테스트
    python scripts/maintenance/fix_operating_income.py             # 실행
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
from scripts.parsers.xbrl_enhancer import XBRLEnhancer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


async def get_null_operating_income_records(conn, fiscal_year: int = None) -> list:
    """operating_income이 NULL인 레코드 조회"""
    query = """
        SELECT
            fd.id,
            fd.company_id,
            fd.fiscal_year,
            fd.revenue,
            fd.operating_income,
            fd.data_source,
            fd.fs_type,
            c.corp_code,
            c.name as company_name
        FROM financial_details fd
        JOIN companies c ON fd.company_id = c.id
        WHERE fd.operating_income IS NULL
          AND fd.revenue IS NOT NULL
    """
    params = []

    if fiscal_year:
        query += " AND fd.fiscal_year = $1"
        params.append(fiscal_year)

    query += " ORDER BY fd.revenue DESC NULLS LAST"

    return await conn.fetch(query, *params)


def find_annual_report_zip(corp_code: str, fiscal_year: int) -> tuple:
    """사업보고서 ZIP 찾기 (fiscal_year 다음 해 제출분)"""
    dart_dir = Path(__file__).parent.parent.parent / 'data' / 'dart'

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

            # 사업보고서 찾기 (가장 큰 ZIP = 본문)
            best_zip = None
            best_size = 0
            best_meta = None

            for meta_file in year_dir.glob('*_meta.json'):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    report_nm = meta.get('report_nm', '')
                    if '사업보고서' in report_nm:
                        zip_path = meta_file.with_name(
                            meta_file.name.replace('_meta.json', '.zip')
                        )
                        if zip_path.exists():
                            size = zip_path.stat().st_size
                            if size > best_size:
                                best_size = size
                                best_zip = zip_path
                                best_meta = meta
                except Exception:
                    continue

            if best_zip:
                return best_zip, best_meta

    return None, None


def extract_xml_from_zip(zip_path: Path) -> str:
    """ZIP에서 가장 큰 XML 추출"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            largest = None
            largest_size = 0

            for name in zf.namelist():
                if name.endswith('.xml') and not name.startswith('_'):
                    info = zf.getinfo(name)
                    if info.file_size > largest_size:
                        largest = name
                        largest_size = info.file_size

            if largest:
                raw = zf.read(largest)
                try:
                    return raw.decode('utf-8')
                except UnicodeDecodeError:
                    return raw.decode('euc-kr', errors='replace')
    except Exception as e:
        logger.error(f"ZIP extraction error: {zip_path}: {e}")
    return None


async def fix_operating_income(
    conn,
    record: dict,
    enhancer: XBRLEnhancer,
    dry_run: bool = False
) -> dict:
    """단일 레코드 operating_income 추출 및 업데이트"""
    result = {
        'company_name': record['company_name'],
        'corp_code': record['corp_code'],
        'fiscal_year': record['fiscal_year'],
        'status': 'skipped',
        'operating_income': None,
    }

    # ZIP 파일 찾기
    zip_path, meta = find_annual_report_zip(record['corp_code'], record['fiscal_year'])

    if not zip_path:
        result['status'] = 'no_zip'
        return result

    # XML 추출
    xml_content = extract_xml_from_zip(zip_path)
    if not xml_content:
        result['status'] = 'no_xml'
        return result

    try:
        # XBRL Enhancer로 operating_income 추출
        fs_type = record['fs_type'] or 'OFS'

        # OFS 먼저 시도
        xbrl_data = enhancer.extract_from_xml(xml_content, target_year=record['fiscal_year'], fs_type='OFS')

        # OFS에서 없으면 CFS 시도
        if not xbrl_data.get('operating_income'):
            xbrl_data = enhancer.extract_from_xml(xml_content, target_year=record['fiscal_year'], fs_type='CFS')
            fs_type = 'CFS'

        operating_income = xbrl_data.get('operating_income')
        result['operating_income'] = operating_income
        result['fs_type'] = fs_type

        if operating_income is not None:
            if not dry_run:
                # DB 업데이트
                await conn.execute("""
                    UPDATE financial_details
                    SET operating_income = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, operating_income, record['id'])

            result['status'] = 'fixed'
        else:
            result['status'] = 'not_found'

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"Error processing {record['company_name']}: {e}")

    return result


async def main():
    arg_parser = argparse.ArgumentParser(description='operating_income NULL 레코드 수정')
    arg_parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 테스트')
    arg_parser.add_argument('--year', type=int, help='특정 연도만 처리 (예: 2024)')
    arg_parser.add_argument('--sample', type=int, help='샘플 N건만 처리')
    args = arg_parser.parse_args()

    logger.info("=" * 70)
    logger.info("operating_income NULL 레코드 수정 시작")
    logger.info("=" * 70)
    logger.info(f"  문제: operating_income이 NULL인 레코드")
    logger.info(f"  해결: XBRL Enhancer (dart_OperatingIncomeLoss)로 재추출")
    logger.info(f"  대상 연도: {args.year or '전체'}")
    logger.info(f"  Dry Run: {args.dry_run}")
    logger.info("=" * 70)

    # asyncpg URL 형식 변환
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')

    conn = await asyncpg.connect(db_url)

    try:
        # 문제 레코드 조회
        records = await get_null_operating_income_records(conn, args.year)

        if args.sample:
            records = records[:args.sample]

        logger.info(f"처리 대상: {len(records)}건 (operating_income=NULL, revenue≠NULL)")

        # XBRL Enhancer 초기화
        enhancer = XBRLEnhancer()

        # 통계
        stats = {
            'total': len(records),
            'fixed': 0,
            'no_zip': 0,
            'no_xml': 0,
            'not_found': 0,
            'errors': 0,
        }

        # 처리 실행
        for i, record in enumerate(records, 1):
            result = await fix_operating_income(conn, record, enhancer, args.dry_run)

            # 통계 업데이트
            if result['status'] == 'fixed':
                stats['fixed'] += 1
            elif result['status'] == 'no_zip':
                stats['no_zip'] += 1
            elif result['status'] == 'no_xml':
                stats['no_xml'] += 1
            elif result['status'] == 'not_found':
                stats['not_found'] += 1
            elif result['status'] == 'error':
                stats['errors'] += 1

            # 진행 상황 출력
            if i % 50 == 0 or i == len(records):
                logger.info(f"진행: {i}/{len(records)} ({i*100/len(records):.1f}%)")

            # 수정된 레코드 상세 출력 (처음 10건 또는 dry-run)
            if result['status'] == 'fixed' and (i <= 10 or args.dry_run):
                op_income_str = f"{result['operating_income']:,}" if result['operating_income'] else 'NULL'
                logger.info(
                    f"  {result['company_name']} ({result['fiscal_year']}): "
                    f"operating_income={op_income_str}"
                )

        # 최종 통계
        logger.info("")
        logger.info("=" * 70)
        logger.info("수정 완료")
        logger.info("=" * 70)
        logger.info(f"  총 처리: {stats['total']}건")
        logger.info(f"  수정 완료: {stats['fixed']}건")
        logger.info(f"  ZIP 없음: {stats['no_zip']}건")
        logger.info(f"  XML 없음: {stats['no_xml']}건")
        logger.info(f"  데이터 없음: {stats['not_found']}건")
        logger.info(f"  오류: {stats['errors']}건")

        if stats['fixed'] > 0:
            fix_rate = stats['fixed'] / stats['total'] * 100
            logger.info(f"  수정률: {fix_rate:.1f}%")

        if args.dry_run:
            logger.info("")
            logger.info("⚠️ Dry Run 모드 - 실제 DB 업데이트 없음")
            logger.info("  실제 실행: python scripts/maintenance/fix_operating_income.py")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
