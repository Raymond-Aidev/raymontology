#!/usr/bin/env python3
"""
기존 CB 인수자 데이터에 법인/단체 기본정보 추가

- 로컬 ZIP 파일에서 XML 추출
- 대표이사, 업무집행자, 최대주주 정보 추출
- cb_subscribers 테이블 업데이트
"""
import asyncio
import asyncpg
import json
import logging
import re
import zipfile
import io
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """DB URL 반환"""
    url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
    if url.startswith('postgresql+asyncpg://'):
        url = url.replace('postgresql+asyncpg://', 'postgresql://')
    return url


def find_zip_file(corp_code: str, rcept_no: str) -> Optional[Path]:
    """ZIP 파일 경로 찾기"""
    base_path = Path(__file__).parent.parent / 'data' / 'dart'

    # batch_XXX 폴더들 탐색
    for batch_dir in base_path.glob('batch_*'):
        corp_dir = batch_dir / corp_code
        if not corp_dir.exists():
            continue

        # 연도별 폴더 탐색
        for year_dir in corp_dir.iterdir():
            if not year_dir.is_dir():
                continue

            zip_path = year_dir / f"{rcept_no}.zip"
            if zip_path.exists():
                return zip_path

    return None


def extract_xml_from_zip(zip_path: Path) -> Optional[str]:
    """ZIP에서 XML 추출"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
            if not xml_files:
                return None

            xml_bytes = zf.read(xml_files[0])

            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    return xml_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue
    except Exception as e:
        logger.error(f"ZIP 추출 실패 {zip_path}: {e}")
    return None


def extract_acode(content: str, acode: str) -> Optional[str]:
    """ACODE 속성으로 값 추출"""
    pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    return None


def parse_share(share_str: str) -> Optional[float]:
    """지분율 파싱"""
    if not share_str or share_str == '-':
        return None
    try:
        cleaned = re.sub(r'[^\d.]', '', share_str)
        if cleaned:
            return float(cleaned)
    except ValueError:
        pass
    return None


def extract_entity_info(content: str) -> Dict:
    """법인/단체 기본정보 추출"""
    result = {
        'representative_name': None,
        'representative_share': None,
        'gp_name': None,
        'gp_share': None,
        'largest_shareholder_name': None,
        'largest_shareholder_share': None,
    }

    # 대표이사(대표조합원) - BAS_NAM1
    bas_nam1 = extract_acode(content, 'BAS_NAM1')
    if bas_nam1 and bas_nam1 != '-' and len(bas_nam1) >= 2:
        result['representative_name'] = bas_nam1[:200]

    bas_rat1 = extract_acode(content, 'BAS_RAT1')
    if bas_rat1 and bas_rat1 != '-':
        result['representative_share'] = parse_share(bas_rat1)

    # 업무집행자(업무집행조합원) - BAS_NAM2
    bas_nam2 = extract_acode(content, 'BAS_NAM2')
    if bas_nam2 and bas_nam2 != '-' and len(bas_nam2) >= 2:
        result['gp_name'] = bas_nam2[:200]

    bas_rat2 = extract_acode(content, 'BAS_RAT2')
    if bas_rat2 and bas_rat2 != '-':
        result['gp_share'] = parse_share(bas_rat2)

    # 최대주주(최대출자자) - BAS_NAM3
    bas_nam3 = extract_acode(content, 'BAS_NAM3')
    if bas_nam3 and bas_nam3 != '-' and len(bas_nam3) >= 2:
        result['largest_shareholder_name'] = bas_nam3[:200]

    bas_rat3 = extract_acode(content, 'BAS_RAT3')
    if bas_rat3 and bas_rat3 != '-':
        result['largest_shareholder_share'] = parse_share(bas_rat3)

    return result


async def update_subscriber_entity_info(conn: asyncpg.Connection, subscriber_id: str, entity_info: Dict):
    """인수자 법인정보 업데이트"""
    await conn.execute("""
        UPDATE cb_subscribers
        SET representative_name = $2,
            representative_share = $3,
            gp_name = $4,
            gp_share = $5,
            largest_shareholder_name = $6,
            largest_shareholder_share = $7,
            updated_at = NOW()
        WHERE id = $1
    """,
        subscriber_id,
        entity_info.get('representative_name'),
        entity_info.get('representative_share'),
        entity_info.get('gp_name'),
        entity_info.get('gp_share'),
        entity_info.get('largest_shareholder_name'),
        entity_info.get('largest_shareholder_share'),
    )


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="CB 인수자 법인정보 업데이트")
    parser.add_argument("--corp-code", help="특정 회사만 처리 (예: 00366517)")
    parser.add_argument("--limit", type=int, default=1000, help="처리할 인수자 수")
    parser.add_argument("--dry-run", action="store_true", help="실제 업데이트 없이 테스트")

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("CB 인수자 법인정보 업데이트 시작")
    logger.info("=" * 80)

    db_url = get_db_url()
    conn = await asyncpg.connect(db_url)

    stats = {
        'total': 0,
        'updated': 0,
        'skipped': 0,
        'not_found': 0,
        'errors': 0
    }

    try:
        # 업데이트가 필요한 인수자 조회 (법인정보가 없는 것)
        query = """
            SELECT cs.id, cs.subscriber_name, cs.source_disclosure_id, c.corp_code
            FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE cs.representative_name IS NULL
              AND cs.gp_name IS NULL
              AND cs.largest_shareholder_name IS NULL
        """
        params = []

        if args.corp_code:
            query += " AND c.corp_code = $1"
            params.append(args.corp_code)

        query += f" LIMIT {args.limit}"

        subscribers = await conn.fetch(query, *params)
        logger.info(f"처리 대상 인수자: {len(subscribers)}명")

        # 공시별로 그룹화
        disclosure_map = {}
        for sub in subscribers:
            rcept_no = sub['source_disclosure_id']
            if rcept_no not in disclosure_map:
                disclosure_map[rcept_no] = {
                    'corp_code': sub['corp_code'],
                    'subscribers': []
                }
            disclosure_map[rcept_no]['subscribers'].append(sub)

        logger.info(f"공시 수: {len(disclosure_map)}건")

        for rcept_no, data in disclosure_map.items():
            corp_code = data['corp_code']
            subs = data['subscribers']

            # ZIP 파일 찾기
            zip_path = find_zip_file(corp_code, rcept_no)
            if not zip_path:
                logger.debug(f"ZIP 파일 없음: {corp_code}/{rcept_no}")
                stats['not_found'] += len(subs)
                continue

            # XML 추출
            content = extract_xml_from_zip(zip_path)
            if not content:
                logger.warning(f"XML 추출 실패: {zip_path}")
                stats['errors'] += len(subs)
                continue

            # 법인정보 추출
            entity_info = extract_entity_info(content)

            # 법인정보가 있는 경우에만 업데이트
            has_info = any([
                entity_info.get('representative_name'),
                entity_info.get('gp_name'),
                entity_info.get('largest_shareholder_name')
            ])

            if not has_info:
                stats['skipped'] += len(subs)
                continue

            # 각 인수자 업데이트
            for sub in subs:
                stats['total'] += 1

                if args.dry_run:
                    logger.info(f"[DRY-RUN] 업데이트 예정: {sub['subscriber_name']} -> {entity_info}")
                    stats['updated'] += 1
                else:
                    try:
                        await update_subscriber_entity_info(conn, sub['id'], entity_info)
                        stats['updated'] += 1
                    except Exception as e:
                        logger.error(f"업데이트 실패 {sub['id']}: {e}")
                        stats['errors'] += 1

            if stats['total'] % 50 == 0:
                logger.info(f"진행: {stats['total']}건 처리, {stats['updated']}건 업데이트")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("업데이트 완료")
        logger.info("=" * 80)
        logger.info(f"총 처리: {stats['total']}건")
        logger.info(f"업데이트: {stats['updated']}건")
        logger.info(f"건너뜀 (정보 없음): {stats['skipped']}건")
        logger.info(f"ZIP 없음: {stats['not_found']}건")
        logger.info(f"오류: {stats['errors']}건")

        # 업데이트 결과 확인
        if not args.dry_run:
            result = await conn.fetch("""
                SELECT subscriber_name, representative_name, gp_name, largest_shareholder_name
                FROM cb_subscribers
                WHERE representative_name IS NOT NULL
                   OR gp_name IS NOT NULL
                   OR largest_shareholder_name IS NOT NULL
                LIMIT 10
            """)

            if result:
                logger.info("\n업데이트된 샘플:")
                for row in result:
                    logger.info(f"  {row['subscriber_name']}: 대표={row['representative_name']}, GP={row['gp_name']}, 최대주주={row['largest_shareholder_name']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
