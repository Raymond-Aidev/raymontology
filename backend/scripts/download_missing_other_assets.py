#!/usr/bin/env python3
"""
기타금융자산/기타자산 파싱을 위한 누락 파일 다운로드

기존 파싱에서 파일이 없거나 손상된 기업/연도의 공시를 다운로드합니다.
손상된 파일 재다운로드 및 누락 기업 신규 다운로드를 수행합니다.

사용법:
    python scripts/download_missing_other_assets.py --sample 10  # 10개 기업만 테스트
    python scripts/download_missing_other_assets.py              # 전체 실행
"""
import asyncio
import aiohttp
import asyncpg
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정
DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)
DART_DATA_DIR = Path(__file__).parent.parent / 'data' / 'dart'

# DART API URLs
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"

# 손상된 파일 목록 (재다운로드 대상)
CORRUPTED_FILES = [
    ("00389970", 2024, "20240329003026"),
    ("00767628", 2022, "20220322000250"),
    ("01262023", 2023, "20230323001570"),
    ("00159810", 2025, "20250327000323"),
    ("00104722", 2025, "20250320000780"),
    ("01504211", 2025, "20250319000467"),
    ("00186939", 2025, "20250404002636"),
    ("00439965", 2024, "20240329000152"),
    ("00815369", 2025, "20250321000422"),
    ("01095704", 2025, "20250324000070"),
    ("00171265", 2025, "20250326000060"),
    ("00535746", 2022, "20220816002148"),
    ("00535746", 2023, "20230321001399"),
    ("00535746", 2024, "20240322000009"),
    ("00606664", 2025, "20250327000342"),
    ("00164636", 2024, "20241114002502"),
    ("00633835", 2025, "20250321000826"),
    ("00140168", 2024, "20240314001750"),
    ("01381984", 2025, "20250328000929"),
]


class DARTDownloader:
    """DART 공시 다운로더"""

    def __init__(self, api_key: str, data_dir: Path):
        self.api_key = api_key
        self.data_dir = data_dir
        self.stats = {
            'total_companies': 0,
            'downloaded': 0,
            'already_exists': 0,
            'no_disclosure': 0,
            'errors': 0
        }

    async def fetch_disclosure_list(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        target_years: List[int]
    ) -> List[Dict]:
        """DART API로 공시 목록 조회 (특정 연도만)"""
        all_disclosures = []

        for year in target_years:
            bgn_de = f"{year}0101"
            end_de = f"{year}1231" if year < 2025 else datetime.now().strftime('%Y%m%d')

            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': bgn_de,
                'end_de': end_de,
                'page_count': 100,
                'pblntf_ty': 'A'  # 정기공시만 (사업보고서 등)
            }

            page_no = 1
            while True:
                params['page_no'] = page_no
                try:
                    async with session.get(DART_LIST_URL, params=params) as response:
                        if response.status != 200:
                            logger.warning(f"HTTP {response.status} for {corp_code}/{year}")
                            break

                        data = await response.json()

                        if data.get('status') != '000':
                            if data.get('status') != '013':  # 조회 데이터 없음은 정상
                                logger.debug(f"API: {corp_code}/{year}: {data.get('message')}")
                            break

                        disclosures = data.get('list', [])
                        if not disclosures:
                            break

                        # 사업보고서/반기보고서/분기보고서만 필터링
                        for disc in disclosures:
                            report_nm = disc.get('report_nm', '')
                            if '사업보고서' in report_nm or '반기' in report_nm or '분기' in report_nm:
                                disc['target_year'] = year
                                all_disclosures.append(disc)

                        total_page = data.get('total_page', 1)
                        if page_no >= total_page:
                            break
                        page_no += 1

                        await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error fetching list for {corp_code}/{year}: {e}")
                    break

        return all_disclosures

    async def download_document(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str,
        output_path: Path
    ) -> bool:
        """공시 문서 다운로드"""
        params = {
            'crtfc_key': self.api_key,
            'rcept_no': rcept_no
        }

        try:
            async with session.get(DART_DOCUMENT_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} downloading {rcept_no}")
                    return False

                content = await response.read()

                # ZIP 파일인지 확인
                if content[:2] != b'PK':
                    logger.warning(f"Not a ZIP file: {rcept_no}")
                    return False

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(content)

                return True

        except Exception as e:
            logger.error(f"Error downloading {rcept_no}: {e}")
            return False

    def find_existing_batch(self, corp_code: str) -> Path:
        """기존 batch 폴더에서 기업 디렉토리 찾기"""
        for batch_dir in self.data_dir.glob('batch_*'):
            corp_dir = batch_dir / corp_code
            if corp_dir.exists():
                return corp_dir
        # 없으면 batch_missing에 생성
        return self.data_dir / 'batch_missing' / corp_code

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        company_name: str,
        target_years: List[int]
    ) -> Tuple[int, int]:
        """단일 기업 처리"""
        self.stats['total_companies'] += 1

        # 공시 목록 조회
        disclosures = await self.fetch_disclosure_list(session, corp_code, target_years)

        if not disclosures:
            self.stats['no_disclosure'] += 1
            logger.info(f"  {company_name}: 공시 없음")
            return 0, 0

        # 기업 디렉토리 결정
        corp_dir = self.find_existing_batch(corp_code)

        # 다운로드
        downloaded = 0
        already_exists = 0

        for disc in disclosures:
            rcept_no = disc['rcept_no']
            year = disc['target_year']

            year_dir = corp_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            output_path = year_dir / f"{rcept_no}.zip"
            meta_path = year_dir / f"{rcept_no}_meta.json"

            if output_path.exists():
                already_exists += 1
                continue

            if await self.download_document(session, rcept_no, output_path):
                downloaded += 1
                self.stats['downloaded'] += 1

                # 메타데이터 저장
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(disc, f, ensure_ascii=False, indent=2)
            else:
                self.stats['errors'] += 1

            await asyncio.sleep(0.1)

        self.stats['already_exists'] += already_exists

        logger.info(f"  {company_name}: 다운로드 {downloaded}, 기존 {already_exists}")
        return downloaded, already_exists

    async def redownload_corrupted(self, session: aiohttp.ClientSession) -> int:
        """손상된 파일 재다운로드"""
        logger.info("=" * 60)
        logger.info("손상된 파일 재다운로드")
        logger.info("=" * 60)

        redownloaded = 0

        for corp_code, year, rcept_no in CORRUPTED_FILES:
            corp_dir = self.find_existing_batch(corp_code)
            year_dir = corp_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            output_path = year_dir / f"{rcept_no}.zip"

            # 기존 파일 삭제 (이미 삭제되었을 수 있음)
            if output_path.exists():
                output_path.unlink()

            if await self.download_document(session, rcept_no, output_path):
                redownloaded += 1
                logger.info(f"  재다운로드 완료: {corp_code}/{year}/{rcept_no}")
            else:
                logger.warning(f"  재다운로드 실패: {corp_code}/{year}/{rcept_no}")

            await asyncio.sleep(0.2)

        logger.info(f"재다운로드 완료: {redownloaded}/{len(CORRUPTED_FILES)}")
        return redownloaded


