#!/usr/bin/env python3
"""
사업보고서에서 최대주주 및 계열회사 정보 파싱

대상: 2022-2024 사업보고서
"""
import asyncio
import asyncpg
import json
import logging
import re
import zipfile
from pathlib import Path
from datetime import date
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_URL = 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'
DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')


def parse_shareholders(xml_content: str) -> list:
    """최대주주/주요주주 정보 파싱"""
    shareholders = []

    # 패턴 1: 최대주주 테이블에서 추출
    # <TD>주주명</TD><TD>지분율</TD><TD>주식수</TD> 형식

    # 최대주주 섹션 찾기
    shareholder_section = re.search(
        r'최대주주[^<]*현황.{0,5000}?(?=Ⅷ\.|VIII\.|임원|$)',
        xml_content,
        re.DOTALL | re.IGNORECASE
    )

    if shareholder_section:
        section_text = shareholder_section.group(0)

        # 테이블 행 추출 패턴
        # 이름, 관계, 주식수, 지분율 순서
        row_pattern = r'<TD[^>]*>([^<]{1,50})</TD>\s*<TD[^>]*>([^<]{0,30})</TD>\s*<TD[^>]*>([\d,]+)</TD>\s*<TD[^>]*>([\d.]+)'

        for match in re.finditer(row_pattern, section_text):
            name = match.group(1).strip()
            relationship = match.group(2).strip()
            shares_str = match.group(3).replace(',', '')
            ratio_str = match.group(4)

            # 필터: 숫자나 빈 값 제외
            if not name or name.isdigit() or len(name) < 2:
                continue
            if name in ['합계', '총계', '소계', '계', '성명', '주주명', '관계']:
                continue

            try:
                shares = int(shares_str) if shares_str else None
                ratio = float(ratio_str) if ratio_str else None

                if ratio and ratio > 0:
                    shareholders.append({
                        'name': name,
                        'relationship': relationship,
                        'shares': shares,
                        'ratio': ratio,
                        'is_largest': len(shareholders) == 0  # 첫 번째가 최대주주
                    })
            except (ValueError, TypeError):
                continue

    # 패턴 2: P 태그 형식
    if not shareholders:
        # 최대주주: 홍길동 (지분율 45.2%)
        p_pattern = r'최대주주[:\s]*([가-힣a-zA-Z\s]+)[,\s]*(?:지분율|소유)?\s*:?\s*([\d.]+)\s*%'
        match = re.search(p_pattern, xml_content)
        if match:
            shareholders.append({
                'name': match.group(1).strip(),
                'relationship': '최대주주',
                'shares': None,
                'ratio': float(match.group(2)),
                'is_largest': True
            })

    return shareholders[:20]  # 최대 20명


