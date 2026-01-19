#!/usr/bin/env python3
"""
Enterprise-Grade CB 공시 파서
20년 풀스택 + 10년 DB 전문가 수준

핵심 기능:
1. 데이터 정규화 & 참조 무결성
2. Fuzzy matching (임원 중복 방지)
3. Temporal data extraction (임기, 공시일)
4. Production-ready error handling
5. Frontend/Backend/Neo4j 호환성
"""
import asyncio
import logging
import sys
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import xml.etree.ElementTree as ET
import re
import json
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from asyncpg.pool import Pool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnterpriseOfficerParser:
    """
    Enterprise-Grade 임원 파서

    책임:
    - XML 파싱
    - 임원 정보 정규화
    - 중복 제거 (fuzzy matching)
    - Temporal 데이터 추출
    - PostgreSQL/Neo4j 호환 구조 생성
    """

    # 직책 정규화 맵핑
    POSITION_NORMALIZE = {
        '대표이사': '대표이사',
        '대표': '대표이사',
        'CEO': '대표이사',
        '전무': '전무이사',
        '전무이사': '전무이사',
        '상무': '상무이사',
        '상무이사': '상무이사',
        '이사': '이사',
        '감사': '감사',
        '사외이사': '사외이사',
        '비상근이사': '비상근이사',
    }

    def __init__(self, pg_pool: Pool):
        self.pg_pool = pg_pool

        # 캐시 (성능 최적화)
        self.company_cache = {}  # corp_code -> company_id
        self.officer_cache = {}  # (name, company_id) -> officer_id

        self.stats = {
            'total_parsed': 0,
            'officers_extracted': 0,
            'officers_created': 0,
            'officers_updated': 0,
            'positions_created': 0,
            'errors': 0,
        }

    def normalize_position(self, raw_position: str) -> str:
        """직책 정규화"""
        if not raw_position:
            return '기타'

        # 공백 제거
        pos = raw_position.strip().replace(' ', '')

        # 정규화 맵핑
        for key, normalized in self.POSITION_NORMALIZE.items():
            if key in pos:
                return normalized

        return raw_position.strip()[:100]  # 최대 100자

    def extract_name(self, text: str) -> Optional[str]:
        """텍스트에서 이름 추출 (한글 2-4자)"""
        if not text:
            return None

        # 한글 이름 패턴 (2-4자)
        match = re.search(r'([가-힣]{2,4})', text)
        if match:
            return match.group(1).strip()

        # 영문 이름
        match = re.search(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)', text)
        if match:
            return match.group(1).strip()

        return None

    def parse_date(self, date_str: str) -> Optional[date]:
        """날짜 파싱 (YYYYMMDD → date)"""
        if not date_str:
            return None

        try:
            # YYYYMMDD 형식
            if len(date_str) == 8 and date_str.isdigit():
                return datetime.strptime(date_str, '%Y%m%d').date()

            # YYYY-MM-DD 형식
            if '-' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d').date()

        except Exception:
            pass

        return None

    def extract_zip(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 XML 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                if not xml_files:
                    return None

                xml_content = zf.read(xml_files[0])

                # 인코딩 감지 및 디코딩
                for encoding in ['utf-8', 'euc-kr', 'cp949']:
                    try:
                        return xml_content.decode(encoding)
                    except:
                        continue

                return xml_content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"ZIP extraction error {zip_path}: {e}")
            return None

    def parse_xml_structure(self, xml_content: str, corp_code: str, rcept_dt: str) -> Dict[str, Any]:
        """
        XML 파싱 → 구조화된 데이터

        Returns:
            {
                'company_name': str,
                'report_date': date,
                'ceo': {'name': str, 'position': str},
                'creator': {'name': str, 'position': str},
                'subscribers': [{'name': str, 'amount': int, 'is_related': bool}]
            }
        """
        result = {
            'company_name': None,
            'report_date': self.parse_date(rcept_dt),
            'ceo': None,
            'creator': None,
            'subscribers': []
        }

        try:
            root = ET.fromstring(xml_content)

            # 회사명
            company_elem = root.find('.//COMPANY-NAME')
            if company_elem is not None and company_elem.text:
                result['company_name'] = company_elem.text.strip()

            # TABLE 구조에서 임원 정보 추출
            for tr in root.findall('.//TR'):
                tds = list(tr.findall('.//TD'))

                for i, td in enumerate(tds):
                    if not td.text:
                        continue

                    text = td.text.replace(' ', '')

                    # 대표이사
                    if '대표이사' in text or '대표' in text:
                        if i + 1 < len(tds) and tds[i + 1].text:
                            name = self.extract_name(tds[i + 1].text)
                            if name:
                                result['ceo'] = {
                                    'name': name,
                                    'position': '대표이사'
                                }

                    # 작성책임자
                    elif '작성책임자' in text or '작성자' in text:
                        # 직책 (다음 TD)
                        position = None
                        if i + 1 < len(tds) and tds[i + 1].text:
                            pos_text = tds[i + 1].text
                            if '직' in pos_text or '책' in pos_text:
                                match = re.search(r'\)(.+)', pos_text)
                                if match:
                                    position = self.normalize_position(match.group(1))

                        # 성명 (그 다음 TD)
                        if i + 2 < len(tds) and tds[i + 2].text:
                            name_text = tds[i + 2].text
                            if '성' in name_text or '명' in name_text:
                                match = re.search(r'\)(.+)', name_text)
                                if match:
                                    name = self.extract_name(match.group(1))
                                    if name:
                                        result['creator'] = {
                                            'name': name,
                                            'position': position or '담당임원'
                                        }

        except Exception as e:
            logger.error(f"XML parsing error: {e}")

        return result

    async def get_or_create_company(
        self,
        conn: asyncpg.Connection,
        corp_code: str,
        company_name: Optional[str] = None
    ) -> Optional[str]:
        """
        회사 조회 또는 생성

        Returns:
            company_id (UUID as string)
        """
        # 캐시 확인
        if corp_code in self.company_cache:
            return self.company_cache[corp_code]

        try:
            # PostgreSQL에서 조회
            company_id = await conn.fetchval("""
                SELECT id FROM companies WHERE corp_code = $1
            """, corp_code)

            if company_id:
                self.company_cache[corp_code] = str(company_id)
                return str(company_id)

            # 없으면 생성 (이름이 있을 경우)
            if company_name:
                company_id = await conn.fetchval("""
                    INSERT INTO companies (id, corp_code, name, created_at, updated_at)
                    VALUES (uuid_generate_v4(), $1, $2, NOW(), NOW())
                    ON CONFLICT (corp_code) DO UPDATE
                    SET name = EXCLUDED.name, updated_at = NOW()
                    RETURNING id
                """, corp_code, company_name)

                if company_id:
                    self.company_cache[corp_code] = str(company_id)
                    return str(company_id)

        except Exception as e:
            logger.error(f"Company lookup error {corp_code}: {e}")

        return None

    def fuzzy_match_name(self, name1: str, name2: str, threshold: float = 0.85) -> bool:
        """
        이름 유사도 매칭 (fuzzy matching)

        Args:
            threshold: 0.85 = 85% 이상 유사하면 동일 인물로 간주
        """
        if not name1 or not name2:
            return False

        ratio = SequenceMatcher(None, name1, name2).ratio()
        return ratio >= threshold

    async def get_or_create_officer(
        self,
        conn: asyncpg.Connection,
        name: str,
        company_id: str,
        position: str
    ) -> Tuple[str, bool]:
        """
        임원 조회 또는 생성 (fuzzy matching)

        Returns:
            (officer_id, is_new)
        """
        cache_key = (name, company_id)

        # 캐시 확인
        if cache_key in self.officer_cache:
            return self.officer_cache[cache_key], False

        try:
            # 1. 정확한 이름 매치
            officer_id = await conn.fetchval("""
                SELECT id FROM officers
                WHERE name = $1 AND current_company_id = $2
            """, name, company_id)

            if officer_id:
                self.officer_cache[cache_key] = str(officer_id)
                return str(officer_id), False

            # 2. Fuzzy matching (같은 회사 내 유사 이름)
            similar_officers = await conn.fetch("""
                SELECT id, name FROM officers
                WHERE current_company_id = $1
            """, company_id)

            for officer in similar_officers:
                if self.fuzzy_match_name(name, officer['name']):
                    self.officer_cache[cache_key] = str(officer['id'])
                    return str(officer['id']), False

            # 3. 신규 생성
            officer_id = await conn.fetchval("""
                INSERT INTO officers (
                    id, name, position, current_company_id,
                    created_at, updated_at
                )
                VALUES (uuid_generate_v4(), $1, $2, $3, NOW(), NOW())
                RETURNING id
            """, name, position, company_id)

            self.officer_cache[cache_key] = str(officer_id)
            self.stats['officers_created'] += 1
            return str(officer_id), True

        except Exception as e:
            logger.error(f"Officer creation error {name}/{company_id}: {e}")
            return None, False

    async def create_officer_position(
        self,
        conn: asyncpg.Connection,
        officer_id: str,
        company_id: str,
        position: str,
        report_date: date,
        source_disclosure_id: str
    ) -> bool:
        """
        임원 직책 temporal 레코드 생성

        UNIQUE 제약조건: (officer_id, company_id, term_start_date, source_disclosure_id)
        """
        try:
            await conn.execute("""
                INSERT INTO officer_positions (
                    id, officer_id, company_id, position,
                    term_start_date, term_end_date, is_current,
                    source_disclosure_id, source_report_date,
                    created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), $1, $2, $3,
                    $4, NULL, TRUE,
                    $5, $4,
                    NOW(), NOW()
                )
                ON CONFLICT (officer_id, company_id, term_start_date, source_disclosure_id)
                DO UPDATE SET
                    position = EXCLUDED.position,
                    source_report_date = EXCLUDED.source_report_date,
                    updated_at = NOW()
            """,
                officer_id, company_id, position,
                report_date,  # term_start_date = report_date (임기 시작일 추정)
                source_disclosure_id
            )

            self.stats['positions_created'] += 1
            return True

        except Exception as e:
            logger.error(f"Position creation error: {e}")
            return False

    async def process_disclosure(
        self,
        conn: asyncpg.Connection,
        disclosure: Dict[str, Any],
        xml_dir: Path
    ) -> bool:
        """개별 공시 처리 (트랜잭션)"""
        disclosure_id = disclosure['id']
        rcept_no = disclosure['rcept_no']
        corp_code = disclosure['corp_code']
        rcept_dt = disclosure['rcept_dt']

        try:
            # XML 파일 경로
            xml_path = xml_dir / f"{rcept_no}.xml"
            if not xml_path.exists():
                return False

            # ZIP 추출
            xml_content = self.extract_zip(xml_path)
            if not xml_content:
                return False

            # XML 파싱
            parsed_data = self.parse_xml_structure(xml_content, corp_code, rcept_dt)

            # Company 조회/생성
            company_id = await self.get_or_create_company(
                conn, corp_code, parsed_data.get('company_name')
            )
            if not company_id:
                return False

            # CEO 처리
            if parsed_data.get('ceo'):
                ceo_info = parsed_data['ceo']
                officer_id, is_new = await self.get_or_create_officer(
                    conn,
                    ceo_info['name'],
                    company_id,
                    ceo_info['position']
                )

                if officer_id:
                    await self.create_officer_position(
                        conn,
                        officer_id,
                        company_id,
                        ceo_info['position'],
                        parsed_data['report_date'] or date.today(),
                        disclosure_id
                    )
                    self.stats['officers_extracted'] += 1

            # Creator (작성책임자) 처리
            if parsed_data.get('creator'):
                creator_info = parsed_data['creator']
                officer_id, is_new = await self.get_or_create_officer(
                    conn,
                    creator_info['name'],
                    company_id,
                    creator_info['position']
                )

                if officer_id:
                    await self.create_officer_position(
                        conn,
                        officer_id,
                        company_id,
                        creator_info['position'],
                        parsed_data['report_date'] or date.today(),
                        disclosure_id
                    )
                    self.stats['officers_extracted'] += 1

            # disclosure_parsed_data에 저장 (Frontend/GraphQL 활용)
            await conn.execute("""
                INSERT INTO disclosure_parsed_data (
                    id, rcept_no, parsed_data, parsed_at, parser_version
                )
                VALUES (uuid_generate_v4(), $1, $2, NOW(), '2.0-enterprise')
                ON CONFLICT (rcept_no) DO UPDATE
                SET parsed_data = EXCLUDED.parsed_data,
                    parsed_at = NOW(),
                    parser_version = EXCLUDED.parser_version
            """,
                rcept_no,
                json.dumps(parsed_data, ensure_ascii=False, default=str)
            )

            self.stats['total_parsed'] += 1
            return True

        except Exception as e:
            logger.error(f"Disclosure processing error {rcept_no}: {e}")
            self.stats['errors'] += 1
            return False


