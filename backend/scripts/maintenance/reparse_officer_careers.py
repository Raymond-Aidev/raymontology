#!/usr/bin/env python3
"""
임원 경력 데이터 재파싱 스크립트

목표: 한글 패턴(전/현)을 사용하는 기업의 임원 경력 데이터 재파싱

문제 상황:
- 기존 파서는 한자 패턴(前/現)만 인식
- 한글 패턴(전/현)을 사용하는 기업의 career_history가 빈 배열

해결 방안:
- v2.2 파서(한글 패턴 지원)로 영향받는 기업 재파싱
- officers 테이블의 career_history 업데이트

사용법:
    cd backend
    source .venv/bin/activate

    # 테스트 (샘플 3개 기업만)
    DATABASE_URL="..." python scripts/maintenance/reparse_officer_careers.py --sample 3 --dry-run

    # 전체 실행
    DATABASE_URL="..." python scripts/maintenance/reparse_officer_careers.py
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
from typing import Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

# DART 데이터 경로
DART_DATA_PATH = Path(__file__).parent.parent.parent / 'data' / 'dart'


def parse_career_v23(career_text: str) -> List[Dict]:
    """v2.3 경력 파싱 (한글 패턴 + 연속 패턴 지원)"""
    careers = []
    if not career_text:
        return careers

    lines = re.split(r'[\n\r]+', career_text)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 줄 내부에서 前/現/전/현 패턴으로 분할 (lookahead 사용)
        segments = re.split(r'(?=[前現전현]\s*[\)）])', line)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # 前) 또는 전) 패턴 (이전 경력)
            former_match = re.match(r'^[前전]\s*[\)）]\s*(.+)', segment)
            if former_match:
                text = former_match.group(1).strip()
                # 다음 패턴이나 날짜 괄호 앞까지만 추출
                text = re.sub(r'\s*[\(（][\d\.\~\-\s]+[\)）]$', '', text)
                if text and len(text) >= 2:
                    careers.append({'text': text, 'status': 'former'})
                continue

            # 現) 또는 현) 패턴 (현재 경력)
            current_match = re.match(r'^[現현]\s*[\)）]\s*(.+)', segment)
            if current_match:
                text = current_match.group(1).strip()
                # 다음 패턴이나 날짜 괄호 앞까지만 추출
                text = re.sub(r'\s*[\(（][\d\.\~\-\s]+[\)）]$', '', text)
                if text and len(text) >= 2:
                    careers.append({'text': text, 'status': 'current'})

    return careers


def format_raw_text(career_text: str) -> str:
    """경력 원문 텍스트 포맷팅 (□ → • 변환)"""
    if not career_text:
        return ""
    raw_text = re.sub(r'□\s*', '\n• ', career_text)
    raw_text = re.sub(r'\n+', '\n', raw_text)
    return raw_text.strip()


def extract_careers_from_zip(zip_path: Path) -> Dict[str, Dict]:
    """ZIP에서 임원별 경력 데이터 추출

    Returns:
        Dict[name_birthdate, {career_history, career_raw_text}]
    """
    officers_careers = {}

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if not name.endswith('.xml'):
                    continue

                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')

                    # SH5_DRCT_STT 테이블 찾기
                    table_pattern = r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>(.*?)</TABLE-GROUP>'
                    table_match = re.search(table_pattern, content, re.DOTALL | re.IGNORECASE)

                    if not table_match:
                        continue

                    table_content = table_match.group(1)

                    # 각 행 파싱
                    row_pattern = r'<TR[^>]*ACOPY="Y"[^>]*>(.*?)</TR>'
                    rows = re.findall(row_pattern, table_content, re.DOTALL)

                    for row in rows:
                        # 성명 추출
                        name_match = re.search(r'ACODE="SH5_NM_T"[^>]*>(.*?)</TE>', row, re.DOTALL)
                        if not name_match:
                            continue

                        raw_name = name_match.group(1)
                        p_match = re.search(r'<P[^>]*>([^<]+)</P>', raw_name)
                        if p_match:
                            officer_name = p_match.group(1).strip()
                        else:
                            officer_name = re.sub(r'<[^>]+>', '', raw_name).strip()

                        if not officer_name or len(officer_name) < 2 or officer_name == '-':
                            continue

                        # 출생년월 추출
                        birth_match = re.search(r'AUNIT="SH5_BIH"[^>]*AUNITVALUE="(\d{6})"', row)
                        birth_date = birth_match.group(1) if birth_match else ''

                        # 경력 추출
                        skl_match = re.search(r'ACODE="SH5_SKL"[^>]*>(.*?)</TE>', row, re.DOTALL)
                        if skl_match:
                            raw_career = skl_match.group(1)
                            p_contents = re.findall(r'<P[^>]*>([^<]*)</P>', raw_career)
                            if p_contents:
                                career_text = '\n'.join(p_contents)
                            else:
                                career_text = re.sub(r'<[^>]+>', '', raw_career)

                            career_text = career_text.strip()
                            career_history = parse_career_v23(career_text)
                            career_raw_text = format_raw_text(career_text)

                            # 원문이 있으면 저장 (파싱 결과 없어도)
                            if career_raw_text:
                                key = f"{officer_name}_{birth_date}"
                                officers_careers[key] = {
                                    'career_history': career_history,
                                    'career_raw_text': career_raw_text
                                }

                except Exception as e:
                    logger.debug(f"Error parsing {name}: {e}")
                    continue

    except zipfile.BadZipFile:
        logger.warning(f"Bad ZIP file: {zip_path}")
    except Exception as e:
        logger.error(f"Error reading {zip_path}: {e}")

    return officers_careers


async def get_affected_companies(conn) -> List[Dict]:
    """career_raw_text가 NULL인 임원이 있는 기업 조회"""
    query = '''
        SELECT
            c.id,
            c.corp_code,
            c.name,
            COUNT(DISTINCT o.id) as empty_career_count
        FROM companies c
        JOIN officer_positions op ON c.id = op.company_id
        JOIN officers o ON op.officer_id = o.id
        WHERE o.career_raw_text IS NULL
          AND op.is_current = true
          AND c.corp_code IS NOT NULL
        GROUP BY c.id, c.corp_code, c.name
        HAVING COUNT(DISTINCT o.id) >= 3
        ORDER BY COUNT(DISTINCT o.id) DESC
    '''
    rows = await conn.fetch(query)
    return [dict(r) for r in rows]


async def find_dart_zip(corp_code: str) -> Optional[Path]:
    """corp_code에 해당하는 최신 사업보고서 ZIP 찾기"""

    # batch_* 및 batch_missing 디렉토리 검색
    for batch_dir in DART_DATA_PATH.glob('batch_*'):
        corp_dir = batch_dir / corp_code
        if corp_dir.exists():
            # 가장 최근 연도의 가장 큰 파일 (사업보고서)
            for year in sorted(corp_dir.iterdir(), reverse=True):
                if year.is_dir():
                    zips = list(year.glob('*.zip'))
                    if zips:
                        # 파일 크기가 가장 큰 것 선택 (사업보고서)
                        largest = max(zips, key=lambda p: p.stat().st_size)
                        return largest

    return None


async def update_officer_career(
    conn,
    officer_name: str,
    birth_date: str,
    career_data: Dict,  # {career_history, career_raw_text}
    dry_run: bool
) -> bool:
    """임원 경력 업데이트 (career_history + career_raw_text)"""
    career_history = career_data.get('career_history', [])
    career_raw_text = career_data.get('career_raw_text', '')

    if birth_date:
        query = '''
            UPDATE officers
            SET career_history = $1, career_raw_text = $2, updated_at = NOW()
            WHERE name = $3 AND birth_date = $4
            RETURNING id
        '''
        args = [json.dumps(career_history, ensure_ascii=False), career_raw_text, officer_name, birth_date]
    else:
        query = '''
            UPDATE officers
            SET career_history = $1, career_raw_text = $2, updated_at = NOW()
            WHERE name = $3 AND birth_date IS NULL
            RETURNING id
        '''
        args = [json.dumps(career_history, ensure_ascii=False), career_raw_text, officer_name]

    if dry_run:
        return True

    try:
        result = await conn.fetchrow(query, *args)
        return result is not None
    except Exception as e:
        logger.error(f"Update failed for {officer_name}: {e}")
        return False


async def reparse_company(
    conn,
    company: Dict,
    dry_run: bool
) -> Dict:
    """단일 기업 재파싱"""
    result = {
        'company_name': company['name'],
        'corp_code': company['corp_code'],
        'zip_found': False,
        'officers_parsed': 0,
        'officers_updated': 0,
    }

    zip_path = await find_dart_zip(company['corp_code'])
    if not zip_path:
        logger.warning(f"ZIP not found for {company['name']} ({company['corp_code']})")
        return result

    result['zip_found'] = True
    result['zip_path'] = str(zip_path)

    # ZIP에서 경력 추출
    officers_careers = extract_careers_from_zip(zip_path)
    result['officers_parsed'] = len(officers_careers)

    if not officers_careers:
        logger.info(f"No careers found in {company['name']}")
        return result

    # DB 업데이트
    updated = 0
    for key, career_data in officers_careers.items():
        parts = key.rsplit('_', 1)
        officer_name = parts[0]
        birth_date = parts[1] if len(parts) > 1 and parts[1] else None

        if await update_officer_career(conn, officer_name, birth_date, career_data, dry_run):
            updated += 1

    result['officers_updated'] = updated
    return result


async def main(sample: int = 0, dry_run: bool = False, corp_code: str = None):
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("임원 경력 데이터 재파싱 시작")
    logger.info(f"모드: {'DRY RUN (변경 없음)' if dry_run else '실제 실행'}")
    if corp_code:
        logger.info(f"대상: corp_code={corp_code}")
    logger.info("=" * 60)

    # DB 연결
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 특정 기업만 처리
        if corp_code:
            query = '''
                SELECT c.id, c.corp_code, c.name, 0 as empty_career_count
                FROM companies c
                WHERE c.corp_code = $1
            '''
            rows = await conn.fetch(query, corp_code)
            companies = [dict(r) for r in rows]
            if not companies:
                logger.error(f"기업을 찾을 수 없습니다: {corp_code}")
                return
        else:
            # 영향받는 기업 조회
            companies = await get_affected_companies(conn)
            logger.info(f"영향받는 기업: {len(companies)}개")

        if sample > 0 and not corp_code:
            companies = companies[:sample]
            logger.info(f"샘플 모드: {sample}개 기업만 처리")

        # 통계
        stats = {
            'total_companies': len(companies),
            'zip_found': 0,
            'total_parsed': 0,
            'total_updated': 0,
        }

        # 재파싱
        for i, company in enumerate(companies, 1):
            logger.info(f"[{i}/{len(companies)}] {company['name']} ({company['corp_code']}) - 영향 임원: {company['empty_career_count']}명")

            result = await reparse_company(conn, company, dry_run)

            if result['zip_found']:
                stats['zip_found'] += 1
            stats['total_parsed'] += result['officers_parsed']
            stats['total_updated'] += result['officers_updated']

            if result['officers_updated'] > 0:
                logger.info(f"  → 파싱: {result['officers_parsed']}명, 업데이트: {result['officers_updated']}명")

        # 결과 출력
        logger.info("")
        logger.info("=" * 60)
        logger.info("재파싱 완료")
        logger.info("=" * 60)
        logger.info(f"처리 기업: {stats['total_companies']}개")
        logger.info(f"ZIP 발견: {stats['zip_found']}개")
        logger.info(f"파싱된 임원: {stats['total_parsed']}명")
        logger.info(f"업데이트된 임원: {stats['total_updated']}명")

        if dry_run:
            logger.info("")
            logger.info("⚠️  DRY RUN 모드: 실제 DB 변경 없음")
            logger.info("실제 실행: --dry-run 플래그 제거")

    finally:
        await conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='임원 경력 데이터 재파싱')
    parser.add_argument('--sample', type=int, default=0, help='샘플 기업 수 (0=전체)')
    parser.add_argument('--dry-run', action='store_true', help='테스트 모드 (DB 변경 없음)')
    parser.add_argument('--corp-code', type=str, help='특정 기업만 처리 (corp_code)')

    args = parser.parse_args()
    asyncio.run(main(sample=args.sample, dry_run=args.dry_run, corp_code=args.corp_code))