def parse_affiliates(xml_content: str) -> list:
    """계열회사 정보 파싱 (AFF_CMP 테이블 기반)"""
    affiliates = []
    seen_names = set()

    # 제외할 단어 목록 (잘못 파싱되기 쉬운 단어들)
    EXCLUDE_WORDS = {
        '이사', '국내', '해외', '한국', '중국', '일본', '미국', '베트남', '인도', '태국',
        '회사명', '계열회사', '관계', '비고', '해당', '없음', '계', '합계', '소계',
        '상장', '비상장', '기타', '합병', '청산', '신설', '제조', '판매', '서비스',
        '지역', '분류', '업종', '사업', '투자', '금융', '보험', '증권', '은행',
        '회사', '상호', '임기', '보통', '지분', '소유', 'CC', 'CP', '관리',
        '설립일', '주소', '주요사업', '자산총액', '지배관계', '종속회사',
    }

    # 방법 1: AFF_CMP 테이블 (계열회사 현황)
    aff_table_pattern = r'<TABLE-GROUP[^>]*ACLASS="AFF_CMP"[^>]*>(.*?)</TABLE-GROUP>'
    aff_match = re.search(aff_table_pattern, xml_content, re.DOTALL | re.IGNORECASE)

    if aff_match:
        table_content = aff_match.group(1)

        # LST_NM (상장 계열사), NLST_NM (비상장 계열사)
        for acode in ['LST_NM', 'NLST_NM']:
            pattern = rf'ACODE="{acode}"[^>]*>([^<]+)<'
            for match in re.finditer(pattern, table_content):
                name = match.group(1).strip()
                name = re.sub(r'\s+', '', name)  # 공백 제거

                if _is_valid_affiliate_name(name, EXCLUDE_WORDS, seen_names):
                    seen_names.add(name)
                    affiliates.append({
                        'name': name,
                        'relationship_type': 'AFFILIATE',
                        'is_listed': acode == 'LST_NM'
                    })

    # 방법 2: SUB_CMPN 테이블 (종속회사 현황)
    sub_table_pattern = r'<TABLE-GROUP[^>]*ACLASS="SUB_CMPN"[^>]*>(.*?)</TABLE-GROUP>'
    sub_match = re.search(sub_table_pattern, xml_content, re.DOTALL | re.IGNORECASE)

    if sub_match:
        table_content = sub_match.group(1)

        # CRP_NM (회사명)
        pattern = r'ACODE="CRP_NM"[^>]*>([^<]+)<'
        for match in re.finditer(pattern, table_content):
            name = match.group(1).strip()
            name = re.sub(r'\s+', '', name)

            if _is_valid_affiliate_name(name, EXCLUDE_WORDS, seen_names):
                seen_names.add(name)
                affiliates.append({
                    'name': name,
                    'relationship_type': 'SUBSIDIARY',
                    'is_listed': False
                })

    # 방법 3: 피지배사/지배사 매트릭스에서 추출
    if '피지배사' in xml_content:
        start_idx = xml_content.find('피지배사')
        table_end = xml_content.find('</TABLE>', start_idx)
        if table_end > start_idx:
            table_text = xml_content[start_idx:table_end]

            # TH 헤더에서 회사명 추출
            header_pattern = r'<TH[^>]*>(.*?)</TH>'
            for match in re.finditer(header_pattern, table_text, re.DOTALL):
                h = match.group(1)
                h = re.sub(r'</?P>', '', h).strip()
                h = re.sub(r'\s+', '', h)

                if _is_valid_affiliate_name(h, EXCLUDE_WORDS, seen_names):
                    seen_names.add(h)
                    affiliates.append({
                        'name': h,
                        'relationship_type': 'AFFILIATE',
                        'is_listed': False
                    })

            # TD에서 회사명 추출
            td_pattern = r'<TD[^>]*>([^<]+)</TD>'
            cells = re.findall(td_pattern, table_text)
            for cell in cells:
                name = cell.strip()
                name = re.sub(r'\s+', '', name)

                # 숫자/지분율이 아닌 경우만
                if not re.match(r'^[\d.,%-]+$', name):
                    if _is_valid_affiliate_name(name, EXCLUDE_WORDS, seen_names):
                        seen_names.add(name)
                        affiliates.append({
                            'name': name,
                            'relationship_type': 'AFFILIATE',
                            'is_listed': False
                        })

    return affiliates[:50]


def _is_valid_affiliate_name(name: str, exclude_words: set, seen: set) -> bool:
    """유효한 계열회사명인지 확인"""
    if not name or name == '-':
        return False
    if len(name) < 3:  # 최소 3자 이상
        return False
    if name in exclude_words:
        return False
    if name in seen:
        return False
    # 숫자만 있는 경우
    if re.match(r'^[\d\s,.%]+$', name):
        return False
    # 회사명 패턴 확인 (한글 또는 영문이 포함되어야 함)
    if not re.search(r'[가-힣a-zA-Z]', name):
        return False
    return True


