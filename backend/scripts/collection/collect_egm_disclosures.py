#!/usr/bin/env python3
"""
임시주주총회 공시 수집 스크립트

DART OpenAPI를 사용하여 임시주주총회 관련 공시를 수집합니다.
- 공시 목록 조회 (DB 기반)
- 공시 본문 다운로드 (DART API)
- egm_disclosures 테이블에 메타데이터 저장

사용법:
    # 2022년 이후 전체 수집
    python -m scripts.collection.collect_egm_disclosures

    # 특정 연도만
    python -m scripts.collection.collect_egm_disclosures --year 2024

    # 목록만 조회 (다운로드 없음)
    python -m scripts.collection.collect_egm_disclosures --list-only

    # 샘플 테스트
    python -m scripts.collection.collect_egm_disclosures --limit 10 --dry-run

환경 변수:
    DATABASE_URL: PostgreSQL 연결 문자열
    DART_API_KEY: DART OpenAPI 키
"""

import argparse
import asyncio
import json
import logging
import os
import zipfile
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

import aiohttp
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DART API 설정
DART_API_KEY = os.getenv('DART_API_KEY', '')
DART_API_BASE = 'https://opendart.fss.or.kr/api'

# 데이터 저장 경로
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'egm'

# Rate limiting
REQUESTS_PER_MINUTE = 900
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE

# 임시주주총회 관련 공시 패턴
EGM_PATTERNS = [
    '임시주주총회결과',
    '주주총회소집결의(임시주주총회)',
    '주주총회소집결의              (임시주주총회)',
    '경영권분쟁소송',
    '사외이사의선임ㆍ해임',
]


