#!/usr/bin/env python3
"""
누락된 상장기업 공시 데이터 다운로드

507개 상장기업의 DART 데이터가 다운로드되지 않아
임원, CB, 주주 등 데이터가 없는 상태
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')

# DART API URLs
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


async def get_missing_companies(conn) -> List[Dict]:
    """다운로드되지 않은 상장기업 목록 조회"""
    # 다운로드된 corp_code 목록 가져오기
    downloaded = set()
    for batch_dir in DART_DATA_DIR.glob('batch_*'):
        for corp_dir in batch_dir.iterdir():
            if corp_dir.is_dir():
                downloaded.add(corp_dir.name)

    logger.info(f"다운로드된 기업: {len(downloaded)}개")

    # 상장기업 목록 조회
    rows = await conn.fetch("""
        SELECT id, corp_code, name, ticker, market
        FROM companies
        WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX')
          AND corp_code IS NOT NULL
        ORDER BY market, name
    """)

    missing = []
    for row in rows:
        if row['corp_code'] not in downloaded:
            missing.append({
                'id': str(row['id']),
                'corp_code': row['corp_code'],
                'name': row['name'],
                'ticker': row['ticker'],
                'market': row['market']
            })

    logger.info(f"누락된 기업: {len(missing)}개")
    return missing


async def fetch_disclosure_list(session: aiohttp.ClientSession, corp_code: str,
                                 bgn_de: str = '20220101', end_de: str = None) -> List[Dict]:
    """DART API로 공시 목록 조회"""
    if not end_de:
        end_de = datetime.now().strftime('%Y%m%d')

    params = {
        'crtfc_key': DART_API_KEY,
        'corp_code': corp_code,
        'bgn_de': bgn_de,
        'end_de': end_de,
        'page_count': 100
    }

    all_disclosures = []
    page_no = 1

    while True:
        params['page_no'] = page_no
        try:
            async with session.get(DART_LIST_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {corp_code}")
                    break

                data = await response.json()

                if data.get('status') != '000':
                    # 013: 조회된 데이터 없음 (정상적인 상황)
                    if data.get('status') == '013':
                        break
                    logger.warning(f"API error for {corp_code}: {data.get('message')}")
                    break

                disclosures = data.get('list', [])
                if not disclosures:
                    break

                all_disclosures.extend(disclosures)

                # 다음 페이지 확인
                total_page = data.get('total_page', 1)
                if page_no >= total_page:
                    break
                page_no += 1

                await asyncio.sleep(0.1)  # Rate limiting

        except Exception as e:
            logger.error(f"Error fetching list for {corp_code}: {e}")
            break

    return all_disclosures


async def download_document(session: aiohttp.ClientSession, rcept_no: str,
                            output_path: Path) -> bool:
    """공시 문서 다운로드"""
    if output_path.exists():
        return True

    params = {
        'crtfc_key': DART_API_KEY,
        'rcept_no': rcept_no
    }

    try:
        async with session.get(DART_DOCUMENT_URL, params=params) as response:
            if response.status != 200:
                return False

            content = await response.read()

            # ZIP 파일인지 확인
            if content[:2] != b'PK':
                return False

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(content)

            return True

    except Exception as e:
        logger.debug(f"Error downloading {rcept_no}: {e}")
        return False


async def process_company(session: aiohttp.ClientSession, conn, company: Dict,
                          batch_dir: Path) -> Dict:
    """단일 기업 처리"""
    corp_code = company['corp_code']
    name = company['name']

    logger.info(f"처리 중: {name} ({corp_code})")

    # 공시 목록 조회
    disclosures = await fetch_disclosure_list(session, corp_code)

    if not disclosures:
        logger.info(f"  → 공시 없음: {name}")
        return {'corp_code': corp_code, 'name': name, 'disclosures': 0, 'downloaded': 0}

    # 기업 디렉토리 생성
    corp_dir = batch_dir / corp_code
    corp_dir.mkdir(parents=True, exist_ok=True)

    # 공시 다운로드
    downloaded = 0
    for disc in disclosures:
        rcept_no = disc['rcept_no']
        rcept_dt = disc['rcept_dt'][:4]  # 연도

        year_dir = corp_dir / rcept_dt
        year_dir.mkdir(exist_ok=True)

        output_path = year_dir / f"{rcept_no}.zip"

        if await download_document(session, rcept_no, output_path):
            downloaded += 1

        # 메타데이터 저장
        meta_path = year_dir / f"{rcept_no}_meta.json"
        if not meta_path.exists():
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(disc, f, ensure_ascii=False, indent=2)

        await asyncio.sleep(0.05)  # Rate limiting

    # DB에 공시 정보 저장
    for disc in disclosures:
        try:
            await conn.execute("""
                INSERT INTO disclosures (corp_code, rcept_no, rcept_dt, report_nm, flr_nm)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (rcept_no) DO NOTHING
            """, corp_code, disc['rcept_no'], disc['rcept_dt'],
                disc.get('report_nm', ''), disc.get('flr_nm', ''))
        except Exception as e:
            logger.debug(f"DB insert error: {e}")

    logger.info(f"  → 완료: {downloaded}/{len(disclosures)}건 다운로드")

    return {
        'corp_code': corp_code,
        'name': name,
        'disclosures': len(disclosures),
        'downloaded': downloaded
    }


async def main():
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("누락된 상장기업 공시 데이터 다운로드 시작")
    logger.info("=" * 60)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 누락된 기업 목록 조회
        missing = await get_missing_companies(conn)

        if not missing:
            logger.info("누락된 기업이 없습니다.")
            return

        # 배치 디렉토리 생성 (batch_missing)
        batch_dir = DART_DATA_DIR / 'batch_missing'
        batch_dir.mkdir(parents=True, exist_ok=True)

        # 다운로드 실행
        results = []

        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(missing):
                result = await process_company(session, conn, company, batch_dir)
                results.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(f"진행: {i + 1}/{len(missing)}개 기업 처리됨")

                await asyncio.sleep(0.2)  # Rate limiting

        # 결과 요약
        total_disclosures = sum(r['disclosures'] for r in results)
        total_downloaded = sum(r['downloaded'] for r in results)
        companies_with_data = len([r for r in results if r['disclosures'] > 0])

        logger.info("=" * 60)
        logger.info("완료!")
        logger.info(f"처리된 기업: {len(results)}개")
        logger.info(f"공시 있는 기업: {companies_with_data}개")
        logger.info(f"총 공시 수: {total_disclosures}건")
        logger.info(f"다운로드: {total_downloaded}건")
        logger.info("=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
