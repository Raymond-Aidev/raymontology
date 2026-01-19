#!/usr/bin/env python3
"""
사업보고서 다운로드 (2022-2025)
- 2022, 2023, 2024: 연간 사업보고서 (reprt_code='11011')
- 2025: 2분기 보고서 (reprt_code='11012')
- 모든 KOSPI/KOSDAQ 상장 기업 대상
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = "1fd0cd12ae5260eafb7de3130ad91f16aa61911b"
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


class BusinessReportDownloader:
    """사업보고서 다운로드 시스템"""

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

        # 다운로드 경로 설정
        self.download_dir = Path(__file__).parent.parent / 'data' / 'business_reports'
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # 메타데이터 저장 경로
        self.metadata_file = self.download_dir / 'business_reports_metadata.json'
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict:
        """메타데이터 파일 로드"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """메타데이터 파일 저장"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    async def find_business_reports(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        corp_name: str,
        year: int,
        report_type: str
    ) -> list:
        """
        특정 기업의 사업보고서 검색

        Args:
            corp_code: 기업 고유번호
            corp_name: 기업명
            year: 사업연도 (2022-2025)
            report_type: '11011' (연간) or '11012' (반기) or '11013' (1분기) or '11014' (3분기)
        """
        try:
            # 시작일/종료일 설정
            if year == 2025:
                # 2025년은 Q2까지만
                bgn_de = '20250101'
                end_de = '20250630'
            else:
                bgn_de = f'{year}0101'
                end_de = f'{year}1231'

            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': bgn_de,
                'end_de': end_de,
                'pblntf_ty': 'A',  # 정기공시
                'page_no': '1',
                'page_count': '100'
            }

            async with session.get(DART_LIST_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"{corp_name} ({year}): HTTP {response.status}")
                    self.stats['errors'] += 1
                    return []

                data = await response.json()

                if data.get('status') != '000':
                    if data.get('status') == '013':
                        # 데이터 없음 (정상)
                        self.stats['no_data'] += 1
                    else:
                        logger.debug(f"{corp_name} ({year}): {data.get('message', 'Unknown error')}")
                        self.stats['errors'] += 1
                    return []

                # 사업보고서 필터링
                reports = []
                for item in data.get('list', []):
                    report_nm = item.get('report_nm', '')
                    reprt_code = item.get('reprt_code', '')

                    # 연간 사업보고서 또는 분기보고서 확인
                    if report_type == '11011':
                        # 연간 사업보고서
                        if '사업보고서' in report_nm and '반기' not in report_nm and '분기' not in report_nm:
                            if reprt_code == '11011':
                                reports.append(item)
                    elif report_type in ['11012', '11013', '11014']:
                        # 분기보고서
                        if reprt_code == report_type:
                            reports.append(item)

                self.stats['reports_found'] += len(reports)
                return reports

        except Exception as e:
            logger.error(f"Error finding reports for {corp_name} ({year}): {e}")
            self.stats['errors'] += 1
            return []

    async def download_report(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str,
        corp_code: str,
        corp_name: str,
        year: int,
        report_type: str
    ) -> bool:
        """사업보고서 XML 다운로드"""
        try:
            # 파일명 생성: {corp_code}_{year}_{report_type}_{rcept_no}.xml
            filename = f"{corp_code}_{year}_{report_type}_{rcept_no}.xml"
            output_file = self.download_dir / filename

            # 이미 다운로드된 경우 스킵
            if output_file.exists():
                self.stats['already_exists'] += 1
                return True

            # DART API 호출
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            async with session.get(DART_DOCUMENT_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Download failed for {corp_name} ({year}): HTTP {response.status}")
                    self.stats['errors'] += 1
                    return False

                content = await response.read()

                # XML 파일 저장
                with open(output_file, 'wb') as f:
                    f.write(content)

                # 메타데이터 저장
                metadata_key = f"{corp_code}_{year}_{report_type}"
                self.metadata[metadata_key] = {
                    'corp_code': corp_code,
                    'corp_name': corp_name,
                    'year': year,
                    'report_type': report_type,
                    'rcept_no': rcept_no,
                    'filename': filename,
                    'download_date': datetime.now().isoformat(),
                    'file_size': len(content)
                }

                self.stats['reports_downloaded'] += 1
                logger.info(f"Downloaded: {corp_name} {year} ({len(content):,} bytes)")
                return True

        except Exception as e:
            logger.error(f"Error downloading {corp_name} ({year}): {e}")
            self.stats['errors'] += 1
            return False

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        company: dict
    ):
        """특정 기업의 모든 사업보고서 처리"""
        corp_code = company['corp_code']
        corp_name = company['name']

        # 2022-2024: 연간 사업보고서
        for year in [2022, 2023, 2024]:
            reports = await self.find_business_reports(
                session, corp_code, corp_name, year, '11011'
            )

            for report in reports:
                await self.download_report(
                    session,
                    report['rcept_no'],
                    corp_code,
                    corp_name,
                    year,
                    '11011'
                )
                await asyncio.sleep(0.3)  # Rate limiting

        # 2025: 2분기 보고서
        reports = await self.find_business_reports(
            session, corp_code, corp_name, 2025, '11012'
        )

        for report in reports:
            await self.download_report(
                session,
                report['rcept_no'],
                corp_code,
                corp_name,
                2025,
                '11012'
            )
            await asyncio.sleep(0.3)  # Rate limiting

    async def download_all(self, companies: list, batch_size: int = 1):
        """모든 기업의 사업보고서 다운로드 (순차 처리로 rate limit 회피)"""
        logger.info(f"Starting download for {len(companies)} companies")

        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(companies):
                # 각 회사를 순차적으로 처리
                await self.process_company(session, company)

                self.stats['companies_processed'] += 1

                # 진행 상황 출력
                if self.stats['companies_processed'] % 50 == 0:
                    logger.info(
                        f"Progress: {self.stats['companies_processed']}/{len(companies)} - "
                        f"Found: {self.stats['reports_found']}, "
                        f"Downloaded: {self.stats['reports_downloaded']}, "
                        f"Already exists: {self.stats['already_exists']}, "
                        f"No data: {self.stats['no_data']}, "
                        f"Errors: {self.stats['errors']}"
                    )

                    # 메타데이터 주기적 저장
                    self._save_metadata()

                # API rate limit - 각 회사마다 0.5초 대기
                await asyncio.sleep(0.5)

        # 최종 메타데이터 저장
        self._save_metadata()


