#!/usr/bin/env python3
"""
426개 대상 기업 임원 정보 파싱 (v2 - 로컬 파싱 후 배치 적재)

1단계: 모든 ZIP 파일을 로컬에서 파싱하여 JSON으로 저장
2단계: JSON 데이터를 배치로 DB에 적재
"""
import asyncio
import asyncpg
import logging
import os
import sys
import json
import re
import zipfile
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(line_buffering=True)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
PARSED_DATA_FILE = Path(__file__).parent / 'parsed_officers_426.json'


def extract_xml_from_zip(zip_path: Path) -> Optional[str]:
    """ZIP에서 모든 XML 추출하고 합침"""
    try:
        all_xml = []
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.xml'):
                    content = zf.read(name)
                    for enc in ['utf-8', 'euc-kr', 'cp949']:
                        try:
                            decoded = content.decode(enc)
                            all_xml.append(decoded)
                            break
                        except:
                            continue
        return '\n'.join(all_xml) if all_xml else None
    except:
        return None


def parse_officer_row(row_xml: str, base_date: str) -> Optional[Dict]:
    """임원 행 파싱"""
    try:
        officer = {'base_date': base_date}

        # 성명 (SH5_NM_T)
        name_match = re.search(r'ACODE="SH5_NM_T"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
        if name_match:
            raw_name = name_match.group(1)
            p_match = re.search(r'<P[^>]*>([^<]+)</P>', raw_name)
            if p_match:
                name = p_match.group(1).strip()
            else:
                name = re.sub(r'<[^>]+>', '', raw_name).strip()
            if name and len(name) >= 2 and name != '-':
                officer['name'] = name

        if not officer.get('name'):
            return None

        # 출생년월 (SH5_BIH)
        birth_match = re.search(r'AUNIT="SH5_BIH"[^>]*AUNITVALUE="(\d{6})"', row_xml)
        if birth_match:
            officer['birth_date'] = birth_match.group(1)

        # 성별
        sex_match = re.search(r'AUNIT="SH5_SEX"[^>]*AUNITVALUE="(\d)"', row_xml)
        if sex_match:
            officer['gender'] = '남' if sex_match.group(1) == '1' else '여'

        # 직위
        pos_match = re.search(r'ACODE="SH5_LEV"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
        if pos_match:
            raw_pos = pos_match.group(1)
            p_match = re.search(r'<P[^>]*>([^<]+)</P>', raw_pos)
            if p_match:
                officer['position'] = p_match.group(1).strip()
            else:
                officer['position'] = re.sub(r'<[^>]+>', '', raw_pos).strip()

        # 주요경력
        career_match = re.search(r'ACODE="SH5_SKL"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
        if career_match:
            raw_career = career_match.group(1)
            career_text = re.sub(r'<[^>]+>', ' ', raw_career).strip()
            career_text = re.sub(r'\s+', ' ', career_text)
            if career_text and career_text != '-':
                officer['career'] = career_text

        # 임기만료일
        term_match = re.search(r'AUNIT="SH5_FIH"[^>]*AUNITVALUE="(\d{8})"', row_xml)
        if term_match:
            officer['term_end_date'] = term_match.group(1)

        return officer
    except:
        return None


def parse_officer_table(xml_content: str) -> List[Dict]:
    """임원현황 테이블 파싱"""
    officers = []

    table_pattern = r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>(.*?)</TABLE-GROUP>'
    table_match = re.search(table_pattern, xml_content, re.DOTALL | re.IGNORECASE)

    if not table_match:
        return officers

    table_content = table_match.group(1)

    base_date_match = re.search(r'AUNIT="BASE_DT"[^>]*AUNITVALUE="(\d{8})"', table_content)
    base_date = base_date_match.group(1) if base_date_match else None

    row_pattern = r'<TR[^>]*ACOPY="Y"[^>]*>(.*?)</TR>'
    rows = re.findall(row_pattern, table_content, re.DOTALL)

    for row in rows:
        officer = parse_officer_row(row, base_date)
        if officer:
            officers.append(officer)

    return officers


def parse_all_files(target_corps: list, corp_map: dict, years: set) -> dict:
    """모든 파일을 로컬에서 파싱"""
    all_data = {}
    total_files = 0
    total_officers = 0

    for i, (corp_code, corp_name) in enumerate(target_corps):
        corp_dirs = corp_map.get(corp_code, [])
        if not corp_dirs:
            continue

        corp_officers = []

        for corp_dir_str in corp_dirs:
            corp_dir = Path(corp_dir_str)
            if not corp_dir.exists():
                continue

            for year_dir in corp_dir.iterdir():
                if not year_dir.is_dir() or year_dir.name not in years:
                    continue

                for zip_file in year_dir.glob("*.zip"):
                    xml_content = extract_xml_from_zip(zip_file)
                    if not xml_content:
                        continue

                    officers = parse_officer_table(xml_content)
                    if officers:
                        rcept_no = zip_file.stem
                        for officer in officers:
                            officer['rcept_no'] = rcept_no
                            officer['year'] = year_dir.name
                        corp_officers.extend(officers)
                        total_files += 1

        if corp_officers:
            all_data[corp_code] = {
                'name': corp_name,
                'officers': corp_officers
            }
            total_officers += len(corp_officers)

        if (i + 1) % 50 == 0:
            logger.info(f"파싱 진행: {i+1}/{len(target_corps)} 기업, {total_files} 파일, {total_officers} 임원")

    logger.info(f"파싱 완료: {len(all_data)} 기업, {total_files} 파일, {total_officers} 임원")
    return all_data


async def load_to_db(parsed_data: dict):
    """파싱된 데이터를 DB에 적재"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 회사 정보 로드
        rows = await conn.fetch("SELECT id, corp_code, market FROM companies WHERE corp_code IS NOT NULL")
        company_cache = {r['corp_code']: str(r['id']) for r in rows}
        company_market = {r['corp_code']: r['market'] for r in rows}
        logger.info(f"회사 캐시 로드: {len(company_cache)}개")

        # 기존 임원 로드
        officer_rows = await conn.fetch("SELECT id, name, birth_date FROM officers")
        officer_cache = {}
        for r in officer_rows:
            key = f"{r['name']}_{r['birth_date'] or ''}"
            officer_cache[key] = str(r['id'])
        logger.info(f"임원 캐시 로드: {len(officer_cache)}개")

        stats = {
            'officers_inserted': 0,
            'positions_inserted': 0,
            'companies_processed': 0
        }

        for corp_code, corp_data in parsed_data.items():
            company_id = company_cache.get(corp_code)
            if not company_id:
                continue

            is_listed = company_market.get(corp_code) in ('KOSPI', 'KOSDAQ', 'KONEX')

            for officer_data in corp_data['officers']:
                name = officer_data.get('name')
                birth_date = officer_data.get('birth_date')
                key = f"{name}_{birth_date or ''}"

                # 임원 조회/생성
                if key in officer_cache:
                    officer_id = officer_cache[key]
                else:
                    officer_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO officers (id, name, birth_date, gender, created_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (name, birth_date) DO NOTHING
                    """, officer_id, name, birth_date, officer_data.get('gender'))

                    # 실제 ID 확인
                    actual_id = await conn.fetchval(
                        "SELECT id FROM officers WHERE name = $1 AND birth_date IS NOT DISTINCT FROM $2",
                        name, birth_date
                    )
                    if actual_id:
                        officer_id = str(actual_id)
                        officer_cache[key] = officer_id
                        stats['officers_inserted'] += 1

                # 포지션 삽입
                position = officer_data.get('position', '임원')
                term_start = None
                term_end = None

                if is_listed:
                    # 임기만료일에서 3년 전을 시작일로 추정
                    if officer_data.get('term_end_date'):
                        try:
                            term_end = datetime.strptime(officer_data['term_end_date'], '%Y%m%d').date()
                            term_start = date(term_end.year - 3, term_end.month, term_end.day)
                        except:
                            pass

                report_date = None
                if officer_data.get('base_date'):
                    try:
                        report_date = datetime.strptime(officer_data['base_date'], '%Y%m%d').date()
                    except:
                        pass

                try:
                    await conn.execute("""
                        INSERT INTO officer_positions
                        (id, officer_id, company_id, position, term_start_date, term_end_date,
                         is_current, source_disclosure_id, report_date, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                        ON CONFLICT (officer_id, company_id, term_start_date)
                        DO UPDATE SET
                            position = EXCLUDED.position,
                            term_end_date = EXCLUDED.term_end_date,
                            is_current = EXCLUDED.is_current
                    """, str(uuid.uuid4()), officer_id, company_id, position,
                        term_start, term_end, True, officer_data.get('rcept_no'), report_date)
                    stats['positions_inserted'] += 1
                except Exception as e:
                    pass  # 중복 무시

            stats['companies_processed'] += 1

            if stats['companies_processed'] % 50 == 0:
                logger.info(
                    f"DB 적재 진행: {stats['companies_processed']}/{len(parsed_data)} 기업 - "
                    f"임원: {stats['officers_inserted']}, 포지션: {stats['positions_inserted']}"
                )

        logger.info("\n" + "=" * 80)
        logger.info("DB 적재 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {stats['companies_processed']}개")
        logger.info(f"생성된 임원: {stats['officers_inserted']}명")
        logger.info(f"생성된 포지션: {stats['positions_inserted']}개")

        officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
        positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

    finally:
        await conn.close()


async def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="426개 대상 기업 임원 파싱 v2")
    arg_parser.add_argument("--corp-list", required=True, help="대상 기업 목록 파일")
    arg_parser.add_argument("--corp-map", default="scripts/corp_dir_map.json", help="기업 폴더 맵")
    arg_parser.add_argument("--years", default="2022,2023,2024", help="파싱할 연도")
    arg_parser.add_argument("--parse-only", action='store_true', help="파싱만 (DB 적재 안함)")
    arg_parser.add_argument("--load-only", action='store_true', help="기존 파싱 결과로 DB 적재만")

    args = arg_parser.parse_args()
    years = set(args.years.split(','))

    if args.load_only:
        if not PARSED_DATA_FILE.exists():
            logger.error(f"파싱 파일 없음: {PARSED_DATA_FILE}")
            return
        with open(PARSED_DATA_FILE, 'r') as f:
            parsed_data = json.load(f)
        logger.info(f"파싱 데이터 로드: {len(parsed_data)} 기업")
        await load_to_db(parsed_data)
        return

    # 폴더 맵 로드
    with open(args.corp_map, 'r') as f:
        corp_map = json.load(f)
    logger.info(f"폴더 맵 로드: {len(corp_map)}개 기업")

    # 대상 기업 로드
    target_corps = []
    with open(args.corp_list, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if parts:
                target_corps.append((parts[0], parts[1] if len(parts) > 1 else ''))

    logger.info(f"대상 기업: {len(target_corps)}개")
    logger.info(f"대상 연도: {years}")

    # 1단계: 로컬 파싱
    logger.info("\n=== 1단계: 로컬 파싱 ===")
    parsed_data = parse_all_files(target_corps, corp_map, years)

    # JSON 저장
    with open(PARSED_DATA_FILE, 'w') as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=2)
    logger.info(f"파싱 결과 저장: {PARSED_DATA_FILE}")

    if args.parse_only:
        return

    # 2단계: DB 적재
    logger.info("\n=== 2단계: DB 적재 ===")
    await load_to_db(parsed_data)


if __name__ == "__main__":
    asyncio.run(main())
