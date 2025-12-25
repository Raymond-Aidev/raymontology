#!/usr/bin/env python3
"""
2025년 3분기보고서 다운로드 스크립트

DART API를 통해 2025년 3분기보고서(reprt_code='11014')를 다운로드합니다.
현금흐름표가 포함된 원본 XML 파일을 다운로드하여 로컬에 저장합니다.

사용법:
    python scripts/download_q3_reports_2025.py --limit 10  # 10개 회사만 테스트
    python scripts/download_q3_reports_2025.py              # 전체 실행
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import json
import os
import zipfile
from io import BytesIO
from pathlib import Path
from datetime import datetime
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DART API 설정
DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)


class Q3ReportDownloader:
    """2025년 3분기보고서 다운로더"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            'companies_processed': 0,
            'reports_found': 0,
            'reports_downloaded': 0,
            'already_exists': 0,
            'errors': 0,
            'no_data': 0
        }

        # 다운로드 경로 설정 (기존 dart 폴더와 같은 구조)
        self.download_dir = Path(__file__).parent.parent / 'data' / 'q3_reports_2025'
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def find_q3_reports(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        corp_name: str
    ) -> list:
        """
        2025년 3분기보고서 검색

        Args:
            corp_code: 기업 고유번호
            corp_name: 기업명
        """
        try:
            # 2025년 3분기보고서 검색 기간 (10월~12월 제출)
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': '20251001',  # 3분기보고서 제출 시작
                'end_de': '20251231',
                'pblntf_ty': 'A',  # 정기공시
                'page_no': '1',
                'page_count': '100'
            }

            async with session.get(DART_LIST_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"{corp_name}: HTTP {response.status}")
                    self.stats['errors'] += 1
                    return []

                data = await response.json()

                if data.get('status') != '000':
                    if data.get('status') == '013':
                        self.stats['no_data'] += 1
                    else:
                        logger.debug(f"{corp_name}: {data.get('message', 'Unknown error')}")
                    return []

                # 3분기보고서 필터링: "분기보고서 (2025.09)"
                reports = []
                for item in data.get('list', []):
                    report_nm = item.get('report_nm', '')
                    # 3분기보고서 확인: "분기보고서 (2025.09)"
                    if '분기보고서' in report_nm and '2025.09' in report_nm:
                        reports.append(item)

                self.stats['reports_found'] += len(reports)
                return reports

        except Exception as e:
            logger.error(f"Error finding reports for {corp_name}: {e}")
            self.stats['errors'] += 1
            return []

    async def download_report(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str,
        corp_code: str,
        corp_name: str
    ) -> bool:
        """3분기보고서 XML 다운로드 (ZIP 형태로 제공됨)"""
        try:
            # 파일명 생성
            corp_dir = self.download_dir / corp_code
            corp_dir.mkdir(exist_ok=True)

            zip_file = corp_dir / f"{rcept_no}.zip"
            meta_file = corp_dir / f"{rcept_no}_meta.json"

            # 이미 다운로드된 경우 스킵
            if zip_file.exists():
                self.stats['already_exists'] += 1
                return True

            # DART API 호출 (ZIP 파일로 제공됨)
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            async with session.get(DART_DOCUMENT_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Download failed for {corp_name}: HTTP {response.status}")
                    self.stats['errors'] += 1
                    return False

                content = await response.read()

                # ZIP 파일 저장
                with open(zip_file, 'wb') as f:
                    f.write(content)

                # 메타데이터 저장
                meta = {
                    'rcept_no': rcept_no,
                    'corp_code': corp_code,
                    'corp_name': corp_name,
                    'report_type': 'q3_2025',
                    'download_date': datetime.now().isoformat(),
                    'file_size': len(content)
                }
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                self.stats['reports_downloaded'] += 1
                logger.info(f"Downloaded: {corp_name} - {rcept_no} ({len(content):,} bytes)")
                return True

        except Exception as e:
            logger.error(f"Error downloading {corp_name}: {e}")
            self.stats['errors'] += 1
            return False

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        company: dict
    ):
        """특정 기업의 3분기보고서 처리"""
        corp_code = company['corp_code']
        corp_name = company['name']

        reports = await self.find_q3_reports(session, corp_code, corp_name)

        for report in reports:
            await self.download_report(
                session,
                report['rcept_no'],
                corp_code,
                corp_name
            )
            await asyncio.sleep(0.3)  # Rate limiting

    async def download_all(self, companies: list):
        """모든 기업의 3분기보고서 다운로드"""
        logger.info(f"Starting Q3 2025 report download for {len(companies)} companies")

        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(companies, 1):
                await self.process_company(session, company)

                self.stats['companies_processed'] += 1

                # 진행 상황 출력
                if self.stats['companies_processed'] % 100 == 0:
                    logger.info(
                        f"Progress: {self.stats['companies_processed']}/{len(companies)} - "
                        f"Found: {self.stats['reports_found']}, "
                        f"Downloaded: {self.stats['reports_downloaded']}, "
                        f"Already exists: {self.stats['already_exists']}, "
                        f"No data: {self.stats['no_data']}, "
                        f"Errors: {self.stats['errors']}"
                    )

                # API rate limit
                await asyncio.sleep(0.5)


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='2025년 3분기보고서 다운로드')
    parser.add_argument('--limit', type=int, help='다운로드할 회사 수 제한')
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("2025년 3분기보고서 다운로드")
    logger.info("=" * 80)

    # PostgreSQL 연결
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 상장 기업 목록 조회
        query = """
            SELECT id, corp_code, name, ticker, market
            FROM companies
            WHERE corp_code IS NOT NULL
              AND market IS NOT NULL
              AND market NOT IN ('ETF', '기타')
            ORDER BY name
        """
        if args.limit:
            query += f" LIMIT {args.limit}"

        companies = await conn.fetch(query)
        logger.info(f"Total companies: {len(companies)}")

        # 다운로더 생성 및 실행
        downloader = Q3ReportDownloader(DART_API_KEY)
        await downloader.download_all([dict(c) for c in companies])

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("다운로드 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {downloader.stats['companies_processed']:,}")
        logger.info(f"발견된 보고서: {downloader.stats['reports_found']:,}")
        logger.info(f"다운로드됨: {downloader.stats['reports_downloaded']:,}")
        logger.info(f"기존 파일: {downloader.stats['already_exists']:,}")
        logger.info(f"데이터 없음: {downloader.stats['no_data']:,}")
        logger.info(f"오류: {downloader.stats['errors']:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
