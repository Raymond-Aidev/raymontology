"""
최대주주 기본정보 파서

DART 사업보고서에서 "최대주주(법인 또는 단체)의 기본정보" 및
"최대주주(법인 또는 단체)의 최근 결산기 재무현황" 테이블을 추출합니다.

ACODE 매핑:
- BAS_NAME: 최대주주 법인명
- BAS_CNT: 출자자수
- BAS_NAM1/RAT1: 대표이사 성명/지분율
- BAS_NAM2/RAT2: 업무집행자 성명/지분율
- BAS_NAM3/RAT3: 최대출자자 성명/지분율
- FIN_NAME: 법인명 (재무현황)
- FIN_AST: 자산총계
- FIN_DEB: 부채총계
- FIN_CAP: 자본총계
- FIN_SAL: 매출액
- FIN_BUF: 영업이익
- FIN_PRF: 당기순이익
"""

import asyncio
import json
import logging
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')


# ACODE 매핑
BASIC_INFO_CODES = {
    'shareholder_name': 'BAS_NAME',
    'investor_count': 'BAS_CNT',
    'ceo_name': 'BAS_NAM1',
    'ceo_share_ratio': 'BAS_RAT1',
    'executor_name': 'BAS_NAM2',
    'executor_share_ratio': 'BAS_RAT2',
    'largest_investor_name': 'BAS_NAM3',
    'largest_investor_share_ratio': 'BAS_RAT3',
}

FINANCIAL_INFO_CODES = {
    'fin_name': 'FIN_NAME',
    'fin_total_assets': 'FIN_AST',
    'fin_total_liabilities': 'FIN_DEB',
    'fin_total_equity': 'FIN_CAP',
    'fin_revenue': 'FIN_SAL',
    'fin_operating_income': 'FIN_BUF',
    'fin_net_income': 'FIN_PRF',
}


