#!/usr/bin/env python3
"""
로컬 DART ZIP 파일에서 임원 정보 파싱

PARSING_STATUS.md 기반:
1. 동일인 식별: name + birth_date (YYYYMM)
2. 경력 파싱: 前/現 패턴
3. 재취임 감지: appointment_number

XML 필드:
- SH5_NM_T: 성명
- SH5_BIH (AUNITVALUE): 출생년월 (197811)
- SH5_SEX (AUNITVALUE): 성별 (1=남, 2=여)
- SH5_LEV: 직위
- SH5_SKL: 주요경력
- SH5_PER: 재직기간
- SH5_FIH (AUNITVALUE): 임기만료일 (YYYYMMDD)
"""
import asyncio
import asyncpg
import logging
import sys
import os
import re
import zipfile
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dateutil.relativedelta import relativedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = Path("/Users/jaejoonpark/raymontology/backend/data/dart")


class OfficerParser:
    """임원 파싱 클래스"""

    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'officers_found': 0,
            'officers_inserted': 0,
            'positions_inserted': 0,
            'errors': 0
        }
        self.company_cache = {}  # corp_code -> company_id
        self.company_market = {}  # corp_code -> market (상장구분)
        self.officer_cache = {}  # name_birthdate -> officer_id

    async def load_companies(self, conn: asyncpg.Connection):
        """회사 정보 로드 (market 정보 포함)"""
        rows = await conn.fetch("SELECT id, corp_code, market FROM companies WHERE corp_code IS NOT NULL")
        self.company_cache = {r['corp_code']: str(r['id']) for r in rows}
        self.company_market = {r['corp_code']: r['market'] for r in rows}
        listed_count = sum(1 for m in self.company_market.values() if m in ('KOSPI', 'KOSDAQ', 'KONEX'))
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개 (상장사: {listed_count}개)")

    def extract_xml_from_zip(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 XML 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        content = zf.read(name)
                        for enc in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                return content.decode(enc)
                            except:
                                continue
        except Exception as e:
            pass
        return None

    def parse_officer_table(self, xml_content: str) -> List[Dict]:
        """임원현황 테이블 파싱"""
        officers = []

        # SH5_DRCT_STT 테이블 찾기
        table_pattern = r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>(.*?)</TABLE-GROUP>'
        table_match = re.search(table_pattern, xml_content, re.DOTALL | re.IGNORECASE)

        if not table_match:
            return officers

        table_content = table_match.group(1)

        # 기준일 추출
        base_date_match = re.search(r'AUNIT="BASE_DT"[^>]*AUNITVALUE="(\d{8})"', table_content)
        base_date = base_date_match.group(1) if base_date_match else None

        # 각 행 파싱 (TBODY의 TR)
        row_pattern = r'<TR[^>]*ACOPY="Y"[^>]*>(.*?)</TR>'
        rows = re.findall(row_pattern, table_content, re.DOTALL)

        for row in rows:
            officer = self._parse_officer_row(row, base_date)
            if officer and officer.get('name'):
                officers.append(officer)

        return officers

    def _parse_officer_row(self, row_xml: str, base_date: str) -> Optional[Dict]:
        """임원 행 파싱"""
        try:
            officer = {'base_date': base_date}

            # 성명 (SH5_NM_T)
            name_match = re.search(r'ACODE="SH5_NM_T"[^>]*>([^<]+)</TE>', row_xml)
            if name_match:
                name = name_match.group(1).strip()
                if name and len(name) >= 2 and name != '-':
                    officer['name'] = name

            if not officer.get('name'):
                return None

            # 출생년월 (SH5_BIH - AUNITVALUE)
            birth_match = re.search(r'AUNIT="SH5_BIH"[^>]*AUNITVALUE="(\d{6})"', row_xml)
            if birth_match:
                officer['birth_date'] = birth_match.group(1)  # 197811

            # 성별 (SH5_SEX - AUNITVALUE: 1=남, 2=여)
            sex_match = re.search(r'AUNIT="SH5_SEX"[^>]*AUNITVALUE="(\d)"', row_xml)
            if sex_match:
                officer['gender'] = '남' if sex_match.group(1) == '1' else '여'

            # 직위 (SH5_LEV)
            pos_match = re.search(r'ACODE="SH5_LEV"[^>]*>([^<]+)</TE>', row_xml)
            if pos_match:
                pos = pos_match.group(1).strip()
                if pos and pos != '-':
                    officer['position'] = pos

            # 등기임원여부 (SH5_REG_DRCT - AUNITVALUE: 1=미등기, 2=등기, 3=사내이사, 4=사외이사, 5=감사)
            reg_match = re.search(r'AUNIT="SH5_REG_DRCT"[^>]*AUNITVALUE="(\d)"', row_xml)
            if reg_match:
                officer['reg_type'] = reg_match.group(1)

            # 상근여부 (SH5_FUL - AUNITVALUE: 1=상근, 2=비상근)
            ful_match = re.search(r'AUNIT="SH5_FUL"[^>]*AUNITVALUE="(\d)"', row_xml)
            if ful_match:
                officer['is_fulltime'] = ful_match.group(1) == '1'

            # 주요경력 (SH5_SKL)
            skl_match = re.search(r'ACODE="SH5_SKL"[^>]*>([^<]*)</TE>', row_xml, re.DOTALL)
            if skl_match:
                officer['career_text'] = skl_match.group(1).strip()
                officer['career_history'] = self._parse_career(officer['career_text'])

            # 재직기간 (SH5_PER)
            per_match = re.search(r'ACODE="SH5_PER"[^>]*>([^<]+)</TE>', row_xml)
            if per_match:
                officer['tenure_text'] = per_match.group(1).strip()
                tenure_dates = self._parse_tenure(officer['tenure_text'])
                if tenure_dates:
                    officer['term_start_date'] = tenure_dates[0]

            # 임기만료일 (SH5_FIH - AUNITVALUE)
            fih_match = re.search(r'AUNIT="SH5_FIH"[^>]*AUNITVALUE="(\d{8})"', row_xml)
            if fih_match:
                try:
                    officer['term_end_date'] = datetime.strptime(fih_match.group(1), '%Y%m%d').date()
                except:
                    pass

            return officer

        except Exception as e:
            return None

    def _parse_career(self, career_text: str) -> List[Dict]:
        """경력 파싱 (前/現 패턴)"""
        careers = []
        if not career_text:
            return careers

        # 줄바꿈 또는 공백으로 구분
        lines = re.split(r'[\n\r]+|(?=[前現])', career_text)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 前) 패턴
            former_match = re.search(r'前[\)）\s]*(.+?)(?:\s*[\(（][\d\.\~\s]+[\)）])?$', line)
            if former_match:
                careers.append({
                    'text': former_match.group(1).strip(),
                    'status': 'former'
                })
                continue

            # 現) 패턴
            current_match = re.search(r'現[\)）\s]*(.+?)(?:\s*[\(（][\d\.\~\s]+[\)）])?$', line)
            if current_match:
                careers.append({
                    'text': current_match.group(1).strip(),
                    'status': 'current'
                })

        return careers

    def _parse_tenure(self, tenure_text: str) -> Optional[Tuple[date, Optional[date]]]:
        """재직기간 파싱 (다양한 형식 지원)"""
        if not tenure_text:
            return None

        # 패턴 1: YYYY.MM ~ (예: 2017.02 ~)
        match = re.search(r'(\d{4})\.(\d{1,2})\s*~', tenure_text)
        if match:
            try:
                year, month = int(match.group(1)), int(match.group(2))
                if 1950 <= year <= 2050 and 1 <= month <= 12:
                    return (date(year, month, 1), None)
            except:
                pass

        # 패턴 2: YYYY-MM-DD ~ (예: 2017-02-01 ~)
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})\s*~', tenure_text)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1950 <= year <= 2050 and 1 <= month <= 12 and 1 <= day <= 31:
                    return (date(year, month, day), None)
            except:
                pass

        # 패턴 3: YYYY/MM ~ (예: 2017/02 ~)
        match = re.search(r'(\d{4})/(\d{1,2})\s*~', tenure_text)
        if match:
            try:
                year, month = int(match.group(1)), int(match.group(2))
                if 1950 <= year <= 2050 and 1 <= month <= 12:
                    return (date(year, month, 1), None)
            except:
                pass

        # 패턴 4: YYYY년 MM월 ~ (예: 2017년 02월 ~)
        match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*~', tenure_text)
        if match:
            try:
                year, month = int(match.group(1)), int(match.group(2))
                if 1950 <= year <= 2050 and 1 <= month <= 12:
                    return (date(year, month, 1), None)
            except:
                pass

        # 패턴 5: YYYYMM (6자리, 예: 201702)
        match = re.search(r'^(\d{4})(\d{2})$', tenure_text.strip())
        if match:
            try:
                year, month = int(match.group(1)), int(match.group(2))
                if 1950 <= year <= 2050 and 1 <= month <= 12:
                    return (date(year, month, 1), None)
            except:
                pass

        # 패턴 6: YYYY.MM.DD ~ (예: 2017.02.01 ~)
        match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*~', tenure_text)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1950 <= year <= 2050 and 1 <= month <= 12 and 1 <= day <= 31:
                    return (date(year, month, day), None)
            except:
                pass

        return None

    async def find_or_create_officer(
        self,
        conn: asyncpg.Connection,
        officer_data: Dict
    ) -> Optional[str]:
        """임원 조회 또는 생성 (동일인 식별: name + birth_date)"""
        name = officer_data.get('name')
        birth_date = officer_data.get('birth_date')

        if not name:
            return None

        # 캐시 키
        cache_key = f"{name}_{birth_date or ''}"

        if cache_key in self.officer_cache:
            return self.officer_cache[cache_key]

        # DB에서 조회
        if birth_date:
            existing = await conn.fetchrow("""
                SELECT id FROM officers
                WHERE name = $1 AND birth_date = $2
            """, name, birth_date)
        else:
            existing = await conn.fetchrow("""
                SELECT id FROM officers
                WHERE name = $1 AND birth_date IS NULL
            """, name)

        if existing:
            officer_id = str(existing['id'])
            self.officer_cache[cache_key] = officer_id
            return officer_id

        # 새로 생성
        officer_id = str(uuid.uuid4())
        try:
            await conn.execute("""
                INSERT INTO officers (id, name, birth_date, gender, career_history, position)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                uuid.UUID(officer_id),
                name,
                birth_date,
                officer_data.get('gender'),
                json.dumps(officer_data.get('career_history', []), ensure_ascii=False),
                officer_data.get('position')
            )
            self.officer_cache[cache_key] = officer_id
            self.stats['officers_inserted'] += 1
            return officer_id
        except asyncpg.UniqueViolationError:
            # 동시 삽입 시 충돌 - 다시 조회
            if birth_date:
                existing = await conn.fetchrow("""
                    SELECT id FROM officers WHERE name = $1 AND birth_date = $2
                """, name, birth_date)
            else:
                existing = await conn.fetchrow("""
                    SELECT id FROM officers WHERE name = $1 AND birth_date IS NULL
                """, name)
            if existing:
                officer_id = str(existing['id'])
                self.officer_cache[cache_key] = officer_id
                return officer_id
        except Exception as e:
            logger.error(f"임원 생성 실패 {name}: {e}")
        return None

    async def upsert_position(
        self,
        conn: asyncpg.Connection,
        officer_id: str,
        company_id: str,
        officer_data: Dict,
        source_disclosure_id: str,
        source_report_date: date
    ) -> bool:
        """임원 포지션 추가 (재취임 감지 포함)"""
        position = officer_data.get('position', '임원')
        term_start = officer_data.get('term_start_date')
        term_end = officer_data.get('term_end_date')

        # 재취임 번호 계산
        appointment_number = 1
        existing = await conn.fetch("""
            SELECT id, term_end_date, appointment_number
            FROM officer_positions
            WHERE officer_id = $1 AND company_id = $2
            ORDER BY term_end_date DESC NULLS LAST
        """, uuid.UUID(officer_id), uuid.UUID(company_id))

        if existing:
            last = existing[0]
            if last['term_end_date'] and term_start and term_start > last['term_end_date']:
                # 임기만료 후 재취임
                appointment_number = (last['appointment_number'] or 1) + 1
            else:
                # 동일 임기 - 업데이트
                appointment_number = last['appointment_number'] or 1

        # 중복 확인
        dup_check = await conn.fetchrow("""
            SELECT id FROM officer_positions
            WHERE officer_id = $1 AND company_id = $2
            AND (term_start_date = $3 OR (term_start_date IS NULL AND $3 IS NULL))
            AND source_disclosure_id = $4
        """, uuid.UUID(officer_id), uuid.UUID(company_id), term_start, source_disclosure_id)

        if dup_check:
            return False

        try:
            await conn.execute("""
                INSERT INTO officer_positions (
                    id, officer_id, company_id, position,
                    term_start_date, term_end_date, is_current,
                    source_disclosure_id, source_report_date,
                    birth_date, gender, appointment_number
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (officer_id, company_id, term_start_date, source_disclosure_id)
                DO UPDATE SET
                    term_end_date = COALESCE(EXCLUDED.term_end_date, officer_positions.term_end_date),
                    is_current = EXCLUDED.is_current,
                    appointment_number = EXCLUDED.appointment_number,
                    updated_at = NOW()
            """,
                uuid.uuid4(),
                uuid.UUID(officer_id),
                uuid.UUID(company_id),
                position,
                term_start,
                term_end,
                term_end is None or term_end >= date.today(),  # is_current
                source_disclosure_id,
                source_report_date,
                officer_data.get('birth_date'),
                officer_data.get('gender'),
                appointment_number
            )
            self.stats['positions_inserted'] += 1
            return True
        except Exception as e:
            logger.error(f"포지션 추가 실패: {e}")
            return False

    def is_listed_company(self, corp_code: str) -> bool:
        """상장사 여부 확인 (KOSPI, KOSDAQ, KONEX만 상장사)"""
        market = self.company_market.get(corp_code)
        return market in ('KOSPI', 'KOSDAQ', 'KONEX')

    async def process_zip_file(
        self,
        conn: asyncpg.Connection,
        zip_path: Path,
        corp_code: str,
        year: str
    ):
        """ZIP 파일 처리"""
        company_id = self.company_cache.get(corp_code)
        if not company_id:
            return

        xml_content = self.extract_xml_from_zip(zip_path)
        if not xml_content:
            return

        # 임원 파싱
        officers = self.parse_officer_table(xml_content)
        if not officers:
            return

        self.stats['files_processed'] += 1
        self.stats['officers_found'] += len(officers)

        # 접수번호 추출 (파일명)
        rcept_no = zip_path.stem  # 20240321001153

        # 보고서 기준일 추출
        report_date = None
        if officers and officers[0].get('base_date'):
            try:
                report_date = datetime.strptime(officers[0]['base_date'], '%Y%m%d').date()
            except:
                pass

        # 비상장사(ETF 등)는 임기 정보 제거 (상장사만 임기 정보 저장)
        is_listed = self.is_listed_company(corp_code)

        for officer_data in officers:
            # 비상장사인 경우 term 정보 제거
            if not is_listed:
                officer_data['term_start_date'] = None
                officer_data['term_end_date'] = None

            officer_id = await self.find_or_create_officer(conn, officer_data)
            if officer_id:
                await self.upsert_position(
                    conn, officer_id, company_id, officer_data,
                    rcept_no, report_date
                )

    async def run(self, years: List[str], limit: int = None):
        """메인 실행"""
        logger.info("=" * 80)
        logger.info("임원 파싱 시작 (로컬 ZIP 파일)")
        logger.info(f"대상 연도: {years}")
        logger.info("=" * 80)

        conn = await asyncpg.connect(DB_URL)

        try:
            # 회사 캐시 로드
            await self.load_companies(conn)

            # ZIP 파일 탐색
            count = 0
            for batch_dir in sorted(DART_DATA_DIR.glob("batch_*")):
                for corp_dir in batch_dir.iterdir():
                    if not corp_dir.is_dir():
                        continue
                    corp_code = corp_dir.name

                    for year_dir in corp_dir.iterdir():
                        if not year_dir.is_dir():
                            continue
                        if year_dir.name not in years:
                            continue

                        for zip_file in year_dir.glob("*.zip"):
                            await self.process_zip_file(conn, zip_file, corp_code, year_dir.name)
                            count += 1

                            if count % 1000 == 0:
                                logger.info(
                                    f"진행: {count}개 파일 처리 - "
                                    f"임원: {self.stats['officers_inserted']}, "
                                    f"포지션: {self.stats['positions_inserted']}"
                                )

                            if limit and count >= limit:
                                break
                        if limit and count >= limit:
                            break
                    if limit and count >= limit:
                        break
                if limit and count >= limit:
                    break

            # 최종 통계
            logger.info("\n" + "=" * 80)
            logger.info("임원 파싱 완료")
            logger.info("=" * 80)
            logger.info(f"처리된 파일: {self.stats['files_processed']}개")
            logger.info(f"발견된 임원: {self.stats['officers_found']}명")
            logger.info(f"생성된 임원: {self.stats['officers_inserted']}명")
            logger.info(f"생성된 포지션: {self.stats['positions_inserted']}개")

            # 현재 상태 확인
            officers_count = await conn.fetchval("SELECT COUNT(*) FROM officers")
            positions_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
            logger.info(f"\n현재 DB: officers={officers_count:,}, officer_positions={positions_count:,}")

        finally:
            await conn.close()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="로컬 ZIP에서 임원 파싱")
    parser.add_argument("--years", default="2022,2023,2024", help="파싱할 연도 (쉼표 구분)")
    parser.add_argument("--limit", type=int, help="처리할 파일 수 제한")

    args = parser.parse_args()
    years = args.years.split(',')

    parser_obj = OfficerParser()
    await parser_obj.run(years, args.limit)


if __name__ == "__main__":
    asyncio.run(main())
