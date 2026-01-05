"""
손상된 ZIP 파일 재다운로드 스크립트

DART API를 사용하여 손상된 ZIP 파일을 재다운로드합니다.

사용법:
    python scripts/redownload_corrupted_zips.py [--dry-run]

환경변수:
    DART_API_KEY: DART API 키 (필수)
"""

import asyncio
import aiohttp
import json
import os
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', 'bbe7fee4ab8a79e62a1e65af20f2ad2a1b4eabe9')
DART_DOCUMENT_URL = 'https://opendart.fss.or.kr/api/document.xml'


async def download_document(session: aiohttp.ClientSession, rcept_no: str, save_path: Path) -> bool:
    """DART API로 문서 다운로드"""
    params = {
        'crtfc_key': DART_API_KEY,
        'rcept_no': rcept_no
    }

    try:
        async with session.get(DART_DOCUMENT_URL, params=params) as response:
            if response.status != 200:
                logger.error(f"HTTP {response.status} for {rcept_no}")
                return False

            content = await response.read()

            # ZIP 파일인지 확인 (매직 바이트)
            if not content[:4] == b'PK\x03\x04':
                # XML 에러 응답일 수 있음
                try:
                    text = content.decode('utf-8')
                    if '<result>' in text:
                        logger.error(f"API error for {rcept_no}: {text[:200]}")
                        return False
                except:
                    pass
                logger.error(f"Not a valid ZIP for {rcept_no}")
                return False

            # 백업 후 저장
            if save_path.exists():
                backup_path = save_path.with_suffix('.zip.bak')
                save_path.rename(backup_path)
                logger.info(f"Backed up old file to {backup_path}")

            save_path.write_bytes(content)
            logger.info(f"Downloaded {rcept_no} -> {save_path} ({len(content):,} bytes)")
            return True

    except Exception as e:
        logger.error(f"Download error for {rcept_no}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description='손상된 ZIP 파일 재다운로드')
    parser.add_argument('--dry-run', action='store_true', help='실제 다운로드 없이 목록만 확인')
    parser.add_argument('--input', default='/tmp/corrupted_zips.txt', help='손상된 ZIP 파일 목록')
    args = parser.parse_args()

    # 손상된 ZIP 목록 읽기
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    corrupted_zips = [line.strip() for line in input_path.read_text().strip().split('\n') if line.strip()]
    logger.info(f"Found {len(corrupted_zips)} corrupted ZIP files")

    # meta.json에서 rcept_no 추출
    download_tasks = []
    for zip_path_str in corrupted_zips:
        zip_path = Path(zip_path_str)
        meta_path = zip_path.with_name(zip_path.stem + '_meta.json')

        if not meta_path.exists():
            logger.warning(f"Meta file not found: {meta_path}")
            continue

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            rcept_no = meta.get('rcept_no')
            if rcept_no:
                download_tasks.append({
                    'rcept_no': rcept_no,
                    'zip_path': zip_path,
                    'corp_code': meta.get('corp_code'),
                    'report_nm': meta.get('report_nm', '')
                })
            else:
                logger.warning(f"No rcept_no in meta: {meta_path}")
        except Exception as e:
            logger.error(f"Error reading meta: {meta_path}: {e}")

    logger.info(f"Found {len(download_tasks)} files to redownload")

    if args.dry_run:
        logger.info("=== DRY RUN - No actual downloads ===")
        for task in download_tasks:
            logger.info(f"  {task['rcept_no']}: {task['report_nm']}")
        return

    # 다운로드 실행
    stats = {'success': 0, 'failed': 0}

    async with aiohttp.ClientSession() as session:
        for i, task in enumerate(download_tasks, 1):
            logger.info(f"[{i}/{len(download_tasks)}] Downloading {task['rcept_no']}...")

            success = await download_document(
                session,
                task['rcept_no'],
                task['zip_path']
            )

            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

            # API 호출 간 딜레이 (rate limiting 방지)
            await asyncio.sleep(0.5)

    logger.info("")
    logger.info("=== 재다운로드 완료 ===")
    logger.info(f"  성공: {stats['success']}건")
    logger.info(f"  실패: {stats['failed']}건")


if __name__ == '__main__':
    asyncio.run(main())
