#!/usr/bin/env python3
"""
DART API를 사용하여 공시 XML 다운로드
"""
import asyncio
import aiohttp
import logging
import sys
from pathlib import Path
from typing import List, Dict
import zipfile
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = "1fd0cd12ae5260eafb7de3130ad91f16aa61911b"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


class DARTDownloader:
    """DART 공시 문서 다운로더"""

    def __init__(self, api_key: str, output_dir: Path):
        self.api_key = api_key
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            'total': 0,
            'downloaded': 0,
            'skipped': 0,
            'errors': 0
        }

    async def download_document(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str,
        corp_name: str
    ) -> bool:
        """개별 문서 다운로드"""
        try:
            # 이미 다운로드된 파일 체크
            output_file = self.output_dir / f"{rcept_no}.xml"
            if output_file.exists():
                self.stats['skipped'] += 1
                return True

            # DART API 호출
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            async with session.get(DART_DOCUMENT_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Failed to download {rcept_no}: HTTP {response.status}")
                    self.stats['errors'] += 1
                    return False

                # ZIP 파일로 저장
                content = await response.read()

                # ZIP 파일인지 확인
                if content[:2] != b'PK':
                    # ZIP이 아니면 에러 메시지일 수 있음
                    error_msg = content.decode('utf-8', errors='ignore')
                    if 'ERROR' in error_msg or 'RESULT' in error_msg:
                        logger.warning(f"API error for {rcept_no} ({corp_name}): {error_msg[:100]}")
                        self.stats['errors'] += 1
                        return False

                # ZIP 파일 저장
                with open(output_file, 'wb') as f:
                    f.write(content)

                self.stats['downloaded'] += 1
                return True

        except Exception as e:
            logger.error(f"Error downloading {rcept_no}: {e}")
            self.stats['errors'] += 1
            return False

    async def download_all(self, disclosures: List[Dict], batch_size: int = 10):
        """모든 문서 다운로드 (배치 처리)"""

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(disclosures), batch_size):
                batch = disclosures[i:i + batch_size]

                tasks = [
                    self.download_document(
                        session,
                        d['rcept_no'],
                        d['corp_name']
                    )
                    for d in batch
                ]

                await asyncio.gather(*tasks)

                self.stats['total'] = i + len(batch)

                # 진행상황 출력
                if self.stats['total'] % 100 == 0:
                    logger.info(
                        f"Progress: {self.stats['total']}/{len(disclosures)} - "
                        f"Downloaded: {self.stats['downloaded']}, "
                        f"Skipped: {self.stats['skipped']}, "
                        f"Errors: {self.stats['errors']}"
                    )

                # API rate limit 방지 (초당 10개 제한)
                await asyncio.sleep(1)


async def main():
    """메인 함수"""

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
            SELECT rcept_no, corp_name, rcept_dt
            FROM disclosures
            ORDER BY rcept_dt DESC
        """)

        logger.info(f"Total disclosures to download: {len(disclosures)}")

        # 다운로드 디렉토리
        output_dir = Path('/app/data/dart_xmls')

        # 다운로더 생성 및 실행
        downloader = DARTDownloader(DART_API_KEY, output_dir)

        await downloader.download_all([dict(d) for d in disclosures], batch_size=10)

        # 최종 통계
        logger.info("=" * 80)
        logger.info("Download Complete")
        logger.info("=" * 80)
        logger.info(f"Total processed: {downloader.stats['total']}")
        logger.info(f"Downloaded: {downloader.stats['downloaded']}")
        logger.info(f"Skipped (already exists): {downloader.stats['skipped']}")
        logger.info(f"Errors: {downloader.stats['errors']}")

        # 다운로드 성공률
        success_rate = (downloader.stats['downloaded'] + downloader.stats['skipped']) / downloader.stats['total'] * 100
        logger.info(f"Success rate: {success_rate:.1f}%")

        # Storage URL 업데이트
        logger.info("Updating storage paths in database...")
        await conn.execute("""
            UPDATE disclosures
            SET storage_url = '/app/data/dart_xmls/' || rcept_no || '.xml',
                storage_key = rcept_no || '.xml'
            WHERE rcept_no IN (
                SELECT rcept_no FROM disclosures
            )
        """)
        logger.info("Storage paths updated")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
