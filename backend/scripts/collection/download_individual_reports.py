#!/usr/bin/env python3
"""
개별 공시자료 다운로드 스크립트

실패한 기업들의 사업보고서/분기보고서를 DART에서 직접 다운로드합니다.
- 2022년: 사업보고서
- 2023년: 사업보고서
- 2024년: 사업보고서
- 2025년: 3분기보고서

사용법:
    python scripts/download_individual_reports.py --sample 5   # 5개 기업만 테스트
    python scripts/download_individual_reports.py              # 전체 실행
"""
import asyncio
import aiohttp
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정
DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_DATA_DIR = Path(__file__).parent.parent / 'data' / 'dart'
MISSING_COMPANIES_FILE = Path(__file__).parent / 'output' / 'missing_companies_20251229_170838.json'

# DART API URLs
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"

# 연도별 검색 조건
YEAR_REPORT_CONFIG = {
    2022: {
        'report_type': '사업보고서',
        'bgn_de': '20230101',  # 2022년 사업보고서는 2023년 초에 제출
        'end_de': '20230430',
    },
    2023: {
        'report_type': '사업보고서',
        'bgn_de': '20240101',
        'end_de': '20240430',
    },
    2024: {
        'report_type': '사업보고서',
        'bgn_de': '20250101',
        'end_de': '20250430',
    },
    2025: {
        'report_type': '분기보고서',  # 3분기보고서
        'bgn_de': '20251001',
        'end_de': '20251231',
    },
}


class IndividualReportDownloader:
    """개별 공시자료 다운로더"""

    def __init__(self, api_key: str, data_dir: Path):
        self.api_key = api_key
        self.data_dir = data_dir
        self.stats = {
            'total_companies': 0,
            'total_years': 0,
            'downloaded': 0,
            'already_exists': 0,
            'not_found': 0,
            'errors': 0
        }

    async def search_report(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        year: int
    ) -> Optional[Dict]:
        """특정 연도의 보고서 검색"""
        config = YEAR_REPORT_CONFIG.get(year)
        if not config:
            logger.warning(f"Unknown year config: {year}")
            return None

        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bgn_de': config['bgn_de'],
            'end_de': config['end_de'],
            'page_count': 100,
            'pblntf_ty': 'A'  # 정기공시
        }

        try:
            async with session.get(DART_LIST_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {corp_code}/{year}")
                    return None

                data = await response.json()

                if data.get('status') != '000':
                    if data.get('status') != '013':  # 조회 데이터 없음
                        logger.debug(f"API: {corp_code}/{year}: {data.get('message')}")
                    return None

                disclosures = data.get('list', [])
                if not disclosures:
                    return None

                # 해당 연도의 보고서 찾기
                report_type = config['report_type']
                for disc in disclosures:
                    report_nm = disc.get('report_nm', '')

                    # 사업보고서 또는 분기보고서 찾기
                    if report_type in report_nm:
                        # 정정 보고서가 아닌 원본 우선
                        if '정정' not in report_nm:
                            disc['target_year'] = year
                            return disc

                # 정정 보고서라도 있으면 사용
                for disc in disclosures:
                    report_nm = disc.get('report_nm', '')
                    if report_type in report_nm:
                        disc['target_year'] = year
                        return disc

                return None

        except Exception as e:
            logger.error(f"Error searching report for {corp_code}/{year}: {e}")
            return None

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
                    # XML 에러 응답일 수 있음
                    if b'<?xml' in content[:100]:
                        logger.warning(f"API error response for {rcept_no}")
                        return False
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
        # 없으면 batch_individual에 생성
        return self.data_dir / 'batch_individual' / corp_code

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        company_name: str,
        missing_years: List[int]
    ) -> Dict:
        """단일 기업 처리"""
        self.stats['total_companies'] += 1
        results = {
            'corp_code': corp_code,
            'name': company_name,
            'downloaded': [],
            'not_found': [],
            'errors': []
        }

        corp_dir = self.find_existing_batch(corp_code)

        for year in missing_years:
            self.stats['total_years'] += 1

            # 이미 파일이 있는지 확인
            year_dir = corp_dir / str(year)
            if year_dir.exists():
                existing_zips = list(year_dir.glob('*.zip'))
                if existing_zips:
                    self.stats['already_exists'] += 1
                    continue

            # 보고서 검색
            report = await self.search_report(session, corp_code, year)
            await asyncio.sleep(0.15)  # Rate limiting

            if not report:
                self.stats['not_found'] += 1
                results['not_found'].append(year)
                logger.info(f"  {company_name}/{year}: 보고서 없음")
                continue

            rcept_no = report['rcept_no']
            output_path = year_dir / f"{rcept_no}.zip"
            meta_path = year_dir / f"{rcept_no}_meta.json"

            # 다운로드
            if await self.download_document(session, rcept_no, output_path):
                self.stats['downloaded'] += 1
                results['downloaded'].append({
                    'year': year,
                    'rcept_no': rcept_no,
                    'report_nm': report.get('report_nm', '')
                })

                # 메타데이터 저장
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)

                logger.info(f"  {company_name}/{year}: 다운로드 완료 ({report.get('report_nm', '')})")
            else:
                self.stats['errors'] += 1
                results['errors'].append(year)
                logger.warning(f"  {company_name}/{year}: 다운로드 실패")

            await asyncio.sleep(0.2)  # Rate limiting

        return results


async def run(limit: int = None):
    """메인 실행"""
    # 누락 기업 목록 로드
    if not MISSING_COMPANIES_FILE.exists():
        logger.error(f"Missing companies file not found: {MISSING_COMPANIES_FILE}")
        return

    with open(MISSING_COMPANIES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    companies = data.get('companies', [])
    if limit:
        companies = companies[:limit]

    logger.info("=" * 60)
    logger.info("개별 공시자료 다운로드 시작")
    logger.info(f"DART API Key: {DART_API_KEY[:8]}...")
    logger.info(f"대상 기업: {len(companies)}개")
    logger.info("=" * 60)

    downloader = IndividualReportDownloader(DART_API_KEY, DART_DATA_DIR)
    all_results = []

    async with aiohttp.ClientSession() as session:
        for i, company in enumerate(companies, 1):
            logger.info(f"[{i}/{len(companies)}] {company['name']} ({company['corp_code']})")

            result = await downloader.process_company(
                session,
                company['corp_code'],
                company['name'],
                company['missing_years']
            )
            all_results.append(result)

            if i % 20 == 0:
                logger.info(f"진행: {i}/{len(companies)} - 다운로드: {downloader.stats['downloaded']}")

            await asyncio.sleep(0.3)

    # 결과 저장
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = output_dir / f'individual_download_results_{timestamp}.json'

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'stats': downloader.stats,
            'results': all_results
        }, f, ensure_ascii=False, indent=2)

    # 결과 요약
    logger.info("=" * 60)
    logger.info("다운로드 완료")
    logger.info("=" * 60)
    logger.info(f"처리 기업: {downloader.stats['total_companies']}개")
    logger.info(f"처리 연도: {downloader.stats['total_years']}건")
    logger.info(f"다운로드: {downloader.stats['downloaded']}건")
    logger.info(f"기존 존재: {downloader.stats['already_exists']}건")
    logger.info(f"보고서 없음: {downloader.stats['not_found']}건")
    logger.info(f"에러: {downloader.stats['errors']}건")
    logger.info(f"결과 파일: {result_file}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='개별 공시자료 다운로드')
    parser.add_argument('--sample', type=int, help='샘플 기업 수')

    args = parser.parse_args()
    asyncio.run(run(limit=args.sample))


if __name__ == "__main__":
    main()