class LargestShareholderParser:
    """최대주주 기본정보 파서"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {
            'total_reports': 0,
            'parsed': 0,
            'no_data': 0,
            'errors': 0,
            'inserted': 0,
            'updated': 0,
        }

    def extract_acode_value(self, xml_content: str, acode: str) -> Optional[str]:
        """ACODE로 값 추출"""
        # TE 태그에서 추출 (테이블 셀)
        pattern = rf'ACODE="{acode}"[^>]*>([^<]*)</TE>'
        match = re.search(pattern, xml_content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value and value != '-':
                return value

        # EXTRACTION 태그에서 추출
        pattern = rf'ACODE="{acode}"[^>]*>([^<]*)</EXTRACTION>'
        match = re.search(pattern, xml_content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value and value != '-':
                return value

        return None

    def parse_number(self, value: str) -> Optional[int]:
        """숫자 문자열을 정수로 변환"""
        if not value or value == '-':
            return None
        try:
            # 쉼표 제거, 괄호(음수) 처리
            cleaned = value.replace(',', '').replace(' ', '')
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None

    def parse_ratio(self, value: str) -> Optional[float]:
        """지분율 문자열을 실수로 변환"""
        if not value or value == '-':
            return None
        try:
            cleaned = value.replace(',', '').replace('%', '').replace(' ', '')
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def parse_xml(self, xml_content: str) -> Dict[str, Any]:
        """XML에서 최대주주 기본정보 추출"""
        result = {}

        # 기본정보 추출
        for field, acode in BASIC_INFO_CODES.items():
            value = self.extract_acode_value(xml_content, acode)
            if value:
                if 'ratio' in field or field == 'investor_count':
                    if 'ratio' in field:
                        result[field] = self.parse_ratio(value)
                    else:
                        result[field] = self.parse_number(value)
                else:
                    result[field] = value

        # 재무현황 추출
        for field, acode in FINANCIAL_INFO_CODES.items():
            if field == 'fin_name':
                continue  # 이미 shareholder_name으로 저장됨
            value = self.extract_acode_value(xml_content, acode)
            if value:
                result[field] = self.parse_number(value)

        return result

    def extract_xml_from_zip(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 가장 큰 XML 추출 (사업보고서 본문)"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                xml_files = [
                    (name, zf.getinfo(name).file_size)
                    for name in zf.namelist()
                    if name.endswith('.xml') and not name.startswith('_')
                ]
                if not xml_files:
                    return None

                # 가장 큰 XML 선택
                largest = max(xml_files, key=lambda x: x[1])
                raw = zf.read(largest[0])

                try:
                    return raw.decode('utf-8')
                except UnicodeDecodeError:
                    return raw.decode('euc-kr', errors='replace')
        except Exception as e:
            logger.debug(f"ZIP 읽기 실패 {zip_path}: {e}")
            return None

    async def get_company_map(self) -> Dict[str, str]:
        """corp_code -> company_id 매핑"""
        rows = await self.conn.fetch(
            "SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL"
        )
        return {row['corp_code']: str(row['id']) for row in rows}

    async def get_existing_records(self) -> set:
        """기존 레코드 (company_id, fiscal_year) 집합"""
        rows = await self.conn.fetch(
            "SELECT company_id, fiscal_year FROM largest_shareholder_info"
        )
        return {(str(row['company_id']), row['fiscal_year']) for row in rows}

    def get_fiscal_year_from_meta(self, meta: dict) -> Optional[int]:
        """메타데이터에서 회계연도 추출"""
        report_nm = meta.get('report_nm', '')
        # "사업보고서 (2024.12)" 형식에서 연도 추출
        match = re.search(r'\((\d{4})\.\d{2}\)', report_nm)
        if match:
            return int(match.group(1))

        # rcept_dt에서 추출 (제출일 기준 전년도)
        rcept_dt = meta.get('rcept_dt', '')
        if rcept_dt and len(rcept_dt) >= 4:
            submit_year = int(rcept_dt[:4])
            # 사업보고서는 보통 3월에 제출되므로 전년도가 회계연도
            return submit_year - 1

        return None

    async def process_report(
        self,
        zip_path: Path,
        meta: dict,
        company_id: str,
        fiscal_year: int
    ) -> Optional[Dict]:
        """단일 보고서 처리"""
        xml_content = self.extract_xml_from_zip(zip_path)
        if not xml_content:
            return None

        # 최대주주 기본정보 파싱
        parsed = self.parse_xml(xml_content)

        # 데이터가 없으면 건너뛰기
        if not parsed.get('shareholder_name'):
            return None

        return {
            'company_id': company_id,
            'fiscal_year': fiscal_year,
            'report_date': meta.get('rcept_dt'),
            **parsed
        }

    async def upsert_record(self, data: Dict) -> bool:
        """레코드 삽입/업데이트"""
        try:
            # report_date 변환
            report_date = None
            if data.get('report_date'):
                try:
                    report_date = datetime.strptime(data['report_date'], '%Y%m%d').date()
                except:
                    pass

            await self.conn.execute("""
                INSERT INTO largest_shareholder_info (
                    company_id, fiscal_year, report_date,
                    shareholder_name, investor_count,
                    ceo_name, ceo_share_ratio,
                    executor_name, executor_share_ratio,
                    largest_investor_name, largest_investor_share_ratio,
                    fin_total_assets, fin_total_liabilities, fin_total_equity,
                    fin_revenue, fin_operating_income, fin_net_income,
                    data_source, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()
                )
                ON CONFLICT (company_id, fiscal_year)
                DO UPDATE SET
                    report_date = EXCLUDED.report_date,
                    shareholder_name = EXCLUDED.shareholder_name,
                    investor_count = EXCLUDED.investor_count,
                    ceo_name = EXCLUDED.ceo_name,
                    ceo_share_ratio = EXCLUDED.ceo_share_ratio,
                    executor_name = EXCLUDED.executor_name,
                    executor_share_ratio = EXCLUDED.executor_share_ratio,
                    largest_investor_name = EXCLUDED.largest_investor_name,
                    largest_investor_share_ratio = EXCLUDED.largest_investor_share_ratio,
                    fin_total_assets = EXCLUDED.fin_total_assets,
                    fin_total_liabilities = EXCLUDED.fin_total_liabilities,
                    fin_total_equity = EXCLUDED.fin_total_equity,
                    fin_revenue = EXCLUDED.fin_revenue,
                    fin_operating_income = EXCLUDED.fin_operating_income,
                    fin_net_income = EXCLUDED.fin_net_income,
                    updated_at = NOW()
            """,
                data['company_id'],
                data['fiscal_year'],
                report_date,
                data.get('shareholder_name'),
                data.get('investor_count'),
                data.get('ceo_name'),
                data.get('ceo_share_ratio'),
                data.get('executor_name'),
                data.get('executor_share_ratio'),
                data.get('largest_investor_name'),
                data.get('largest_investor_share_ratio'),
                data.get('fin_total_assets'),
                data.get('fin_total_liabilities'),
                data.get('fin_total_equity'),
                data.get('fin_revenue'),
                data.get('fin_operating_income'),
                data.get('fin_net_income'),
                'LOCAL_DART'
            )
            return True
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")
            return False

    async def run(self, sample: int = None, dry_run: bool = False):
        """전체 파싱 실행"""
        logger.info("=" * 60)
        logger.info("최대주주 기본정보 파싱 시작")
        logger.info("=" * 60)

        # 회사 매핑 로드
        company_map = await self.get_company_map()
        logger.info(f"회사 수: {len(company_map)}")

        # 기존 레코드 로드
        existing = await self.get_existing_records()
        logger.info(f"기존 레코드: {len(existing)}")

        # DART 데이터 디렉토리
        dart_dir = Path(__file__).parent.parent.parent / 'data' / 'dart'

        # 모든 사업보고서 메타 파일 수집
        meta_files = []
        for batch_dir in sorted(dart_dir.glob('batch_*')):
            for meta_file in batch_dir.glob('*/*/[0-9]*_meta.json'):
                meta_files.append(meta_file)

        logger.info(f"메타 파일 수: {len(meta_files)}")

        if sample:
            meta_files = meta_files[:sample]
            logger.info(f"샘플 {sample}건만 처리")

        # 처리
        processed = 0
        for i, meta_file in enumerate(meta_files, 1):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                # 사업보고서만 처리
                report_nm = meta.get('report_nm', '')
                if '사업보고서' not in report_nm:
                    continue

                self.stats['total_reports'] += 1

                # corp_code 추출
                corp_code = meta_file.parent.parent.name
                if corp_code not in company_map:
                    continue

                company_id = company_map[corp_code]

                # 회계연도 추출
                fiscal_year = self.get_fiscal_year_from_meta(meta)
                if not fiscal_year:
                    continue

                # 이미 존재하면 건너뛰기
                if (company_id, fiscal_year) in existing:
                    continue

                # ZIP 파일 경로
                zip_path = meta_file.with_name(
                    meta_file.name.replace('_meta.json', '.zip')
                )
                if not zip_path.exists():
                    continue

                # 파싱
                result = await self.process_report(
                    zip_path, meta, company_id, fiscal_year
                )

                if not result:
                    self.stats['no_data'] += 1
                    continue

                self.stats['parsed'] += 1

                # DB 저장
                if not dry_run:
                    if await self.upsert_record(result):
                        self.stats['inserted'] += 1
                        existing.add((company_id, fiscal_year))

                processed += 1

            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"처리 실패 {meta_file}: {e}")

            # 진행 상황
            if i % 1000 == 0:
                logger.info(f"진행: {i}/{len(meta_files)} ({i*100/len(meta_files):.1f}%)")

        # 최종 통계
        logger.info("")
        logger.info("=" * 60)
        logger.info("파싱 완료")
        logger.info("=" * 60)
        logger.info(f"  사업보고서: {self.stats['total_reports']}건")
        logger.info(f"  최대주주 정보 있음: {self.stats['parsed']}건")
        logger.info(f"  최대주주 정보 없음: {self.stats['no_data']}건")
        logger.info(f"  DB 저장: {self.stats['inserted']}건")
        logger.info(f"  오류: {self.stats['errors']}건")

        if dry_run:
            logger.info("")
            logger.info("⚠️ Dry Run 모드 - 실제 DB 저장 없음")

        return self.stats


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='최대주주 기본정보 파싱')
    parser.add_argument('--sample', type=int, help='샘플 N건만 처리')
    parser.add_argument('--dry-run', action='store_true', help='실제 저장 없이 테스트')
    args = parser.parse_args()

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")

    # asyncpg URL 형식 변환
    db_url = DATABASE_URL.replace('postgresql://', 'postgres://')
    if '+asyncpg' in db_url:
        db_url = db_url.replace('+asyncpg', '')

    conn = await asyncpg.connect(db_url)

    try:
        parser_instance = LargestShareholderParser(conn)
        await parser_instance.run(sample=args.sample, dry_run=args.dry_run)
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
