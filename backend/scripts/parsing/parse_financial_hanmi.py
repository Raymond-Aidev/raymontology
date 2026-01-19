#!/usr/bin/env python3
"""
한미반도체 재무제표 파싱 테스트
"""
import asyncio
import asyncpg
import json
import re
import zipfile
import logging
import os
from pathlib import Path
from datetime import date
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
HANMI_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart/batch_missing/00161383')


def parse_number(text: str) -> int:
    """숫자 문자열 파싱"""
    if not text:
        return None
    text = text.strip().replace(',', '').replace(' ', '')
    is_negative = text.startswith('(') and text.endswith(')')
    if is_negative:
        text = text[1:-1]
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

    patterns = {
        'total_assets': r'자산\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_liabilities': r'부채\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_equity': r'자본\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'revenue': r'(?:매출액|수익\(매출액\))</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'operating_profit': r'영업이익(?:\(손실\))?</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'net_income': r'(?:당기순이익(?:\(손실\))?|당기순손익)</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, xml_content, re.IGNORECASE | re.DOTALL)
        if match:
            value = parse_number(match.group(1))
            if value is not None:
                data[field] = value

    return data


async def main():
    """한미반도체 재무제표 파싱"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 한미반도체 company_id 확인
        row = await conn.fetchrow(
            "SELECT id, name FROM companies WHERE corp_code = '00161383'"
        )
        if not row:
            logger.error("한미반도체 not found")
            return

        company_id = row['id']
        logger.info(f"한미반도체 company_id: {company_id}")

        # 현재 재무제표 확인
        current = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_statements WHERE company_id = $1",
            company_id
        )
        logger.info(f"현재 재무제표: {current}건")

        parsed_count = 0
        inserted_count = 0

        # 연도별 폴더 순회
        for year_dir in sorted(HANMI_DIR.iterdir()):
            if not year_dir.is_dir():
                continue

            year = year_dir.name
            logger.info(f"\n=== {year}년 ===")

            # meta 파일 찾기
            for meta_file in year_dir.glob("*_meta.json"):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    report_nm = meta.get('report_nm', '')
                    rcept_no = meta.get('rcept_no')

                    logger.info(f"  {rcept_no}: {report_nm}")

                    # 사업보고서만 처리
                    if '사업보고서' not in report_nm:
                        logger.info("    -> 사업보고서 아님, 스킵")
                        continue

                    # 연도 추출
                    year_match = re.search(r'\((\d{4})\.(\d{2})\)', report_nm)
                    if not year_match:
                        continue

                    fiscal_year = int(year_match.group(1))
                    fiscal_month = int(year_match.group(2))

                    if fiscal_month != 12:
                        logger.info("    -> 12월 결산 아님, 스킵")
                        continue

                    # ZIP 파일 열기
                    zip_path = meta_file.with_suffix('').with_name(rcept_no + '.zip')
                    if not zip_path.exists():
                        logger.warning(f"    -> ZIP 없음: {zip_path}")
                        continue

                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                        if not xml_files:
                            continue

                        main_xml = max(xml_files, key=lambda x: zf.getinfo(x).file_size)

                        try:
                            content = zf.read(main_xml).decode('utf-8')
                        except:
                            content = zf.read(main_xml).decode('euc-kr', errors='ignore')

                        fin_data = extract_financial_data(content)

                        if not fin_data:
                            logger.warning("    -> 재무 데이터 추출 실패")
                            continue

                        parsed_count += 1
                        logger.info(f"    -> 파싱 성공: {fin_data}")

                        # DB 삽입
                        stmt_date = date(fiscal_year, 12, 31)

                        try:
                            await conn.execute("""
                                INSERT INTO financial_statements
                                (id, company_id, fiscal_year, quarter, statement_date, report_type,
                                 total_assets, total_liabilities, total_equity, revenue,
                                 operating_profit, net_income, source_rcept_no, created_at)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
                                ON CONFLICT (company_id, fiscal_year, quarter)
                                DO UPDATE SET
                                    total_assets = EXCLUDED.total_assets,
                                    total_liabilities = EXCLUDED.total_liabilities,
                                    total_equity = EXCLUDED.total_equity,
                                    revenue = EXCLUDED.revenue,
                                    operating_profit = EXCLUDED.operating_profit,
                                    net_income = EXCLUDED.net_income
                            """,
                                str(uuid.uuid4()), company_id, fiscal_year, None, stmt_date,
                                '사업보고서',
                                fin_data.get('total_assets'),
                                fin_data.get('total_liabilities'),
                                fin_data.get('total_equity'),
                                fin_data.get('revenue'),
                                fin_data.get('operating_profit'),
                                fin_data.get('net_income'),
                                rcept_no
                            )
                            inserted_count += 1
                            logger.info(f"    -> DB 저장 완료 (fiscal_year={fiscal_year})")
                        except Exception as e:
                            logger.error(f"    -> DB 저장 실패: {e}")

                except Exception as e:
                    logger.error(f"  오류 {meta_file}: {e}")

        # 최종 결과
        logger.info("\n" + "=" * 60)
        logger.info(f"파싱 완료: {parsed_count}건, 저장: {inserted_count}건")

        after = await conn.fetchval(
            "SELECT COUNT(*) FROM financial_statements WHERE company_id = $1",
            company_id
        )
        logger.info(f"한미반도체 재무제표: {current} -> {after}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
