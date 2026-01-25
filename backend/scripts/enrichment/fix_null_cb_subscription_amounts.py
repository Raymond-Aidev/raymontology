#!/usr/bin/env python3
"""
CB 인수금액 NULL 건 재추출 스크립트

subscription_amount가 NULL인 CB 인수자 데이터를
DART 원본 공시 파일에서 재추출하여 업데이트합니다.

사용법:
    python -m scripts.enrichment.fix_null_cb_subscription_amounts --dry-run
    python -m scripts.enrichment.fix_null_cb_subscription_amounts
"""
import asyncio
import asyncpg
import glob
import io
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수 로드
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env.production')

# 설정
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DB_URL = DB_URL.replace('postgresql+asyncpg://', 'postgresql://')  # asyncpg 호환

DART_DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')
CB_SAMPLES_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/cb_samples_test')
DOWNLOAD_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/cb_fix_downloads')

# DART API 설정
DART_API_KEY = os.getenv("DART_API_KEY", "1fd0cd12ae5260eafb7de3130ad91f16aa61911b")
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


def normalize_name(name: str, keep_parens: bool = False) -> str:
    """이름 정규화 (비교용)

    Args:
        name: 원본 이름
        keep_parens: True면 괄호 내용 유지 (상세 비교용)
    """
    if not name:
        return ""
    # HTML 엔티티 제거
    name = re.sub(r'&[^;]+;', '', name)
    # 공백 정규화
    name = re.sub(r'\s+', ' ', name).strip()
    # 괄호 내용 제거 (기본)
    if not keep_parens:
        name = re.sub(r'\([^)]*\)', '', name)
        name = re.sub(r'「[^」]*」', '', name)
        name = re.sub(r'"[^"]*"', '', name)
    # 공백 제거
    name = re.sub(r'\s+', '', name)
    return name.strip()


def extract_core_name(name: str) -> str:
    """핵심 이름 추출 (회사명, 펀드명 등의 공통 부분)"""
    if not name:
        return ""
    # 괄호 이전 부분 추출
    match = re.match(r'^([^(「"]+)', name)
    if match:
        core = match.group(1).strip()
        # 공백 제거
        core = re.sub(r'\s+', '', core)
        return core
    return normalize_name(name)