async def parse_shareholders_affiliates():
    """사업보고서에서 주주/계열회사 파싱"""
    conn = await asyncpg.connect(DB_URL)

    try:
        # 시작 전 카운트
        shareholders_before = await conn.fetchval("SELECT COUNT(*) FROM major_shareholders")
        affiliates_before = await conn.fetchval("SELECT COUNT(*) FROM affiliates")
        logger.info(f"작업 전 major_shareholders: {shareholders_before}건, affiliates: {affiliates_before}건")

        # company_id 매핑
        companies = await conn.fetch("SELECT id, corp_code, name FROM companies WHERE corp_code IS NOT NULL")
        corp_to_id = {c['corp_code']: c['id'] for c in companies}
        corp_to_name = {c['corp_code']: c['name'] for c in companies}
        name_to_id = {c['name']: c['id'] for c in companies}
        logger.info(f"회사 매핑: {len(corp_to_id)}개")

        stats = {
            'scanned': 0,
            'parsed_shareholders': 0,
            'parsed_affiliates': 0,
            'saved_shareholders': 0,
            'saved_affiliates': 0,
            'errors': 0
        }

        shareholder_batch = []
        affiliate_batch = []

        # 배치 폴더 순회
        batch_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith('batch_')])

        for batch_dir in batch_dirs:
            meta_files = list(batch_dir.rglob('*_meta.json'))

            for meta_file in meta_files:
                stats['scanned'] += 1

                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                    report_nm = meta.get('report_nm', '')
                    corp_code = meta.get('corp_code')
                    rcept_no = meta.get('rcept_no')
                    rcept_dt = meta.get('rcept_dt', '')

                    # 회사 ID 확인
                    if corp_code not in corp_to_id:
                        continue

                    company_id = corp_to_id[corp_code]

                    # 사업보고서만 필터링
                    if '사업보고서' not in report_nm:
                        continue

                    # 연도 추출
                    year_match = re.search(r'\((\d{4})\.(\d{2})\)', report_nm)
                    if not year_match:
                        continue

                    fiscal_year = int(year_match.group(1))

                    # 2022-2024만
                    if fiscal_year < 2022 or fiscal_year > 2024:
                        continue

                    # ZIP 파일 열기
                    zip_path = meta_file.parent / f"{rcept_no}.zip"
                    if not zip_path.exists():
                        continue

                    # 파일 크기 체크 (너무 작으면 손상)
                    if zip_path.stat().st_size < 1000:
                        continue

                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                            if not xml_files:
                                continue

                            main_xml = max(xml_files, key=lambda x: zf.getinfo(x).file_size)

                            try:
                                content = zf.read(main_xml).decode('utf-8')
                            except:
                                content = zf.read(main_xml).decode('euc-kr', errors='ignore')

                            # 주주 파싱
                            shareholders = parse_shareholders(content)
                            if shareholders:
                                stats['parsed_shareholders'] += len(shareholders)

                                report_date = None
                                if rcept_dt and len(rcept_dt) == 8:
                                    try:
                                        report_date = date(int(rcept_dt[:4]), int(rcept_dt[4:6]), int(rcept_dt[6:8]))
                                    except:
                                        pass

                                for sh in shareholders:
                                    shareholder_batch.append((
                                        uuid.uuid4(),
                                        company_id,
                                        sh['name'],
                                        sh['name'],  # normalized (TODO: 정규화)
                                        'INDIVIDUAL' if len(sh['name']) <= 4 else 'INSTITUTION',
                                        sh.get('shares'),
                                        sh.get('ratio'),
                                        sh.get('is_largest', False),
                                        sh.get('relationship') == '특수관계인',
                                        report_date,
                                        fiscal_year,
                                        4,  # Q4 (사업보고서)
                                        None,
                                        None,
                                        rcept_no
                                    ))

                            # 계열회사 파싱
                            affiliates_data = parse_affiliates(content)
                            if affiliates_data:
                                stats['parsed_affiliates'] += len(affiliates_data)

                                for aff in affiliates_data:
                                    # 계열회사가 DB에 있는지 확인
                                    affiliate_company_id = name_to_id.get(aff['name'])
                                    if not affiliate_company_id:
                                        # 유사 이름 검색
                                        for db_name, db_id in name_to_id.items():
                                            if aff['name'] in db_name or db_name in aff['name']:
                                                affiliate_company_id = db_id
                                                break

                                    if affiliate_company_id and affiliate_company_id != company_id:
                                        affiliate_batch.append((
                                            uuid.uuid4(),
                                            company_id,
                                            affiliate_company_id,
                                            aff['name'],
                                            None,  # business_number
                                            aff.get('relationship_type', 'AFFILIATE'),
                                            aff.get('is_listed', False),
                                            None,  # ownership_ratio
                                            None,  # voting_rights_ratio
                                            None,  # total_assets
                                            None,  # revenue
                                            None,  # net_income
                                            rcept_no,
                                            rcept_dt
                                        ))

                            # 배치 삽입
                            if len(shareholder_batch) >= 500:
                                saved = await insert_shareholders(conn, shareholder_batch)
                                stats['saved_shareholders'] += saved
                                logger.info(f"  주주 {stats['saved_shareholders']}건 저장")
                                shareholder_batch = []

                            if len(affiliate_batch) >= 200:
                                saved = await insert_affiliates(conn, affiliate_batch)
                                stats['saved_affiliates'] += saved
                                logger.info(f"  계열 {stats['saved_affiliates']}건 저장")
                                affiliate_batch = []

                    except zipfile.BadZipFile:
                        continue

                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 5:
                        logger.error(f"오류 {meta_file}: {e}")

                if stats['scanned'] % 10000 == 0:
                    logger.info(f"진행: {stats['scanned']:,}건 스캔")

            logger.info(f"배치 {batch_dir.name} 완료")

        # 남은 데이터 삽입
        if shareholder_batch:
            saved = await insert_shareholders(conn, shareholder_batch)
            stats['saved_shareholders'] += saved

        if affiliate_batch:
            saved = await insert_affiliates(conn, affiliate_batch)
            stats['saved_affiliates'] += saved

        # 최종 결과
        shareholders_after = await conn.fetchval("SELECT COUNT(*) FROM major_shareholders")
        affiliates_after = await conn.fetchval("SELECT COUNT(*) FROM affiliates")

        logger.info("\n" + "=" * 60)
        logger.info("주주/계열회사 파싱 완료")
        logger.info("=" * 60)
        logger.info(f"스캔: {stats['scanned']:,}건")
        logger.info(f"파싱 주주: {stats['parsed_shareholders']:,}건")
        logger.info(f"파싱 계열: {stats['parsed_affiliates']:,}건")
        logger.info(f"저장 주주: {stats['saved_shareholders']:,}건")
        logger.info(f"저장 계열: {stats['saved_affiliates']:,}건")
        logger.info(f"오류: {stats['errors']:,}건")
        logger.info("-" * 60)
        logger.info(f"major_shareholders: {shareholders_before}건 → {shareholders_after}건 (+{shareholders_after - shareholders_before}건)")
        logger.info(f"affiliates: {affiliates_before}건 → {affiliates_after}건 (+{affiliates_after - affiliates_before}건)")
        logger.info("=" * 60)

    finally:
        await conn.close()


