"""
Financial Details 재파싱 스크립트 (v4.0)

v3.1 파서 버그 수정 후 전체 데이터 재파싱:
- 단위 감지 버그 수정 (백만원 > 천원 > 원 순서)
- 삼성전자, SK하이닉스 등 대기업 데이터 정확도 개선
- gross_profit 계산 추가

사용법:
    # 테스트 (삼성전자, SK하이닉스만)
    python -m scripts.reparse_financial_details_v4 --test

    # 특정 연도만
    python -m scripts.reparse_financial_details_v4 --year 2024

    # 문제 레코드만 (매출 < 1B인 KOSPI 기업)
    python -m scripts.reparse_financial_details_v4 --fix-critical

    # 전체 재파싱
    python -m scripts.reparse_financial_details_v4 --all

    # Dry-run (DB 업데이트 없이 테스트)
    python -m scripts.reparse_financial_details_v4 --all --dry-run
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from scripts.parsers import FinancialParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"


class FinancialDetailsReparser:
    """Financial Details 재파싱기 v4.0"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.parser = None
        self.stats = {
            'total': 0,
            'success': 0,
            'skipped': 0,
            'no_zip': 0,
            'parse_failed': 0,
            'errors': 0,
        }
        self.dart_dir = Path(__file__).parent.parent / 'data' / 'dart'

    async def run(
        self,
        mode: str = 'test',
        year: Optional[int] = None,
        company_names: Optional[List[str]] = None,
    ):
        """재파싱 실행"""
        logger.info("=" * 70)
        logger.info("Financial Details 재파싱 v4.0")
        logger.info(f"  Mode: {mode}")
        logger.info(f"  Year: {year or '전체'}")
        logger.info(f"  Dry-run: {self.dry_run}")
        logger.info("=" * 70)

        conn = await asyncpg.connect(DATABASE_URL)

        try:
            # 파서 초기화
            self.parser = FinancialParser(database_url=DATABASE_URL, enable_xbrl=True)
            await self.parser.load_companies(conn)

            # 대상 레코드 조회
            targets = await self._get_targets(conn, mode, year, company_names)
            logger.info(f"재파싱 대상: {len(targets)}건")

            if not targets:
                logger.warning("처리할 대상이 없습니다.")
                return

            # 재파싱 실행
            for i, target in enumerate(targets, 1):
                await self._reparse_single(conn, target)

                if i % 100 == 0:
                    logger.info(f"진행: {i}/{len(targets)} ({i*100/len(targets):.1f}%)")

            # 결과 출력
            self._print_summary()

        finally:
            await conn.close()

    async def _get_targets(
        self,
        conn: asyncpg.Connection,
        mode: str,
        year: Optional[int],
        company_names: Optional[List[str]],
    ) -> List[Dict]:
        """재파싱 대상 조회"""

        if mode == 'test':
            # 테스트: 삼성전자, SK하이닉스
            query = """
                SELECT
                    fd.id, fd.company_id, fd.fiscal_year, fd.data_source,
                    c.corp_code, c.name as company_name, c.market
                FROM financial_details fd
                JOIN companies c ON fd.company_id = c.id
                WHERE c.name IN ('삼성전자', 'SK하이닉스', 'POSCO홀딩스')
                ORDER BY c.name, fd.fiscal_year
            """
            return [dict(r) for r in await conn.fetch(query)]

        elif mode == 'fix-critical':
            # 문제 레코드: KOSPI 기업 중 매출 < 1B
            query = """
                SELECT
                    fd.id, fd.company_id, fd.fiscal_year, fd.data_source,
                    c.corp_code, c.name as company_name, c.market
                FROM financial_details fd
                JOIN companies c ON fd.company_id = c.id
                WHERE c.market = 'KOSPI'
                  AND fd.revenue IS NOT NULL
                  AND fd.revenue > 0
                  AND fd.revenue < 1000000000
                  AND fd.data_source = 'LOCAL_DART_V3_XBRL'
                ORDER BY c.name, fd.fiscal_year
            """
            return [dict(r) for r in await conn.fetch(query)]

        elif mode == 'all':
            # 전체: LOCAL_DART_V3_XBRL 소스만
            query = """
                SELECT
                    fd.id, fd.company_id, fd.fiscal_year, fd.data_source,
                    c.corp_code, c.name as company_name, c.market
                FROM financial_details fd
                JOIN companies c ON fd.company_id = c.id
                WHERE fd.data_source IN ('LOCAL_DART_V3_XBRL', 'LOCAL_DART_V2', 'LOCAL_DART')
            """
            params = []

            if year:
                query += " AND fd.fiscal_year = $1"
                params.append(year)

            query += " ORDER BY c.name, fd.fiscal_year"
            return [dict(r) for r in await conn.fetch(query, *params)]

        elif company_names:
            # 특정 회사만
            placeholders = ', '.join(f'${i+1}' for i in range(len(company_names)))
            query = f"""
                SELECT
                    fd.id, fd.company_id, fd.fiscal_year, fd.data_source,
                    c.corp_code, c.name as company_name, c.market
                FROM financial_details fd
                JOIN companies c ON fd.company_id = c.id
                WHERE c.name IN ({placeholders})
                ORDER BY c.name, fd.fiscal_year
            """
            return [dict(r) for r in await conn.fetch(query, *company_names)]

        return []

    async def _reparse_single(self, conn: asyncpg.Connection, target: Dict):
        """단일 레코드 재파싱"""
        self.stats['total'] += 1

        corp_code = target['corp_code']
        fiscal_year = target['fiscal_year']
        company_name = target['company_name']

        # ZIP 파일 찾기
        zip_path, meta = self._find_report_zip(corp_code, fiscal_year)

        if not zip_path:
            self.stats['no_zip'] += 1
            logger.debug(f"ZIP 없음: {company_name} {fiscal_year}")
            return

        try:
            # 파싱
            result = await self.parser.parse(zip_path, meta)

            if not result.get('success'):
                self.stats['parse_failed'] += 1
                logger.warning(f"파싱 실패: {company_name} {fiscal_year}")
                return

            parsed_data = result.get('data', {})

            # gross_profit 계산 (없으면)
            if parsed_data.get('gross_profit') is None:
                revenue = parsed_data.get('revenue')
                cost_of_sales = parsed_data.get('cost_of_sales')
                if revenue is not None and cost_of_sales is not None:
                    parsed_data['gross_profit'] = revenue - cost_of_sales

            # DB 업데이트
            if not self.dry_run:
                await self._update_record(conn, target['id'], parsed_data)

            self.stats['success'] += 1

            # 주요 변경 로그
            old_revenue = await conn.fetchval(
                "SELECT revenue FROM financial_details WHERE id = $1",
                target['id']
            )
            new_revenue = parsed_data.get('revenue')

            if old_revenue and new_revenue and abs(old_revenue - new_revenue) > 1_000_000_000:
                logger.info(
                    f"  {company_name} {fiscal_year}: "
                    f"매출 {old_revenue:,} → {new_revenue:,}"
                )

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"오류: {company_name} {fiscal_year} - {e}")

    def _find_report_zip(self, corp_code: str, fiscal_year: int) -> Tuple[Optional[Path], Optional[Dict]]:
        """보고서 ZIP 파일 찾기"""
        # 제출연도: 사업보고서는 fiscal_year + 1년에 제출
        search_years = [fiscal_year + 1, fiscal_year, fiscal_year + 2]

        for batch_dir in sorted(self.dart_dir.glob('batch_*')):
            corp_dir = batch_dir / corp_code
            if not corp_dir.exists():
                continue

            for search_year in search_years:
                year_dir = corp_dir / str(search_year)
                if not year_dir.exists():
                    continue

                # 사업보고서 찾기
                for meta_file in year_dir.glob('*_meta.json'):
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)

                        report_nm = meta.get('report_nm', '')
                        if '사업보고서' in report_nm:
                            # 해당 연도 보고서인지 확인
                            if f'({fiscal_year}.' in report_nm:
                                zip_path = meta_file.with_name(
                                    meta_file.name.replace('_meta.json', '.zip')
                                )
                                if zip_path.exists():
                                    return zip_path, meta
                    except Exception:
                        continue

        return None, None

    async def _update_record(self, conn: asyncpg.Connection, record_id, data: Dict):
        """레코드 업데이트"""
        # 업데이트할 필드들
        fields = [
            'revenue', 'cost_of_sales', 'gross_profit', 'operating_income', 'net_income',
            'total_assets', 'total_equity', 'total_liabilities',
            'current_assets', 'current_liabilities', 'non_current_assets', 'non_current_liabilities',
            'cash_and_equivalents', 'short_term_investments', 'trade_and_other_receivables',
            'inventories', 'tangible_assets', 'intangible_assets',
            'trade_payables', 'short_term_borrowings', 'long_term_borrowings', 'bonds_payable',
            'capital_stock', 'capital_surplus', 'retained_earnings', 'treasury_stock',
            'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
            'capex', 'dividend_paid', 'interest_expense',
        ]

        set_clauses = []
        values = []
        idx = 1

        for field in fields:
            value = data.get(field)
            if value is not None:
                set_clauses.append(f"{field} = ${idx}")
                values.append(value)
                idx += 1

        if not set_clauses:
            return

        # 메타 정보 업데이트
        set_clauses.append(f"data_source = ${idx}")
        values.append('LOCAL_DART_V4_FIXED')
        idx += 1

        set_clauses.append(f"updated_at = ${idx}")
        values.append(datetime.utcnow())
        idx += 1

        values.append(record_id)

        query = f"""
            UPDATE financial_details
            SET {', '.join(set_clauses)}
            WHERE id = ${idx}
        """

        await conn.execute(query, *values)

    def _print_summary(self):
        """결과 요약 출력"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("재파싱 완료")
        logger.info("=" * 70)
        logger.info(f"  총 처리: {self.stats['total']}건")
        logger.info(f"  성공: {self.stats['success']}건")
        logger.info(f"  ZIP 없음: {self.stats['no_zip']}건")
        logger.info(f"  파싱 실패: {self.stats['parse_failed']}건")
        logger.info(f"  오류: {self.stats['errors']}건")

        if self.stats['total'] > 0:
            success_rate = self.stats['success'] / self.stats['total'] * 100
            logger.info(f"  성공률: {success_rate:.1f}%")

        if self.dry_run:
            logger.info("")
            logger.info("⚠️ Dry-run 모드 - 실제 DB 업데이트 없음")


async def main():
    parser = argparse.ArgumentParser(description='Financial Details 재파싱 v4.0')
    parser.add_argument('--test', action='store_true', help='테스트 (삼성전자, SK하이닉스, POSCO)')
    parser.add_argument('--fix-critical', action='store_true', help='문제 레코드만 수정')
    parser.add_argument('--all', action='store_true', help='전체 재파싱')
    parser.add_argument('--year', type=int, help='특정 연도만')
    parser.add_argument('--companies', type=str, help='특정 회사 (쉼표 구분)')
    parser.add_argument('--dry-run', action='store_true', help='DB 업데이트 없이 테스트')
    args = parser.parse_args()

    # 모드 결정
    if args.test:
        mode = 'test'
    elif args.fix_critical:
        mode = 'fix-critical'
    elif args.all:
        mode = 'all'
    elif args.companies:
        mode = 'companies'
    else:
        print("모드를 선택하세요: --test, --fix-critical, --all, --companies")
        return

    company_names = None
    if args.companies:
        company_names = [c.strip() for c in args.companies.split(',')]

    reparser = FinancialDetailsReparser(dry_run=args.dry_run)
    await reparser.run(mode=mode, year=args.year, company_names=company_names)


if __name__ == '__main__':
    asyncio.run(main())
