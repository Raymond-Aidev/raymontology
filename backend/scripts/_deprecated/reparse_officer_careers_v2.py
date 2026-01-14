#!/usr/bin/env python3
"""
임원 경력 재파싱 스크립트 (v2.4)

career_raw_text가 있지만 career_history가 비어있는 레코드를
개선된 파서로 재파싱하여 업데이트.

사용법:
    # 테스트 (dry-run)
    DATABASE_URL="..." python scripts/reparse_officer_careers_v2.py --sample 20 --dry-run

    # 전체 실행
    DATABASE_URL="..." python scripts/reparse_officer_careers_v2.py
"""

import asyncio
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_career_v24(career_text: str) -> List[Dict]:
    """경력 파싱 (v2.4 - 다양한 패턴 지원)

    지원 패턴:
    1. 괄호 패턴: 前), 現), 전), 현)
    2. 공백 패턴: 前 OO, 現 OO, 전 OO, 현 OO
    3. 연도 범위: YYYY ~ 현재, YYYY ~ YYYY
    4. 불릿 패턴: ▷, -, ·, •
    5. 괄호 연도: OO회사(YYYY년~YYYY년)
    6. 슬래시 기간: 'YY.MM~'YY.MM
    """
    careers = []
    if not career_text:
        return careers

    # 줄바꿈 또는 불릿 구분으로 분할
    lines = re.split(r'[\n\r]+|[•·▷]', career_text)
    # 추가로 - 로 시작하는 항목 분리 (앞에 공백 있어야 함)
    expanded_lines = []
    for line in lines:
        # "- A- B" 형태를 분리
        parts = re.split(r'(?:^|\s)-\s*', line)
        expanded_lines.extend(parts)
    lines = expanded_lines

    for line in lines:
        line = line.strip()
        if not line or line == '-' or len(line) < 3:
            continue

        # 1. 괄호 패턴: 前), 現), 전), 현)
        bracket_match = re.match(r'^[前전]\s*[\)）]\s*(.+)', line)
        if bracket_match:
            text = clean_career_text(bracket_match.group(1))
            if text:
                careers.append({'text': text, 'status': 'former'})
            continue

        bracket_match = re.match(r'^[現현]\s*[\)）]\s*(.+)', line)
        if bracket_match:
            text = clean_career_text(bracket_match.group(1))
            if text:
                careers.append({'text': text, 'status': 'current'})
            continue

        # 2. 공백 패턴: 전 OO, 현 OO (단어 시작)
        space_match = re.match(r'^전\s+(.{2,})', line)
        if space_match:
            text = clean_career_text(space_match.group(1))
            if text:
                careers.append({'text': text, 'status': 'former'})
            continue

        space_match = re.match(r'^현\s+(.{2,})', line)
        if space_match:
            text = clean_career_text(space_match.group(1))
            if text:
                careers.append({'text': text, 'status': 'current'})
            continue

        # 3. 연도 범위 + 현재: YYYY ~ 현재 OO
        year_current_match = re.match(r'^(\d{4})\s*[~\-]\s*현재\s+(.+)', line)
        if year_current_match:
            text = clean_career_text(year_current_match.group(2))
            if text:
                careers.append({'text': text, 'status': 'current'})
            continue

        # 4. 연도 범위 (종료): YYYY ~ YYYY OO
        year_range_match = re.match(r'^(\d{4})\s*[~\-]\s*(\d{4})\s+(.+)', line)
        if year_range_match:
            text = clean_career_text(year_range_match.group(3))
            if text:
                careers.append({'text': text, 'status': 'former'})
            continue

        # 5. 기간 패턴: YYYY.MM ~ YYYY.MM OO
        period_match = re.match(r'^(\d{4})[\.\/](\d{1,2})\s*[~\-]\s*(\d{4})?[\.\/]?(\d{1,2})?\s+(.+)', line)
        if period_match:
            text = clean_career_text(period_match.group(5))
            end_year = period_match.group(3)
            if text:
                status = 'former' if end_year else 'unknown'
                careers.append({'text': text, 'status': status})
            continue

        # 6. 줄 내부 연속 패턴: "현 A현 B전 C"
        inline_current = re.findall(r'[現현]\s*([^\s前전現현]{2,}?)(?=[前전現현]|$)', line)
        for text in inline_current:
            text = clean_career_text(text)
            if text:
                careers.append({'text': text, 'status': 'current'})

        inline_former = re.findall(r'[前전]\s*([^\s前전現현]{2,}?)(?=[前전現현]|$)', line)
        for text in inline_former:
            text = clean_career_text(text)
            if text:
                careers.append({'text': text, 'status': 'former'})

        # 7. 괄호 연도 패턴: OO회사(YYYY년) 또는 OO회사(YYYY년~YYYY년)
        year_paren_match = re.match(r'^(.+?)[\(（](\d{4})년?(?:[~\-](\d{4})년?)?[\)）]', line)
        if year_paren_match:
            text = clean_career_text(year_paren_match.group(1))
            end_year = year_paren_match.group(3)
            if text:
                status = 'former' if end_year else 'unknown'
                careers.append({'text': text, 'status': status})
            continue

        # 8. 슬래시 기간: 'YY.MM~'YY.MM OO 또는 'YY.MM~ OO
        short_period_match = re.match(r"^'?(\d{2})[\.\/](\d{1,2})[~\-]+'?(\d{2})?[\.\/]?(\d{1,2})?\s+(.+)", line)
        if short_period_match:
            text = clean_career_text(short_period_match.group(5))
            end_year = short_period_match.group(3)
            if text:
                status = 'former' if end_year else 'unknown'
                careers.append({'text': text, 'status': status})
            continue

        # 9. 단순 항목 (회사명 + 직책): "삼성전자 인사팀장" - 구조화된 텍스트면 추가
        # 최소 4자 이상, 회사명 패턴 감지
        if len(line) >= 6 and re.search(r'(주식회사|㈜|\(주\)|회사|은행|증권|투자|대표|이사|본부장|팀장|부장|과장|차장|부사장|사장|감사)', line):
            text = clean_career_text(line)
            if text and text not in [c['text'] for c in careers]:
                careers.append({'text': text, 'status': 'unknown'})

    return careers


