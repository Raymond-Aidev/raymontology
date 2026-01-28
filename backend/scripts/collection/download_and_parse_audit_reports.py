"""
신규 상장 기업 감사보고서 다운로드 및 파싱 (v1.0)

45개 신규 상장 기업의 감사보고서를 DART API에서 다운로드하고
financial_details 테이블에 적재합니다.

대상 기업: 사업보고서 없이 감사보고서만 있는 기업 (2024년 기준)

사용법:
    # 대상 기업 조회만
    python -m scripts.collection.download_and_parse_audit_reports --list

    # 테스트 (샘플 3개, dry-run)
    python -m scripts.collection.download_and_parse_audit_reports --sample 3 --dry-run

    # 전체 실행
    python -m scripts.collection.download_and_parse_audit_reports

환경 변수:
    DATABASE_URL: DB 접속 정보 (필수)
    DART_API_KEY: DART OpenAPI 키 (필수)
"""

import argparse
import asyncio
import io
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import asyncpg
import httpx
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수 로드
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env.production')

# 설정
DB_URL = os.getenv('DATABASE_URL', '')
DB_URL = DB_URL.replace('postgresql+asyncpg://', 'postgresql://')  # asyncpg 호환

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_DOCUMENT_URL = 'https://opendart.fss.or.kr/api/document.xml'

# 저장 경로
AUDIT_REPORTS_DIR = PROJECT_ROOT / 'data' / 'audit_reports' / '2024'


async def get_target_companies(conn: asyncpg.Connection, fiscal_year: int = 2024) -> List[Dict]:
    """감사보고서만 있는 기업 목록 조회

    조건:
    - LISTED 기업
    - 해당 연도 사업보고서 없음
    - 해당 연도 감사보고서 있음
    - financial_details에 해당 연도 데이터 없음
    """
    query = """
    WITH target_companies AS (
        SELECT c.id, c.ticker, c.name, c.corp_code
        FROM companies c
        LEFT JOIN financial_details fd ON c.id = fd.company_id AND fd.fiscal_year = $1
        WHERE c.listing_status = 'LISTED'
          AND c.company_type IN ('NORMAL', 'SPAC', 'REIT')
          AND fd.id IS NULL  -- financial_details 없음
    )
    SELECT
        tc.id,
        tc.ticker,
        tc.name,
        tc.corp_code,
        d.rcept_no,
        d.report_nm,
        d.rcept_dt
    FROM target_companies tc
    JOIN disclosures d ON tc.corp_code = d.corp_code
    WHERE d.report_nm LIKE '%감사보고서%'
      AND d.report_nm LIKE '%(' || $1::text || '%'  -- 해당 연도
      AND NOT EXISTS (
          -- 사업보고서가 없는 기업만
          SELECT 1 FROM disclosures d2
          WHERE d2.corp_code = tc.corp_code
            AND d2.report_nm LIKE '%사업보고서%'
            AND d2.report_nm LIKE '%(' || $1::text || '%'
      )
    ORDER BY tc.name, d.rcept_dt DESC
    """

    rows = await conn.fetch(query, fiscal_year)

    # 기업별로 가장 최근 감사보고서만 선택
    companies = {}
    for row in rows:
        corp_code = row['corp_code']
        if corp_code not in companies:
            companies[corp_code] = dict(row)

    return list(companies.values())


