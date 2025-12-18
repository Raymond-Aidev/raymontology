#!/usr/bin/env python3
"""
재무지표 계산 엔진 테스트

샘플 회사들의 재무지표를 계산하고 출력
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Company, FinancialStatement
from app.services.financial_metrics import FinancialMetricsCalculator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_metrics():
    """재무지표 계산 테스트"""
    logger.info("=" * 60)
    logger.info("재무지표 계산 엔진 테스트")
    logger.info("=" * 60)
    logger.info("")

    calculator = FinancialMetricsCalculator()

    async with AsyncSessionLocal() as db:
        # 재무데이터가 있는 회사 5개 샘플 조회
        result = await db.execute(
            select(Company).
            join(FinancialStatement, Company.id == FinancialStatement.company_id).
            limit(5)
        )
        companies = result.scalars().all()

        logger.info(f"테스트 대상: {len(companies)}개 회사")
        logger.info("")

        for i, company in enumerate(companies, 1):
            logger.info("=" * 60)
            logger.info(f"{i}. {company.name} ({company.ticker or company.corp_code})")
            logger.info("=" * 60)

            # 재무제표 조회
            stmt_result = await db.execute(
                select(FinancialStatement).
                where(FinancialStatement.company_id == company.id).
                order_by(FinancialStatement.fiscal_year.desc(), FinancialStatement.quarter.desc()).
                limit(1)
            )
            latest_stmt = stmt_result.scalar_one_or_none()

            if latest_stmt:
                logger.info(f"최신 재무제표: {latest_stmt.fiscal_year}년 {latest_stmt.quarter or '연간'}")
            else:
                logger.info("재무제표 없음")
                logger.info("")
                continue

            # 재무지표 계산
            try:
                metrics = await calculator.get_company_metrics(db, str(company.id))

                logger.info("")
                logger.info("【재무지표】")
                logger.info(f"  1. 현금자산총액: {metrics['cash_assets_billion'] or 'N/A'} 억원")
                logger.info(f"  2. 매출 CAGR (2022-2024): {metrics['revenue_cagr'] or 'N/A'}%")
                logger.info(f"  3. 매출채권 회전율: {metrics['ar_turnover'] or 'N/A'} 회")
                logger.info(f"  4. 매입채무 회전율: {metrics['ap_turnover'] or 'N/A'} 회")
                logger.info(f"  5. 재고자산 회전율: {metrics['inventory_turnover'] or 'N/A'} 회")
                logger.info(f"  6. 부채비율: {metrics['debt_ratio'] or 'N/A'}%")
                logger.info(f"  7. 유동비율: {metrics['current_ratio'] or 'N/A'}%")

                # 건전성 분석
                health = await calculator.analyze_company_health(db, str(company.id))

                logger.info("")
                logger.info(f"【재무 건전성 점수】{health['health_score']:.1f}/100")

                if health['strengths']:
                    logger.info("")
                    logger.info("【강점】")
                    for strength in health['strengths']:
                        logger.info(f"  ✓ {strength}")

                if health['warnings']:
                    logger.info("")
                    logger.info("【주의사항】")
                    for warning in health['warnings']:
                        logger.info(f"  ⚠ {warning}")

                logger.info("")

            except Exception as e:
                logger.error(f"지표 계산 실패: {e}", exc_info=True)
                logger.info("")

    logger.info("=" * 60)
    logger.info("테스트 완료!")
    logger.info("=" * 60)


async def test_batch_metrics():
    """배치 계산 테스트"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("배치 재무지표 계산 테스트")
    logger.info("=" * 60)
    logger.info("")

    calculator = FinancialMetricsCalculator()

    async with AsyncSessionLocal() as db:
        # 재무데이터가 있는 회사 10개
        result = await db.execute(
            select(Company.id, Company.name).
            join(FinancialStatement, Company.id == FinancialStatement.company_id).
            limit(10)
        )
        companies_data = result.all()

        company_ids = [str(row[0]) for row in companies_data]
        company_names = {str(row[0]): row[1] for row in companies_data}

        logger.info(f"배치 처리: {len(company_ids)}개 회사")
        logger.info("")

        # 배치 계산
        batch_results = await calculator.get_batch_metrics(db, company_ids)

        # 결과 출력
        for company_id, metrics in batch_results.items():
            company_name = company_names.get(company_id, "Unknown")
            logger.info(f"{company_name}:")
            logger.info(f"  현금자산: {metrics['cash_assets_billion'] or 'N/A'}억원 | "
                       f"CAGR: {metrics['revenue_cagr'] or 'N/A'}% | "
                       f"부채비율: {metrics['debt_ratio'] or 'N/A'}%")

        logger.info("")
        logger.info("배치 계산 완료!")


async def main():
    """메인 함수"""
    await test_metrics()
    await test_batch_metrics()


if __name__ == "__main__":
    asyncio.run(main())
