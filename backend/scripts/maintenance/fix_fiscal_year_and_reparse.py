"""
fiscal_year 수정 및 재파싱 스크립트

문제: 2025년 디렉토리에 저장된 사업보고서 (2024.12)가 fiscal_year=2025로 잘못 저장됨
     이로 인해 XBRL ACONTEXT(CFY2024)와 target_year(2025) 불일치로 revenue 등 추출 실패

해결:
1. fiscal_year=2025이면서 실제 회계연도가 2024인 레코드 식별
2. fiscal_year를 2024로 수정
3. XBRL Enhancer로 재파싱하여 누락된 revenue, operating_income 등 추출

사용법:
    python scripts/maintenance/fix_fiscal_year_and_reparse.py --dry-run   # 테스트
    python scripts/maintenance/fix_fiscal_year_and_reparse.py             # 실행
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
from scripts.parsers import FinancialParser
from scripts.parsers.xbrl_enhancer import XBRLEnhancer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


async def get_mismatched_records(conn) -> list:
    """fiscal_year가 잘못된 레코드 조회

    조건:
    - fiscal_year = 2025
    - data_source = 'LOCAL_DART_V3_XBRL'
    - revenue IS NULL (XBRL 추출 실패)
    """
    query = """
        SELECT
            fd.id,
            fd.company_id,
            fd.fiscal_year,
            fd.revenue,
            fd.operating_income,
            fd.data_source,
            c.corp_code,
            c.name as company_name
        FROM financial_details fd
        JOIN companies c ON fd.company_id = c.id
        WHERE fd.fiscal_year = 2025
          AND fd.data_source = 'LOCAL_DART_V3_XBRL'
          AND fd.revenue IS NULL
        ORDER BY c.name
    """
    return await conn.fetch(query)


def find_annual_report_zip(corp_code: str) -> tuple:
    """2025년 디렉토리에서 사업보고서 (2024.12) 찾기"""
    dart_dir = Path(__file__).parent.parent.parent / 'data' / 'dart'

    # batch_* 디렉토리 검색
    for batch_dir in sorted(dart_dir.glob('batch_*')):
        corp_dir = batch_dir / corp_code
        if not corp_dir.exists():
            continue

        year_dir = corp_dir / '2025'
        if not year_dir.exists():
            continue

        # 사업보고서 (2024.12) 찾기
        for meta_file in year_dir.glob('*_meta.json'):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                report_nm = meta.get('report_nm', '')
                # "사업보고서 (2024.12)" 형식 확인
                if '사업보고서' in report_nm and '2024' in report_nm:
                    zip_path = meta_file.with_name(
                        meta_file.name.replace('_meta.json', '.zip')
                    )
                    if zip_path.exists():
                        return zip_path, meta
            except Exception:
                continue

    return None, None


async def fix_and_reparse(
    conn,
    parser: FinancialParser,
    record: dict,
    dry_run: bool = False
) -> dict:
    """단일 레코드 수정 및 재파싱"""
    result = {
        'company_name': record['company_name'],
        'corp_code': record['corp_code'],
        'old_fiscal_year': record['fiscal_year'],
        'new_fiscal_year': 2024,
        'status': 'skipped',
        'revenue': None,
        'operating_income': None,
    }

    # ZIP 파일 찾기
    zip_path, meta = find_annual_report_zip(record['corp_code'])

    if not zip_path:
        result['status'] = 'no_zip'
        return result

    # report_nm에서 실제 회계연도 확인
    report_nm = meta.get('report_nm', '')
    if '2024' not in report_nm:
        result['status'] = 'wrong_year'
        return result

    try:
        # XBRL Enhancer로 직접 추출 (target_year=2024)
        import zipfile

        xml_content = None
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.xml') and not name.startswith('_'):
                    info = zf.getinfo(name)
                    raw = zf.read(name)
                    try:
                        content = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        content = raw.decode('euc-kr', errors='replace')

                    if xml_content is None or len(content) > len(xml_content):
                        xml_content = content

        if not xml_content:
            result['status'] = 'no_xml'
            return result

        # XBRL Enhancer로 2024년 데이터 추출
        enhancer = XBRLEnhancer()

        # OFS (별도재무제표) 먼저 시도
        xbrl_data = enhancer.extract_from_xml(xml_content, target_year=2024, fs_type='OFS')
        fs_type = 'OFS'

        # OFS에서 revenue가 없으면 CFS (연결재무제표) 시도
        if not xbrl_data.get('revenue'):
            xbrl_data = enhancer.extract_from_xml(xml_content, target_year=2024, fs_type='CFS')
            fs_type = 'CFS'

        result['revenue'] = xbrl_data.get('revenue')
        result['operating_income'] = xbrl_data.get('operating_income') or xbrl_data.get('gross_profit')
        result['fs_type'] = fs_type

        if not dry_run:
            # 1. fiscal_year 수정 + XBRL 데이터 업데이트
            update_query = """
                UPDATE financial_details
                SET
                    fiscal_year = 2024,
                    revenue = COALESCE($2, revenue),
                    operating_income = COALESCE($3, operating_income),
                    cost_of_sales = COALESCE($4, cost_of_sales),
                    net_income = COALESCE($5, net_income),
                    capital_stock = COALESCE($6, capital_stock),
                    capital_surplus = COALESCE($7, capital_surplus),
                    retained_earnings = COALESCE($8, retained_earnings),
                    treasury_stock = COALESCE($9, treasury_stock),
                    interest_expense = COALESCE($10, interest_expense),
                    tax_expense = COALESCE($11, tax_expense),
                    fs_type = $12,
                    data_source = 'LOCAL_DART_V3_XBRL_FIXED',
                    updated_at = NOW()
                WHERE id = $1
            """

            await conn.execute(
                update_query,
                record['id'],
                xbrl_data.get('revenue'),
                xbrl_data.get('operating_income'),
                xbrl_data.get('cost_of_sales'),
                xbrl_data.get('net_income'),
                xbrl_data.get('capital_stock'),
                xbrl_data.get('capital_surplus'),
                xbrl_data.get('retained_earnings'),
                xbrl_data.get('treasury_stock'),
                xbrl_data.get('interest_expense'),
                xbrl_data.get('tax_expense'),
                fs_type
            )

            result['status'] = 'fixed'
        else:
            result['status'] = 'dry_run'

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"Error processing {record['company_name']}: {e}")

    return result


async def main():
    arg_parser = argparse.ArgumentParser(description='fiscal_year 수정 및 재파싱')
    arg_parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 테스트')
    arg_parser.add_argument('--sample', type=int, help='샘플 N건만 처리')
    args = arg_parser.parse_args()

    logger.info("=" * 70)
    logger.info("fiscal_year 수정 및 재파싱 시작")
    logger.info("=" * 70)
    logger.info(f"  문제: fiscal_year=2025로 저장되었지만 실제 회계연도는 2024")
    logger.info(f"  해결: fiscal_year를 2024로 수정하고 XBRL Enhancer로 revenue 등 추출")
    logger.info(f"  Dry Run: {args.dry_run}")
    logger.info("=" * 70)

    # asyncpg URL 형식 변환
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')

    conn = await asyncpg.connect(db_url)

    try:
        # 문제 레코드 조회
        records = await get_mismatched_records(conn)

        if args.sample:
            records = records[:args.sample]

        logger.info(f"처리 대상: {len(records)}건 (fiscal_year=2025, revenue=NULL)")

        # 파서 초기화
        parser = FinancialParser(enable_xbrl=True)

        # 통계
        stats = {
            'total': len(records),
            'fixed': 0,
            'no_zip': 0,
            'no_xml': 0,
            'wrong_year': 0,
            'errors': 0,
            'revenue_recovered': 0,
        }

        # 처리 실행
        for i, record in enumerate(records, 1):
            result = await fix_and_reparse(conn, parser, record, args.dry_run)

            # 통계 업데이트
            if result['status'] in ['fixed', 'dry_run']:
                stats['fixed'] += 1
                if result['revenue']:
                    stats['revenue_recovered'] += 1
            elif result['status'] == 'no_zip':
                stats['no_zip'] += 1
            elif result['status'] == 'no_xml':
                stats['no_xml'] += 1
            elif result['status'] == 'wrong_year':
                stats['wrong_year'] += 1
            elif result['status'] == 'error':
                stats['errors'] += 1

            # 진행 상황 출력
            if i % 50 == 0 or i == len(records):
                logger.info(f"진행: {i}/{len(records)} ({i*100/len(records):.1f}%)")

            # 수정된 레코드 상세 출력 (처음 10건 또는 dry-run)
            if result['status'] in ['fixed', 'dry_run'] and (i <= 10 or args.dry_run):
                revenue_str = f"{result['revenue']:,}" if result['revenue'] else 'NULL'
                op_income_str = f"{result['operating_income']:,}" if result['operating_income'] else 'NULL'
                logger.info(
                    f"  {result['company_name']}: fiscal_year 2025→2024, "
                    f"revenue={revenue_str}, op_income={op_income_str}"
                )

        # 최종 통계
        logger.info("")
        logger.info("=" * 70)
        logger.info("수정 완료")
        logger.info("=" * 70)
        logger.info(f"  총 처리: {stats['total']}건")
        logger.info(f"  수정 완료: {stats['fixed']}건")
        logger.info(f"  매출액 복구: {stats['revenue_recovered']}건")
        logger.info(f"  ZIP 없음: {stats['no_zip']}건")
        logger.info(f"  XML 없음: {stats['no_xml']}건")
        logger.info(f"  연도 불일치: {stats['wrong_year']}건")
        logger.info(f"  오류: {stats['errors']}건")

        if args.dry_run:
            logger.info("")
            logger.info("⚠️ Dry Run 모드 - 실제 DB 업데이트 없음")
            logger.info("  실제 실행: python scripts/maintenance/fix_fiscal_year_and_reparse.py")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