async def download_report(rcept_no: str, output_dir: Path) -> Optional[Path]:
    """DART API에서 보고서 다운로드

    Args:
        rcept_no: 접수번호
        output_dir: 저장 디렉토리

    Returns:
        저장된 ZIP 파일 경로 (실패 시 None)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{rcept_no}.zip"

    # 이미 존재하면 스킵
    if zip_path.exists():
        logger.debug(f"Already exists: {zip_path}")
        return zip_path

    url = f"{DART_DOCUMENT_URL}?crtfc_key={DART_API_KEY}&rcept_no={rcept_no}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"Download failed: {rcept_no} - HTTP {response.status_code}")
                return None

            content = response.content

            # ZIP 파일 확인
            if content[:4] != b'PK\x03\x04':
                # XML 에러 응답일 수 있음
                if b'errCode' in content:
                    logger.warning(f"DART API error: {rcept_no}")
                    return None

            # 저장
            with open(zip_path, 'wb') as f:
                f.write(content)

            logger.debug(f"Downloaded: {zip_path}")
            return zip_path

    except Exception as e:
        logger.error(f"Download error: {rcept_no} - {e}")
        return None


async def parse_and_save(
    conn: asyncpg.Connection,
    zip_path: Path,
    meta: Dict,
    dry_run: bool = False
) -> bool:
    """감사보고서 파싱 및 DB 저장

    Args:
        conn: DB 연결
        zip_path: ZIP 파일 경로
        meta: 메타데이터 (company_id, corp_code, rcept_no, report_nm)
        dry_run: True면 저장 안함

    Returns:
        성공 여부
    """
    from scripts.parsers.audit_report_parser import AuditReportParser

    parser = AuditReportParser(skip_db_check=True)

    # 파싱
    result = await parser.parse(zip_path, meta)

    if not result['success']:
        logger.warning(f"Parse failed: {meta['name']} - {result['errors']}")
        return False

    data = result['data']
    target_year = result['target_year']

    logger.info(f"Parsed {len(data)} fields for {meta['name']} ({target_year})")

    if dry_run:
        logger.info(f"  [DRY-RUN] Would save to financial_details")
        return True

    # financial_details 테이블 컬럼 확인
    columns_rows = await conn.fetch("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'financial_details'
    """)
    valid_columns = {row['column_name'] for row in columns_rows}

    # 저장할 데이터 준비
    # unique constraint: (company_id, fiscal_year, fiscal_quarter, fs_type)
    import uuid
    insert_data = {
        'id': str(uuid.uuid4()),
        'company_id': str(meta['company_id']),
        'fiscal_year': target_year,
        'fiscal_quarter': None,  # 감사보고서는 연간 데이터 (None = annual)
        'fs_type': 'OFS',  # 개별 재무제표 (OFS = Own Financial Statements)
    }

    # 연결감사보고서인 경우 fs_type 변경
    if '연결' in meta.get('report_nm', ''):
        insert_data['fs_type'] = 'CFS'  # CFS = Consolidated Financial Statements

    for field, value in data.items():
        if field in valid_columns:
            insert_data[field] = value

    # UPSERT
    columns = list(insert_data.keys())
    placeholders = [f'${i+1}' for i in range(len(columns))]

    update_clause = ', '.join([
        f"{col} = EXCLUDED.{col}"
        for col in columns
        if col not in ('id', 'company_id', 'fiscal_year', 'fiscal_quarter', 'fs_type')
    ])

    query = f"""
        INSERT INTO financial_details ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        ON CONFLICT (company_id, fiscal_year, fiscal_quarter, fs_type)
        DO UPDATE SET {update_clause}
    """

    try:
        await conn.execute(query, *[insert_data[col] for col in columns])
        logger.info(f"  Saved financial_details for {meta['name']}")
        return True
    except Exception as e:
        logger.error(f"  DB save failed: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="신규 상장 기업 감사보고서 다운로드 및 파싱")
    parser.add_argument("--list", action="store_true", help="대상 기업 목록만 조회")
    parser.add_argument("--sample", type=int, default=0, help="샘플 개수 (0=전체)")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 테스트")
    parser.add_argument("--year", type=int, default=2024, help="대상 회계연도")
    parser.add_argument("--delay", type=float, default=0.5, help="API 호출 간격 (초)")
    args = parser.parse_args()

    if not DB_URL:
        logger.error("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        return

    logger.info("=" * 80)
    logger.info("신규 상장 기업 감사보고서 다운로드 및 파싱")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 대상 기업 조회
        companies = await get_target_companies(conn, args.year)
        logger.info(f"대상 기업: {len(companies)}개")

        if args.list:
            print("\n대상 기업 목록:")
            print("-" * 80)
            for c in companies:
                print(f"  {c['ticker']} {c['name']}: {c['report_nm']} ({c['rcept_no']})")
            return

        if args.sample > 0:
            companies = companies[:args.sample]
            logger.info(f"샘플 처리: {len(companies)}개")

        # 통계
        stats = {
            'total': len(companies),
            'downloaded': 0,
            'parsed': 0,
            'saved': 0,
            'errors': 0,
        }

        # 처리
        for i, company in enumerate(companies, 1):
            logger.info(f"\n[{i}/{len(companies)}] {company['name']} ({company['ticker']})")

            # 다운로드
            zip_path = await download_report(company['rcept_no'], AUDIT_REPORTS_DIR)

            if not zip_path:
                stats['errors'] += 1
                continue

            stats['downloaded'] += 1

            # 파싱 및 저장
            meta = {
                'company_id': company['id'],
                'corp_code': company['corp_code'],
                'rcept_no': company['rcept_no'],
                'report_nm': company['report_nm'],
                'name': company['name'],
            }

            success = await parse_and_save(conn, zip_path, meta, args.dry_run)

            if success:
                stats['parsed'] += 1
                if not args.dry_run:
                    stats['saved'] += 1
            else:
                stats['errors'] += 1

            # API rate limit
            await asyncio.sleep(args.delay)

        # 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("처리 결과")
        logger.info("=" * 80)
        logger.info(f"대상 기업: {stats['total']}개")
        logger.info(f"다운로드: {stats['downloaded']}개")
        logger.info(f"파싱 성공: {stats['parsed']}개")
        if not args.dry_run:
            logger.info(f"DB 저장: {stats['saved']}개")
        logger.info(f"오류: {stats['errors']}개")

        if args.dry_run:
            logger.info("\n[DRY-RUN] 실제 저장 없이 테스트만 수행됨")

        # DB 현황 확인
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_details WHERE fiscal_year = $1",
            args.year
        )
        logger.info(f"\nfinancial_details ({args.year}년): {count}건")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
