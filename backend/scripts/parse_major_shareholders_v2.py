#!/usr/bin/env python3
"""
대주주 정보 재파싱 스크립트 v2

기존 파싱 문제점:
- "자산 총계", "거래량" 등 비정상 데이터가 주주명으로 저장됨
- 테이블 구조 오인식

개선 사항:
1. HTML 태그 제거 후 순수 텍스트 기반 파싱
2. "최대주주 및 특수관계인의 주식소유 현황" 섹션 정확 타겟팅
3. 엄격한 데이터 검증 (이름 길이, 지분율 범위, 무효 키워드 필터)
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import json
from pathlib import Path
from datetime import date
from typing import List, Dict, Any, Optional
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')

# 무효 키워드 목록 (주주명으로 사용 불가)
INVALID_KEYWORDS = {
    '자산', '부채', '자본', '매출', '영업', '순이익', '총계', '합계', '소계', '계',
    '거래량', '주가', '평균', '최저', '최고', '월간', '일간', '연간',
    '성명', '관계', '주식수', '지분율', '비고', '기초', '기말', '종류',
    '보통주', '우선주', '의결권', '단위', '기준일', '주주', '특수관계인',
    '변동', '취득', '처분', '이익', '손실', '증가', '감소',
}

# 법인 키워드 (정상적인 주주명에 포함될 수 있음)
COMPANY_SUFFIXES = ['㈜', '주식회사', '유한회사', '합자회사', 'Inc', 'Corp', 'Ltd', 'LLC']


def normalize_name(name: str) -> str:
    """이름 정규화"""
    if not name:
        return ""
    name = unicodedata.normalize('NFC', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def is_valid_shareholder_name(name: str) -> bool:
    """유효한 주주명인지 검증"""
    if not name or len(name) < 2:
        return False

    # 숫자만 있는 경우
    if re.match(r'^[\d,.\s]+$', name):
        return False

    # 숫자로 시작하는 경우 (펀드명 제외)
    # 예외: "2018큐씨피13호 사모투자합자회사" 등 연도+한글 조합
    if re.match(r'^[0-9]', name):
        # 연도(20XX) + 한글/영문 조합은 허용
        if re.match(r'^20[0-9]{2}[가-힣A-Za-z]', name) and len(name) > 10:
            pass  # 펀드명 허용
        else:
            return False

    # 날짜/기간 패턴 (예: "03 ~ 12", "78. 03 ~ 81. 02")
    if re.match(r'^[0-9]{2,4}\s*[\.~]', name):
        return False

    # 무효 키워드 포함
    name_lower = name.lower()
    for keyword in INVALID_KEYWORDS:
        if keyword in name_lower:
            return False

    # 특수문자만 있는 경우
    if re.match(r'^[\W\s]+$', name):
        return False

    # 너무 긴 이름 (문장일 가능성)
    if len(name) > 50:
        return False

    # "의", "은", "는", "이", "가" 등으로 끝나면 문장 일부일 가능성
    if re.search(r'(의|은|는|이|가|을|를|에|로|와|과)$', name):
        # 단, 법인명은 예외
        if not any(suffix in name for suffix in COMPANY_SUFFIXES):
            return False

    return True


def extract_shareholder_ratio(text: str) -> Optional[float]:
    """지분율 추출"""
    if not text:
        return None

    text = text.replace(' ', '').replace('%', '').replace(',', '')
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        try:
            ratio = float(match.group(1))
            # 지분율은 0-100 범위
            if 0 < ratio <= 100:
                return ratio
        except:
            pass
    return None


def extract_share_count(text: str) -> Optional[int]:
    """주식수 추출"""
    if not text:
        return None

    text = text.replace(',', '').replace(' ', '')
    match = re.search(r'(\d+)', text)
    if match:
        try:
            return int(match.group(1))
        except:
            pass
    return None


def parse_shareholder_section(text: str) -> List[Dict[str, Any]]:
    """최대주주 섹션에서 주주 정보 파싱"""
    shareholders = []

    # HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', '\n', text)
    clean_text = re.sub(r'\n+', '\n', clean_text)
    clean_text = re.sub(r'[ \t]+', ' ', clean_text)

    # "최대주주 및 특수관계인의 주식소유 현황" 섹션 찾기
    section_patterns = [
        r'최대주주\s*및\s*특수관계인의?\s*주식소유\s*현황(.+?)(?:2\.\s*최대주주의|최대주주\s*변동|주식\s*소유\s*현황\s*변동|소액주주)',
        r'최대주주\s*및\s*그\s*특수관계인(.+?)(?:2\.\s*최대주주의|최대주주\s*변동)',
    ]

    section_text = None
    for pattern in section_patterns:
        match = re.search(pattern, clean_text, re.DOTALL | re.IGNORECASE)
        if match:
            section_text = match.group(1)
            break

    if not section_text:
        return shareholders

    # 테이블 데이터 추출 패턴
    # 형식: 이름 관계 주식종류 주식수 지분율 주식수 지분율 비고
    # 또는: 이름 관계 주식수 지분율

    lines = section_text.split('\n')

    # 첫 번째 방법: 줄 단위로 패턴 매칭
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 이름 후보 확인
        if is_valid_shareholder_name(line) and len(line) <= 30:
            # 다음 줄들에서 관계와 지분율 찾기
            relationship = None
            ratio = None
            shares = None

            for j in range(1, min(8, len(lines) - i)):
                next_line = lines[i + j].strip() if i + j < len(lines) else ""

                # 관계 확인
                if next_line in ['최대주주', '특수관계인', '본인', '배우자', '자녀', '임원', '계열회사']:
                    relationship = next_line
                    continue

                # 지분율 확인
                if re.match(r'^\d+\.?\d*$', next_line) and ratio is None:
                    temp_ratio = extract_shareholder_ratio(next_line)
                    if temp_ratio:
                        ratio = temp_ratio
                        continue

                # 주식수 확인
                if re.match(r'^[\d,]+$', next_line) and shares is None:
                    shares = extract_share_count(next_line)
                    continue

                # 다른 주주 이름이 나오면 중단
                if is_valid_shareholder_name(next_line) and len(next_line) <= 30:
                    break

            if ratio and ratio > 0:
                shareholders.append({
                    'name': normalize_name(line),
                    'relationship': relationship or '주주',
                    'shares': shares,
                    'ratio': ratio,
                    'is_largest': relationship == '최대주주' or len(shareholders) == 0
                })

    # 두 번째 방법: 한 줄에 모든 정보가 있는 경우
    # "SK스퀘어㈜ 최대주주 의결권 있는 주식 146,100,000 20.07 146,100,000 20.07"
    pattern = r'([가-힣A-Za-z\s㈜]+)\s+(최대주주|특수관계인|본인)\s+(?:의결권[^0-9]*)?(\d[\d,]*)\s+(\d+\.?\d*)'

    for match in re.finditer(pattern, section_text):
        name = match.group(1).strip()
        relationship = match.group(2)
        shares = extract_share_count(match.group(3))
        ratio = extract_shareholder_ratio(match.group(4))

        if is_valid_shareholder_name(name) and ratio:
            # 중복 체크
            if not any(s['name'] == normalize_name(name) for s in shareholders):
                shareholders.append({
                    'name': normalize_name(name),
                    'relationship': relationship,
                    'shares': shares,
                    'ratio': ratio,
                    'is_largest': relationship == '최대주주'
                })

    # 지분율 기준 정렬
    shareholders.sort(key=lambda x: x['ratio'] or 0, reverse=True)

    # 최대 20명까지
    return shareholders[:20]


class ShareholderParserV2:
    """개선된 대주주 정보 파싱"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {'parsed': 0, 'saved': 0, 'errors': 0, 'skipped': 0}
        self.company_cache = {}

    async def load_company_cache(self):
        """회사 정보 캐시 로드"""
        rows = await self.conn.fetch("SELECT id, corp_code, name FROM companies WHERE corp_code IS NOT NULL")
        self.company_cache = {r['corp_code']: {'id': r['id'], 'name': r['name']} for r in rows}
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개")

    def read_xml_from_zip(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 XML 내용 읽기"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml') and not name.startswith('_'):
                        content = zf.read(name)
                        try:
                            return content.decode('utf-8')
                        except:
                            return content.decode('euc-kr', errors='ignore')
        except Exception as e:
            logger.debug(f"ZIP 읽기 실패 {zip_path}: {e}")
        return None

    async def process_report(self, corp_code: str, rcept_no: str, zip_path: Path, report_year: int) -> int:
        """사업보고서 처리"""
        if corp_code not in self.company_cache:
            return 0

        xml_content = self.read_xml_from_zip(zip_path)
        if not xml_content:
            return 0

        shareholders = parse_shareholder_section(xml_content)
        if not shareholders:
            return 0

        company_id = self.company_cache[corp_code]['id']
        saved = 0

        for sh in shareholders:
            try:
                # 기존 데이터 확인
                existing = await self.conn.fetchval("""
                    SELECT id FROM major_shareholders
                    WHERE company_id = $1 AND shareholder_name = $2 AND report_year = $3
                """, company_id, sh['name'], report_year)

                if existing:
                    # 업데이트
                    await self.conn.execute("""
                        UPDATE major_shareholders SET
                            share_ratio = $1,
                            share_count = $2,
                            is_largest_shareholder = $3,
                            shareholder_type = $4,
                            updated_at = NOW()
                        WHERE id = $5
                    """, sh['ratio'], sh['shares'], sh['is_largest'],
                        'INSTITUTION' if any(s in sh['name'] for s in COMPANY_SUFFIXES) else 'INDIVIDUAL',
                        existing)
                else:
                    # 삽입
                    await self.conn.execute("""
                        INSERT INTO major_shareholders (
                            company_id, shareholder_name, shareholder_name_normalized,
                            shareholder_type, share_count, share_ratio,
                            is_largest_shareholder, report_year, source_rcept_no
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, company_id, sh['name'], normalize_name(sh['name']).lower(),
                        'INSTITUTION' if any(s in sh['name'] for s in COMPANY_SUFFIXES) else 'INDIVIDUAL',
                        sh['shares'], sh['ratio'], sh['is_largest'], report_year, rcept_no)

                saved += 1
            except Exception as e:
                logger.debug(f"저장 실패 {sh['name']}: {e}")

        return saved

    async def find_business_reports(self) -> List[Dict]:
        """사업보고서 목록 조회"""
        reports = await self.conn.fetch("""
            SELECT DISTINCT d.corp_code, d.rcept_no, d.rcept_dt
            FROM disclosures d
            WHERE d.report_nm LIKE '%사업보고서%'
              AND d.report_nm NOT LIKE '%첨부%'
              AND d.report_nm NOT LIKE '%기재정정%'
              AND d.rcept_dt >= '20220101'
            ORDER BY d.corp_code, d.rcept_dt DESC
        """)
        return [dict(r) for r in reports]

    async def run(self):
        """실행"""
        logger.info("=" * 60)
        logger.info("대주주 정보 재파싱 시작 (v2)")
        logger.info("=" * 60)

        await self.load_company_cache()

        # 기존 불량 데이터 삭제
        logger.info("기존 불량 데이터 정리 중...")
        deleted = await self.conn.execute("""
            DELETE FROM major_shareholders
            WHERE shareholder_name ~ '^[0-9,]+$'
               OR shareholder_name IN ('자산 총계', '부채 총계', '거래량', '평균', '월간', '최저', '최저(일)', '최저 일거래량', '월간거래량')
               OR shareholder_name LIKE '%의 지분율%'
               OR shareholder_name LIKE '%주식수를 합산%'
               OR LENGTH(shareholder_name) > 50
        """)
        logger.info(f"불량 데이터 삭제: {deleted}")

        # 사업보고서 목록 조회
        reports = await self.find_business_reports()
        logger.info(f"처리할 사업보고서: {len(reports)}건")

        # 처리
        processed = 0
        for report in reports:
            corp_code = report['corp_code']
            rcept_no = report['rcept_no']
            rcept_dt = report['rcept_dt']

            # ZIP 파일 찾기
            zip_path = None
            for batch_dir in DART_DATA_DIR.glob('batch_*'):
                corp_dir = batch_dir / corp_code
                if corp_dir.exists():
                    for year_dir in corp_dir.iterdir():
                        zip_file = year_dir / f"{rcept_no}.zip"
                        if zip_file.exists():
                            zip_path = zip_file
                            break
                if zip_path:
                    break

            if not zip_path:
                continue

            # 연도 추출
            try:
                report_year = int(rcept_dt[:4])
            except:
                report_year = 2024

            saved = await self.process_report(corp_code, rcept_no, zip_path, report_year)
            if saved > 0:
                self.stats['saved'] += saved
                processed += 1

            self.stats['parsed'] += 1

            if self.stats['parsed'] % 100 == 0:
                logger.info(f"진행: {self.stats['parsed']}건 처리, {self.stats['saved']}건 저장")

        logger.info("=" * 60)
        logger.info("완료!")
        logger.info(f"처리된 보고서: {self.stats['parsed']}건")
        logger.info(f"저장된 주주 정보: {self.stats['saved']}건")
        logger.info("=" * 60)


async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        parser = ShareholderParserV2(conn)
        await parser.run()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