class EGMDisclosureCollector:
    """임시주주총회 공시 수집기"""

    def __init__(self, database_url: str, api_key: str = None):
        self.database_url = database_url
        self.api_key = api_key or DART_API_KEY
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다")

        self.session: Optional[aiohttp.ClientSession] = None
        self.pool: Optional[asyncpg.Pool] = None

        self.stats = {
            'total_found': 0,
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'db_inserted': 0,
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.pool = await asyncpg.create_pool(self.database_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.pool:
            await self.pool.close()

    async def get_egm_disclosures_from_db(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None
    ) -> List[Dict]:
        """DB에서 임시주주총회 관련 공시 조회

        이미 disclosures 테이블에 인덱싱된 공시 중
        임시주주총회 관련 공시만 필터링

        Args:
            start_year: 시작 연도
            end_year: 종료 연도 (기본: 현재 연도)
            limit: 최대 조회 개수

        Returns:
            공시 목록
        """
        if end_year is None:
            end_year = datetime.now().year

        async with self.pool.acquire() as conn:
            # LIKE 패턴 조합
            pattern_conditions = " OR ".join([
                f"d.report_nm LIKE '%{pattern}%'"
                for pattern in EGM_PATTERNS
            ])

            query = f"""
                SELECT
                    d.id,
                    d.rcept_no,
                    d.corp_code,
                    d.corp_name,
                    d.stock_code,
                    d.report_nm,
                    d.rcept_dt,
                    c.id as company_id,
                    c.name as company_name,
                    c.market,
                    c.listing_status
                FROM disclosures d
                LEFT JOIN companies c ON d.corp_code = c.corp_code
                WHERE ({pattern_conditions})
                  AND SUBSTRING(d.rcept_dt, 1, 4)::int >= $1
                  AND SUBSTRING(d.rcept_dt, 1, 4)::int <= $2
                  AND c.listing_status = 'LISTED'
                ORDER BY d.rcept_dt DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            rows = await conn.fetch(query, start_year, end_year)

            results = []
            for row in rows:
                results.append({
                    'disclosure_id': row['rcept_no'],
                    'corp_code': row['corp_code'],
                    'corp_name': row['corp_name'] or row['company_name'],
                    'report_nm': row['report_nm'],
                    'rcept_dt': row['rcept_dt'],
                    'company_id': str(row['company_id']) if row['company_id'] else None,
                    'market': row['market'],
                })

            logger.info(f"DB에서 {len(results)}건의 임시주주총회 관련 공시 조회")
            return results

    async def check_already_collected(self, disclosure_id: str) -> bool:
        """이미 수집된 공시인지 확인"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM egm_disclosures WHERE disclosure_id = $1",
                disclosure_id
            )
            return result is not None

    async def download_disclosure(
        self,
        rcept_no: str,
        corp_code: str,
        output_dir: Path
    ) -> Optional[Path]:
        """DART API에서 공시 본문 다운로드

        Args:
            rcept_no: 접수번호
            corp_code: 회사코드
            output_dir: 저장 디렉토리

        Returns:
            ZIP 파일 경로 또는 None
        """
        zip_path = output_dir / f"{rcept_no}.zip"

        # 이미 다운로드된 경우 스킵
        if zip_path.exists():
            logger.debug(f"이미 존재: {rcept_no}")
            return zip_path

        # DART API 호출
        url = f"{DART_API_BASE}/document.xml"
        params = {
            'crtfc_key': self.api_key,
            'rcept_no': rcept_no,
        }

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"다운로드 실패 ({resp.status}): {rcept_no}")
                    return None

                content_type = resp.headers.get('Content-Type', '')

                # XML 에러 응답 체크
                if 'xml' in content_type or 'text' in content_type:
                    text = await resp.text()
                    if '<status>' in text:
                        logger.warning(f"API 오류 응답: {rcept_no}")
                        return None

                content = await resp.read()

                if len(content) < 100:
                    logger.warning(f"파일이 너무 작음: {rcept_no}")
                    return None

                output_dir.mkdir(parents=True, exist_ok=True)

                with open(zip_path, 'wb') as f:
                    f.write(content)

                # ZIP 검증
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        xml_count = sum(1 for n in zf.namelist() if n.endswith('.xml'))
                        if xml_count == 0:
                            logger.warning(f"XML 파일 없음: {rcept_no}")
                            zip_path.unlink()
                            return None
                except zipfile.BadZipFile:
                    logger.warning(f"잘못된 ZIP 파일: {rcept_no}")
                    zip_path.unlink()
                    return None

                return zip_path

        except Exception as e:
            logger.error(f"다운로드 오류 {rcept_no}: {e}")
            return None

    async def insert_egm_disclosure(
        self,
        disclosure: Dict,
        zip_path: Optional[Path] = None
    ) -> bool:
        """egm_disclosures 테이블에 저장

        Args:
            disclosure: 공시 메타데이터
            zip_path: 다운로드된 ZIP 파일 경로 (선택)

        Returns:
            성공 여부
        """
        async with self.pool.acquire() as conn:
            try:
                # 날짜 파싱
                disclosure_date = None
                rcept_dt = disclosure.get('rcept_dt', '')
                if rcept_dt and len(rcept_dt) >= 8:
                    try:
                        disclosure_date = date(
                            int(rcept_dt[:4]),
                            int(rcept_dt[4:6]),
                            int(rcept_dt[6:8])
                        )
                    except:
                        pass

                # 공시 유형 분류
                report_nm = disclosure.get('report_nm', '')
                egm_type = 'REGULAR'
                if '경영권분쟁' in report_nm or '가처분' in report_nm:
                    egm_type = 'COURT_ORDERED'
                elif '소집허가' in report_nm:
                    egm_type = 'COURT_ORDERED'

                # company_id 처리
                company_id = None
                if disclosure.get('company_id'):
                    try:
                        company_id = uuid.UUID(disclosure['company_id'])
                    except:
                        pass

                await conn.execute("""
                    INSERT INTO egm_disclosures (
                        id, disclosure_id, company_id, corp_code, corp_name,
                        disclosure_date, egm_type, parse_status, created_at, updated_at
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW()
                    )
                    ON CONFLICT (disclosure_id) DO UPDATE SET
                        updated_at = NOW()
                """,
                    uuid.uuid4(),
                    disclosure['disclosure_id'],
                    company_id,
                    disclosure['corp_code'],
                    disclosure['corp_name'],
                    disclosure_date,
                    egm_type,
                    'PENDING',
                )
                return True

            except Exception as e:
                logger.error(f"DB 삽입 실패 {disclosure['disclosure_id']}: {e}")
                return False

    async def collect_all(
        self,
        start_year: int = 2022,
        end_year: int = None,
        limit: int = None,
        list_only: bool = False,
        dry_run: bool = False,
        skip_download: bool = False,
    ) -> Dict:
        """전체 수집 실행

        Args:
            start_year: 시작 연도
            end_year: 종료 연도
            limit: 최대 수집 개수
            list_only: 목록만 조회
            dry_run: 실제 저장 없이 테스트
            skip_download: 다운로드 건너뛰기 (DB 저장만)

        Returns:
            수집 통계
        """
        logger.info(f"=== 임시주주총회 공시 수집 시작 ===")
        logger.info(f"기간: {start_year} ~ {end_year or '현재'}")

        # DB에서 공시 목록 조회
        disclosures = await self.get_egm_disclosures_from_db(
            start_year=start_year,
            end_year=end_year,
            limit=limit
        )
        self.stats['total_found'] = len(disclosures)

        if list_only:
            logger.info(f"\n목록 조회 완료: {len(disclosures)}건")
            for d in disclosures[:20]:
                logger.info(f"  - [{d['rcept_dt']}] {d['corp_name']}: {d['report_nm'][:50]}")
            if len(disclosures) > 20:
                logger.info(f"  ... 외 {len(disclosures) - 20}건")
            return self.stats

        # 저장 디렉토리
        output_dir = DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # 수집 실행
        for i, disclosure in enumerate(disclosures):
            if (i + 1) % 50 == 0:
                logger.info(f"진행: {i+1}/{len(disclosures)} ({(i+1)/len(disclosures)*100:.1f}%)")

            disclosure_id = disclosure['disclosure_id']

            # 이미 수집된 공시 스킵
            if await self.check_already_collected(disclosure_id):
                self.stats['skipped'] += 1
                continue

            # 다운로드 (선택)
            zip_path = None
            if not skip_download and not dry_run:
                year = disclosure.get('rcept_dt', '')[:4]
                year_dir = output_dir / year
                zip_path = await self.download_disclosure(
                    rcept_no=disclosure_id,
                    corp_code=disclosure['corp_code'],
                    output_dir=year_dir
                )

                if zip_path:
                    self.stats['downloaded'] += 1
                else:
                    self.stats['failed'] += 1

                await asyncio.sleep(REQUEST_DELAY)

            # DB 저장
            if not dry_run:
                if await self.insert_egm_disclosure(disclosure, zip_path):
                    self.stats['db_inserted'] += 1

        # 결과 요약
        logger.info(f"\n=== 수집 완료 ===")
        logger.info(f"총 공시: {self.stats['total_found']}")
        logger.info(f"다운로드: {self.stats['downloaded']}")
        logger.info(f"스킵: {self.stats['skipped']}")
        logger.info(f"실패: {self.stats['failed']}")
        logger.info(f"DB 저장: {self.stats['db_inserted']}")
        logger.info(f"저장 위치: {output_dir}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description='임시주주총회 공시 수집')
    parser.add_argument('--year', type=int, help='특정 연도만 수집')
    parser.add_argument('--start-year', type=int, default=2022, help='시작 연도 (기본: 2022)')
    parser.add_argument('--limit', type=int, help='최대 수집 개수')
    parser.add_argument('--list-only', action='store_true', help='목록만 조회')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 테스트')
    parser.add_argument('--skip-download', action='store_true', help='다운로드 건너뛰기')

    args = parser.parse_args()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

    start_year = args.year or args.start_year
    end_year = args.year if args.year else None

    async with EGMDisclosureCollector(database_url) as collector:
        await collector.collect_all(
            start_year=start_year,
            end_year=end_year,
            limit=args.limit,
            list_only=args.list_only,
            dry_run=args.dry_run,
            skip_download=args.skip_download,
        )


if __name__ == '__main__':
    asyncio.run(main())
