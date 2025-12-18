#!/usr/bin/env python3
"""
CB 날짜 데이터 수정 스크립트
- 잘못된 issue_date (>2025 or <2000) NULL 처리
- maturity_date < issue_date 논리 오류 수정
- source_disclosure_id로 원본 공시에서 재파싱 시도
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import glob
from datetime import datetime, date
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'


def parse_date_safe(date_str: str) -> Optional[date]:
    """안전한 날짜 파싱 (YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD)"""
    if not date_str:
        return None

    # 숫자만 추출
    digits = re.sub(r'[^\d]', '', date_str)

    if len(digits) == 8:
        try:
            year = int(digits[:4])
            month = int(digits[4:6])
            day = int(digits[6:8])

            # 유효성 검사
            if year < 2000 or year > 2026:
                return None
            if month < 1 or month > 12:
                return None
            if day < 1 or day > 31:
                return None

            return date(year, month, day)
        except:
            return None

    # YYYY-MM-DD 또는 YYYY.MM.DD 형식
    for fmt in ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.year < 2000 or dt.year > 2026:
                return None
            return dt.date()
        except:
            continue

    return None


def extract_dates_from_xml(xml_content: str) -> Dict[str, Any]:
    """XML에서 CB 날짜 정보 추출"""
    result = {
        'issue_date': None,
        'maturity_date': None,
        'conversion_start_date': None,
        'conversion_end_date': None
    }

    try:
        # UTF-8 또는 EUC-KR 시도
        if isinstance(xml_content, bytes):
            try:
                content = xml_content.decode('utf-8')
            except:
                content = xml_content.decode('euc-kr', errors='ignore')
        else:
            content = xml_content

        # 발행일 패턴
        issue_patterns = [
            r'납\s*입\s*일[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})',
            r'발\s*행\s*일[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})',
            r'AUNIT="ISDT"[^>]*AUNITVALUE="(\d{8})"',
        ]

        for pattern in issue_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                parsed = parse_date_safe(match.group(1))
                if parsed:
                    result['issue_date'] = parsed
                    break

        # 만기일 패턴
        maturity_patterns = [
            r'만\s*기\s*일[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})',
            r'상\s*환\s*일[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})',
            r'AUNIT="MTDT"[^>]*AUNITVALUE="(\d{8})"',
        ]

        for pattern in maturity_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                parsed = parse_date_safe(match.group(1))
                if parsed:
                    result['maturity_date'] = parsed
                    break

        # 전환기간 패턴
        conv_patterns = [
            r'전\s*환\s*청\s*구\s*기\s*간[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})[^\d]*[~부터\-까지]*[^\d]*(\d{4}[\.\-/년]?\s*\d{1,2}[\.\-/월]?\s*\d{1,2})',
        ]

        for pattern in conv_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = parse_date_safe(match.group(1))
                end = parse_date_safe(match.group(2))
                if start:
                    result['conversion_start_date'] = start
                if end:
                    result['conversion_end_date'] = end
                break

    except Exception as e:
        logger.debug(f"XML 파싱 오류: {e}")

    return result


async def find_disclosure_zip(disclosure_id: str) -> Optional[str]:
    """source_disclosure_id로 ZIP 파일 경로 찾기"""
    # 패턴: YYYYMMDDNNNNNN (14자리)
    if not disclosure_id or len(disclosure_id) != 14:
        return None

    # 다양한 경로 패턴 시도
    patterns = [
        f"{DART_DATA_DIR}/**/{disclosure_id}.zip",
        f"{DART_DATA_DIR}/**/cb/{disclosure_id}.zip",
        f"{DART_DATA_DIR}/**/disclosures/{disclosure_id}.zip",
    ]

    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    return None


class CBDateFixer:
    """CB 날짜 수정기"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {
            'total_invalid': 0,
            'fixed_from_source': 0,
            'set_to_null': 0,
            'logic_errors_fixed': 0,
            'errors': 0
        }

    async def fix_invalid_dates(self):
        """잘못된 날짜 수정"""
        # 1. 잘못된 issue_date (>2025 또는 <2000) 찾기
        invalid_dates = await self.conn.fetch("""
            SELECT id, company_id, issue_date, maturity_date, source_disclosure_id
            FROM convertible_bonds
            WHERE EXTRACT(YEAR FROM issue_date) > 2025
               OR EXTRACT(YEAR FROM issue_date) < 2000
        """)

        logger.info(f"잘못된 issue_date: {len(invalid_dates)}건")
        self.stats['total_invalid'] = len(invalid_dates)

        for row in invalid_dates:
            cb_id = row['id']
            disclosure_id = row['source_disclosure_id']

            # 원본 공시에서 재파싱 시도
            fixed = False
            if disclosure_id:
                zip_path = await find_disclosure_zip(disclosure_id)
                if zip_path:
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            for name in zf.namelist():
                                if name.endswith('.xml'):
                                    content = zf.read(name)
                                    dates = extract_dates_from_xml(content)

                                    if dates['issue_date']:
                                        await self.conn.execute("""
                                            UPDATE convertible_bonds
                                            SET issue_date = $1,
                                                maturity_date = COALESCE($2, maturity_date),
                                                updated_at = NOW()
                                            WHERE id = $3
                                        """, dates['issue_date'], dates['maturity_date'], cb_id)

                                        self.stats['fixed_from_source'] += 1
                                        fixed = True
                                        logger.debug(f"CB {cb_id}: issue_date -> {dates['issue_date']}")
                                    break
                    except Exception as e:
                        logger.debug(f"ZIP 처리 오류: {e}")

            # 재파싱 실패 시 NULL 처리
            if not fixed:
                await self.conn.execute("""
                    UPDATE convertible_bonds
                    SET issue_date = NULL,
                        updated_at = NOW()
                    WHERE id = $1
                """, cb_id)
                self.stats['set_to_null'] += 1

        logger.info(f"원본 재파싱 성공: {self.stats['fixed_from_source']}건")
        logger.info(f"NULL 처리: {self.stats['set_to_null']}건")

    async def fix_logic_errors(self):
        """논리적 오류 수정 (maturity_date < issue_date)"""
        # maturity_date < issue_date 케이스
        logic_errors = await self.conn.fetch("""
            SELECT id, issue_date, maturity_date
            FROM convertible_bonds
            WHERE maturity_date < issue_date
              AND issue_date IS NOT NULL
              AND maturity_date IS NOT NULL
        """)

        logger.info(f"논리 오류 (maturity < issue): {len(logic_errors)}건")

        for row in logic_errors:
            cb_id = row['id']
            issue_date = row['issue_date']
            maturity_date = row['maturity_date']

            # 날짜 스왑이 합리적인지 확인
            if issue_date.year >= 2000 and issue_date.year <= 2026:
                if maturity_date.year >= 2000 and maturity_date.year <= 2030:
                    # 날짜 스왑
                    await self.conn.execute("""
                        UPDATE convertible_bonds
                        SET issue_date = $1,
                            maturity_date = $2,
                            updated_at = NOW()
                        WHERE id = $3
                    """, maturity_date, issue_date, cb_id)
                    self.stats['logic_errors_fixed'] += 1
                    logger.debug(f"CB {cb_id}: 날짜 스왑 {issue_date} <-> {maturity_date}")
                else:
                    # maturity_date가 이상하면 NULL
                    await self.conn.execute("""
                        UPDATE convertible_bonds
                        SET maturity_date = NULL,
                            updated_at = NOW()
                        WHERE id = $1
                    """, cb_id)
            else:
                # issue_date가 이상하면 NULL
                await self.conn.execute("""
                    UPDATE convertible_bonds
                    SET issue_date = NULL,
                        updated_at = NOW()
                    WHERE id = $1
                """, cb_id)

        logger.info(f"논리 오류 수정: {self.stats['logic_errors_fixed']}건")

    async def validate_all_dates(self):
        """모든 날짜 데이터 유효성 재검증"""
        # 추가 유효성 검사
        await self.conn.execute("""
            UPDATE convertible_bonds
            SET maturity_date = NULL
            WHERE EXTRACT(YEAR FROM maturity_date) > 2040
               OR EXTRACT(YEAR FROM maturity_date) < 2000
        """)

        await self.conn.execute("""
            UPDATE convertible_bonds
            SET conversion_start_date = NULL
            WHERE EXTRACT(YEAR FROM conversion_start_date) > 2040
               OR EXTRACT(YEAR FROM conversion_start_date) < 2000
        """)

        await self.conn.execute("""
            UPDATE convertible_bonds
            SET conversion_end_date = NULL
            WHERE EXTRACT(YEAR FROM conversion_end_date) > 2040
               OR EXTRACT(YEAR FROM conversion_end_date) < 2000
        """)

        logger.info("날짜 유효성 검증 완료")


