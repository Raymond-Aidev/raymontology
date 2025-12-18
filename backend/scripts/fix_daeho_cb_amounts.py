#!/usr/bin/env python3
"""
대호에이엘 CB 인수자 인수금액 수정

대호에이엘의 CB 인수자 금액이 모두 NULL인 문제를 수정
로컬 DART 공시 파일에서 직접 인수금액을 추출하여 업데이트
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import glob
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'
CORP_CODE = '00428729'  # 대호에이엘


def _parse_amount(amount_str):
    """금액 파싱"""
    if not amount_str or amount_str == '-':
        return None
    try:
        cleaned = re.sub(r'[^\d]', '', amount_str)
        if cleaned:
            return int(cleaned)
    except ValueError:
        pass
    return None


def normalize_name(name: str) -> str:
    """이름 정규화 - 모든 공백과 특수문자 제거하여 키로 사용"""
    if not name:
        return ""
    name = re.sub(r'&[^;]+;', '', name)  # &cr; 등 제거
    name = re.sub(r'\s+', '', name)  # 공백 제거
    name = re.sub(r'[()（）]', '', name)  # 괄호 제거
    return name.strip()


def load_xml_from_zip(zip_path: str) -> str:
    """ZIP 파일에서 XML 내용 로드"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.xml'):
                    content = zf.read(name)
                    # 여러 인코딩 시도
                    for encoding in ['utf-8', 'euc-kr', 'cp949']:
                        try:
                            return content.decode(encoding)
                        except UnicodeDecodeError:
                            continue
    except Exception as e:
        logger.debug(f"ZIP 로드 실패 {zip_path}: {e}")
    return None


