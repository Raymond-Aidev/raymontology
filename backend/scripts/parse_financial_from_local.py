#!/usr/bin/env python3
"""
로컬 DART 보고서에서 재무제표 파싱

- 2022-2024: 사업보고서 (연간)
- 2025: 반기보고서 (Q2)
"""
import asyncio
import asyncpg
import json
import logging
import re
import zipfile
from pathlib import Path
from datetime import date
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'
DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')


def parse_number(text: str) -> int:
    """숫자 문자열 파싱 (괄호는 음수)"""
    if not text:
        return None
    text = text.strip()
    text = text.replace(',', '').replace(' ', '')

    # 괄호로 감싸진 경우 음수
    is_negative = text.startswith('(') and text.endswith(')')
    if is_negative:
        text = text[1:-1]

    # 숫자만 추출
    text = re.sub(r'[^\d.-]', '', text)

    if not text or text == '-':
        return None

    try:
        value = int(float(text))
        return -value if is_negative else value
    except:
        return None


def extract_financial_data(xml_content: str) -> dict:
    """XML에서 재무제표 데이터 추출"""
    data = {}

    # 패턴: "항목명</P>" 다음에 나오는 숫자
    patterns = {
        'total_assets': r'자산\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_liabilities': r'부채\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_equity': r'자본\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'revenue': r'(?:매출액|수익\(매출액\))</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'operating_profit': r'영업이익(?:\(손실\))?</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'net_income': r'(?:당기순이익(?:\(손실\))?|당기순손익)</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
    }

    # 대체 패턴: TD 태그 사용
    alt_patterns = {
        'total_assets': r'자산\s*총계</TD>\s*<TD[^>]*>([^<]+)</TD>',
        'total_liabilities': r'부채\s*총계</TD>\s*<TD[^>]*>([^<]+)</TD>',
        'total_equity': r'자본\s*총계</TD>\s*<TD[^>]*>([^<]+)</TD>',
        'revenue': r'매출액</TD>\s*<TD[^>]*>([^<]+)</TD>',
        'operating_profit': r'영업이익</TD>\s*<TD[^>]*>([^<]+)</TD>',
        'net_income': r'당기순이익</TD>\s*<TD[^>]*>([^<]+)</TD>',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, xml_content, re.IGNORECASE | re.DOTALL)
        if match:
            value = parse_number(match.group(1))
            if value is not None:
                data[field] = value

    # 대체 패턴으로 누락된 필드 채우기
    for field, pattern in alt_patterns.items():
        if field not in data:
            match = re.search(pattern, xml_content, re.IGNORECASE | re.DOTALL)
            if match:
                value = parse_number(match.group(1))
                if value is not None:
                    data[field] = value

    return data


