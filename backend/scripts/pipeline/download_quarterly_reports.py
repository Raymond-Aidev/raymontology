#!/usr/bin/env python3
"""
DART 분기보고서 다운로드

DART OpenAPI를 사용하여 분기보고서를 다운로드합니다.
다운로드된 파일은 data/dart/quarterly/{year}/{quarter}/ 디렉토리에 저장됩니다.

사용법:
    python -m scripts.pipeline.download_quarterly_reports --quarter Q1 --year 2025
    python -m scripts.pipeline.download_quarterly_reports --quarter Q4 --year 2024  # 사업보고서
    python -m scripts.pipeline.download_quarterly_reports --list-only  # 다운로드 없이 목록만

환경 변수:
    DART_API_KEY: DART OpenAPI 키
"""

import argparse
import asyncio
import json
import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from io import BytesIO

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DART API 설정
DART_API_KEY = os.getenv('DART_API_KEY', '')
DART_API_BASE = 'https://opendart.fss.or.kr/api'

# 데이터 저장 경로
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart' / 'quarterly'

# 분기별 보고서 코드
REPORT_CODES = {
    'Q1': '11013',  # 1분기보고서
    'Q2': '11012',  # 반기보고서
    'Q3': '11014',  # 3분기보고서
    'Q4': '11011',  # 사업보고서
}

# Rate limiting
REQUESTS_PER_MINUTE = 900  # DART API 제한
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE


