#!/usr/bin/env python3
"""
Priority 3-2: CB issue_date 739건 보강
공시 원문에서 발행일/납입일 추출
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import re
import zipfile
import io
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class CBDateEnricher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {'processed': 0, 'updated': 0, 'errors': 0}

    async def download_disclosure(self, session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
        """공시 XML 다운로드"""
        try:
            params = {'crtfc_key': self.api_key, 'rcept_no': rcept_no}
            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as r:
                if r.status == 200:
                    content = await r.read()
                    try:
                        with zipfile.ZipFile(io.BytesIO(content)) as zf:
                            for name in zf.namelist():
                                if name.endswith('.xml'):
                                    xml_bytes = zf.read(name)
                                    for enc in ['euc-kr', 'utf-8', 'cp949']:
                                        try:
                                            return xml_bytes.decode(enc)
                                        except:
                                            continue
                    except zipfile.BadZipFile:
                        for enc in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                return content.decode(enc)
                            except:
                                continue
        except Exception as e:
            logger.debug(f"다운로드 실패 {rcept_no}: {e}")
        return None

    def parse_dates(self, xml_content: str) -> dict:
        """발행일/납입일/만기일 파싱"""
        result = {}

        # 납입일 (발행일)
        patterns = [
            r'납입일[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
            r'발행일[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
            r'AUNIT="IO3_SBSCRP_DT"[^>]*>(\d{4})[년.\-/]?(\d{1,2})[월.\-/]?(\d{1,2})',
            r'>(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일[^<]*납입',
        ]
        for pattern in patterns:
            m = re.search(pattern, xml_content, re.IGNORECASE)
            if m:
                try:
                    result['issue_date'] = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    break
                except:
                    pass

        # 만기일
        patterns = [
            r'만기일[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
            r'상환일[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
            r'AUNIT="IO3_MTRT_DT"[^>]*>(\d{4})[년.\-/]?(\d{1,2})[월.\-/]?(\d{1,2})',
        ]
        for pattern in patterns:
            m = re.search(pattern, xml_content, re.IGNORECASE)
            if m:
                try:
                    result['maturity_date'] = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    break
                except:
                    pass

        # 전환가액
        patterns = [
            r'전환가액[^<]*[:\s]*([0-9,]+)\s*원',
            r'AUNIT="IO3_CNVRSN_PRC"[^>]*>([0-9,]+)',
        ]
        for pattern in patterns:
            m = re.search(pattern, xml_content, re.IGNORECASE)
            if m:
                try:
                    result['conversion_price'] = int(m.group(1).replace(',', ''))
                    break
                except:
                    pass

        return result

    async def enrich_cb(self, session: aiohttp.ClientSession, conn: asyncpg.Connection, cb: dict) -> bool:
        """CB 데이터 보강"""
        rcept_no = cb.get('source_disclosure_id')
        if not rcept_no:
            return False

        xml = await self.download_disclosure(session, rcept_no)
        if not xml:
            return False

        dates = self.parse_dates(xml)
        if not dates:
            return False

        try:
            update_parts = []
            params = []
            param_idx = 1

            if dates.get('issue_date'):
                update_parts.append(f"issue_date = ${param_idx}")
                params.append(dates['issue_date'])
                param_idx += 1

            if dates.get('maturity_date'):
                update_parts.append(f"maturity_date = ${param_idx}")
                params.append(dates['maturity_date'])
                param_idx += 1

            if dates.get('conversion_price') and not cb.get('conversion_price'):
                update_parts.append(f"conversion_price = ${param_idx}")
                params.append(dates['conversion_price'])
                param_idx += 1

            if not update_parts:
                return False

            update_parts.append("updated_at = NOW()")
            params.append(cb['id'])

            await conn.execute(f"""
                UPDATE convertible_bonds
                SET {', '.join(update_parts)}
                WHERE id = ${param_idx}
            """, *params)

            self.stats['updated'] += 1
            return True

        except Exception as e:
            logger.debug(f"업데이트 실패 {cb['id']}: {e}")
            self.stats['errors'] += 1
            return False


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("CB issue_date 보강 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)
    enricher = CBDateEnricher(DART_API_KEY)

    try:
        # issue_date가 없는 CB 조회
        cbs = await conn.fetch("""
            SELECT id, source_disclosure_id, conversion_price
            FROM convertible_bonds
            WHERE issue_date IS NULL
            AND source_disclosure_id IS NOT NULL
            LIMIT $1
        """, args.limit)
        logger.info(f"보강 대상 CB: {len(cbs)}개")

        async with aiohttp.ClientSession() as session:
            for i, cb in enumerate(cbs):
                await enricher.enrich_cb(session, conn, dict(cb))
                enricher.stats['processed'] += 1

                if (i + 1) % 50 == 0:
                    logger.info(f"진행: {i+1}/{len(cbs)} - 업데이트: {enricher.stats['updated']}")

                await asyncio.sleep(0.5)

        # 결과
        logger.info("\n" + "=" * 80)
        logger.info("CB 보강 완료")
        logger.info(f"처리: {enricher.stats['processed']}개")
        logger.info(f"업데이트: {enricher.stats['updated']}개")
        logger.info(f"오류: {enricher.stats['errors']}개")

        # 현재 상태
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(issue_date) as has_issue_date,
                COUNT(maturity_date) as has_maturity_date,
                COUNT(conversion_price) as has_conv_price
            FROM convertible_bonds
        """)
        logger.info(f"\nCB 현황: 총 {stats['total']:,}개")
        logger.info(f"  issue_date: {stats['has_issue_date']:,}개 ({100*stats['has_issue_date']/stats['total']:.1f}%)")
        logger.info(f"  maturity_date: {stats['has_maturity_date']:,}개")
        logger.info(f"  conversion_price: {stats['has_conv_price']:,}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