def extract_subscribers_from_xml(content: str) -> dict:
    """XML에서 인수자별 금액 추출"""
    subscribers = {}

    # TR 단위로 ISSU_NM과 ISSU_AMT 찾기
    tr_pattern = r'<TR[^>]*>(.*?)</TR>'
    tr_matches = re.findall(tr_pattern, content, re.DOTALL | re.IGNORECASE)

    for tr_content in tr_matches:
        # ISSU_NM 찾기 (여러 패턴 지원)
        name_match = re.search(r'<T[EU][^>]*ACODE="ISSU_NM"[^>]*>(.*?)</T[EU]>', tr_content, re.DOTALL | re.IGNORECASE)
        if not name_match:
            continue

        # 이름 정리 (HTML 태그, &cr; 제거)
        name_raw = name_match.group(1)
        name = re.sub(r'<[^>]+>', '', name_raw)
        name = re.sub(r'&[^;]+;', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if not name or name == '-' or len(name) < 2:
            continue

        # 금액 추출
        amt_match = re.search(r'<T[EU][^>]*ACODE="ISSU_AMT"[^>]*>([^<]*)</T[EU]>', tr_content, re.IGNORECASE)
        if amt_match:
            amount = _parse_amount(amt_match.group(1))
            if amount:
                name_key = normalize_name(name)
                subscribers[name_key] = {
                    'name': name,
                    'amount': amount
                }
                logger.debug(f"  발견: {name} = {amount:,}원")

    return subscribers


async def main():
    logger.info("=" * 80)
    logger.info(f"대호에이엘(corp_code={CORP_CODE}) CB 인수자 인수금액 수정")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        # 1. 현재 상태 확인
        zero_count = await conn.fetchval("""
            SELECT COUNT(*) FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE c.corp_code = $1
              AND (cs.subscription_amount IS NULL OR cs.subscription_amount = 0)
        """, CORP_CODE)

        total_count = await conn.fetchval("""
            SELECT COUNT(*) FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE c.corp_code = $1
        """, CORP_CODE)

        logger.info(f"수정 전: 인수금액 NULL/0원: {zero_count}건 / 전체 {total_count}건")

        if zero_count == 0:
            logger.info("수정할 인수자가 없습니다")
            return

        # 2. 전환사채권발행결정 공시 파일 찾기 (2022-2025년)
        all_zips = []
        for year in ['2022', '2023', '2024', '2025']:
            zip_pattern = f"{DART_DATA_DIR}/**/{CORP_CODE}/{year}/*.zip"
            all_zips.extend(glob.glob(zip_pattern, recursive=True))
        logger.info(f"발견된 ZIP 파일: {len(all_zips)}개")

        # 메타 파일로 전환사채권발행결정 공시만 필터링
        cb_disclosures = []
        for zip_path in all_zips:
            meta_path = zip_path.replace('.zip', '_meta.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_content = f.read()
                    if '전환사채권발행결정' in meta_content or '전환사채발행결정' in meta_content:
                        # rcept_no 추출
                        rcept_match = re.search(r'"rcept_no":\s*"(\d+)"', meta_content)
                        if rcept_match:
                            cb_disclosures.append({
                                'zip_path': zip_path,
                                'rcept_no': rcept_match.group(1)
                            })

        logger.info(f"전환사채권발행결정 공시: {len(cb_disclosures)}건")

        # 3. 각 공시에서 인수자 정보 추출
        all_subscribers = {}
        for disc in cb_disclosures:
            logger.info(f"\n처리 중: {disc['rcept_no']}")

            xml_content = load_xml_from_zip(disc['zip_path'])
            if not xml_content:
                logger.warning(f"  XML 로드 실패")
                continue

            extracted = extract_subscribers_from_xml(xml_content)
            logger.info(f"  발견된 인수자: {len(extracted)}명")

            for key, data in extracted.items():
                if key not in all_subscribers or data['amount'] > all_subscribers[key]['amount']:
                    all_subscribers[key] = data

        logger.info(f"\n총 발견된 고유 인수자: {len(all_subscribers)}명")
        for key, data in all_subscribers.items():
            logger.info(f"  - {data['name']}: {data['amount']:,}원")

        # 4. DB 인수자 목록 조회
        db_subscribers = await conn.fetch("""
            SELECT cs.id, cs.subscriber_name
            FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE c.corp_code = $1
              AND (cs.subscription_amount IS NULL OR cs.subscription_amount = 0)
        """, CORP_CODE)

        logger.info(f"\nDB에서 금액 없는 인수자: {len(db_subscribers)}명")

        # 5. 매칭 및 업데이트
        stats = {'updated': 0, 'not_found': 0}

        for row in db_subscribers:
            sub_id = row['id']
            sub_name = row['subscriber_name']
            sub_key = normalize_name(sub_name)

            # 정확히 일치하는 것 찾기
            amount = None
            if sub_key in all_subscribers:
                amount = all_subscribers[sub_key]['amount']
            else:
                # 부분 일치 시도
                for ext_key, ext_data in all_subscribers.items():
                    if sub_key in ext_key or ext_key in sub_key:
                        amount = ext_data['amount']
                        logger.info(f"  부분 매칭: '{sub_name}' ↔ '{ext_data['name']}'")
                        break

            if amount:
                await conn.execute("""
                    UPDATE cb_subscribers
                    SET subscription_amount = $1, updated_at = NOW()
                    WHERE id = $2
                """, float(amount), sub_id)
                stats['updated'] += 1
                logger.info(f"  업데이트: {sub_name} = {amount:,}원")
            else:
                stats['not_found'] += 1
                logger.warning(f"  매칭 실패: {sub_name}")

        # 6. 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("수정 완료")
        logger.info("=" * 80)
        logger.info(f"업데이트: {stats['updated']}건")
        logger.info(f"매칭 실패: {stats['not_found']}건")

        # 최종 현황
        final_zero = await conn.fetchval("""
            SELECT COUNT(*) FROM cb_subscribers cs
            JOIN convertible_bonds cb ON cs.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE c.corp_code = $1
              AND (cs.subscription_amount IS NULL OR cs.subscription_amount = 0)
        """, CORP_CODE)

        logger.info(f"\n수정 후: 인수금액 NULL/0원: {final_zero}건 / 전체 {total_count}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