async def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("사업보고서 다운로드 (2022-2025)")
    logger.info("=" * 80)

    # PostgreSQL 연결
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 상장 기업 목록 조회
        companies = await conn.fetch("""
            SELECT id, corp_code, name, ticker, market
            FROM companies
            WHERE corp_code IS NOT NULL
            ORDER BY market, ticker
        """)

        logger.info(f"Total companies: {len(companies)}")

        # 사업보고서 다운로더 생성
        downloader = BusinessReportDownloader(DART_API_KEY)

        # 사업보고서 다운로드 (순차 처리)
        await downloader.download_all([dict(c) for c in companies])

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("사업보고서 다운로드 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {downloader.stats['companies_processed']:,}")
        logger.info(f"발견된 보고서: {downloader.stats['reports_found']:,}")
        logger.info(f"다운로드됨: {downloader.stats['reports_downloaded']:,}")
        logger.info(f"기존 파일: {downloader.stats['already_exists']:,}")
        logger.info(f"데이터 없음: {downloader.stats['no_data']:,}")
        logger.info(f"오류: {downloader.stats['errors']:,}")

        # 메타데이터 통계
        logger.info(f"\n총 메타데이터 레코드: {len(downloader.metadata):,}")

        # 연도별 통계
        year_stats = {}
        for key, meta in downloader.metadata.items():
            year = meta['year']
            year_stats[year] = year_stats.get(year, 0) + 1

        logger.info("\n연도별 보고서 수:")
        for year in sorted(year_stats.keys()):
            logger.info(f"  {year}: {year_stats[year]:,}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
