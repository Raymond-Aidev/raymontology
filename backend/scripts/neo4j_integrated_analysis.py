#!/usr/bin/env python3
"""
Neo4j 통합 그래프 분석

전체 네트워크의 핵심 인사이트 도출:
- 가장 영향력 있는 회사
- 가장 영향력 있는 임원
- 핵심 투자자
- 네트워크 클러스터
- 겸직 임원
- 순환 투자 구조
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jIntegratedAnalyzer:
    """통합 그래프 분석기"""

    def __init__(self):
        self.driver = None

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

    async def analyze_most_connected_companies(self):
        """가장 많이 연결된 회사 (허브 회사)"""
        logger.info("=" * 60)
        logger.info("1. 가장 많이 연결된 회사 (네트워크 허브)")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 전체 연결 수 (임원 + 계열사 + CB)
            result = await session.run("""
                MATCH (c:Company)
                OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
                OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(a:Company)
                OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
                WITH c,
                     COUNT(DISTINCT o) as officer_count,
                     COUNT(DISTINCT a) as affiliate_count,
                     COUNT(DISTINCT cb) as cb_count
                RETURN c.name as company,
                       officer_count,
                       affiliate_count,
                       cb_count,
                       (officer_count + affiliate_count + cb_count) as total_connections
                ORDER BY total_connections DESC
                LIMIT 10
            """)

            companies = []
            async for record in result:
                companies.append({
                    "company": record["company"],
                    "officers": record["officer_count"],
                    "affiliates": record["affiliate_count"],
                    "cbs": record["cb_count"],
                    "total": record["total_connections"]
                })

            for idx, company in enumerate(companies, 1):
                logger.info(f"{idx:2d}. {company['company']}")
                logger.info(f"     임원: {company['officers']:,}명 | 계열사: {company['affiliates']:,}개 | CB: {company['cbs']:,}개 | 총: {company['total']:,}개")

    async def analyze_most_influential_officers(self):
        """가장 영향력 있는 임원 (여러 회사 겸직)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("2. 가장 영향력 있는 임원 (여러 회사 겸직)")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                WITH o, COLLECT(DISTINCT c.name) as companies, COUNT(DISTINCT c) as company_count
                WHERE company_count > 1
                RETURN o.name as officer,
                       company_count,
                       companies
                ORDER BY company_count DESC
                LIMIT 10
            """)

            officers = []
            async for record in result:
                officers.append({
                    "officer": record["officer"],
                    "count": record["company_count"],
                    "companies": record["companies"]
                })

            if officers:
                for idx, officer in enumerate(officers, 1):
                    logger.info(f"{idx:2d}. {officer['officer']}: {officer['count']}개 회사")
                    logger.info(f"     {', '.join(officer['companies'][:5])}")
            else:
                logger.info("겸직 임원이 없습니다.")

    async def analyze_most_active_investors(self):
        """가장 활발한 투자자 (여러 CB 인수)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("3. 가장 활발한 CB 투자자")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb:ConvertibleBond)
                MATCH (c:Company)-[:ISSUED]->(cb)
                WITH s,
                     COUNT(DISTINCT cb) as cb_count,
                     COUNT(DISTINCT c) as company_count,
                     COLLECT(DISTINCT c.name) as companies
                RETURN s.name as subscriber,
                       cb_count,
                       company_count,
                       companies
                ORDER BY cb_count DESC
                LIMIT 10
            """)

            investors = []
            async for record in result:
                investors.append({
                    "subscriber": record["subscriber"],
                    "cb_count": record["cb_count"],
                    "company_count": record["company_count"],
                    "companies": record["companies"]
                })

            for idx, investor in enumerate(investors, 1):
                logger.info(f"{idx:2d}. {investor['subscriber']}")
                logger.info(f"     CB: {investor['cb_count']:,}개 | 투자 회사: {investor['company_count']:,}개")
                logger.info(f"     {', '.join(investor['companies'][:5])}")

    async def analyze_board_member_networks(self):
        """이사회 멤버 네트워크 (이사로 있는 임원)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("4. 이사회 멤버 네트워크")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 가장 많은 이사회에 참여하는 임원
            result = await session.run("""
                MATCH (o:Officer)-[:BOARD_MEMBER_AT]->(c:Company)
                WITH o, COUNT(DISTINCT c) as board_count, COLLECT(DISTINCT c.name) as companies
                RETURN o.name as officer,
                       o.position as position,
                       board_count,
                       companies
                ORDER BY board_count DESC
                LIMIT 10
            """)

            board_members = []
            async for record in result:
                board_members.append({
                    "officer": record["officer"],
                    "position": record["position"],
                    "count": record["board_count"],
                    "companies": record["companies"]
                })

            if board_members:
                for idx, member in enumerate(board_members, 1):
                    logger.info(f"{idx:2d}. {member['officer']} ({member['position']})")
                    logger.info(f"     {member['count']}개 이사회 참여")
                    logger.info(f"     {', '.join(member['companies'][:5])}")

    async def analyze_affiliate_groups(self):
        """계열사 그룹 분석"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("5. 계열사 그룹 분석")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 가장 많은 계열사를 가진 그룹
            result = await session.run("""
                MATCH (parent:Company)-[:HAS_AFFILIATE]->(affiliate:Company)
                WITH parent, COUNT(DISTINCT affiliate) as affiliate_count
                RETURN parent.name as parent_company,
                       affiliate_count
                ORDER BY affiliate_count DESC
                LIMIT 10
            """)

            groups = []
            async for record in result:
                groups.append({
                    "parent": record["parent_company"],
                    "count": record["affiliate_count"]
                })

            for idx, group in enumerate(groups, 1):
                logger.info(f"{idx:2d}. {group['parent']}: {group['count']}개 계열사")

    async def analyze_cb_issuing_companies(self):
        """CB 발행 회사 분석"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("6. CB 발행 회사 분석")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
                WITH c, COUNT(cb) as cb_count
                RETURN c.name as company,
                       cb_count
                ORDER BY cb_count DESC
                LIMIT 10
            """)

            companies = []
            async for record in result:
                companies.append({
                    "company": record["company"],
                    "count": record["cb_count"]
                })

            for idx, company in enumerate(companies, 1):
                logger.info(f"{idx:2d}. {company['company']}: {company['count']}개 CB 발행")

    async def analyze_network_statistics(self):
        """전체 네트워크 통계"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("7. 전체 네트워크 통계")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 노드 통계
            result = await session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, COUNT(n) as count
                ORDER BY count DESC
            """)

            logger.info("노드 통계:")
            async for record in result:
                logger.info(f"  {record['label']:20s}: {record['count']:,}개")

            # 관계 통계
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, COUNT(r) as count
                ORDER BY count DESC
            """)

            logger.info("\n관계 통계:")
            async for record in result:
                logger.info(f"  {record['rel_type']:20s}: {record['count']:,}개")

            # 밀도 분석
            result = await session.run("""
                MATCH (c:Company)
                WITH COUNT(c) as company_count
                MATCH ()-[r]->()
                RETURN company_count,
                       COUNT(r) as relationship_count,
                       COUNT(r) * 1.0 / company_count as avg_connections_per_company
            """)

            stats = await result.single()
            logger.info(f"\n네트워크 밀도:")
            logger.info(f"  회사당 평균 연결: {stats['avg_connections_per_company']:.2f}개")

    async def analyze_cross_network_patterns(self):
        """교차 네트워크 패턴 (임원-CB-계열사 연결)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("8. 교차 네트워크 패턴")
        logger.info("=" * 60)

        async with self.driver.session() as session:
            # 자사 CB를 인수한 임원이 있는 회사
            result = await session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
                MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb)
                WHERE s.name CONTAINS o.name OR o.name CONTAINS s.name
                RETURN c.name as company,
                       o.name as officer,
                       s.name as subscriber,
                       cb.bond_name as bond
                LIMIT 10
            """)

            patterns = []
            async for record in result:
                patterns.append({
                    "company": record["company"],
                    "officer": record["officer"],
                    "subscriber": record["subscriber"],
                    "bond": record["bond"]
                })

            if patterns:
                logger.info("자사 CB 인수 가능성이 있는 케이스:")
                for idx, pattern in enumerate(patterns, 1):
                    logger.info(f"{idx:2d}. {pattern['company']}")
                    logger.info(f"     임원: {pattern['officer']}")
                    logger.info(f"     인수자: {pattern['subscriber']}")
            else:
                logger.info("자사 CB 인수 패턴이 발견되지 않았습니다.")

    async def run_full_analysis(self):
        """전체 분석 실행"""
        logger.info("통합 그래프 분석 시작...")
        logger.info("")

        await self.analyze_most_connected_companies()
        await self.analyze_most_influential_officers()
        await self.analyze_most_active_investors()
        await self.analyze_board_member_networks()
        await self.analyze_affiliate_groups()
        await self.analyze_cb_issuing_companies()
        await self.analyze_network_statistics()
        await self.analyze_cross_network_patterns()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 통합 그래프 분석 완료!")
        logger.info("=" * 60)


async def main():
    async with Neo4jIntegratedAnalyzer() as analyzer:
        await analyzer.run_full_analysis()


if __name__ == "__main__":
    asyncio.run(main())
