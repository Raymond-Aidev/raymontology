"""
OfficerParser - DART 임원정보 파서

검증된 v2.1 로직 재사용:
- 동일인 식별 (name + birth_date)
- 경력 파싱 (前/現 패턴)
- 재취임 감지 (appointment_number)
- 시계열 임기 추적

개선사항 (Phase 3.1 반영):
- Unique 제약 변경: (officer_id, company_id, term_start_date) - source_disclosure_id 제외
- position_history JSONB로 직책 변동 보존
- 중복 레코드 생성 방지

사용법:
    from scripts.parsers import OfficerParser

    parser = OfficerParser()
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            await parser.parse_and_save(conn, zip_path, meta)
"""

import asyncpg
import json
import logging
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .base import BaseParser

logger = logging.getLogger(__name__)


class OfficerParser(BaseParser):
    """DART 임원정보 파서 (v2.1 + Phase 3.1 개선)"""

    def __init__(self, database_url: Optional[str] = None):
        super().__init__(database_url)
        self.company_cache = {}  # corp_code -> company_id
        self.company_market = {}  # corp_code -> market
        self.officer_cache = {}  # name_birthdate -> officer_id

    async def load_companies(self, conn: asyncpg.Connection):
        """회사 정보 로드"""
        rows = await conn.fetch(
            "SELECT id, corp_code, market FROM companies WHERE corp_code IS NOT NULL"
        )
        self.company_cache = {r['corp_code']: str(r['id']) for r in rows}
        self.company_market = {r['corp_code']: r['market'] for r in rows}
        listed_count = sum(1 for m in self.company_market.values() if m in ('KOSPI', 'KOSDAQ', 'KONEX'))
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개 (상장사: {listed_count}개)")

    def is_listed_company(self, corp_code: str) -> bool:
        """상장사 여부"""
        return self.company_market.get(corp_code) in ('KOSPI', 'KOSDAQ', 'KONEX')

    # =========================================================================
    # XML 파싱
    # =========================================================================

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

        # 각 행 파싱
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

            # 성별 (SH5_SEX)
            sex_match = re.search(r'AUNIT="SH5_SEX"[^>]*AUNITVALUE="(\d)"', row_xml)
            if sex_match:
                officer['gender'] = '남' if sex_match.group(1) == '1' else '여'

            # 직위 (SH5_LEV)
            pos_match = re.search(r'ACODE="SH5_LEV"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
            if pos_match:
                raw_pos = pos_match.group(1)
                p_match = re.search(r'<P[^>]*>([^<]+)</P>', raw_pos)
                if p_match:
                    pos = p_match.group(1).strip()
                else:
                    pos = re.sub(r'<[^>]+>', '', raw_pos).strip()
                if pos and pos != '-':
                    officer['position'] = pos

            # 등기임원여부 (SH5_REG_DRCT)
            reg_match = re.search(r'AUNIT="SH5_REG_DRCT"[^>]*AUNITVALUE="(\d)"', row_xml)
            if reg_match:
                officer['reg_type'] = reg_match.group(1)

            # 상근여부 (SH5_FUL)
            ful_match = re.search(r'AUNIT="SH5_FUL"[^>]*AUNITVALUE="(\d)"', row_xml)
            if ful_match:
                officer['is_fulltime'] = ful_match.group(1) == '1'

            # 주요경력 (SH5_SKL)
            skl_match = re.search(r'ACODE="SH5_SKL"[^>]*>(.*?)</TE>', row_xml, re.DOTALL)
            if skl_match:
                raw_career = skl_match.group(1)
                p_contents = re.findall(r'<P[^>]*>([^<]*)</P>', raw_career)
                if p_contents:
                    career_text = '\n'.join(p_contents)
                else:
                    career_text = re.sub(r'<[^>]+>', '', raw_career)
                officer['career_text'] = career_text.strip()
                officer['career_history'] = self._parse_career(officer['career_text'])

                # 원문 텍스트 저장 (□ → • 변환, UI 표시용)
                # v2.4: 패턴 파싱 실패해도 원문은 항상 표시 가능
                raw_text = officer['career_text']
                if raw_text:
                    # □ 불릿을 줄바꿈 + 불릿으로 변환
                    raw_text = re.sub(r'□\s*', '\n• ', raw_text)
                    # 연속 줄바꿈 정리
                    raw_text = re.sub(r'\n+', '\n', raw_text)
                    officer['career_raw_text'] = raw_text.strip()

            # 재직기간 (SH5_PER)
            per_match = re.search(r'ACODE="SH5_PER"[^>]*>([^<]+)</TE>', row_xml)
            if per_match:
                officer['tenure_text'] = per_match.group(1).strip()
                tenure_dates = self._parse_tenure(officer['tenure_text'])
                if tenure_dates:
                    officer['term_start_date'] = tenure_dates[0]

            # 임기만료일 (SH5_FIH)
            fih_match = re.search(r'AUNIT="SH5_FIH"[^>]*AUNITVALUE="(\d{8})"', row_xml)
            if fih_match:
                try:
                    officer['term_end_date'] = datetime.strptime(fih_match.group(1), '%Y%m%d').date()
                except:
                    pass

            return officer

        except Exception as e:
            logger.debug(f"Row parse error: {e}")
            return None

    def _parse_career(self, career_text: str) -> List[Dict]:
        """경력 파싱 (前/現/전/현 패턴)

        v2.3 개선:
        - 한자 패턴: 前), 現)
        - 한글 패턴: 전), 현)
        - 괄호 변형: ), ）, ) 공백 등 모두 지원
        - 줄 내부 연속 패턴 지원 (예: "현) A현) B" → 2개 경력)
        """
        careers = []
        if not career_text:
            return careers

        # 줄바꿈으로 먼저 분할
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

    def _parse_tenure(self, tenure_text: str) -> Optional[Tuple[date, Optional[date]]]:
        """재직기간 파싱"""
        if not tenure_text:
            return None

        patterns = [
            # YYYY.MM ~
            (r'(\d{4})\.(\d{1,2})\s*~', lambda m: (int(m.group(1)), int(m.group(2)), 1)),
            # YYYY-MM-DD ~
            (r'(\d{4})-(\d{1,2})-(\d{1,2})\s*~', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
            # YYYY/MM ~
            (r'(\d{4})/(\d{1,2})\s*~', lambda m: (int(m.group(1)), int(m.group(2)), 1)),
            # YYYY년 MM월 ~
            (r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*~', lambda m: (int(m.group(1)), int(m.group(2)), 1)),
            # YYYYMM (6자리)
            (r'^(\d{4})(\d{2})$', lambda m: (int(m.group(1)), int(m.group(2)), 1)),
            # YYYY.MM.DD ~
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*~', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        ]

        for pattern, extractor in patterns:
            match = re.search(pattern, tenure_text.strip())
            if match:
                try:
                    year, month, day = extractor(match)
                    if 1950 <= year <= 2050 and 1 <= month <= 12 and 1 <= day <= 31:
                        return (date(year, month, day), None)
                except:
                    pass

        return None

    # =========================================================================
    # DB 저장
    # =========================================================================

    async def find_or_create_officer(self, conn: asyncpg.Connection, officer_data: Dict) -> Optional[str]:
        """임원 조회 또는 생성"""
        name = officer_data.get('name')
        birth_date = officer_data.get('birth_date')

        if not name:
            return None

        cache_key = f"{name}_{birth_date or ''}"

        if cache_key in self.officer_cache:
            return self.officer_cache[cache_key]

        # DB 조회
        if birth_date:
            existing = await conn.fetchrow(
                "SELECT id FROM officers WHERE name = $1 AND birth_date = $2",
                name, birth_date
            )
        else:
            existing = await conn.fetchrow(
                "SELECT id FROM officers WHERE name = $1 AND birth_date IS NULL",
                name
            )

        if existing:
            officer_id = str(existing['id'])
            self.officer_cache[cache_key] = officer_id
            return officer_id

        # 생성
        officer_id = str(uuid.uuid4())
        try:
            await conn.execute("""
                INSERT INTO officers (id, name, birth_date, gender, career_history, career_raw_text, position)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid.UUID(officer_id),
                name,
                birth_date,
                officer_data.get('gender'),
                json.dumps(officer_data.get('career_history', []), ensure_ascii=False),
                officer_data.get('career_raw_text'),  # 원문 텍스트
                officer_data.get('position')
            )
            self.officer_cache[cache_key] = officer_id
            self.stats['records_created'] += 1
            return officer_id
        except asyncpg.UniqueViolationError:
            # 동시 삽입 충돌
            if birth_date:
                existing = await conn.fetchrow(
                    "SELECT id FROM officers WHERE name = $1 AND birth_date = $2",
                    name, birth_date
                )
            else:
                existing = await conn.fetchrow(
                    "SELECT id FROM officers WHERE name = $1 AND birth_date IS NULL",
                    name
                )
            if existing:
                officer_id = str(existing['id'])
                self.officer_cache[cache_key] = officer_id
                return officer_id
        except Exception as e:
            logger.error(f"임원 생성 실패 {name}: {e}")
            self.stats['errors'] += 1

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
        """임원 포지션 UPSERT (v2.1 - position_history 지원)

        Phase 3.1 개선:
        - Unique: (officer_id, company_id, term_start_date)
        - 직책 변경 시 position_history에 이전 직책 기록
        """
        position = officer_data.get('position', '임원')
        term_start = officer_data.get('term_start_date')
        term_end = officer_data.get('term_end_date')
        is_current = term_end is None or term_end >= date.today()

        # 재취임 번호 계산
        appointment_number = 1
        existing_positions = await conn.fetch("""
            SELECT id, term_end_date, appointment_number, position
            FROM officer_positions
            WHERE officer_id = $1 AND company_id = $2
            ORDER BY term_end_date DESC NULLS LAST
        """, uuid.UUID(officer_id), uuid.UUID(company_id))

        if existing_positions:
            last = existing_positions[0]
            if last['term_end_date'] and term_start and term_start > last['term_end_date']:
                appointment_number = (last['appointment_number'] or 1) + 1
            else:
                appointment_number = last['appointment_number'] or 1

        # 기존 레코드 확인 (새 Unique 제약 기준)
        existing = await conn.fetchrow("""
            SELECT id, position, position_history, source_disclosure_id
            FROM officer_positions
            WHERE officer_id = $1 AND company_id = $2
            AND (term_start_date = $3 OR (term_start_date IS NULL AND $3 IS NULL))
        """, uuid.UUID(officer_id), uuid.UUID(company_id), term_start)

        if existing:
            # 기존 레코드 업데이트 (직책 변경 시 history에 기록)
            old_position = existing['position']
            old_history = existing['position_history'] or []

            if old_position != position:
                # 이전 직책을 history에 추가
                new_history_item = {
                    'position': old_position,
                    'source_disclosure_id': existing['source_disclosure_id'],
                    'updated_at': datetime.now().isoformat()
                }

                # 중복 방지
                if not any(h.get('position') == old_position for h in old_history):
                    old_history.append(new_history_item)

                await conn.execute("""
                    UPDATE officer_positions SET
                        position = $1,
                        position_history = $2,
                        term_end_date = COALESCE($3, term_end_date),
                        is_current = $4,
                        source_disclosure_id = $5,
                        source_report_date = $6,
                        updated_at = NOW()
                    WHERE id = $7
                """,
                    position,
                    json.dumps(old_history, ensure_ascii=False),
                    term_end,
                    is_current,
                    source_disclosure_id,
                    source_report_date,
                    existing['id']
                )
                self.stats['records_updated'] += 1
            else:
                # 직책 동일 - 메타데이터만 업데이트
                await conn.execute("""
                    UPDATE officer_positions SET
                        term_end_date = COALESCE($1, term_end_date),
                        is_current = $2,
                        source_disclosure_id = $3,
                        source_report_date = $4,
                        updated_at = NOW()
                    WHERE id = $5
                """,
                    term_end, is_current, source_disclosure_id, source_report_date, existing['id']
                )

            return True

        # 새 레코드 삽입
        try:
            await conn.execute("""
                INSERT INTO officer_positions (
                    id, officer_id, company_id, position,
                    term_start_date, term_end_date, is_current,
                    source_disclosure_id, source_report_date,
                    birth_date, gender, appointment_number,
                    position_history
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                uuid.uuid4(),
                uuid.UUID(officer_id),
                uuid.UUID(company_id),
                position,
                term_start,
                term_end,
                is_current,
                source_disclosure_id,
                source_report_date,
                officer_data.get('birth_date'),
                officer_data.get('gender'),
                appointment_number,
                '[]'
            )
            self.stats['records_created'] += 1
            return True
        except asyncpg.UniqueViolationError:
            # 동시 삽입 충돌 - 재시도 (UPDATE로)
            logger.debug(f"Position conflict, retrying update: {officer_id}")
            return await self.upsert_position(
                conn, officer_id, company_id, officer_data,
                source_disclosure_id, source_report_date
            )
        except Exception as e:
            logger.error(f"Position upsert failed: {e}")
            self.stats['errors'] += 1
            return False

    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """단일 보고서 파싱"""
        result = {
            'success': False,
            'officers': [],
            'errors': [],
        }

        # 모든 XML 추출 (임원정보가 분리된 파일에 있을 수 있음)
        xml_contents = self.extract_all_xml_from_zip(zip_path)
        if not xml_contents:
            result['errors'].append('XML extraction failed')
            return result

        for xml_content in xml_contents:
            officers = self.parse_officer_table(xml_content)
            result['officers'].extend(officers)

        if result['officers']:
            result['success'] = True
            result['meta'] = {
                'corp_code': meta.get('corp_code'),
                'rcept_no': meta.get('rcept_no'),
            }

        return result

    async def save_to_db(self, conn: asyncpg.Connection, data: Dict[str, Any]) -> bool:
        """파싱 결과 DB 저장"""
        if not data.get('success') or not data.get('officers'):
            return False

        meta = data.get('meta', {})
        corp_code = meta.get('corp_code')
        rcept_no = meta.get('rcept_no', '')

        if not corp_code or corp_code not in self.company_cache:
            logger.warning(f"Unknown corp_code: {corp_code}")
            return False

        company_id = self.company_cache[corp_code]

        # 보고서 기준일
        report_date = None
        if data['officers'] and data['officers'][0].get('base_date'):
            try:
                report_date = datetime.strptime(data['officers'][0]['base_date'], '%Y%m%d').date()
            except:
                report_date = date.today()

        saved_count = 0
        for officer_data in data['officers']:
            officer_id = await self.find_or_create_officer(conn, officer_data)
            if officer_id:
                success = await self.upsert_position(
                    conn, officer_id, company_id, officer_data,
                    rcept_no, report_date
                )
                if success:
                    saved_count += 1

        return saved_count > 0
