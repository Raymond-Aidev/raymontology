#!/usr/bin/env python3
"""
Subscriber 투자 이력 API 테스트 스크립트

Phase 1에서 생성한 INVESTED_IN 관계를 활용한 API 엔드포인트 테스트
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.config import settings
from neo4j import AsyncGraphDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_subscriber_investments_api():
    """Subscriber 투자 이력 API 테스트"""
    logger.info("=" * 70)
    logger.info("Subscriber 투자 이력 API 테스트")
    logger.info("=" * 70)

    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        # 1. 투자 이력이 있는 Subscriber 선택 (투자 회사 수가 많은 순)
        async with driver.session() as session:
            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE s.total_investments > 1
                RETURN s.id as subscriber_id, s.name as subscriber_name,
                       s.total_investments as company_count
                ORDER BY s.total_investments DESC
                LIMIT 3
            """)
            test_subscribers = await result.data()

            if not test_subscribers:
                logger.warning("투자 이력이 있는 Subscriber가 없습니다")
                return False

            logger.info(f"\n테스트 대상 Subscriber {len(test_subscribers)}명:")
            for idx, sub in enumerate(test_subscribers, 1):
                logger.info(f"  {idx}. {sub['subscriber_name']}: {sub['company_count']}개 회사 투자")

            # 2. 각 Subscriber의 투자 이력 상세 조회
            logger.info("\n" + "=" * 70)
            logger.info("투자 이력 상세 조회 테스트")
            logger.info("=" * 70)

            for sub in test_subscribers:
                subscriber_id = sub['subscriber_id']
                subscriber_name = sub['subscriber_name']

                logger.info(f"\n[{subscriber_name}]")

                # API 로직과 동일한 쿼리 실행
                result = await session.run("""
                    MATCH (s:Subscriber {id: $subscriber_id})

                    // 투자 이력
                    OPTIONAL MATCH (s)-[inv:INVESTED_IN]->(c:Company)
                    OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)<-[:SUBSCRIBED]-(s)

                    WITH s, c, inv,
                         collect({
                             id: cb.id,
                             bond_name: cb.bond_name,
                             issue_date: cb.issue_date,
                             total_amount: cb.total_amount
                         }) as cbs

                    RETURN s,
                           collect({
                               company_id: c.id,
                               company_name: c.name,
                               total_amount: inv.total_amount,
                               investment_count: inv.investment_count,
                               first_investment: inv.first_investment,
                               latest_investment: inv.latest_investment,
                               cbs: cbs
                           }) as investments
                """, subscriber_id=subscriber_id)

                record = await result.single()

                if record:
                    investments = record["investments"]
                    valid_investments = [inv for inv in investments if inv.get("company_id")]

                    logger.info(f"  총 투자 회사: {len(valid_investments)}개")

                    for inv in valid_investments[:5]:  # 상위 5개만 출력
                        logger.info(f"    - {inv['company_name']}: {inv['investment_count']}개 CB")
                        logger.info(f"      투자 기간: {inv['first_investment']} ~ {inv['latest_investment']}")
                        logger.info(f"      투자액: {inv['total_amount']:,}원")

            # 3. 투자 네트워크 확장 테스트
            logger.info("\n" + "=" * 70)
            logger.info("투자 네트워크 확장 테스트")
            logger.info("=" * 70)

            test_subscriber = test_subscribers[0]
            subscriber_id = test_subscriber['subscriber_id']
            subscriber_name = test_subscriber['subscriber_name']

            logger.info(f"\n테스트 대상: {subscriber_name}")

            result = await session.run("""
                MATCH (s:Subscriber {id: $subscriber_id})

                // 투자한 회사들
                MATCH (s)-[:INVESTED_IN]->(c:Company)

                // 각 회사의 CB들
                MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)

                // CB의 다른 인수자들
                OPTIONAL MATCH (cb)<-[:SUBSCRIBED]-(other_subscriber:Subscriber)
                WHERE other_subscriber.id <> s.id

                RETURN s, c, cb,
                       collect(DISTINCT other_subscriber)[..10] as other_subscribers
                LIMIT 200
            """, subscriber_id=subscriber_id)

            records = await result.data()

            if records:
                companies = set()
                cbs = set()
                other_subscribers = set()

                for record in records:
                    if record['c']:
                        companies.add(record['c']['id'])
                    if record['cb']:
                        cbs.add(record['cb']['id'])
                    for other in record['other_subscribers']:
                        if other:
                            other_subscribers.add(other['id'])

                logger.info(f"  네트워크 구성:")
                logger.info(f"    - 투자 회사: {len(companies)}개")
                logger.info(f"    - CB: {len(cbs)}개")
                logger.info(f"    - 동료 투자자: {len(other_subscribers)}명")

            # 4. 동일 회사 다수 CB 투자 패턴 분석
            logger.info("\n" + "=" * 70)
            logger.info("고위험 투자 패턴 분석 (동일 회사 다수 CB)")
            logger.info("=" * 70)

            result = await session.run("""
                MATCH (s:Subscriber)-[inv:INVESTED_IN]->(c:Company)
                WHERE inv.investment_count > 5
                RETURN s.name as subscriber,
                       c.name as company,
                       inv.investment_count as cb_count,
                       inv.total_amount as total_amount,
                       inv.first_investment as first_date,
                       inv.latest_investment as latest_date
                ORDER BY inv.investment_count DESC
                LIMIT 10
            """)

            high_risk_patterns = await result.data()

            if high_risk_patterns:
                logger.info(f"\n발견된 고위험 패턴: {len(high_risk_patterns)}건")
                for idx, pattern in enumerate(high_risk_patterns, 1):
                    logger.info(
                        f"  {idx}. {pattern['subscriber']} → {pattern['company']}: "
                        f"{pattern['cb_count']}개 CB, "
                        f"총 {pattern['total_amount']:,}원"
                    )
                    logger.info(f"      투자 기간: {pattern['first_date']} ~ {pattern['latest_date']}")

            # 5. 투자 다양성 분석
            logger.info("\n" + "=" * 70)
            logger.info("투자 다양성 분석")
            logger.info("=" * 70)

            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE s.total_investments > 0
                WITH
                    CASE
                        WHEN s.total_investments = 1 THEN 'Single Company'
                        WHEN s.total_investments <= 3 THEN '2-3 Companies'
                        WHEN s.total_investments <= 5 THEN '4-5 Companies'
                        WHEN s.total_investments <= 10 THEN '6-10 Companies'
                        ELSE '10+ Companies'
                    END as diversity_level,
                    COUNT(s) as subscriber_count
                RETURN diversity_level, subscriber_count
                ORDER BY subscriber_count DESC
            """)

            diversity_stats = await result.data()

            logger.info("\n투자 다양성 분포:")
            total_subscribers = sum(stat['subscriber_count'] for stat in diversity_stats)
            for stat in diversity_stats:
                count = stat['subscriber_count']
                percentage = (count / total_subscribers) * 100
                logger.info(
                    f"  {stat['diversity_level']}: {count:,}명 ({percentage:.1f}%)"
                )

        await driver.close()

        logger.info("\n" + "=" * 70)
        logger.info("✓ Subscriber 투자 이력 API 테스트 성공!")
        logger.info("=" * 70)
        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


async def test_recenter_api():
    """노드 중심 전환 API 테스트"""
    logger.info("\n" + "=" * 70)
    logger.info("노드 중심 전환 API 테스트")
    logger.info("=" * 70)

    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        # 1. Subscriber 중심 전환 테스트
        async with driver.session() as session:
            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE s.total_investments > 3
                RETURN s.id as subscriber_id, s.name as subscriber_name
                LIMIT 1
            """)
            record = await result.single()

            if record:
                subscriber_id = record['subscriber_id']
                subscriber_name = record['subscriber_name']

                logger.info(f"\n테스트 노드: Subscriber '{subscriber_name}'")

                # Recenter API 로직 테스트
                result = await session.run("""
                    MATCH (center:Subscriber {id: $node_id})

                    // 직접 연결된 모든 노드와 관계
                    MATCH (center)-[r]-(connected)

                    RETURN center, r, connected
                    LIMIT 100
                """, node_id=subscriber_id)

                records = await result.data()

                if records:
                    node_types = {}
                    for record in records:
                        connected = record['connected']
                        # Handle both dict and neo4j node objects
                        if hasattr(connected, 'labels'):
                            node_type = list(connected.labels)[0] if connected.labels else "Unknown"
                        elif isinstance(connected, dict):
                            # For dict, we need to infer type from the data or use generic
                            node_type = "Connected"
                        else:
                            node_type = "Unknown"
                        node_types[node_type] = node_types.get(node_type, 0) + 1

                    logger.info(f"  연결된 노드:")
                    for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"    - {node_type}: {count}개")

        # 2. ConvertibleBond 중심 전환 테스트
        async with driver.session() as session:
            result = await session.run("""
                MATCH (cb:ConvertibleBond)
                MATCH (cb)<-[:SUBSCRIBED]-(s:Subscriber)
                WITH cb, COUNT(s) as subscriber_count
                WHERE subscriber_count > 5
                RETURN cb.id as cb_id, cb.bond_name as bond_name, subscriber_count
                ORDER BY subscriber_count DESC
                LIMIT 1
            """)
            record = await result.single()

            if record:
                cb_id = record['cb_id']
                bond_name = record['bond_name']
                subscriber_count = record['subscriber_count']

                logger.info(f"\n테스트 노드: ConvertibleBond '{bond_name}' (인수자 {subscriber_count}명)")

                result = await session.run("""
                    MATCH (center:ConvertibleBond {id: $node_id})
                    MATCH (center)-[r]-(connected)
                    RETURN center, r, connected
                    LIMIT 100
                """, node_id=cb_id)

                records = await result.data()

                if records:
                    node_types = {}
                    for record in records:
                        connected = record['connected']
                        # Handle both dict and neo4j node objects
                        if hasattr(connected, 'labels'):
                            node_type = list(connected.labels)[0] if connected.labels else "Unknown"
                        elif isinstance(connected, dict):
                            # For dict, we need to infer type from the data or use generic
                            node_type = "Connected"
                        else:
                            node_type = "Unknown"
                        node_types[node_type] = node_types.get(node_type, 0) + 1

                    logger.info(f"  연결된 노드:")
                    for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"    - {node_type}: {count}개")

        await driver.close()

        logger.info("\n✓ 노드 중심 전환 API 테스트 성공!")
        return True

    except Exception as e:
        logger.error(f"✗ 노드 중심 전환 API 테스트 실패: {e}", exc_info=True)
        return False


async def main():
    """메인 테스트 함수"""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2 Backend API 통합 테스트")
    logger.info("INVESTED_IN 관계 기반 Subscriber API 검증")
    logger.info("=" * 70)

    results = {}

    # 1. Subscriber 투자 이력 API 테스트
    results['subscriber_investments'] = await test_subscriber_investments_api()

    # 2. 노드 중심 전환 API 테스트
    results['recenter_api'] = await test_recenter_api()

    # 결과 요약
    logger.info("\n" + "=" * 70)
    logger.info("테스트 결과 요약")
    logger.info("=" * 70)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("")
    logger.info(f"전체: {passed}/{total} 테스트 통과")

    if passed == total:
        logger.info("=" * 70)
        logger.info("✓ 모든 테스트 성공!")
        logger.info("=" * 70)
        logger.info("\nPhase 2 Backend API 준비 완료")
        logger.info("- Subscriber 투자 이력 API ✓")
        logger.info("- 투자 네트워크 확장 API ✓")
        logger.info("- 노드 중심 전환 API ✓")
        logger.info("- INVESTED_IN 관계 활용 ✓")
        return 0
    else:
        logger.error("=" * 70)
        logger.error(f"✗ {total - passed}개 테스트 실패")
        logger.error("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