class QuarterlyReportDownloader:
    """분기별 보고서 다운로더"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or DART_API_KEY
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다")

        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'total': 0,
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_report_list(
        self,
        quarter: str,
        year: int,
        corp_code: Optional[str] = None
    ) -> List[Dict]:
        """분기보고서 목록 조회

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도
            corp_code: 특정 회사만 조회 (선택)

        Returns:
            보고서 목록
        """
        pblntf_ty = REPORT_CODES.get(quarter)
        if not pblntf_ty:
            raise ValueError(f"잘못된 분기: {quarter}")

        # 분기별 검색 기간 설정
        date_ranges = self._get_date_range(quarter, year)

        all_reports = []

        for bgn_de, end_de in date_ranges:
            page = 1
            while True:
                params = {
                    'crtfc_key': self.api_key,
                    'bgn_de': bgn_de,
                    'end_de': end_de,
                    'pblntf_ty': 'A',  # 정기공시
                    'pblntf_detail_ty': pblntf_ty,
                    'page_no': str(page),
                    'page_count': '100',
                }

                if corp_code:
                    params['corp_code'] = corp_code

                url = f"{DART_API_BASE}/list.json"

                try:
                    async with self.session.get(url, params=params) as resp:
                        data = await resp.json()

                    if data.get('status') != '000':
                        if data.get('status') == '013':  # 결과 없음
                            break
                        logger.warning(f"API 오류: {data.get('message')}")
                        break

                    reports = data.get('list', [])
                    if not reports:
                        break

                    all_reports.extend(reports)
                    logger.debug(f"페이지 {page}: {len(reports)}건 조회")

                    # 다음 페이지 확인
                    total_page = int(data.get('total_page', 1))
                    if page >= total_page:
                        break
                    page += 1

                    await asyncio.sleep(REQUEST_DELAY)

                except Exception as e:
                    logger.error(f"목록 조회 오류: {e}")
                    break

        logger.info(f"{quarter} {year} 보고서 목록: {len(all_reports)}건")
        return all_reports

    def _get_date_range(self, quarter: str, year: int) -> List[Tuple[str, str]]:
        """분기별 검색 기간 반환

        보고서 제출 기간 기준 (마감일 + 45일)
        """
        if quarter == 'Q1':
            # 1분기: 5월 중순까지 제출
            return [(f'{year}0401', f'{year}0531')]
        elif quarter == 'Q2':
            # 반기: 8월 중순까지 제출
            return [(f'{year}0701', f'{year}0831')]
        elif quarter == 'Q3':
            # 3분기: 11월 중순까지 제출
            return [(f'{year}1001', f'{year}1130')]
        else:  # Q4
            # 사업보고서: 다음해 3월까지 제출
            next_year = year + 1
            return [(f'{next_year}0101', f'{next_year}0430')]

    async def download_report(
        self,
        rcept_no: str,
        corp_code: str,
        corp_name: str,
        output_dir: Path
    ) -> bool:
        """개별 보고서 다운로드

        Args:
            rcept_no: 접수번호
            corp_code: 회사코드
            corp_name: 회사명
            output_dir: 저장 디렉토리

        Returns:
            성공 여부
        """
        # 이미 다운로드된 경우 스킵
        zip_path = output_dir / f"{rcept_no}.zip"
        meta_path = output_dir / f"{rcept_no}_meta.json"

        if zip_path.exists() and meta_path.exists():
            logger.debug(f"이미 존재: {rcept_no}")
            return True

        # 문서 다운로드
        url = f"{DART_API_BASE}/document.xml"
        params = {
            'crtfc_key': self.api_key,
            'rcept_no': rcept_no,
        }

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"다운로드 실패 ({resp.status}): {rcept_no}")
                    return False

                content_type = resp.headers.get('Content-Type', '')

                # XML 에러 응답 체크
                if 'xml' in content_type or 'text' in content_type:
                    text = await resp.text()
                    if '<status>' in text:
                        logger.warning(f"API 오류 응답: {rcept_no}")
                        return False

                # ZIP 파일 저장
                content = await resp.read()

                if len(content) < 100:
                    logger.warning(f"파일이 너무 작음: {rcept_no}")
                    return False

                output_dir.mkdir(parents=True, exist_ok=True)

                with open(zip_path, 'wb') as f:
                    f.write(content)

                # ZIP 파일 검증 및 XML 개수 확인
                xml_count = 0
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        xml_count = sum(1 for n in zf.namelist() if n.endswith('.xml'))
                except zipfile.BadZipFile:
                    logger.warning(f"잘못된 ZIP 파일: {rcept_no}")
                    zip_path.unlink()
                    return False

                # 메타 파일 생성 (v2.0 스키마)
                meta = {
                    'rcept_no': rcept_no,
                    'corp_code': corp_code,
                    'corp_name': corp_name,
                    'stock_code': '',  # 목록에서 가져올 수 없음
                    'report_type': '',  # 파서에서 결정
                    'report_nm': '',
                    'rcept_dt': '',
                    'flr_nm': '',
                    'file_size': len(content),
                    'xml_count': xml_count,
                    'downloaded_at': datetime.now().isoformat(),
                    'schema_version': '2.0',
                }

                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                return True

        except Exception as e:
            logger.error(f"다운로드 오류 {rcept_no}: {e}")
            return False

    async def download_all(
        self,
        quarter: str,
        year: int,
        limit: Optional[int] = None,
        list_only: bool = False
    ) -> Dict:
        """전체 보고서 다운로드

        Args:
            quarter: 분기 (Q1, Q2, Q3, Q4)
            year: 연도
            limit: 최대 다운로드 개수 (테스트용)
            list_only: True면 목록만 조회

        Returns:
            다운로드 통계
        """
        logger.info(f"=== {quarter} {year} 보고서 다운로드 시작 ===")

        # 보고서 목록 조회
        reports = await self.get_report_list(quarter, year)
        self.stats['total'] = len(reports)

        if list_only:
            logger.info(f"목록 조회 완료: {len(reports)}건")
            for r in reports[:10]:
                logger.info(f"  - {r.get('corp_name')}: {r.get('report_nm')}")
            if len(reports) > 10:
                logger.info(f"  ... 외 {len(reports) - 10}건")
            return self.stats

        if limit:
            reports = reports[:limit]
            logger.info(f"다운로드 제한: {limit}건")

        # 저장 디렉토리
        output_dir = DATA_DIR / str(year) / quarter
        output_dir.mkdir(parents=True, exist_ok=True)

        # 다운로드 실행
        for i, report in enumerate(reports):
            if (i + 1) % 100 == 0:
                logger.info(f"진행: {i+1}/{len(reports)} ({(i+1)/len(reports)*100:.1f}%)")

            rcept_no = report.get('rcept_no')
            corp_code = report.get('corp_code')
            corp_name = report.get('corp_name')

            success = await self.download_report(rcept_no, corp_code, corp_name, output_dir)

            if success:
                self.stats['downloaded'] += 1
            else:
                self.stats['failed'] += 1

            await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"\n=== 다운로드 완료 ===")
        logger.info(f"총 보고서: {self.stats['total']}")
        logger.info(f"다운로드: {self.stats['downloaded']}")
        logger.info(f"실패: {self.stats['failed']}")
        logger.info(f"저장 위치: {output_dir}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description='DART 분기보고서 다운로드')
    parser.add_argument('--quarter', choices=['Q1', 'Q2', 'Q3', 'Q4'], required=True,
                        help='분기 (Q1=1분기, Q2=반기, Q3=3분기, Q4=사업보고서)')
    parser.add_argument('--year', type=int, required=True, help='연도')
    parser.add_argument('--limit', type=int, help='최대 다운로드 개수 (테스트용)')
    parser.add_argument('--list-only', action='store_true', help='목록만 조회')

    args = parser.parse_args()

    async with QuarterlyReportDownloader() as downloader:
        await downloader.download_all(
            quarter=args.quarter,
            year=args.year,
            limit=args.limit,
            list_only=args.list_only
        )


if __name__ == '__main__':
    asyncio.run(main())
