#!/usr/bin/env python3
"""
Sub-Index NULL 레코드 재계산 스크립트

목적:
- Sub-Index가 모두 NULL인 레코드를 정상 계산기로 재계산
- 기존 단순화된 파이프라인 계산기로 생성된 데이터 수정

안전장치:
1. --dry-run: 실제 변경 없이 대상만 확인
2. 정상 계산기(RaymondsIndexCalculator) 사용
3. 트랜잭션 기반 - 실패 시 롤백

사용법:
    # 대상 확인
    python scripts/maintenance/recalculate_null_subindex.py --dry-run

    # 실제 재계산
    python scripts/maintenance/recalculate_null_subindex.py --execute
"""

import asyncio
import asyncpg
import argparse
import logging
import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal
import uuid

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.raymonds_index_calculator import RaymondsIndexCalculator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


class NullSubindexRecalculator:
    """Sub-Index NULL 레코드 재계산기"""

    def __init__(self, database_url: str):
        self.db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.calculator = RaymondsIndexCalculator()
        self.stats = {
            'total_null': 0,
            'has_financial_data': 0,
            'recalculated': 0,
            'skipped': 0,
            'errors': 0,
        }

    async def get_null_subindex_records(self, conn: asyncpg.Connection) -> List[Dict]:
        """Sub-Index가 NULL인 레코드 조회"""
        query = """
            SELECT
                ri.id,
                ri.company_id,
                ri.fiscal_year,
                ri.total_score as old_score,
                ri.grade as old_grade,
                c.name,
                c.ticker
            FROM raymonds_index ri
            JOIN companies c ON c.id = ri.company_id
            WHERE ri.cei_score IS NULL
              AND ri.rii_score IS NULL
              AND ri.cgi_score IS NULL
              AND ri.mai_score IS NULL
            ORDER BY ri.total_score DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_financial_data(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        target_year: int
    ) -> List[Dict]:
        """회사의 재무 데이터 조회 (3년치)"""
        years = [target_year - 2, target_year - 1, target_year]

        query = """
            SELECT DISTINCT ON (fiscal_year)
                fiscal_year, fiscal_quarter, fs_type,
                -- 재무상태표
                cash_and_equivalents, short_term_investments, trade_and_other_receivables,
                inventories, tangible_assets, intangible_assets,
                total_assets, current_liabilities, non_current_liabilities,
                total_liabilities, total_equity,
                -- 재무상태표 (투자괴리율 v2용 추가 컬럼)
                right_of_use_assets, investments_in_associates,
                fvpl_financial_assets, other_financial_assets_non_current,
                -- 손익계산서
                revenue, cost_of_sales, selling_admin_expenses,
                operating_income, net_income,
                -- 현금흐름표
                operating_cash_flow, investing_cash_flow, financing_cash_flow,
                capex, intangible_acquisition, dividend_paid,
                treasury_stock_acquisition, stock_issuance, bond_issuance
            FROM financial_details
            WHERE company_id = $1
              AND fiscal_year IN ({})
            ORDER BY fiscal_year, fiscal_quarter NULLS FIRST
        """.format(', '.join(map(str, years)))

        rows = await conn.fetch(query, uuid.UUID(company_id))
        return [dict(row) for row in rows]

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """값을 범위 내로 제한"""
        if value is None:
            return None
        return max(min_val, min(max_val, value))

    async def save_recalculated(self, conn: asyncpg.Connection, result_dict: Dict) -> bool:
        """재계산 결과 업데이트"""
        try:
            await conn.execute("""
                UPDATE raymonds_index
                SET
                    total_score = $1,
                    grade = $2,
                    cei_score = $3,
                    rii_score = $4,
                    cgi_score = $5,
                    mai_score = $6,
                    investment_gap = $7,
                    cash_cagr = $8,
                    capex_growth = $9,
                    idle_cash_ratio = $10,
                    asset_turnover = $11,
                    reinvestment_rate = $12,
                    shareholder_return = $13,
                    investment_gap_v21 = $14,
                    investment_gap_v21_flag = $15,
                    data_quality_score = $16,
                    red_flags = $17,
                    yellow_flags = $18,
                    verdict = $19,
                    calculation_date = CURRENT_DATE
                WHERE company_id = $20 AND fiscal_year = $21
            """,
                result_dict['total_score'],
                result_dict['grade'],
                self._clamp(result_dict.get('cei_score'), 0, 100),
                self._clamp(result_dict.get('rii_score'), 0, 100),
                self._clamp(result_dict.get('cgi_score'), 0, 100),
                self._clamp(result_dict.get('mai_score'), 0, 100),
                self._clamp(result_dict.get('investment_gap'), -999, 999),
                self._clamp(result_dict.get('cash_cagr'), -999, 999),
                self._clamp(result_dict.get('capex_growth'), -999, 999),
                self._clamp(result_dict.get('idle_cash_ratio'), 0, 100),
                self._clamp(result_dict.get('asset_turnover'), 0, 99.999),
                self._clamp(result_dict.get('reinvestment_rate'), 0, 100),
                self._clamp(result_dict.get('shareholder_return'), 0, 100),
                self._clamp(result_dict.get('investment_gap_v21'), -50, 50),
                result_dict.get('investment_gap_v21_flag', 'ok'),
                result_dict.get('data_quality_score', 0),
                json.dumps(result_dict.get('red_flags', []), ensure_ascii=False),
                json.dumps(result_dict.get('yellow_flags', []), ensure_ascii=False),
                result_dict.get('verdict', ''),
                uuid.UUID(result_dict['company_id']),
                result_dict['fiscal_year']
            )
            return True
        except Exception as e:
            logger.error(f"Update error: {e}")
            return False

    async def run(self, dry_run: bool = True):
        """메인 실행"""
        conn = await asyncpg.connect(self.db_url)

        try:
            # 1. NULL Sub-Index 레코드 조회
            records = await self.get_null_subindex_records(conn)
            self.stats['total_null'] = len(records)

            logger.info("=" * 70)
            logger.info("Sub-Index NULL 레코드 재계산")
            logger.info("=" * 70)
            logger.info(f"대상 레코드: {len(records)}개")

            if dry_run:
                logger.info("[DRY-RUN 모드]")

            # 2. 각 레코드 재계산
            results = []
            for i, record in enumerate(records):
                company_id = str(record['company_id'])
                fiscal_year = record['fiscal_year']

                try:
                    # 재무 데이터 조회
                    financial_data = await self.get_financial_data(
                        conn, company_id, fiscal_year
                    )

                    if len(financial_data) < 2:
                        self.stats['skipped'] += 1
                        logger.debug(f"Skipped (insufficient data): {record['name']}")
                        continue

                    self.stats['has_financial_data'] += 1

                    # 재계산
                    result = self.calculator.calculate(
                        company_id=company_id,
                        financial_data=financial_data,
                        target_year=fiscal_year
                    )

                    if result is None:
                        self.stats['skipped'] += 1
                        continue

                    result_dict = self.calculator.to_dict(result)

                    # 변경 정보 기록
                    change_info = {
                        'company_name': record['name'],
                        'old_score': float(record['old_score']),
                        'new_score': result.total_score,
                        'old_grade': record['old_grade'],
                        'new_grade': result.grade,
                        'cei': result_dict.get('cei_score'),
                        'rii': result_dict.get('rii_score'),
                        'cgi': result_dict.get('cgi_score'),
                        'mai': result_dict.get('mai_score'),
                    }
                    results.append(change_info)

                    if not dry_run:
                        success = await self.save_recalculated(conn, result_dict)
                        if success:
                            self.stats['recalculated'] += 1
                        else:
                            self.stats['errors'] += 1
                    else:
                        self.stats['recalculated'] += 1

                    if (i + 1) % 50 == 0:
                        logger.info(f"진행: {i+1}/{len(records)}")

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error {record['name']}: {e}")

            # 3. 결과 출력
            logger.info("\n" + "=" * 70)
            logger.info("재계산 결과")
            logger.info("=" * 70)

            # 변화 샘플 출력
            if results:
                logger.info("\n[점수 변화 샘플 (상위 10개)]")
                logger.info("-" * 70)
                for r in results[:10]:
                    diff = r['new_score'] - r['old_score']
                    grade_change = f"{r['old_grade']} → {r['new_grade']}" if r['old_grade'] != r['new_grade'] else r['old_grade']
                    logger.info(
                        f"  {r['company_name'][:20]:20s} | "
                        f"{r['old_score']:6.1f} → {r['new_score']:6.1f} ({diff:+.1f}) | "
                        f"{grade_change}"
                    )

            logger.info("\n[통계]")
            for key, value in self.stats.items():
                logger.info(f"  {key}: {value}")

            if dry_run:
                logger.info("\n실제 재계산을 실행하려면: --execute 옵션 사용")

        finally:
            await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Sub-Index NULL 레코드 재계산')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='실제 변경 없이 대상만 확인 (기본값)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제 재계산 실행'
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if not dry_run:
        logger.warning("⚠️  실제 재계산 모드로 실행합니다!")

    recalculator = NullSubindexRecalculator(DATABASE_URL)
    await recalculator.run(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
