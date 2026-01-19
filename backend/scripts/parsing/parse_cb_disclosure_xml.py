#!/usr/bin/env python3
"""
CB 공시 XML 파서
- ZIP 압축 해제
- XML 파싱
- 임원 정보 추출 (대표이사, 작성책임자)
- CB 인수자 정보 추출
"""
import asyncio
import logging
import sys
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBDisclosureParser:
    """CB 공시 문서 파서"""

    def __init__(self):
        self.stats = {
            'total': 0,
            'parsed': 0,
            'officers_found': 0,
            'subscribers_found': 0,
            'errors': 0
        }

    def extract_zip(self, zip_path: Path) -> Optional[str]:
        """ZIP 파일에서 XML 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # 첫 번째 XML 파일 찾기
                xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
                if not xml_files:
                    return None

                xml_content = zip_file.read(xml_files[0])
                # EUC-KR 또는 UTF-8 디코딩 시도
                try:
                    return xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        return xml_content.decode('euc-kr')
                    except:
                        return xml_content.decode('cp949', errors='ignore')
        except Exception as e:
            logger.error(f"Error extracting {zip_path}: {e}")
            return None

    def parse_xml(self, xml_content: str) -> Dict[str, Any]:
        """XML 파싱하여 구조화된 데이터 추출"""
        result = {
            'company_name': None,
            'ceo': None,  # 대표이사
            'document_creator': None,  # 작성책임자
            'creator_position': None,  # 작성책임자 직책
            'report_date': None,
            'subscribers': [],  # CB 인수자 목록
            'bond_info': {}  # 사채 정보
        }

        try:
            # XML 파싱
            root = ET.fromstring(xml_content)

            # 회사명
            company_elem = root.find('.//COMPANY-NAME')
            if company_elem is not None:
                result['company_name'] = company_elem.text

            # XML 텍스트에서 대표이사 추출 (TABLE 구조)
            for td in root.findall('.//TD'):
                if td.text and '대' in td.text and '표' in td.text:
                    # 다음 TD가 대표이사 이름
                    parent = root
                    for tr in root.findall('.//TR'):
                        tds = list(tr.findall('.//TD'))
                        for i, td_elem in enumerate(tds):
                            if td_elem.text and '대  표   이  사' in td_elem.text.replace(' ', ''):
                                if i + 1 < len(tds):
                                    result['ceo'] = tds[i + 1].text.strip() if tds[i + 1].text else None
                            elif td_elem.text and '작 성 책 임 자' in td_elem.text.replace(' ', ''):
                                # 직책과 성명 추출
                                if i + 1 < len(tds):
                                    position_text = tds[i + 1].text.strip() if tds[i + 1].text else ''
                                    if '직' in position_text and '책' in position_text:
                                        # (직책)전무 형식
                                        match = re.search(r'\)(.+)', position_text)
                                        if match:
                                            result['creator_position'] = match.group(1).strip()
                                if i + 2 < len(tds):
                                    name_text = tds[i + 2].text.strip() if tds[i + 2].text else ''
                                    if '성' in name_text and '명' in name_text:
                                        # (성명)박종완 형식
                                        match = re.search(r'\)(.+)', name_text)
                                        if match:
                                            result['document_creator'] = match.group(1).strip()

            # TODO: CB 인수자 정보 추출 (실제 구조 확인 필요)
            # 이 부분은 실제 XML 구조를 보고 추가 개발 필요

        except Exception as e:
            logger.error(f"Error parsing XML: {e}")

        return result

    async def process_disclosure(
        self,
        disclosure_id: str,
        rcept_no: str,
        storage_path: Path,
        conn: asyncpg.Connection
    ) -> Dict[str, Any]:
        """개별 공시 처리"""
        try:
            # XML 파일 경로
            xml_path = storage_path / f"{rcept_no}.xml"

            if not xml_path.exists():
                logger.warning(f"XML file not found: {xml_path}")
                return None

            # ZIP 압축 해제
            xml_content = self.extract_zip(xml_path)
            if not xml_content:
                logger.warning(f"Failed to extract XML from {xml_path}")
                return None

            # XML 파싱
            parsed_data = self.parse_xml(xml_content)

            # parsed_data를 disclosure_parsed_data 테이블에 저장
            import json
            await conn.execute("""
                INSERT INTO disclosure_parsed_data (
                    id, rcept_no, parsed_data, parsed_at, parser_version
                )
                VALUES (uuid_generate_v4(), $1, $2, $3, $4)
                ON CONFLICT (rcept_no) DO UPDATE
                SET parsed_data = EXCLUDED.parsed_data,
                    parsed_at = EXCLUDED.parsed_at,
                    parser_version = EXCLUDED.parser_version
            """,
                rcept_no,
                json.dumps(parsed_data, ensure_ascii=False),
                datetime.now(),
                '1.0'
            )

            self.stats['parsed'] += 1
            if parsed_data.get('ceo') or parsed_data.get('document_creator'):
                self.stats['officers_found'] += 1

            return parsed_data

        except Exception as e:
            logger.error(f"Error processing disclosure {rcept_no}: {e}")
            self.stats['errors'] += 1
            return None


async def main():
    """메인 함수"""
    parser = CBDisclosureParser()

    # PostgreSQL 연결
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 공시 목록 조회
        disclosures = await conn.fetch("""
            SELECT id, rcept_no, corp_code, corp_name
            FROM disclosures
            ORDER BY rcept_dt DESC
            LIMIT 100
        """)

        logger.info(f"Processing {len(disclosures)} disclosures (sample)")

        storage_path = Path('/app/data/cb_samples_test')

        for disclosure in disclosures:
            parser.stats['total'] += 1

            result = await parser.process_disclosure(
                disclosure['id'],
                disclosure['rcept_no'],
                storage_path,
                conn
            )

            if parser.stats['parsed'] % 10 == 0:
                logger.info(
                    f"Progress: {parser.stats['parsed']}/{parser.stats['total']} parsed, "
                    f"{parser.stats['officers_found']} with officers, "
                    f"{parser.stats['errors']} errors"
                )

        # 최종 통계
        logger.info("=" * 80)
        logger.info("XML Parsing Complete")
        logger.info("=" * 80)
        logger.info(f"Total processed: {parser.stats['total']}")
        logger.info(f"Successfully parsed: {parser.stats['parsed']}")
        logger.info(f"Officers found: {parser.stats['officers_found']}")
        logger.info(f"Subscribers found: {parser.stats['subscribers_found']}")
        logger.info(f"Errors: {parser.stats['errors']}")

        # 샘플 데이터 확인
        sample = await conn.fetch("""
            SELECT rcept_no, parsed_data->>'company_name' as company,
                   parsed_data->>'ceo' as ceo,
                   parsed_data->>'document_creator' as creator
            FROM disclosure_parsed_data
            WHERE parsed_data->>'ceo' IS NOT NULL
            LIMIT 5
        """)

        logger.info("\nSample parsed data:")
        for row in sample:
            logger.info(f"  {row['company']} - CEO: {row['ceo']}, Creator: {row['creator']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
