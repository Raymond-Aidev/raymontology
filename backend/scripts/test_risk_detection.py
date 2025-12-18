#!/usr/bin/env python3
"""
위험 패턴 탐지 엔진 테스트

실제 데이터로 8가지 위험 패턴을 검증
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Company
from app.services.risk_detection import RiskDetectionEngine
from app.config import settings
from neo4j import AsyncGraphDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_single_company_risk(company_id: str, company_name: str):
    """특정 회사의 위험도 분석"""
    logger.info("=" * 70)
    logger.info(f"위험도 분석: {company_name}")
    logger.info("=" * 70)

    # Neo4j driver
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        engine = RiskDetectionEngine(driver)

        async with AsyncSessionLocal() as db:
            # 종합 위험도 분석
            analysis = await engine.analyze_company_risk(db, company_id)

            logger.info("")
            logger.info(f"【종합 위험도】 {analysis['overall_risk_level'].upper()}")
            logger.info(f"【위험 점수】 {analysis['risk_score']:.1f}/100")
            logger.info("")

            # 각 패턴별 분석 결과
            patterns = analysis["patterns"]

            # 1. 순환 투자
            circular = patterns.get("circular_investment", [])
            if circular:
                logger.info(f"【1. 순환 투자】 발견: {len(circular)}개")
                for i, cycle in enumerate(circular[:3], 1):
                    logger.info(f"  {i}. {' → '.join(cycle['cycle'])}")
                    logger.info(f"     총액: {cycle['total_amount']:,}원 | 위험도: {cycle['risk_level']}")
            else:
                logger.info("【1. 순환 투자】 없음")

            logger.info("")

            # 2. 과도한 CB 발행
            cb_data = patterns.get("excessive_cb", {})
            logger.info(f"【2. 과도한 CB 발행】")
            logger.info(f"  최근 12개월 CB 발행: {cb_data.get('cb_count', 0)}건")
            logger.info(f"  총 발행액: {cb_data.get('total_amount', 0):,}원")
            if cb_data.get('avg_interval_days'):
                logger.info(f"  평균 발행 간격: {cb_data['avg_interval_days']:.1f}일")
            logger.info(f"  위험도: {cb_data.get('risk_level', 'N/A')}")

            logger.info("")

            # 3. 임원 집중도
            officer_conc = patterns.get("officer_concentration", {})
            officers = officer_conc.get("high_concentration_officers", [])
            logger.info(f"【3. 임원 집중도】")
            if officers:
                logger.info(f"  다수 겸직 임원: {len(officers)}명")
                for officer in officers[:3]:
                    logger.info(f"  - {officer['officer_name']}: {officer['position_count']}개 회사 겸직 "
                              f"(영향력: {officer['influence_score']:.3f})")
            else:
                logger.info("  다수 겸직 임원 없음")
            logger.info(f"  위험도: {officer_conc.get('risk_level', 'N/A')}")

            logger.info("")

            # 4. 재무 악화 + CB
            financial_cb = patterns.get("financial_distress_cb", {})
            logger.info(f"【4. 재무 악화 + CB 발행】")
            logger.info(f"  재무 건전성 점수: {financial_cb.get('health_score', 'N/A'):.1f}/100")
            logger.info(f"  최근 CB 발행: {financial_cb.get('recent_cb_count', 0)}건")
            logger.info(f"  CB 총액: {financial_cb.get('cb_total_amount', 0):,}원")

            warnings = financial_cb.get("warnings", [])
            if warnings:
                logger.info("  ⚠ 경고:")
                for warning in warnings[:3]:
                    logger.info(f"    - {warning}")

            logger.info(f"  위험도: {financial_cb.get('risk_level', 'N/A')}")

            logger.info("")

            # 5. 특수관계자 거래
            related = patterns.get("related_party_transactions", {})
            logger.info(f"【5. 특수관계자 거래】")

            affiliate_inv = related.get("affiliate_investments", [])
            if affiliate_inv:
                logger.info(f"  계열사 CB 투자: {len(affiliate_inv)}건")
                for inv in affiliate_inv[:2]:
                    logger.info(f"    - {inv['company']}: {inv['investment_count']}건, "
                              f"{inv['total_amount']:,}원")

            officer_inv = related.get("officer_linked_investments", [])
            if officer_inv:
                logger.info(f"  임원 겸직 회사 CB 투자: {len(officer_inv)}건")
                for inv in officer_inv[:2]:
                    logger.info(f"    - {inv['company']} (임원: {inv['officer']}): "
                              f"{inv['investment_count']}건")

            if not affiliate_inv and not officer_inv:
                logger.info("  특수관계자 거래 없음")

            logger.info(f"  위험도: {related.get('risk_level', 'N/A')}")

            logger.info("")

            # 6. 임원 이동 패턴
            movement = patterns.get("officer_movement", {})
            high_risk_officers = movement.get("high_risk_officers", [])
            logger.info(f"【6. 임원 이동 패턴】")
            if high_risk_officers:
                logger.info(f"  잦은 이동 임원: {len(high_risk_officers)}명")
                for officer in high_risk_officers[:3]:
                    logger.info(f"    - {officer['officer']}: {officer['career_count']}회 경력 변경")
            else:
                logger.info("  특이 패턴 없음")
            logger.info(f"  위험도: {movement.get('risk_level', 'N/A')}")

            logger.info("")

            # 7. CB 투자자 집중
            investor_conc = patterns.get("cb_investor_concentration", {})
            top_investors = investor_conc.get("top_investors", [])
            logger.info(f"【7. CB 투자자 집중】")
            if top_investors:
                logger.info(f"  집중 투자자: {len(top_investors)}명")
                for inv in top_investors[:3]:
                    logger.info(f"    - {inv['investor']}: {inv['investment_count']}건 "
                              f"(집중도: {inv['concentration_ratio']*100:.1f}%)")
            else:
                logger.info("  투자자 집중 없음")
            logger.info(f"  위험도: {investor_conc.get('risk_level', 'N/A')}")

            logger.info("")

            # 8. 계열사 연쇄 부실
            affiliate_risk = patterns.get("affiliate_chain_risk", {})
            logger.info(f"【8. 계열사 연쇄 부실】")
            logger.info(f"  전체 계열사: {affiliate_risk.get('total_affiliates', 0)}개")
            if affiliate_risk.get("note"):
                logger.info(f"  참고: {affiliate_risk['note']}")
            logger.info(f"  위험도: {affiliate_risk.get('risk_level', 'N/A')}")

            logger.info("")

    finally:
        await driver.close()


async def test_multiple_companies():
    """여러 회사의 위험도 비교 분석"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("다수 회사 위험도 비교 분석")
    logger.info("=" * 70)
    logger.info("")

    # CB를 많이 발행한 회사 조회
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
                WITH c, COUNT(cb) as cb_count
                WHERE cb_count >= 2
                RETURN c.id as company_id, c.name as company_name, cb_count
                ORDER BY cb_count DESC
                LIMIT 5
            """)
            companies = await result.data()

        if not companies:
            logger.info("CB 발행 회사 없음")
            return

        engine = RiskDetectionEngine(driver)
        results = []

        async with AsyncSessionLocal() as db:
            for company in companies:
                company_id = company["company_id"]
                company_name = company["company_name"]
                cb_count = company["cb_count"]

                try:
                    analysis = await engine.analyze_company_risk(db, company_id)
                    results.append({
                        "name": company_name,
                        "cb_count": cb_count,
                        "risk_score": analysis["risk_score"],
                        "risk_level": analysis["overall_risk_level"]
                    })
                except Exception as e:
                    logger.error(f"분석 실패: {company_name} - {e}")

        # 결과 출력
        logger.info("【위험도 순위】")
        logger.info("")
        results.sort(key=lambda x: x["risk_score"], reverse=True)

        for i, result in enumerate(results, 1):
            logger.info(f"{i}. {result['name']}")
            logger.info(f"   CB 발행: {result['cb_count']}건 | "
                       f"위험 점수: {result['risk_score']:.1f}/100 | "
                       f"등급: {result['risk_level'].upper()}")
            logger.info("")

    finally:
        await driver.close()


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="위험 패턴 탐지 테스트")
    parser.add_argument("--company-id", help="특정 회사 ID (UUID)")
    parser.add_argument("--company-name", help="특정 회사명")
    args = parser.parse_args()

    if args.company_id and args.company_name:
        # 특정 회사 분석
        await test_single_company_risk(args.company_id, args.company_name)
    else:
        # 샘플 회사로 테스트
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            # CB를 발행한 회사 중 1개 샘플
            result = await db.execute(text("""
                SELECT DISTINCT c.id, c.name
                FROM companies c
                JOIN convertible_bonds cb ON c.id = cb.company_id
                LIMIT 1
            """))
            company = result.first()

            if company:
                await test_single_company_risk(str(company.id), company.name)
            else:
                logger.warning("CB 발행 회사를 찾을 수 없습니다")

        # 다수 회사 비교
        await test_multiple_companies()

    logger.info("=" * 70)
    logger.info("✓ 테스트 완료")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