async def get_missing_companies_from_db(conn, limit: int = None) -> List[Dict]:
    """DB에서 파일 없는 기업/연도 조회"""
    query = """
        SELECT DISTINCT
            c.corp_code,
            c.name,
            fd.fiscal_year
        FROM financial_details fd
        JOIN companies c ON fd.company_id = c.id
        WHERE c.corp_code IS NOT NULL
          AND (fd.other_financial_assets_current IS NULL
               OR fd.other_assets_current IS NULL)
        ORDER BY c.name, fd.fiscal_year
    """

    rows = await conn.fetch(query)

    # 기업별로 그룹핑
    by_company = {}
    for row in rows:
        corp_code = row['corp_code']
        if corp_code not in by_company:
            by_company[corp_code] = {
                'corp_code': corp_code,
                'name': row['name'],
                'years': []
            }
        by_company[corp_code]['years'].append(row['fiscal_year'])

    companies = list(by_company.values())

    if limit:
        companies = companies[:limit]

    return companies


async def run(limit: int = None):
    """메인 실행"""
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        logger.info("=" * 60)
        logger.info("누락 파일 다운로드 시작")
        logger.info(f"DART API Key: {DART_API_KEY[:8]}...")
        logger.info("=" * 60)

        downloader = DARTDownloader(DART_API_KEY, DART_DATA_DIR)

        async with aiohttp.ClientSession() as session:
            # 1. 손상된 파일 재다운로드
            await downloader.redownload_corrupted(session)

            # 2. 누락 기업 다운로드
            companies = await get_missing_companies_from_db(conn, limit)

            logger.info("=" * 60)
            logger.info(f"누락 기업 다운로드: {len(companies)}개")
            logger.info("=" * 60)

            for i, company in enumerate(companies, 1):
                await downloader.process_company(
                    session,
                    company['corp_code'],
                    company['name'],
                    company['years']
                )

                if i % 20 == 0:
                    logger.info(f"진행: {i}/{len(companies)} - 다운로드: {downloader.stats['downloaded']}")

                await asyncio.sleep(0.2)

        # 결과 요약
        logger.info("=" * 60)
        logger.info("다운로드 완료")
        logger.info("=" * 60)
        logger.info(f"처리 기업: {downloader.stats['total_companies']}개")
        logger.info(f"다운로드: {downloader.stats['downloaded']}건")
        logger.info(f"기존 존재: {downloader.stats['already_exists']}건")
        logger.info(f"공시 없음: {downloader.stats['no_disclosure']}개")
        logger.info(f"에러: {downloader.stats['errors']}건")
        logger.info("=" * 60)

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='누락 파일 다운로드')
    parser.add_argument('--sample', type=int, help='샘플 기업 수')

    args = parser.parse_args()
    asyncio.run(run(limit=args.sample))


if __name__ == "__main__":
    main()