def extract_fund_number(name: str) -> Optional[str]:
    """펀드 번호 추출 (예: '펀드1', '펀드 16')"""
    # 다양한 패턴 매칭
    patterns = [
        r'펀드\s*(\d+)',
        r'펀드\s*제?\s*(\d+)',
        r'본건\s*펀드\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(1)
    return None


def parse_amount(amount_str: str) -> Optional[int]:
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


def extract_subscribers_from_xml(content: str) -> Dict[str, int]:
    """XML에서 인수자 이름과 금액 추출"""
    subscribers = {}

    # TR 단위로 ISSU_NM과 ISSU_AMT 추출
    tr_pattern = r'<TR[^>]*>(.*?)</TR>'
    tr_matches = re.findall(tr_pattern, content, re.DOTALL | re.IGNORECASE)

    for tr_content in tr_matches:
        # ISSU_NM 찾기
        name_match = re.search(
            r'<TE[^>]*ACODE="ISSU_NM"[^>]*>(.*?)</TE>',
            tr_content,
            re.DOTALL | re.IGNORECASE
        )
        if not name_match:
            continue

        # 이름 추출 (HTML 태그 제거)
        name_raw = name_match.group(1)
        name = re.sub(r'<[^>]+>', '', name_raw)
        name = re.sub(r'&[^;]+;', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if not name or name == '-' or len(name) < 2:
            continue

        # 금액 추출 - 중첩 태그 지원 (예: <TE><P>100,000</P></TE>)
        amt_match = re.search(
            r'<TE[^>]*ACODE="ISSU_AMT"[^>]*>(.*?)</TE>',
            tr_content,
            re.DOTALL | re.IGNORECASE
        )
        if amt_match:
            # HTML 태그 제거 후 금액 추출
            amt_raw = amt_match.group(1)
            amt_text = re.sub(r'<[^>]+>', '', amt_raw)
            amt_text = re.sub(r'&[^;]+;', '', amt_text)
            amt_text = amt_text.strip()

            amount = parse_amount(amt_text)
            if amount and amount > 0:
                # 정규화된 이름을 키로 사용
                name_key = normalize_name(name)
                subscribers[name_key] = amount
                # 원본 이름도 저장 (매칭 용이)
                subscribers[name] = amount

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
                    except UnicodeDecodeError:
                        try:
                            return content.decode('euc-kr', errors='ignore')
                        except:
                            return content.decode('cp949', errors='ignore')
    except Exception as e:
        logger.debug(f"ZIP 로드 실패 {zip_path}: {e}")
    return None


def find_local_file(corp_code: str, rcept_no: str) -> Optional[Tuple[str, str]]:
    """로컬에서 공시 파일 찾기 (ZIP 또는 XML)

    Returns:
        Tuple of (file_path, file_type) where file_type is 'zip' or 'xml'
    """
    # 공시번호에서 연도 추출 (예: 20220408002970 -> 2022)
    year = rcept_no[:4] if len(rcept_no) >= 4 else None

    # 1. cb_samples_test 폴더 먼저 확인 (최근 다운로드)
    for ext in ['xml', 'zip']:
        local_path = CB_SAMPLES_DIR / f"{rcept_no}.{ext}"
        if local_path.exists():
            return (str(local_path), ext)

    # 2. DOWNLOAD_DIR 확인 (이전 실행에서 다운로드)
    for ext in ['xml', 'zip']:
        local_path = DOWNLOAD_DIR / f"{rcept_no}.{ext}"
        if local_path.exists():
            return (str(local_path), ext)

    # 3. DART 데이터 디렉토리 패턴 검색 (ZIP)
    patterns = [
        f"{DART_DATA_DIR}/batch_*/{corp_code}/{year}/{rcept_no}.zip" if year else None,
        f"{DART_DATA_DIR}/batch_*/{corp_code}/*/{rcept_no}.zip",
        f"{DART_DATA_DIR}/batch_missing/{corp_code}/{year}/{rcept_no}.zip" if year else None,
        f"{DART_DATA_DIR}/batch_missing/{corp_code}/*/{rcept_no}.zip",
        f"{DART_DATA_DIR}/**/{rcept_no}.zip",
    ]

    for pattern in patterns:
        if pattern is None:
            continue
        files = glob.glob(pattern, recursive=True)
        if files:
            return (files[0], 'zip')

    return None


async def download_disclosure(rcept_no: str) -> Optional[str]:
    """DART API에서 공시 다운로드"""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    xml_path = DOWNLOAD_DIR / f"{rcept_no}.xml"

    # 이미 존재하면 반환
    if xml_path.exists():
        return str(xml_path)

    url = f"{DART_DOCUMENT_URL}?crtfc_key={DART_API_KEY}&rcept_no={rcept_no}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.debug(f"다운로드 실패: {rcept_no} - Status {response.status_code}")
                return None

            content = response.content

            # ZIP 파일인 경우 추출
            if content[:4] == b'PK\x03\x04':
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                    if xml_files:
                        xml_content = zf.read(xml_files[0])
                        with open(xml_path, 'wb') as f:
                            f.write(xml_content)
                        logger.debug(f"다운로드 완료: {rcept_no}")
                        return str(xml_path)
            else:
                # XML 응답 확인
                if b'<?xml' in content[:100] or b'<DOCUMENT' in content[:200]:
                    with open(xml_path, 'wb') as f:
                        f.write(content)
                    return str(xml_path)
                else:
                    # 에러 응답 (JSON 등)
                    logger.debug(f"잘못된 응답: {rcept_no}")
                    return None

    except Exception as e:
        logger.debug(f"다운로드 예외: {rcept_no} - {e}")

    return None


def find_zip_file(corp_code: str, rcept_no: str) -> Optional[str]:
    """DART 데이터 디렉토리에서 ZIP 파일 찾기 (하위 호환)"""
    result = find_local_file(corp_code, rcept_no)
    if result:
        return result[0]
    return None


async def get_null_subscribers(conn: asyncpg.Connection, year_filter: str = None) -> List[Dict]:
    """subscription_amount가 NULL인 인수자 목록 조회

    Args:
        year_filter: 연도 필터 (예: '2022,2023,2024')
    """
    query = """
        SELECT
            cs.id,
            cs.subscriber_name,
            cs.source_disclosure_id,
            cb.source_disclosure_id as cb_source_disclosure_id,
            c.corp_code,
            c.name as company_name
        FROM cb_subscribers cs
        JOIN convertible_bonds cb ON cs.cb_id = cb.id
        JOIN companies c ON cb.company_id = c.id
        WHERE cs.subscription_amount IS NULL
    """

    if year_filter:
        years = [y.strip() for y in year_filter.split(',')]
        year_conditions = " OR ".join([
            f"COALESCE(cs.source_disclosure_id, cb.source_disclosure_id) LIKE '{y}%'"
            for y in years
        ])
        query += f" AND ({year_conditions})"

    query += " ORDER BY c.corp_code, cb.source_disclosure_id"

    rows = await conn.fetch(query)

    return [dict(r) for r in rows]


async def update_subscription_amount(
    conn: asyncpg.Connection,
    subscriber_id: str,
    amount: int,
    dry_run: bool = False
) -> bool:
    """인수금액 업데이트"""
    if dry_run:
        return True

    try:
        await conn.execute("""
            UPDATE cb_subscribers
            SET subscription_amount = $1,
                updated_at = NOW()
            WHERE id = $2
        """, float(amount), subscriber_id)
        return True
    except Exception as e:
        logger.error(f"업데이트 실패 {subscriber_id}: {e}")
        return False


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="CB 인수금액 NULL 건 재추출")
    parser.add_argument("--dry-run", action="store_true", help="실제 업데이트 없이 시뮬레이션")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 건수 (0=무제한)")
    parser.add_argument("--years", type=str, default="2022,2023,2024,2025",
                        help="처리할 공시 연도 (콤마 구분, 기본값: 2022,2023,2024,2025)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("CB 인수금액 NULL 건 재추출 시작")
    logger.info(f"모드: {'DRY-RUN (시뮬레이션)' if args.dry_run else '실제 업데이트'}")
    logger.info(f"대상 연도: {args.years}")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        # NULL 인수자 목록 조회 (연도 필터 적용)
        null_subscribers = await get_null_subscribers(conn, args.years)
        total_count = len(null_subscribers)
        logger.info(f"NULL 인수금액 건수: {total_count}건")

        if args.limit > 0:
            null_subscribers = null_subscribers[:args.limit]
            logger.info(f"처리 대상: {len(null_subscribers)}건 (limit={args.limit})")

        # 통계
        stats = {
            'processed': 0,
            'updated': 0,
            'local_found': 0,
            'downloaded': 0,
            'file_not_found': 0,
            'name_not_matched': 0,
            'amount_not_found': 0,
            'errors': 0
        }

        # 공시별로 그룹화하여 처리 (효율성)
        disclosure_groups: Dict[str, List[Dict]] = {}
        for sub in null_subscribers:
            # source_disclosure_id 우선, 없으면 CB의 source_disclosure_id 사용
            rcept_no = sub['source_disclosure_id'] or sub['cb_source_disclosure_id']
            if rcept_no:
                if rcept_no not in disclosure_groups:
                    disclosure_groups[rcept_no] = []
                disclosure_groups[rcept_no].append(sub)

        logger.info(f"처리할 공시: {len(disclosure_groups)}개")

        # 공시별 처리
        processed_disclosures = 0
        for rcept_no, subscribers in disclosure_groups.items():
            processed_disclosures += 1

            # 로컬 파일 찾기
            corp_code = subscribers[0]['corp_code']
            local_result = find_local_file(corp_code, rcept_no)

            xml_content = None

            if local_result:
                file_path, file_type = local_result
                stats['local_found'] += 1

                if file_type == 'zip':
                    xml_content = load_xml_from_zip(file_path)
                else:  # xml
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            xml_content = f.read()
                    except:
                        pass

            # 로컬에 없으면 DART API 다운로드
            if not xml_content:
                xml_path = await download_disclosure(rcept_no)
                if xml_path:
                    stats['downloaded'] += 1
                    try:
                        with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                            xml_content = f.read()
                    except:
                        pass

            if not xml_content:
                stats['file_not_found'] += len(subscribers)
                logger.debug(f"파일 없음: {rcept_no} ({subscribers[0]['company_name']})")
                continue

            # 인수자 정보 추출
            extracted = extract_subscribers_from_xml(xml_content)

            if not extracted:
                stats['amount_not_found'] += len(subscribers)
                continue

            # 각 NULL 인수자 매칭
            for sub in subscribers:
                stats['processed'] += 1

                subscriber_name = sub['subscriber_name']
                normalized = normalize_name(subscriber_name)
                ext_core = ""  # 스코프 문제 해결

                # 매칭 시도 (여러 전략)
                amount = None

                # 1. 정확한 매칭 (원본 이름)
                if subscriber_name in extracted:
                    amount = extracted[subscriber_name]
                elif normalized in extracted:
                    amount = extracted[normalized]
                else:
                    # 2. 핵심 이름 + 펀드 번호 매칭 (증권사 펀드 케이스)
                    sub_core = extract_core_name(subscriber_name)
                    sub_fund_num = extract_fund_number(subscriber_name)

                    for ext_name, ext_amount in extracted.items():
                        ext_core = extract_core_name(ext_name)
                        ext_fund_num = extract_fund_number(ext_name)

                        # 핵심 이름이 같고 펀드 번호도 같으면 매칭
                        if sub_core and ext_core:
                            # 핵심 이름 비교 (정규화 후)
                            sub_core_norm = re.sub(r'\s+', '', sub_core)
                            ext_core_norm = re.sub(r'\s+', '', ext_core)

                            if sub_core_norm == ext_core_norm:
                                # 펀드 번호가 있으면 번호도 비교
                                if sub_fund_num and ext_fund_num:
                                    if sub_fund_num == ext_fund_num:
                                        amount = ext_amount
                                        break
                                elif not sub_fund_num and not ext_fund_num:
                                    # 둘 다 펀드 번호 없으면 매칭
                                    amount = ext_amount
                                    break

                    # 3. 부분 매칭 (이름이 포함된 경우)
                    if not amount:
                        for ext_name, ext_amount in extracted.items():
                            ext_normalized = normalize_name(ext_name)
                            if normalized in ext_normalized or ext_normalized in normalized:
                                amount = ext_amount
                                break
                            # 길이 3 이상인 경우 핵심 이름 부분 일치
                            if len(sub_core) >= 3 and len(ext_core) >= 3:
                                if sub_core in ext_core or ext_core in sub_core:
                                    # 펀드 번호가 있으면 반드시 일치해야 함
                                    if sub_fund_num and ext_fund_num:
                                        if sub_fund_num == ext_fund_num:
                                            amount = ext_amount
                                            break
                                    elif not sub_fund_num and not ext_fund_num:
                                        amount = ext_amount
                                        break

                if amount:
                    success = await update_subscription_amount(
                        conn, sub['id'], amount, args.dry_run
                    )
                    if success:
                        stats['updated'] += 1
                        logger.debug(f"업데이트: {subscriber_name} -> {amount:,}원")
                else:
                    stats['name_not_matched'] += 1
                    logger.debug(f"매칭 실패: {subscriber_name} (공시: {rcept_no})")

            # 진행 상황 출력
            if processed_disclosures % 50 == 0:
                logger.info(
                    f"진행: {processed_disclosures}/{len(disclosure_groups)} 공시 - "
                    f"업데이트: {stats['updated']}, 매칭실패: {stats['name_not_matched']}"
                )

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("재추출 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 공시: {processed_disclosures}개")
        logger.info(f"  - 로컬 파일 사용: {stats['local_found']}개")
        logger.info(f"  - DART API 다운로드: {stats['downloaded']}개")
        logger.info(f"  - 파일 없음: {stats['file_not_found']}건")
        logger.info(f"처리된 NULL 건: {stats['processed']}건")
        logger.info(f"  - 업데이트 성공: {stats['updated']}건")
        logger.info(f"  - 이름 매칭 실패: {stats['name_not_matched']}건")
        logger.info(f"  - 금액 없음: {stats['amount_not_found']}건")

        if args.dry_run:
            logger.info("\n[DRY-RUN] 실제 업데이트 없이 시뮬레이션만 수행됨")
            logger.info("실제 업데이트를 수행하려면 --dry-run 옵션 없이 실행하세요")

        # 업데이트 후 DB 현황
        null_after = await conn.fetchval(
            "SELECT COUNT(*) FROM cb_subscribers WHERE subscription_amount IS NULL"
        )
        logger.info(f"\n현재 NULL 인수금액: {null_after}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
