#!/usr/bin/env python3
"""
전환사채 발행결정 공시 재처리 (로컬 파일 기반)

2022년 이후 '전환사채 발행결정' 공시를 로컬 ZIP 파일에서 재파싱하여
CB 발행 정보와 인수자 정보를 업데이트
"""
import asyncio
import asyncpg
import json
import logging
import os
import re
import zipfile
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'
CB_JSON_PATH = '/Users/jaejoonpark/raymontology/backend/data/cb_disclosures_by_company_full.json'

# 상수
MAX_BOND_NAME_LENGTH = 200
MAX_SUBSCRIBER_NAME_LENGTH = 500
MAX_RELATIONSHIP_LENGTH = 200
MAX_RATIONALE_LENGTH = 500


def _parse_amount(amount_str: str) -> Optional[int]:
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


def _parse_korean_date(date_str: str) -> Optional[datetime]:
    """한국어 날짜 파싱"""
    if not date_str or date_str == '-':
        return None
    try:
        match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?', date_str)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 2000 <= y <= 2040 and 1 <= m <= 12 and 1 <= d <= 31:
                return datetime(y, m, d).date()
    except ValueError:
        pass
    return None


def _extract_acode(content: str, acode: str) -> Optional[str]:
    """ACODE 속성으로 값 추출"""
    # 단순 패턴
    pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
    match = re.search(pattern, content)
    if match and match.group(1).strip():
        return match.group(1).strip()

    # 중첩 태그 패턴
    pattern2 = rf'<TE[^>]*ACODE="{acode}"[^>]*>(.*?)</TE>'
    match2 = re.search(pattern2, content, re.DOTALL)
    if match2:
        text = re.sub(r'<[^>]+>', '', match2.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            return text
    return None


def _extract_aunit(content: str, aunit: str) -> Optional[str]:
    """AUNIT 속성으로 값 추출"""
    pattern = rf'<TU[^>]*AUNIT="{aunit}"[^>]*>([^<]*)</TU>'
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    return None


def normalize_name(name: str) -> str:
    """이름 정규화"""
    if not name:
        return ""
    name = re.sub(r'&[^;]+;', '', name)
    name = re.sub(r'\s+', '', name)
    return name.strip()


def parse_cb_info(content: str, disclosure: Dict) -> Optional[Dict]:
    """CB 발행 정보 파싱"""
    result = {
        'bond_name': None,
        'bond_type': 'CB',
        'issue_date': None,
        'maturity_date': None,
        'issue_amount': None,
        'interest_rate': None,
        'conversion_price': None,
        'conversion_start_date': None,
        'conversion_end_date': None,
        'use_of_proceeds': None,
        'source_disclosure_id': disclosure.get('rcept_no'),
        'source_date': disclosure.get('rcept_dt')
    }

    # 채권 유형
    report_nm = disclosure.get('report_nm', '')
    if '신주인수권부사채' in report_nm or 'BW' in report_nm:
        result['bond_type'] = 'BW'
    elif '교환사채' in report_nm or 'EB' in report_nm:
        result['bond_type'] = 'EB'

    # 사채종류 + 회차
    pl_knd = _extract_acode(content, 'PL_KND')
    seq_no = _extract_acode(content, 'SEQ_NO')
    if pl_knd:
        bond_name = f"제{seq_no}회 {pl_knd}" if seq_no and seq_no != '-' else pl_knd
        result['bond_name'] = bond_name[:MAX_BOND_NAME_LENGTH]
    else:
        result['bond_name'] = '전환사채'

    # 권면총액
    result['issue_amount'] = _parse_amount(_extract_acode(content, 'DNM_SUM'))

    # 표면이율
    prft_rate = _extract_acode(content, 'PRFT_RATE')
    if prft_rate and prft_rate != '-':
        try:
            result['interest_rate'] = float(prft_rate)
        except ValueError:
            pass

    # 전환가액
    result['conversion_price'] = _parse_amount(_extract_acode(content, 'EXE_PRC'))

    # 만기일
    result['maturity_date'] = _parse_korean_date(_extract_aunit(content, 'EXP_DT'))

    # 납입일/발행일
    pym_dt = _extract_aunit(content, 'PYM_DT')
    sbsc_dt = _extract_aunit(content, 'SBSC_DT')
    result['issue_date'] = _parse_korean_date(pym_dt) or _parse_korean_date(sbsc_dt)

    # 전환청구기간
    result['conversion_start_date'] = _parse_korean_date(_extract_aunit(content, 'SB_BGN_DT'))
    result['conversion_end_date'] = _parse_korean_date(_extract_aunit(content, 'SB_END_DT'))

    # 자금사용목적
    fnd_use = _extract_acode(content, 'FND_USE1')
    if not fnd_use or fnd_use == '-':
        fnd_use = _extract_aunit(content, 'FND1_PPS')
    if fnd_use and fnd_use != '-':
        result['use_of_proceeds'] = fnd_use[:500]

    # Fallback
    if not result['issue_amount']:
        patterns = [r'권면\s*(?:총액|금액)[^\d]*([0-9,]+)', r'발행\s*(?:총액|금액)[^\d]*([0-9,]+)']
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                result['issue_amount'] = _parse_amount(match.group(1))
                if result['issue_amount']:
                    break

    return result if result['issue_amount'] else None


def parse_subscribers(content: str, disclosure: Dict) -> List[Dict]:
    """인수자 정보 파싱 - 모든 인수자와 금액 추출"""
    subscribers = []
    rcept_no = disclosure.get('rcept_no')
    seen_keys = set()

    # TR 단위로 ISSU_NM과 ISSU_AMT 추출
    tr_pattern = r'<TR[^>]*>(.*?)</TR>'
    tr_matches = re.findall(tr_pattern, content, re.DOTALL | re.IGNORECASE)

    for tr_content in tr_matches:
        name_match = re.search(r'<TE[^>]*ACODE="ISSU_NM"[^>]*>(.*?)</TE>', tr_content, re.DOTALL | re.IGNORECASE)
        if not name_match:
            continue

        # 이름 추출
        name_raw = name_match.group(1)
        name = re.sub(r'<[^>]+>', '', name_raw)
        name = re.sub(r'&[^;]+;', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if not name or name == '-' or len(name) < 2:
            continue

        # 중복 체크
        name_key = normalize_name(name)
        if name_key in seen_keys:
            continue
        seen_keys.add(name_key)

        # 금액 추출
        amt_match = re.search(r'<TE[^>]*ACODE="ISSU_AMT"[^>]*>([^<]*)</TE>', tr_content, re.IGNORECASE)
        amount = None
        if amt_match:
            amount = _parse_amount(amt_match.group(1))

        # 관계 추출
        rlt_match = re.search(r'<TE[^>]*ACODE="RLT"[^>]*>([^<]*)</TE>', tr_content, re.IGNORECASE)
        relationship = None
        if rlt_match and rlt_match.group(1).strip() != '-':
            relationship = rlt_match.group(1).strip()[:MAX_RELATIONSHIP_LENGTH]

        subscribers.append({
            'subscriber_name': name[:MAX_SUBSCRIBER_NAME_LENGTH],
            'relationship_to_company': relationship,
            'subscription_amount': amount,
            'is_related_party': 'Y' if relationship else 'N',
            'source_disclosure_id': rcept_no,
        })

    # 첫 번째 인수자에 추가 정보
    if subscribers:
        rlt = _extract_acode(content, 'RLT')
        issu_slt = _extract_acode(content, 'ISSU_SLT')
        if rlt and rlt != '-' and not subscribers[0].get('relationship_to_company'):
            subscribers[0]['relationship_to_company'] = rlt[:MAX_RELATIONSHIP_LENGTH]
            subscribers[0]['is_related_party'] = 'Y'
        if issu_slt and issu_slt != '-':
            subscribers[0]['selection_rationale'] = issu_slt[:MAX_RATIONALE_LENGTH]

    return subscribers


def load_xml_from_zip(zip_path: str) -> Optional[str]:
    """ZIP 파일에서 XML 로드"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.xml'):
                    content = zf.read(name)
                    try:
                        return content.decode('utf-8')
                    except:
                        return content.decode('euc-kr', errors='ignore')
    except Exception as e:
        logger.debug(f"ZIP 로드 실패: {e}")
    return None


async def main():
    logger.info("=" * 80)
    logger.info("전환사채 발행결정 공시 재처리 시작")
    logger.info("=" * 80)

    # CB 공시 목록 로드
    with open(CB_JSON_PATH, 'r', encoding='utf-8') as f:
        all_disclosures = json.load(f)

    # 2022년 이후 '전환사채 발행결정' 필터링
    cb_disclosures = [d for d in all_disclosures
                      if '전환사채' in d.get('report_nm', '')
                      and '발행결정' in d.get('report_nm', '')
                      and d.get('rcept_dt', '0') >= '20220101']

    logger.info(f"대상 공시: {len(cb_disclosures)}건")

    conn = await asyncpg.connect(DB_URL)

    try:
        # 회사 캐시 로드
        rows = await conn.fetch("SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL")
        company_cache = {r['corp_code']: r['id'] for r in rows}
        logger.info(f"회사 캐시: {len(company_cache)}개")

        stats = {
            'processed': 0,
            'cb_inserted': 0,
            'cb_updated': 0,
            'cb_skipped': 0,
            'subscribers_created': 0,
            'file_not_found': 0,
            'parse_failed': 0,
            'errors': 0
        }

        for i, disclosure in enumerate(cb_disclosures):
            rcept_no = disclosure.get('rcept_no')
            corp_code = disclosure.get('corp_code')

            company_id = company_cache.get(corp_code)
            if not company_id:
                stats['cb_skipped'] += 1
                continue

            # ZIP 파일 찾기
            zip_pattern = f"{DART_DATA_DIR}/**/{corp_code}/*/{rcept_no}.zip"
            zip_files = glob.glob(zip_pattern, recursive=True)

            if not zip_files:
                stats['file_not_found'] += 1
                continue

            xml_content = load_xml_from_zip(zip_files[0])
            if not xml_content:
                stats['file_not_found'] += 1
                continue

            # CB 정보 파싱
            cb_info = parse_cb_info(xml_content, disclosure)
            if not cb_info:
                stats['parse_failed'] += 1
                continue

            try:
                # CB UPSERT
                result = await conn.fetchrow("""
                    INSERT INTO convertible_bonds (
                        id, company_id, bond_name, issue_date, maturity_date,
                        issue_amount, interest_rate, conversion_price,
                        conversion_start_date, conversion_end_date,
                        use_of_proceeds, status, source_disclosure_id,
                        created_at, updated_at
                    ) VALUES (
                        uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active', $11,
                        NOW(), NOW()
                    )
                    ON CONFLICT (company_id, bond_name, issue_date) DO UPDATE SET
                        maturity_date = COALESCE(EXCLUDED.maturity_date, convertible_bonds.maturity_date),
                        issue_amount = COALESCE(EXCLUDED.issue_amount, convertible_bonds.issue_amount),
                        interest_rate = COALESCE(EXCLUDED.interest_rate, convertible_bonds.interest_rate),
                        conversion_price = COALESCE(EXCLUDED.conversion_price, convertible_bonds.conversion_price),
                        conversion_start_date = COALESCE(EXCLUDED.conversion_start_date, convertible_bonds.conversion_start_date),
                        conversion_end_date = COALESCE(EXCLUDED.conversion_end_date, convertible_bonds.conversion_end_date),
                        source_disclosure_id = COALESCE(EXCLUDED.source_disclosure_id, convertible_bonds.source_disclosure_id),
                        updated_at = NOW()
                    RETURNING id, (xmax = 0) as inserted
                """,
                    company_id,
                    cb_info['bond_name'],
                    cb_info['issue_date'],
                    cb_info['maturity_date'],
                    cb_info['issue_amount'],
                    cb_info['interest_rate'],
                    cb_info['conversion_price'],
                    cb_info.get('conversion_start_date'),
                    cb_info.get('conversion_end_date'),
                    cb_info.get('use_of_proceeds'),
                    rcept_no
                )

                if result:
                    cb_id = result['id']
                    if result['inserted']:
                        stats['cb_inserted'] += 1
                    else:
                        stats['cb_updated'] += 1

                    # 인수자 파싱 및 저장
                    subscribers = parse_subscribers(xml_content, disclosure)
                    for sub in subscribers:
                        try:
                            # 중복 체크
                            existing = await conn.fetchval("""
                                SELECT 1 FROM cb_subscribers
                                WHERE cb_id = $1 AND subscriber_name = $2
                            """, cb_id, sub['subscriber_name'])

                            if existing:
                                # 인수금액 업데이트 (NULL인 경우)
                                if sub.get('subscription_amount'):
                                    await conn.execute("""
                                        UPDATE cb_subscribers
                                        SET subscription_amount = COALESCE(subscription_amount, $1),
                                            updated_at = NOW()
                                        WHERE cb_id = $2 AND subscriber_name = $3
                                    """, float(sub['subscription_amount']), cb_id, sub['subscriber_name'])
                            else:
                                await conn.execute("""
                                    INSERT INTO cb_subscribers (
                                        id, cb_id, subscriber_name, relationship_to_company,
                                        subscription_amount, selection_rationale, is_related_party,
                                        source_disclosure_id, created_at, updated_at
                                    ) VALUES (
                                        uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, NOW(), NOW()
                                    )
                                """,
                                    cb_id,
                                    sub['subscriber_name'],
                                    sub.get('relationship_to_company'),
                                    float(sub['subscription_amount']) if sub.get('subscription_amount') else None,
                                    sub.get('selection_rationale'),
                                    sub.get('is_related_party', 'N'),
                                    rcept_no
                                )
                                stats['subscribers_created'] += 1
                        except Exception as e:
                            logger.debug(f"인수자 저장 오류: {e}")

                stats['processed'] += 1

            except Exception as e:
                logger.debug(f"공시 처리 오류 {rcept_no}: {e}")
                stats['errors'] += 1

            if (i + 1) % 100 == 0:
                logger.info(f"진행: {i+1}/{len(cb_disclosures)} - 처리: {stats['processed']}, CB 신규: {stats['cb_inserted']}, 인수자: {stats['subscribers_created']}")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("재처리 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 공시: {stats['processed']}건")
        logger.info(f"CB 신규 생성: {stats['cb_inserted']}개")
        logger.info(f"CB 업데이트: {stats['cb_updated']}개")
        logger.info(f"CB 스킵 (회사 없음): {stats['cb_skipped']}개")
        logger.info(f"파일 없음: {stats['file_not_found']}건")
        logger.info(f"파싱 실패: {stats['parse_failed']}건")
        logger.info(f"인수자 생성: {stats['subscribers_created']}명")
        logger.info(f"오류: {stats['errors']}건")

        # DB 현황
        cb_count = await conn.fetchval("SELECT COUNT(*) FROM convertible_bonds")
        sub_count = await conn.fetchval("SELECT COUNT(*) FROM cb_subscribers")
        null_amt = await conn.fetchval("SELECT COUNT(*) FROM cb_subscribers WHERE subscription_amount IS NULL OR subscription_amount = 0")

        logger.info(f"\nDB 현황:")
        logger.info(f"  전환사채: {cb_count}개")
        logger.info(f"  인수자: {sub_count}명")
        logger.info(f"  인수금액 NULL/0: {null_amt}건 ({null_amt*100/sub_count:.1f}%)")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
