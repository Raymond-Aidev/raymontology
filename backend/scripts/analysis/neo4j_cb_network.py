"""
Neo4j CB 네트워크 구축

PostgreSQL의 CB 데이터를 Neo4j 그래프로 임포트하여
회사 → CB → 인수자 관계망 구축
"""
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Company, ConvertibleBond, CBSubscriber
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jCBNetworkBuilder:
    """
    Neo4j CB 네트워크 구축기

    그래프 스키마:
    - (Company) -[:ISSUED]-> (ConvertibleBond) <-[:SUBSCRIBED]- (Subscriber)
    - (Subscriber) -[:INVESTED_IN]-> (Company)
    """

    def __init__(self):
        self.driver = None
        self.stats = {
            "companies": 0,
            "cbs": 0,
            "subscribers": 0,
            "issued_rels": 0,
            "subscribed_rels": 0,
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

    async def clear_cb_network(self):
        """기존 CB 네트워크 데이터 삭제"""
        async with self.driver.session() as session:
            # CB 관련 노드와 관계 삭제
            await session.run("""
                MATCH (cb:ConvertibleBond)
                DETACH DELETE cb
            """)

            await session.run("""
                MATCH (s:Subscriber)
                DETACH DELETE s
            """)

            # ISSUED 관계 삭제 (Company는 유지)
            await session.run("""
                MATCH ()-[r:ISSUED]->()
                DELETE r
            """)

            logger.info("✓ 기존 CB 네트워크 데이터 삭제 완료")

    async def create_constraints(self):
        """Neo4j 제약 조건 및 인덱스 생성"""
        async with self.driver.session() as session:
            # ConvertibleBond 유니크 제약
            await session.run("""
                CREATE CONSTRAINT cb_id IF NOT EXISTS
                FOR (cb:ConvertibleBond) REQUIRE cb.id IS UNIQUE
            """)

            # Subscriber 유니크 제약
            await session.run("""
                CREATE CONSTRAINT subscriber_id IF NOT EXISTS
                FOR (s:Subscriber) REQUIRE s.id IS UNIQUE
            """)

            # Company 인덱스 (이미 존재할 수 있음)
            try:
                await session.run("""
                    CREATE CONSTRAINT company_id IF NOT EXISTS
                    FOR (c:Company) REQUIRE c.id IS UNIQUE
                """)
            except Exception:
                pass  # 이미 존재하는 경우 무시

            # 인덱스 생성
            await session.run("""
                CREATE INDEX subscriber_name IF NOT EXISTS
                FOR (s:Subscriber) ON (s.name)
            """)

            await session.run("""
                CREATE INDEX cb_company IF NOT EXISTS
                FOR (cb:ConvertibleBond) ON (cb.company_id)
            """)

            logger.info("✓ Neo4j 제약 조건 및 인덱스 생성 완료")

    async def import_companies_with_cbs(self, db: AsyncSession):
        """CB를 발행한 회사 임포트"""
        # CB를 발행한 회사만 조회
        result = await db.execute(
            select(Company)
            .join(ConvertibleBond, Company.id == ConvertibleBond.company_id)
            .distinct()
        )
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
                        c.updated_at = CASE WHEN $updated_at IS NOT NULL THEN datetime($updated_at) ELSE NULL END
                """, {
                    "id": str(company.id),
                    "corp_code": company.corp_code,
                    "name": company.name,
                    "ticker": company.ticker,
                    "sector": company.sector,
                    "industry": company.industry,
                    "market": company.market,
                    "updated_at": company.updated_at.isoformat() if company.updated_at else None,
                })
                self.stats["companies"] += 1

        logger.info(f"✓ {self.stats['companies']}개 회사 임포트 완료")

    async def import_convertible_bonds(self, db: AsyncSession):
        """전환사채 임포트 및 관계 생성"""
        result = await db.execute(select(ConvertibleBond))
        cbs = result.scalars().all()

        async with self.driver.session() as session:
            for cb in cbs:
                # CB 노드 생성 (NULL 날짜 처리: date(null) 오류 방지)
                await session.run("""
                    CREATE (cb:ConvertibleBond {
                        id: $id,
                        bond_name: $bond_name,
                        bond_type: $bond_type,
                        issue_date: CASE WHEN $issue_date IS NOT NULL THEN date($issue_date) ELSE NULL END,
                        maturity_date: CASE WHEN $maturity_date IS NOT NULL THEN date($maturity_date) ELSE NULL END,
                        issue_amount: $issue_amount,
                        interest_rate: $interest_rate,
                        conversion_price: $conversion_price,
                        conversion_ratio: $conversion_ratio,
                        outstanding_amount: $outstanding_amount,
                        status: $status,
                        source_disclosure_id: $source_disclosure_id,
                        created_at: CASE WHEN $created_at IS NOT NULL THEN datetime($created_at) ELSE NULL END
                    })
                """, {
                    "id": str(cb.id),
                    "bond_name": cb.bond_name,
                    "bond_type": cb.bond_type,
                    "issue_date": cb.issue_date.isoformat() if cb.issue_date else None,
                    "maturity_date": cb.maturity_date.isoformat() if cb.maturity_date else None,
                    "issue_amount": cb.issue_amount,
                    "interest_rate": cb.interest_rate,
                    "conversion_price": cb.conversion_price,
                    "conversion_ratio": cb.conversion_ratio,
                    "outstanding_amount": cb.outstanding_amount,
                    "status": cb.status,
                    "source_disclosure_id": cb.source_disclosure_id,
                    "created_at": cb.created_at.isoformat() if cb.created_at else None,
                })

                # Company → CB 관계 생성 (NULL 날짜 처리)
                await session.run("""
                    MATCH (c:Company {id: $company_id})
                    MATCH (cb:ConvertibleBond {id: $cb_id})
                    CREATE (c)-[:ISSUED {
                        issue_date: CASE WHEN $issue_date IS NOT NULL THEN date($issue_date) ELSE NULL END,
                        amount: $issue_amount
                    }]->(cb)
                """, {
                    "company_id": str(cb.company_id),
                    "cb_id": str(cb.id),
                    "issue_date": cb.issue_date.isoformat() if cb.issue_date else None,
                    "issue_amount": cb.issue_amount,
                })

                self.stats["cbs"] += 1
                self.stats["issued_rels"] += 1

        logger.info(f"✓ {self.stats['cbs']}개 CB 임포트 완료")
        logger.info(f"✓ {self.stats['issued_rels']}개 ISSUED 관계 생성 완료")

    async def import_subscribers(self, db: AsyncSession):
        """CB 인수자 임포트 및 관계 생성"""
        result = await db.execute(select(CBSubscriber))
        subscribers = result.scalars().all()

        # 인수자명으로 그룹핑 (동일 인수자가 여러 CB에 투자)
        subscriber_map = {}
        for sub in subscribers:
            if sub.subscriber_name not in subscriber_map:
                subscriber_map[sub.subscriber_name] = {
                    "id": str(sub.id),  # 첫 번째 ID 사용
                    "name": sub.subscriber_name,
                    "type": sub.subscriber_type,
                    # 법인/단체 기본정보 (첫 번째 유효한 값 사용)
                    "representative_name": getattr(sub, 'representative_name', None),
                    "gp_name": getattr(sub, 'gp_name', None),
                    "largest_shareholder_name": getattr(sub, 'largest_shareholder_name', None),
                    "subscriptions": []
                }
            else:
                # 이미 존재하는 경우, 법인정보가 없으면 업데이트
                existing = subscriber_map[sub.subscriber_name]
                if not existing.get("representative_name") and getattr(sub, 'representative_name', None):
                    existing["representative_name"] = sub.representative_name
                if not existing.get("gp_name") and getattr(sub, 'gp_name', None):
                    existing["gp_name"] = sub.gp_name
                if not existing.get("largest_shareholder_name") and getattr(sub, 'largest_shareholder_name', None):
                    existing["largest_shareholder_name"] = sub.largest_shareholder_name
            subscriber_map[sub.subscriber_name]["subscriptions"].append(sub)

        async with self.driver.session() as session:
            for sub_name, sub_info in subscriber_map.items():
                # Subscriber 노드 생성 (MERGE로 중복 방지)
                await session.run("""
                    MERGE (s:Subscriber {name: $name})
                    SET s.id = $id,
                        s.type = $type,
                        s.representative_name = $representative_name,
                        s.gp_name = $gp_name,
                        s.largest_shareholder_name = $largest_shareholder_name
                """, {
                    "id": sub_info["id"],
                    "name": sub_info["name"],
                    "type": sub_info["type"],
                    "representative_name": sub_info.get("representative_name"),
                    "gp_name": sub_info.get("gp_name"),
                    "largest_shareholder_name": sub_info.get("largest_shareholder_name"),
                })
                self.stats["subscribers"] += 1

                # 각 CB에 대한 SUBSCRIBED 관계 생성 (MERGE로 중복 방지)
                for sub in sub_info["subscriptions"]:
                    await session.run("""
                        MATCH (s:Subscriber {name: $subscriber_name})
                        MATCH (cb:ConvertibleBond {id: $cb_id})
                        MERGE (s)-[r:SUBSCRIBED]->(cb)
                        SET r.subscription_id = $subscription_id,
                            r.amount = $amount,
                            r.quantity = $quantity,
                            r.relationship = $relationship,
                            r.is_related_party = $is_related_party,
                            r.selection_rationale = $rationale,
                            r.subscribed_at = CASE WHEN $subscribed_at IS NOT NULL THEN datetime($subscribed_at) ELSE NULL END
                    """, {
                        "subscriber_name": sub.subscriber_name,
                        "cb_id": str(sub.cb_id),
                        "subscription_id": str(sub.id),
                        "amount": sub.subscription_amount,
                        "quantity": sub.subscription_quantity,
                        "relationship": sub.relationship_to_company,
                        "is_related_party": sub.is_related_party,
                        "rationale": sub.selection_rationale,
                        "subscribed_at": sub.created_at.isoformat() if sub.created_at else None,
                    })
                    self.stats["subscribed_rels"] += 1

        logger.info(f"✓ {self.stats['subscribers']}명 인수자 임포트 완료")
        logger.info(f"✓ {self.stats['subscribed_rels']}개 SUBSCRIBED 관계 생성 완료")

    async def create_derived_relationships(self):
        """파생 관계 생성: Subscriber → Company (투자 관계)"""
        async with self.driver.session() as session:
            # Subscriber가 CB를 통해 투자한 Company로의 직접 관계 생성
            result = await session.run("""
                MATCH (s:Subscriber)-[sub:SUBSCRIBED]->(cb:ConvertibleBond)<-[:ISSUED]-(c:Company)
                MERGE (s)-[inv:INVESTED_IN]->(c)
                ON CREATE SET
                    inv.total_amount = sub.amount,
                    inv.cb_count = 1
                ON MATCH SET
                    inv.total_amount = inv.total_amount + sub.amount,
                    inv.cb_count = inv.cb_count + 1
                RETURN COUNT(inv) as count
            """)
            record = await result.single()
            count = record["count"] if record else 0

            logger.info(f"✓ {count}개 INVESTED_IN 관계 생성 완료")

    async def verify_network(self):
        """네트워크 통계 확인"""
        async with self.driver.session() as session:
            # 노드 카운트
            result = await session.run("""
                MATCH (c:Company) RETURN COUNT(c) as count
            """)
            company_count = (await result.single())["count"]

            result = await session.run("""
                MATCH (cb:ConvertibleBond) RETURN COUNT(cb) as count
            """)
            cb_count = (await result.single())["count"]

            result = await session.run("""
                MATCH (s:Subscriber) RETURN COUNT(s) as count
            """)
            subscriber_count = (await result.single())["count"]

            # 관계 카운트
            result = await session.run("""
                MATCH ()-[r:ISSUED]->() RETURN COUNT(r) as count
            """)
            issued_count = (await result.single())["count"]

            result = await session.run("""
                MATCH ()-[r:SUBSCRIBED]->() RETURN COUNT(r) as count
            """)
            subscribed_count = (await result.single())["count"]

            result = await session.run("""
                MATCH ()-[r:INVESTED_IN]->() RETURN COUNT(r) as count
            """)
            invested_count = (await result.single())["count"]

            logger.info("=" * 60)
            logger.info("Neo4j CB 네트워크 통계")
            logger.info("=" * 60)
            logger.info(f"  회사 (Company):           {company_count:,}개")
            logger.info(f"  전환사채 (CB):            {cb_count:,}개")
            logger.info(f"  인수자 (Subscriber):       {subscriber_count:,}명")
            logger.info(f"  ISSUED 관계:              {issued_count:,}개")
            logger.info(f"  SUBSCRIBED 관계:          {subscribed_count:,}개")
            logger.info(f"  INVESTED_IN 관계:         {invested_count:,}개")
            logger.info("=" * 60)

    async def build_network(self):
        """전체 네트워크 구축 프로세스"""
        logger.info("CB 네트워크 구축 시작...")

        async with AsyncSessionLocal() as db:
            # 1. 기존 데이터 삭제
            logger.info("[1/6] 기존 CB 네트워크 데이터 삭제 중...")
            await self.clear_cb_network()

            # 2. 제약 조건 생성
            logger.info("[2/6] Neo4j 제약 조건 및 인덱스 생성 중...")
            await self.create_constraints()

            # 3. 회사 임포트
            logger.info("[3/6] CB 발행 회사 임포트 중...")
            await self.import_companies_with_cbs(db)

            # 4. CB 임포트
            logger.info("[4/6] 전환사채 임포트 중...")
            await self.import_convertible_bonds(db)

            # 5. 인수자 임포트
            logger.info("[5/6] CB 인수자 임포트 중...")
            await self.import_subscribers(db)

            # 6. 파생 관계 생성
            logger.info("[6/6] 파생 관계 (INVESTED_IN) 생성 중...")
            await self.create_derived_relationships()

        # 검증
        await self.verify_network()

        logger.info("✓ CB 네트워크 구축 완료!")


async def main():
    async with Neo4jCBNetworkBuilder() as builder:
        await builder.build_network()


if __name__ == "__main__":
    asyncio.run(main())