async def parse_financial_statements():
    """로컬 보고서에서 재무제표 파싱"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 시작 전 카운트
        before_count = await conn.fetchval("SELECT COUNT(*) FROM financial_statements")
        logger.info(f"작업 전 financial_statements: {before_count}건")

        # company_id 매핑 (corp_code -> id)
        companies = await conn.fetch("SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL")
        corp_to_id = {c['corp_code']: c['id'] for c in companies}
        logger.info(f"회사 매핑: {len(corp_to_id)}개")

        stats = {
            'scanned': 0,
            'parsed': 0,
            'saved': 0,
            'no_data': 0,
            'errors': 0
        }

        # 배치 데이터
        batch_data = []

        # 배치 폴더 순회
        batch_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith('batch_')])

        for batch_dir in batch_dirs:
            meta_files = list(batch_dir.rglob('*_meta.json'))

            for meta_file in meta_files:
                stats['scanned'] += 1

                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    report_nm = meta.get('report_nm', '')
                    corp_code = meta.get('corp_code')
                    rcept_no = meta.get('rcept_no')

                    # 회사 ID 확인
                    if corp_code not in corp_to_id:
                        continue

                    company_id = corp_to_id[corp_code]

                    # 보고서 타입 필터링
                    # 2022-2024: 사업보고서, 2025: 반기보고서
                    year_match = re.search(r'\((\d{4})\.(\d{2})\)', report_nm)
                    if not year_match:
                        continue

                    fiscal_year = int(year_match.group(1))
                    fiscal_month = int(year_match.group(2))

                    # 필터링 조건
                    is_annual = '사업보고서' in report_nm and fiscal_month == 12
                    is_semiannual = '반기보고서' in report_nm and fiscal_month == 6

                    if fiscal_year <= 2024 and not is_annual:
                        continue
                    if fiscal_year == 2025 and not is_semiannual:
                        continue

                    # ZIP 파일 열기
                    zip_path = meta_file.with_suffix('.zip').with_name(rcept_no + '.zip')
                    if not zip_path.exists():
                        continue

                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        # 메인 XML 파일 찾기 (가장 큰 것)
                        xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                        if not xml_files:
                            continue

                        main_xml = max(xml_files, key=lambda x: zf.getinfo(x).file_size)

                        try:
                            content = zf.read(main_xml).decode('utf-8')
                        except:
                            content = zf.read(main_xml).decode('euc-kr', errors='ignore')

                        # 재무제표 파싱
                        fin_data = extract_financial_data(content)

                        if not fin_data:
                            stats['no_data'] += 1
                            continue

                        stats['parsed'] += 1

                        # 데이터 준비
                        quarter = None if is_annual else 'Q2'
                        report_type = '사업보고서' if is_annual else '반기보고서'
                        statement_date = date(fiscal_year, 12, 31) if is_annual else date(fiscal_year, 6, 30)

                        batch_data.append((
                            company_id,
                            fiscal_year,
                            quarter,
                            statement_date,
                            report_type,
                            fin_data.get('total_assets'),
                            fin_data.get('total_liabilities'),
                            fin_data.get('total_equity'),
                            fin_data.get('revenue'),
                            fin_data.get('operating_profit'),
                            fin_data.get('net_income'),
                            rcept_no
                        ))

                        # 배치 삽입
                        if len(batch_data) >= 100:
                            saved = await insert_batch(conn, batch_data)
                            stats['saved'] += saved
                            logger.info(f"  {stats['saved']}건 저장 (스캔: {stats['scanned']:,}, 파싱: {stats['parsed']})")
                            batch_data = []

                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 5:
                        logger.error(f"오류 {meta_file}: {e}")

            logger.info(f"배치 {batch_dir.name} 완료 - 스캔: {stats['scanned']:,}")

        # 남은 데이터 삽입
        if batch_data:
            saved = await insert_batch(conn, batch_data)
            stats['saved'] += saved

        # 최종 결과
        after_count = await conn.fetchval("SELECT COUNT(*) FROM financial_statements")

        logger.info("\n" + "=" * 60)
        logger.info("재무제표 파싱 완료")
        logger.info("=" * 60)
        logger.info(f"스캔: {stats['scanned']:,}건")
        logger.info(f"파싱 성공: {stats['parsed']:,}건")
        logger.info(f"저장: {stats['saved']:,}건")
        logger.info(f"데이터 없음: {stats['no_data']:,}건")
        logger.info(f"오류: {stats['errors']:,}건")
        logger.info("-" * 60)
        logger.info(f"financial_statements: {before_count}건 → {after_count}건 (+{after_count - before_count}건)")
        logger.info("=" * 60)

    finally:
        await conn.close()


async def insert_batch(conn, batch_data):
    """배치 삽입"""
    saved = 0
    for row in batch_data:
        try:
            await conn.execute("""
                INSERT INTO financial_statements (
                    id, company_id, fiscal_year, quarter, statement_date, report_type,
                    total_assets, total_liabilities, total_equity,
                    revenue, operating_profit, net_income,
                    source_rcept_no, created_at, updated_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, quarter) DO UPDATE SET
                    total_assets = COALESCE(EXCLUDED.total_assets, financial_statements.total_assets),
                    total_liabilities = COALESCE(EXCLUDED.total_liabilities, financial_statements.total_liabilities),
                    total_equity = COALESCE(EXCLUDED.total_equity, financial_statements.total_equity),
                    revenue = COALESCE(EXCLUDED.revenue, financial_statements.revenue),
                    operating_profit = COALESCE(EXCLUDED.operating_profit, financial_statements.operating_profit),
                    net_income = COALESCE(EXCLUDED.net_income, financial_statements.net_income),
                    source_rcept_no = EXCLUDED.source_rcept_no,
                    updated_at = NOW()
            """,
                uuid.uuid4(),  # id
                row[0],        # company_id
                row[1],        # fiscal_year
                row[2],        # quarter
                row[3],        # statement_date
                row[4],        # report_type
                row[5],        # total_assets
                row[6],        # total_liabilities
                row[7],        # total_equity
                row[8],        # revenue
                row[9],        # operating_profit
                row[10],       # net_income
                row[11]        # source_rcept_no
            )
            saved += 1
        except Exception as e:
            if 'duplicate' not in str(e).lower():
                logger.error(f"삽입 오류: {e}")
    return saved


if __name__ == "__main__":
    asyncio.run(parse_financial_statements())