async def main():
    logger.info("=" * 80)
    logger.info("CB 날짜 데이터 수정 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        fixer = CBDateFixer(conn)

        # 수정 전 상태
        before = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(issue_date) as has_issue_date,
                COUNT(CASE WHEN EXTRACT(YEAR FROM issue_date) > 2025 THEN 1 END) as invalid_future,
                COUNT(CASE WHEN maturity_date < issue_date THEN 1 END) as logic_error
            FROM convertible_bonds
        """)
        logger.info(f"\n수정 전 상태:")
        logger.info(f"  - 총 CB: {before['total']}건")
        logger.info(f"  - issue_date 있음: {before['has_issue_date']}건")
        logger.info(f"  - 잘못된 미래 날짜: {before['invalid_future']}건")
        logger.info(f"  - 논리 오류: {before['logic_error']}건")

        # 수정 실행
        await fixer.fix_invalid_dates()
        await fixer.fix_logic_errors()
        await fixer.validate_all_dates()

        # 수정 후 상태
        after = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(issue_date) as has_issue_date,
                COUNT(CASE WHEN EXTRACT(YEAR FROM issue_date) > 2025 THEN 1 END) as invalid_future,
                COUNT(CASE WHEN maturity_date < issue_date THEN 1 END) as logic_error
            FROM convertible_bonds
        """)

        logger.info(f"\n수정 후 상태:")
        logger.info(f"  - 총 CB: {after['total']}건")
        logger.info(f"  - issue_date 있음: {after['has_issue_date']}건")
        logger.info(f"  - 잘못된 미래 날짜: {after['invalid_future']}건")
        logger.info(f"  - 논리 오류: {after['logic_error']}건")

        logger.info("\n" + "=" * 80)
        logger.info("CB 날짜 수정 완료")
        logger.info(f"  - 원본 재파싱: {fixer.stats['fixed_from_source']}건")
        logger.info(f"  - NULL 처리: {fixer.stats['set_to_null']}건")
        logger.info(f"  - 논리 오류 수정: {fixer.stats['logic_errors_fixed']}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