async def insert_shareholders(conn, batch_data):
    """주주 배치 삽입"""
    saved = 0
    for row in batch_data:
        try:
            await conn.execute("""
                INSERT INTO major_shareholders (
                    id, company_id, shareholder_name, shareholder_name_normalized,
                    shareholder_type, share_count, share_ratio,
                    is_largest_shareholder, is_related_party,
                    report_date, report_year, report_quarter,
                    change_reason, previous_share_ratio, source_rcept_no
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT DO NOTHING
            """, *row)
            saved += 1
        except Exception as e:
            if 'duplicate' not in str(e).lower():
                pass  # 로그 생략
    return saved


async def insert_affiliates(conn, batch_data):
    """계열회사 배치 삽입"""
    saved = 0
    for row in batch_data:
        try:
            await conn.execute("""
                INSERT INTO affiliates (
                    id, parent_company_id, affiliate_company_id, affiliate_name,
                    business_number, relationship_type, is_listed,
                    ownership_ratio, voting_rights_ratio,
                    total_assets, revenue, net_income,
                    source_disclosure_id, source_date
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (parent_company_id, affiliate_company_id, source_date) DO NOTHING
            """, *row)
            saved += 1
        except Exception as e:
            if 'duplicate' not in str(e).lower():
                pass  # 로그 생략
    return saved


if __name__ == "__main__":
    asyncio.run(parse_shareholders_affiliates())