def clean_career_text(text: str) -> Optional[str]:
    """경력 텍스트 정리"""
    if not text:
        return None
    text = re.sub(r'\s*[\(（][\d\.\~\-\s]+[\)）]$', '', text.strip())
    text = text.strip(' \t-–—')
    if len(text) < 2:
        return None
    return text


async def reparse_officer_careers(
    database_url: str,
    sample: int = 0,
    dry_run: bool = False
):
    """임원 경력 재파싱"""

    pool = await asyncpg.create_pool(database_url)

    async with pool.acquire() as conn:
        # career_raw_text가 있지만 career_history가 비어있는 레코드
        query = """
            SELECT id, name, career_raw_text
            FROM officers
            WHERE career_raw_text IS NOT NULL
              AND career_raw_text != ''
              AND (career_history IS NULL OR career_history = '[]'::jsonb)
        """
        rows = await conn.fetch(query)
        logger.info(f"재파싱 대상: {len(rows)}건")

        if sample > 0:
            rows = rows[:sample]
            logger.info(f"샘플 모드: {sample}건만 처리")

        stats = {
            'total': len(rows),
            'updated': 0,
            'no_parse': 0
        }

        for i, row in enumerate(rows, 1):
            officer_id = row['id']
            name = row['name']
            raw_text = row['career_raw_text']

            careers = parse_career_v24(raw_text)

            if careers:
                if not dry_run:
                    await conn.execute(
                        "UPDATE officers SET career_history = $1, updated_at = NOW() WHERE id = $2",
                        json.dumps(careers, ensure_ascii=False),
                        officer_id
                    )
                stats['updated'] += 1

                if i <= 10 or (i % 1000 == 0):
                    logger.info(f"[{i}/{stats['total']}] {name}: {len(careers)}개 경력 추출")
                    for c in careers[:3]:
                        logger.info(f"    - [{c['status']}] {c['text'][:40]}...")
            else:
                stats['no_parse'] += 1

        # 결과 출력
        print("\n" + "="*60)
        print("임원 경력 재파싱 결과")
        print("="*60)
        print(f"총 대상:     {stats['total']}건")
        print(f"파싱 성공:   {stats['updated']}건")
        print(f"파싱 실패:   {stats['no_parse']}건")
        print(f"성공률:      {100*stats['updated']/stats['total']:.1f}%")
        if dry_run:
            print("\n[DRY-RUN] 실제 DB 업데이트 없음")
        print("="*60)

    await pool.close()


def main():
    parser = argparse.ArgumentParser(description='임원 경력 재파싱')
    parser.add_argument('--sample', type=int, default=0, help='샘플 수')
    parser.add_argument('--dry-run', action='store_true', help='테스트 모드')
    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경 변수 필요")
        sys.exit(1)

    asyncio.run(reparse_officer_careers(
        database_url=database_url,
        sample=args.sample,
        dry_run=args.dry_run
    ))


if __name__ == '__main__':
    main()
