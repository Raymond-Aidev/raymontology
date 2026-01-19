#!/usr/bin/env python3
"""
CB 투자 이력 집계 및 INVESTED_IN 관계 생성

목적:
1. Subscriber → CB → Company 경로에서 투자 이력 집계
2. Subscriber → Company 직접 연결 (INVESTED_IN 관계) 생성
3. total_investments, investment_count 속성 계산
4. 인수자의 투자 패턴 분석 가능하게 함

그래프 구조:
- 기존: (Subscriber)-[:SUBSCRIBED]->(CB)<-[:ISSUED]-(Company)
- 추가: (Subscriber)-[:INVESTED_IN {
    total_amount: 5000000000,
    investment_count: 3,
    first_investment: "2020-01",
    latest_investment: "2024-03",
    avg_investment: 1666666667
  }]->(Company)
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CBInvestmentAggregator:
    """CB 투자 이력 집계기"""

    def __init__(self):
        self.driver = None
        self.stats = {
            "subscribers_processed": 0,
            "invested_in_created": 0,
            "total_investment_amount": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        await self.driver.verify_connectivity()
        logger.info(f"✓ Neo4j 연결 성공: {settings.neo4j_uri}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()

    async def step1_check_existing_data(self):
        """기존 데이터 확인"""
        logger.info("=" * 60)
        logger.info("Step 1: 기존 데이터 확인")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # Subscriber 수
            result = await session.run("""
                MATCH (s:Subscriber)
                RETURN COUNT(s) as count
            """)
            subscriber_count = (await result.single())["count"]
            logger.info(f"Subscriber 노드: {subscriber_count:,}개")

            # SUBSCRIBED 관계 수
            result = await session.run("""
                MATCH ()-[r:SUBSCRIBED]->()
                RETURN COUNT(r) as count
            """)
            subscribed_count = (await result.single())["count"]
            logger.info(f"SUBSCRIBED 관계: {subscribed_count:,}개")

            # 기존 INVESTED_IN 관계 (있다면)
            result = await session.run("""
                MATCH ()-[r:INVESTED_IN]->()
                RETURN COUNT(r) as count
            """)
            invested_in_count = (await result.single())["count"]
            logger.info(f"기존 INVESTED_IN 관계: {invested_in_count:,}개")

    async def step2_delete_existing_invested_in(self):
        """기존 INVESTED_IN 관계 삭제 (재계산을 위해)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 2: 기존 INVESTED_IN 관계 삭제")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                MATCH ()-[r:INVESTED_IN]->()
                DELETE r
                RETURN COUNT(r) as deleted_count
            """)
            deleted_count = (await result.single())["deleted_count"]
            logger.info(f"✓ 삭제된 INVESTED_IN 관계: {deleted_count:,}개")

    async def step3_create_invested_in_relationships(self):
        """
        INVESTED_IN 관계 생성

        각 Subscriber가 각 Company에 투자한 총액과 횟수를 집계
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 3: INVESTED_IN 관계 생성")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                // Subscriber가 CB를 통해 투자한 Company 찾기
                MATCH (s:Subscriber)-[sub:SUBSCRIBED]->(cb:ConvertibleBond)
                MATCH (c:Company)-[:ISSUED]->(cb)

                // 집계
                WITH s, c,
                     COUNT(cb) as investment_count,
                     SUM(COALESCE(sub.subscription_amount, 0)) as total_amount,
                     COLLECT(cb.issue_date) as investment_dates,
                     AVG(COALESCE(sub.subscription_amount, 0)) as avg_amount

                // 날짜 정렬
                WITH s, c, investment_count, total_amount, avg_amount,
                     investment_dates[0] as first_investment,
                     investment_dates[-1] as latest_investment

                // INVESTED_IN 관계 생성
                CREATE (s)-[inv:INVESTED_IN {
                    total_amount: total_amount,
                    investment_count: investment_count,
                    first_investment: first_investment,
                    latest_investment: latest_investment,
                    avg_investment: avg_amount
                }]->(c)

                RETURN COUNT(inv) as created_count,
                       SUM(total_amount) as total_invested
            """)

            stats = await result.single()
            self.stats["invested_in_created"] = stats["created_count"]
            self.stats["total_investment_amount"] = stats["total_invested"]

            logger.info(f"✓ INVESTED_IN 관계 생성: {stats['created_count']:,}개")
            logger.info(f"  총 투자액: {stats['total_invested']:,}원")

    async def step4_update_subscriber_properties(self):
        """
        Subscriber 노드에 투자 통계 속성 추가

        - total_investments: 총 투자 회사 수
        - total_investment_amount: 총 투자액
        - investment_diversity: 투자 다양성 점수 (0~1)
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 4: Subscriber 투자 통계 업데이트")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (s:Subscriber)
                OPTIONAL MATCH (s)-[inv:INVESTED_IN]->(c:Company)

                WITH s,
                     COUNT(DISTINCT c) as total_investments,
                     SUM(inv.total_amount) as total_amount,
                     SUM(inv.investment_count) as total_cb_count

                SET s.total_investments = total_investments,
                    s.total_investment_amount = total_amount,
                    s.total_cb_count = total_cb_count,
                    s.investment_diversity = CASE
                        WHEN total_investments = 0 THEN 0.0
                        WHEN total_investments = 1 THEN 0.2
                        WHEN total_investments <= 3 THEN 0.4
                        WHEN total_investments <= 5 THEN 0.6
                        WHEN total_investments <= 10 THEN 0.8
                        ELSE 1.0
                    END

                RETURN COUNT(s) as updated_count,
                       AVG(total_investments) as avg_companies,
                       MAX(total_investments) as max_companies
            """)

            stats = await result.single()
            logger.info(f"✓ Subscriber 속성 업데이트: {stats['updated_count']:,}개")
            logger.info(f"  평균 투자 회사 수: {stats['avg_companies']:.2f}개")
            logger.info(f"  최대 투자 회사 수: {stats['max_companies']}개")

    async def step5_create_indexes(self):
        """투자 관련 인덱스 생성"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 5: 인덱스 생성")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # Subscriber.total_investments 인덱스
            try:
                await session.run("""
                    CREATE INDEX subscriber_total_investments IF NOT EXISTS
                    FOR (s:Subscriber) ON (s.total_investments)
                """)
                logger.info("✓ Subscriber.total_investments 인덱스 생성")
            except Exception as e:
                logger.warning(f"인덱스 생성 실패: {e}")

            # Subscriber.investment_diversity 인덱스
            try:
                await session.run("""
                    CREATE INDEX subscriber_investment_diversity IF NOT EXISTS
                    FOR (s:Subscriber) ON (s.investment_diversity)
                """)
                logger.info("✓ Subscriber.investment_diversity 인덱스 생성")
            except Exception as e:
                logger.warning(f"인덱스 생성 실패: {e}")

    async def step6_analyze_results(self):
        """결과 분석"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 6: 투자 패턴 분석")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 최대 투자자 TOP 10
            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE s.total_investments > 0
                RETURN s.name as subscriber,
                       s.total_investments as company_count,
                       s.total_cb_count as cb_count,
                       s.total_investment_amount as total_amount
                ORDER BY s.total_investments DESC
                LIMIT 10
            """)

            logger.info("\n최대 투자자 TOP 10 (투자 회사 수 기준):")
            rank = 1
            async for record in result:
                logger.info(
                    f"  {rank:2d}. {record['subscriber']}: "
                    f"{record['company_count']}개 회사, "
                    f"{record['cb_count']}개 CB, "
                    f"총 {record['total_amount']:,}원"
                )
                rank += 1

            # 투자 다양성 분포
            result = await session.run("""
                MATCH (s:Subscriber)
                WITH s.total_investments as count, COUNT(s) as subscriber_count
                RETURN count, subscriber_count
                ORDER BY count DESC
                LIMIT 10
            """)

            logger.info("\n투자 회사 수 분포 (TOP 10):")
            async for record in result:
                logger.info(f"  {record['count']}개 회사: {record['subscriber_count']:,}명")

            # 투자 집중도 분석 (1개 회사에만 투자 vs 분산 투자)
            result = await session.run("""
                MATCH (s:Subscriber)
                WITH
                    CASE
                        WHEN s.total_investments = 1 THEN 'Single Company'
                        WHEN s.total_investments <= 3 THEN '2-3 Companies'
                        WHEN s.total_investments <= 5 THEN '4-5 Companies'
                        WHEN s.total_investments <= 10 THEN '6-10 Companies'
                        ELSE '10+ Companies'
                    END as investment_pattern,
                    COUNT(s) as count
                RETURN investment_pattern, count
                ORDER BY investment_pattern
            """)

            logger.info("\n투자 패턴 분포:")
            async for record in result:
                logger.info(f"  {record['investment_pattern']}: {record['count']:,}명")

            # 고위험 패턴: 동일 회사에 여러 CB 투자
            result = await session.run("""
                MATCH (s:Subscriber)-[inv:INVESTED_IN]->(c:Company)
                WHERE inv.investment_count > 1
                RETURN s.name as subscriber,
                       c.name as company,
                       inv.investment_count as cb_count,
                       inv.total_amount as total_amount
                ORDER BY inv.investment_count DESC
                LIMIT 10
            """)

            logger.info("\n동일 회사 다수 CB 투자 (잠재적 관계사 투자):")
            async for record in result:
                logger.info(
                    f"  {record['subscriber']} → {record['company']}: "
                    f"{record['cb_count']}개 CB, "
                    f"총 {record['total_amount']:,}원"
                )

    async def run(self):
        """전체 집계 프로세스 실행"""
        logger.info("=" * 60)
        logger.info("CB 투자 이력 집계 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            await self.step1_check_existing_data()
            await self.step2_delete_existing_invested_in()
            await self.step3_create_invested_in_relationships()
            await self.step4_update_subscriber_properties()
            await self.step5_create_indexes()
            await self.step6_analyze_results()

            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ 집계 완료!")
            logger.info("=" * 60)
            logger.info(f"INVESTED_IN 관계 생성: {self.stats['invested_in_created']:,}개")
            logger.info(f"총 투자액: {self.stats['total_investment_amount']:,}원")
            logger.info(f"에러: {self.stats['errors']:,}개")
            logger.info("")

        except Exception as e:
            logger.error(f"집계 중 오류 발생: {e}", exc_info=True)
            raise


async def main():
    """메인 함수"""
    async with CBInvestmentAggregator() as aggregator:
        await aggregator.run()


if __name__ == "__main__":
    asyncio.run(main())