async def main():
    """메인 함수"""

    # PostgreSQL Connection Pool
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    pool = await asyncpg.create_pool(
        db_url,
        min_size=5,
        max_size=20,
        command_timeout=60
    )

    try:
        parser = EnterpriseOfficerParser(pool)

        async with pool.acquire() as conn:
            # 공시 목록 조회
            disclosures = await conn.fetch("""
                SELECT id, rcept_no, corp_code, rcept_dt, corp_name
                FROM disclosures
                ORDER BY rcept_dt DESC
            """)

        logger.info(f"Processing {len(disclosures)} disclosures...")

        xml_dir = Path('/app/data/dart_xmls')

        # 배치 처리
        batch_size = 100
        for i in range(0, len(disclosures), batch_size):
            batch = disclosures[i:i + batch_size]

            async with pool.acquire() as conn:
                async with conn.transaction():
                    for disclosure in batch:
                        await parser.process_disclosure(
                            conn,
                            dict(disclosure),
                            xml_dir
                        )

            if parser.stats['total_parsed'] % 500 == 0:
                logger.info(
                    f"Progress: {parser.stats['total_parsed']}/{len(disclosures)} - "
                    f"Officers: {parser.stats['officers_extracted']} extracted, "
                    f"{parser.stats['officers_created']} created, "
                    f"Positions: {parser.stats['positions_created']}, "
                    f"Errors: {parser.stats['errors']}"
                )

        # 최종 통계
        logger.info("=" * 80)
        logger.info("Enterprise Parsing Complete")
        logger.info("=" * 80)
        logger.info(f"Total parsed: {parser.stats['total_parsed']}")
        logger.info(f"Officers extracted: {parser.stats['officers_extracted']}")
        logger.info(f"Officers created: {parser.stats['officers_created']}")
        logger.info(f"Officer positions created: {parser.stats['positions_created']}")
        logger.info(f"Errors: {parser.stats['errors']}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
