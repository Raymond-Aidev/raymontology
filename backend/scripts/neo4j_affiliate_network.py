"""
Neo4j 계열사 네트워크 구축

PostgreSQL의 계열사 데이터를 Neo4j 그래프로 임포트하여
회사 → 계열사 관계망 구축
"""
import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime

from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Company, Affiliate
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jAffiliateNetworkBuilder:
    """
    Neo4j 계열사 네트워크 구축기

    그래프 스키마:
    - (Company)-[:AFFILIATE_OF]-(Company)  # 양방향 계열 관계
    - (Company)-[:CONTROLS]->(Company)  # 지배력이 있는 경우 (지분율 > 50%)
    """

    def __init__(self):
        self.driver = None
        self.stats = {
            "companies": 0,
            "affiliate_rels": 0,
            "control_rels": 0,
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

    async def get_affiliate_related_companies(self, db: AsyncSession) -> Set[str]:
        """계열사 관계가 있는 모든 회사 ID 수집"""
        result = await db.execute(
            select(Affiliate.parent_company_id, Affiliate.affiliate_company_id).distinct()
        )
        rows = result.all()

        company_ids = set()
        for row in rows:
            company_ids.add(str(row.parent_company_id))
            if row.affiliate_company_id:
                company_ids.add(str(row.affiliate_company_id))

        return company_ids

    async def import_all_companies(self, db: AsyncSession):
        """전체 회사 임포트 (계열사 관계를 위해 필요)"""
        result = await db.execute(select(Company))
        companies = result.scalars().all()

        async with self.driver.session() as session:
            for company in companies:
                await session.run("""
                    MERGE (c:Company {id: $id})
                    SET c.corp_code = $corp_code,
                        c.name = $name,
                        c.ticker = $ticker,
                        c.sector = $sector,
                        c.industry = $industry,
                        c.market = $market,
                        c.market_cap = $market_cap,
                        c.revenue = $revenue,
                        c.net_income = $net_income,
                        c.total_assets = $total_assets,
                        c.updated_at = datetime($updated_at)
                """, {
                    "id": str(company.id),
                    "corp_code": company.corp_code,
                    "name": company.name,
                    "ticker": company.ticker,
                    "sector": company.sector,
                    "industry": company.industry,
                    "market": company.market,
                    "market_cap": company.market_cap,
                    "revenue": company.revenue,
                    "net_income": company.net_income,
                    "total_assets": company.total_assets,
                    "updated_at": company.updated_at.isoformat() if company.updated_at else None,
                })
                self.stats["companies"] += 1

        logger.info(f"✓ {self.stats['companies']}개 회사 임포트 완료")

    async def import_affiliate_relationships(self, db: AsyncSession):
        """계열사 관계 임포트"""
        result = await db.execute(select(Affiliate))
        affiliates = result.scalars().all()

        async with self.driver.session() as session:
            for affiliate in affiliates:
                # affiliate_company_id가 있는 경우 (Company로 매핑됨)
                if affiliate.affiliate_company_id:
                    # AFFILIATE_OF 관계 생성 (Graph API와 일치)
                    await session.run("""
                        MATCH (parent:Company {id: $parent_id})
                        MATCH (affiliate:Company {id: $affiliate_id})
                        MERGE (parent)-[r:AFFILIATE_OF]-(affiliate)
                        SET r.affiliate_name = $affiliate_name,
                            r.relationship_type = $relationship_type,
                            r.ownership_ratio = $ownership_ratio,
                            r.voting_rights_ratio = $voting_rights_ratio,
                            r.is_listed = $is_listed,
                            r.total_assets = $total_assets,
                            r.revenue = $revenue,
                            r.net_income = $net_income,
                            r.source_date = $source_date
                    """, {
                        "parent_id": str(affiliate.parent_company_id),
                        "affiliate_id": str(affiliate.affiliate_company_id),
                        "affiliate_name": affiliate.affiliate_name,
                        "relationship_type": affiliate.relationship_type,
                        "ownership_ratio": affiliate.ownership_ratio,
                        "voting_rights_ratio": affiliate.voting_rights_ratio,
                        "is_listed": affiliate.is_listed,
                        "total_assets": affiliate.total_assets,
                        "revenue": affiliate.revenue,
                        "net_income": affiliate.net_income,
                        "source_date": affiliate.source_date,
                    })
                    self.stats["affiliate_rels"] += 1

                    # 지배력 관계 (지분율 > 50%)
                    if affiliate.ownership_ratio and affiliate.ownership_ratio > 50:
                        await session.run("""
                            MATCH (parent:Company {id: $parent_id})
                            MATCH (affiliate:Company {id: $affiliate_id})
                            MERGE (parent)-[r:CONTROLS]->(affiliate)
                            SET r.ownership_ratio = $ownership_ratio,
                                r.source_date = $source_date
                        """, {
                            "parent_id": str(affiliate.parent_company_id),
                            "affiliate_id": str(affiliate.affiliate_company_id),
                            "ownership_ratio": affiliate.ownership_ratio,
                            "source_date": affiliate.source_date,
                        })
                        self.stats["control_rels"] += 1

        logger.info(f"✓ {self.stats['affiliate_rels']}개 AFFILIATE_OF 관계 생성 완료")
        logger.info(f"✓ {self.stats['control_rels']}개 CONTROLS 관계 생성 완료")

    async def create_indexes(self):
        """계열사 관계 인덱스 생성"""
        async with self.driver.session() as session:
            # AFFILIATE_OF 관계 인덱스
            await session.run("""
                CREATE INDEX affiliate_of_ownership IF NOT EXISTS
                FOR ()-[r:AFFILIATE_OF]-() ON (r.ownership_ratio)
            """)

            await session.run("""
                CREATE INDEX affiliate_of_type IF NOT EXISTS
                FOR ()-[r:AFFILIATE_OF]-() ON (r.relationship_type)
            """)

            logger.info("✓ 계열사 관계 인덱스 생성 완료")

    async def analyze_circular_ownership(self):
        """순환 출자 구조 분석"""
        async with self.driver.session() as session:
            # 순환 출자 검색 (최대 5단계)
            result = await session.run("""
                MATCH path = (c:Company)-[:AFFILIATE_OF*1..5]-(c)
                RETURN c.name as company, length(path) as cycle_length
                ORDER BY cycle_length
                LIMIT 10
            """)

            cycles = []
            async for record in result:
                cycles.append({
                    "company": record["company"],
                    "cycle_length": record["cycle_length"]
                })

            if cycles:
                logger.info("=" * 60)
                logger.info("순환 출자 구조 발견:")
                for cycle in cycles:
                    logger.info(f"  {cycle['company']}: {cycle['cycle_length']}단계 순환")
                logger.info("=" * 60)
            else:
                logger.info("✓ 순환 출자 구조 없음")

    async def verify_network(self):
        """네트워크 통계 확인"""
        async with self.driver.session() as session:
            # 노드 카운트
            result = await session.run("""
                MATCH (c:Company) RETURN COUNT(c) as count
            """)
            company_count = (await result.single())["count"]

            # 관계 카운트
            result = await session.run("""
                MATCH ()-[r:AFFILIATE_OF]-() RETURN COUNT(r) as count
            """)
            affiliate_count = (await result.single())["count"]

            result = await session.run("""
                MATCH ()-[r:CONTROLS]->() RETURN COUNT(r) as count
            """)
            control_count = (await result.single())["count"]

            # 계열사가 가장 많은 회사 TOP 5
            result = await session.run("""
                MATCH (c:Company)-[:AFFILIATE_OF]-(a:Company)
                RETURN c.name as company, COUNT(DISTINCT a) as affiliate_count
                ORDER BY affiliate_count DESC
                LIMIT 5
            """)
            top_companies = []
            async for record in result:
                top_companies.append({
                    "company": record["company"],
                    "count": record["affiliate_count"]
                })

            logger.info("=" * 60)
            logger.info("Neo4j 계열사 네트워크 통계")
            logger.info("=" * 60)
            logger.info(f"  회사 (Company):           {company_count:,}개")
            logger.info(f"  AFFILIATE_OF 관계:        {affiliate_count:,}개")
            logger.info(f"  CONTROLS 관계:            {control_count:,}개")
            logger.info("")
            logger.info("  계열사가 많은 회사 TOP 5:")
            for company in top_companies:
                logger.info(f"    {company['company']}: {company['count']}개")
            logger.info("=" * 60)

    async def build_network(self):
        """전체 네트워크 구축 프로세스"""
        logger.info("계열사 네트워크 구축 시작...")

        async with AsyncSessionLocal() as db:
            # 1. 전체 회사 임포트
            logger.info("[1/4] 전체 회사 임포트 중...")
            await self.import_all_companies(db)

            # 2. 계열사 관계 임포트
            logger.info("[2/4] 계열사 관계 임포트 중...")
            await self.import_affiliate_relationships(db)

            # 3. 인덱스 생성
            logger.info("[3/4] 인덱스 생성 중...")
            await self.create_indexes()

            # 4. 순환 출자 분석
            logger.info("[4/4] 순환 출자 구조 분석 중...")
            await self.analyze_circular_ownership()

        # 검증
        await self.verify_network()

        logger.info("✓ 계열사 네트워크 구축 완료!")


async def main():
    async with Neo4jAffiliateNetworkBuilder() as builder:
        await builder.build_network()


if __name__ == "__main__":
    asyncio.run(main())
