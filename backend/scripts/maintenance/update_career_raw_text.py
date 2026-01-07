#!/usr/bin/env python3
"""
임원 career_raw_text 업데이트 스크립트

목적: 기존 임원 데이터에 사업보고서 '주요경력' 원문 추가
- DART XML에서 SH5_SKL 필드 추출
- □ 불릿을 • 불릿으로 변환
- officers.career_raw_text 컬럼 업데이트

사용법:
    cd backend
    source .venv/bin/activate

    # 테스트 (샘플 10개 기업만)
    DATABASE_URL="..." python scripts/maintenance/update_career_raw_text.py --sample 10 --dry-run

    # 전체 실행
    DATABASE_URL="..." python scripts/maintenance/update_career_raw_text.py

    # 특정 기업만
    DATABASE_URL="..." python scripts/maintenance/update_career_raw_text.py --corp-code 00525679
"""

import asyncio
import asyncpg
import argparse
import json
import logging
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL 환경 변수가 설정되지 않았습니다")
    sys.exit(1)

# asyncpg용 URL 변환
if DATABASE_URL.startswith('postgresql+asyncpg://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

# DART 데이터 경로
DART_DATA_PATH = Path(__file__).parent.parent.parent / 'data' / 'dart'


def find_company_zip(corp_code: str) -> Optional[Path]:
    """회사의 최신 사업보고서 ZIP 파일 찾기"""
    # batch_001 ~ batch_missing 순서로 검색
    for batch_dir in sorted(DART_DATA_PATH.glob('batch_*'), reverse=True):
        corp_dir = batch_dir / corp_code
        if corp_dir.exists():
            # 최신 연도 우선
            for year_dir in sorted(corp_dir.glob('*'), reverse=True):
                if year_dir.is_dir():
                    # meta.json에서 사업보고서 찾기
                    for meta_file in year_dir.glob('*_meta.json'):
                        try:
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                if '사업보고서' in meta.get('report_nm', ''):
                                    zip_file = meta_file.with_suffix('.zip')
                                    zip_file = Path(str(zip_file).replace('_meta.json', '.zip'))
                                    if zip_file.exists():
                                        return zip_file
                        except:
                            continue
    return None


def extract_officers_from_xml(xml_content: str) -> List[Dict]:
    """XML에서 임원 정보 추출

    v2.4: TR 행 단위로 직접 파싱 (TABLE 경계 무시)
    - SH5_NM과 SH5_SKL이 같은 TR 행에 있으면 매칭
    """
    officers = []

    # TR 행 단위로 추출 (TABLE 구조에 의존하지 않음)
    rows = re.findall(r'<TR[^>]*>(.*?)</TR>', xml_content, re.DOTALL)

    for row_xml in rows:
        # 헤더 행 스킵
        if 'AUNITVALUE="H"' in row_xml or 'AUNIT="HD"' in row_xml:
            continue

        # SH5_NM이 없으면 스킵
        if 'ACODE="SH5_NM"' not in row_xml:
            continue

        officer = {}

        # 성명 (SH5_NM)
        nm_match = re.search(r'ACODE="SH5_NM"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
        if nm_match:
            name_raw = nm_match.group(1)
            # P 태그 내용 추출 또는 태그 제거
            p_match = re.search(r'<P[^>]*>([^<]*)</P>', name_raw)
            if p_match:
                name = p_match.group(1).strip()
            else:
                name = re.sub(r'<[^>]+>', '', name_raw).strip()
            if name and name != '-' and not name.startswith('(주)'):
                officer['name'] = name

        # 출생년월 (SH5_BIR)
        bir_match = re.search(r'AUNIT="SH5_BIR"[^>]*AUNITVALUE="(\d{6})"', row_xml)
        if bir_match:
            val = bir_match.group(1)
            if len(val) == 6:
                officer['birth_date'] = f"{val[:4]}.{val[4:]}"

        # 주요경력 (SH5_SKL)
        skl_match = re.search(r'ACODE="SH5_SKL"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
        if skl_match:
            raw_career = skl_match.group(1)
            p_contents = re.findall(r'<P[^>]*>([^<]*)</P>', raw_career)
            if p_contents:
                career_text = '\n'.join(p_contents)
            else:
                career_text = re.sub(r'<[^>]+>', '', raw_career)
            career_text = career_text.strip()

            if career_text:
                # □ 불릿을 • 불릿으로 변환
                raw_text = re.sub(r'□\s*', '\n• ', career_text)
                raw_text = re.sub(r'\n+', '\n', raw_text)
                officer['career_raw_text'] = raw_text.strip()

        if 'name' in officer and 'career_raw_text' in officer:
            officers.append(officer)

    return officers


async def update_career_raw_text(
    conn: asyncpg.Connection,
    corp_code: str,
    dry_run: bool = False
) -> Tuple[int, int]:
    """회사 임원들의 career_raw_text 업데이트"""
    updated_count = 0
    error_count = 0

    # ZIP 파일 찾기
    zip_file = find_company_zip(corp_code)
    if not zip_file:
        logger.debug(f"  {corp_code}: 사업보고서 ZIP 없음")
        return 0, 0

    # XML에서 임원 정보 추출
    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
            if not xml_files:
                return 0, 0

            # 가장 큰 XML 파일 (보통 사업보고서 본문)
            xml_file = max(xml_files, key=lambda x: zf.getinfo(x).file_size)
            xml_content = zf.read(xml_file).decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"  {corp_code}: ZIP 읽기 실패 - {e}")
        return 0, 1

    # 임원 정보 추출
    officers_from_xml = extract_officers_from_xml(xml_content)
    if not officers_from_xml:
        logger.debug(f"  {corp_code}: XML에서 임원 정보 없음")
        return 0, 0

    # DB에서 해당 회사 임원 조회
    company_query = "SELECT id FROM companies WHERE corp_code = $1"
    company = await conn.fetchrow(company_query, corp_code)
    if not company:
        return 0, 0

    company_id = company['id']

    # officer_positions에서 해당 회사 임원 목록 조회
    positions_query = """
        SELECT DISTINCT o.id, o.name, o.birth_date
        FROM officers o
        JOIN officer_positions op ON o.id = op.officer_id
        WHERE op.company_id = $1
    """
    officers_in_db = await conn.fetch(positions_query, company_id)

    # 이름 + 생년월로 매칭하여 업데이트
    for db_officer in officers_in_db:
        name = db_officer['name']
        birth_date = db_officer['birth_date']
        officer_id = db_officer['id']

        # XML에서 매칭되는 임원 찾기
        matched = None
        for xml_officer in officers_from_xml:
            if xml_officer['name'] == name:
                # 생년월 매칭 (있으면 확인, 없으면 이름만으로 매칭)
                if birth_date and xml_officer.get('birth_date'):
                    if birth_date == xml_officer['birth_date']:
                        matched = xml_officer
                        break
                elif not birth_date:
                    matched = xml_officer
                    break

        if matched and matched.get('career_raw_text'):
            if not dry_run:
                try:
                    await conn.execute(
                        "UPDATE officers SET career_raw_text = $1, updated_at = NOW() WHERE id = $2",
                        matched['career_raw_text'],
                        officer_id
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(f"  {name} 업데이트 실패: {e}")
                    error_count += 1
            else:
                logger.info(f"  [DRY-RUN] {name}: {matched['career_raw_text'][:50]}...")
                updated_count += 1

    return updated_count, error_count


async def main(args):
    """메인 함수"""
    start_time = datetime.now()
    logger.info(f"=== career_raw_text 업데이트 시작 ===")
    logger.info(f"  dry_run: {args.dry_run}")
    logger.info(f"  sample: {args.sample}")
    logger.info(f"  corp_code: {args.corp_code}")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 대상 기업 목록 조회
        if args.corp_code:
            corps = [{'corp_code': args.corp_code}]
        else:
            query = """
                SELECT DISTINCT c.corp_code
                FROM companies c
                JOIN officer_positions op ON c.id = op.company_id
                ORDER BY c.corp_code
            """
            if args.sample:
                query = query.replace('ORDER BY', f'ORDER BY RANDOM() LIMIT {args.sample} --')
            corps = await conn.fetch(query)

        total_updated = 0
        total_errors = 0
        processed = 0

        for row in corps:
            corp_code = row['corp_code']
            updated, errors = await update_career_raw_text(conn, corp_code, args.dry_run)
            total_updated += updated
            total_errors += errors
            processed += 1

            if processed % 100 == 0:
                logger.info(f"  진행: {processed}/{len(corps)}, 업데이트: {total_updated}, 오류: {total_errors}")

        logger.info(f"\n=== 완료 ===")
        logger.info(f"  처리 기업: {processed}")
        logger.info(f"  업데이트 임원: {total_updated}")
        logger.info(f"  오류: {total_errors}")
        logger.info(f"  소요 시간: {datetime.now() - start_time}")

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="career_raw_text 업데이트")
    parser.add_argument("--dry-run", action="store_true", help="실제 업데이트 없이 테스트")
    parser.add_argument("--sample", type=int, help="샘플 기업 수")
    parser.add_argument("--corp-code", help="특정 기업만 처리")
    args = parser.parse_args()

    asyncio.run(main(args))
