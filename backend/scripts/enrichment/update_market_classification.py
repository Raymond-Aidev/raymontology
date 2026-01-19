#!/usr/bin/env python3
"""
KOSPI/KOSDAQ 시장구분 업데이트
- DART API의 corp_code.xml에서 시장구분 정보 수집
- companies 테이블의 market 필드 업데이트
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = "1fd0cd12ae5260eafb7de3130ad91f16aa61911b"
CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"


async def download_corp_code_xml():
    """DART API에서 corp_code.xml 다운로드"""
    logger.info("DART API에서 corp_code.xml 다운로드 중...")

    params = {'crtfc_key': DART_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(CORP_CODE_URL, params=params) as response:
            if response.status != 200:
                raise Exception(f"DART API 호출 실패: HTTP {response.status}")

            content = await response.read()

            # ZIP 파일 압축 해제
            import zipfile
            import io

            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                if not xml_files:
                    raise Exception("ZIP 파일에 XML이 없습니다")

                xml_content = zf.read(xml_files[0])

                # 인코딩 처리
                try:
                    return xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    return xml_content.decode('euc-kr', errors='ignore')


def parse_corp_code_xml(xml_content: str) -> dict:
    """corp_code.xml 파싱하여 회사별 시장구분 매핑"""
    logger.info("corp_code.xml 파싱 중...")

    root = ET.fromstring(xml_content)
    corp_map = {}

    for company in root.findall('.//list'):
        corp_code_elem = company.find('corp_code')
        stock_code_elem = company.find('stock_code')
        corp_name_elem = company.find('corp_name')

        # stock_code에서 시장구분 추출
        # 6자리 숫자 = 상장, 빈값 = 비상장
        corp_code = corp_code_elem.text if corp_code_elem is not None else None
        stock_code = stock_code_elem.text if stock_code_elem is not None else None
        corp_name = corp_name_elem.text if corp_name_elem is not None else None

        if corp_code and stock_code and len(stock_code.strip()) == 6:
            # KOSPI: 앞자리가 0으로 시작하거나 005~009로 시작
            # KOSDAQ: 그 외
            first_three = stock_code[:3]

            if first_three in ['000', '001', '002', '003', '004', '005', '006', '007', '008', '009']:
                market = 'KOSPI'
            else:
                market = 'KOSDAQ'

            corp_map[corp_code] = {
                'stock_code': stock_code,
                'corp_name': corp_name,
                'market': market
            }

    logger.info(f"파싱 완료: {len(corp_map)}개 상장 기업")

    # 통계
    kospi_count = sum(1 for v in corp_map.values() if v['market'] == 'KOSPI')
    kosdaq_count = sum(1 for v in corp_map.values() if v['market'] == 'KOSDAQ')
    logger.info(f"  KOSPI: {kospi_count}개")
    logger.info(f"  KOSDAQ: {kosdaq_count}개")

    return corp_map


async def update_companies_market(corp_map: dict):
    """companies 테이블의 market 필드 업데이트"""
    logger.info("companies 테이블 업데이트 중...")

    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 현재 상태 확인
        before_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE market = 'KOSPI') as kospi,
                COUNT(*) FILTER (WHERE market = 'KOSDAQ') as kosdaq,
                COUNT(*) FILTER (WHERE market IS NULL OR market NOT IN ('KOSPI', 'KOSDAQ')) as no_market
            FROM companies
        """)

        logger.info(f"\n업데이트 전:")
        logger.info(f"  총 회사: {before_stats['total']:,}")
        logger.info(f"  KOSPI: {before_stats['kospi']:,}")
        logger.info(f"  KOSDAQ: {before_stats['kosdaq']:,}")
        logger.info(f"  미지정: {before_stats['no_market']:,}")

        # 업데이트
        updated = 0
        not_found = 0

        for corp_code, info in corp_map.items():
            result = await conn.execute("""
                UPDATE companies
                SET market = $1,
                    updated_at = NOW()
                WHERE corp_code = $2
            """, info['market'], corp_code)

            # "UPDATE N" 형식에서 숫자 추출
            rows_updated = int(result.split()[1]) if result else 0

            if rows_updated > 0:
                updated += rows_updated
            else:
                not_found += 1

        logger.info(f"\n업데이트 결과:")
        logger.info(f"  업데이트됨: {updated:,}개")
        logger.info(f"  DB에 없음: {not_found:,}개")

        # 업데이트 후 상태 확인
        after_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE market = 'KOSPI') as kospi,
                COUNT(*) FILTER (WHERE market = 'KOSDAQ') as kosdaq,
                COUNT(*) FILTER (WHERE market IS NULL OR market NOT IN ('KOSPI', 'KOSDAQ')) as no_market
            FROM companies
        """)

        logger.info(f"\n업데이트 후:")
        logger.info(f"  총 회사: {after_stats['total']:,}")
        logger.info(f"  KOSPI: {after_stats['kospi']:,}")
        logger.info(f"  KOSDAQ: {after_stats['kosdaq']:,}")
        logger.info(f"  미지정: {after_stats['no_market']:,}")

        # 샘플 확인
        samples = await conn.fetch("""
            SELECT name, ticker, market, corp_code
            FROM companies
            WHERE market IN ('KOSPI', 'KOSDAQ')
            ORDER BY ticker
            LIMIT 10
        """)

        logger.info(f"\n시장구분 업데이트된 샘플:")
        for row in samples:
            logger.info(f"  {row['name']:20s} (티커: {row['ticker']}, 시장: {row['market']})")

    finally:
        await conn.close()


async def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("KOSPI/KOSDAQ 시장구분 업데이트")
    logger.info("=" * 80)

    try:
        # 1. DART API에서 corp_code.xml 다운로드
        xml_content = await download_corp_code_xml()

        # 2. XML 파싱하여 시장구분 매핑 생성
        corp_map = parse_corp_code_xml(xml_content)

        # 3. companies 테이블 업데이트
        await update_companies_market(corp_map)

        logger.info("\n" + "=" * 80)
        logger.info("완료")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
