#!/usr/bin/env python3
"""
CB 데이터를 Neo4j에 동기화하는 독립 스크립트
법인정보(대표이사, 업무집행자, 최대주주) 포함
"""
import asyncio
import asyncpg
import logging
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 설정
DB_URL = "postgresql://postgres:dev_password@localhost:5432/raymontology_dev"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"


async def main():
    logger.info("CB 네트워크 Neo4j 동기화 시작...")

    # DB 연결
    conn = await asyncpg.connect(DB_URL)
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # 1. 기존 CB 네트워크 삭제
        logger.info("[1/5] 기존 CB 네트워크 삭제...")
        async with driver.session() as session:
            await session.run("MATCH (cb:ConvertibleBond) DETACH DELETE cb")
            await session.run("MATCH (s:Subscriber) DETACH DELETE s")
            await session.run("MATCH ()-[r:ISSUED]->() DELETE r")

        # 2. CB 발행 회사 조회 및 업데이트 (기존 노드 재사용)
        logger.info("[2/5] CB 발행 회사 업데이트...")
        companies = await conn.fetch("""
            SELECT DISTINCT c.id, c.corp_code, c.name, c.ticker, c.sector, c.industry, c.market
            FROM companies c
            JOIN convertible_bonds cb ON c.id = cb.company_id
        """)

        async with driver.session() as session:
            for c in companies:
                # corp_code 기준으로 기존 회사 노드를 찾아서 업데이트
                # 없으면 새로 생성 (id 기준)
                await session.run("""
                    MERGE (c:Company {corp_code: $corp_code})
                    SET c.id = $id,
                        c.name = $name,
                        c.ticker = $ticker,
                        c.sector = $sector,
                        c.industry = $industry,
                        c.market = $market
                """, {
                    "id": str(c['id']),
                    "corp_code": c['corp_code'],
                    "name": c['name'],
                    "ticker": c['ticker'],
                    "sector": c['sector'],
                    "industry": c['industry'],
                    "market": c['market'],
                })
        logger.info(f"  회사 {len(companies)}개 업데이트 완료")

        # 3. CB 임포트
        logger.info("[3/5] 전환사채 임포트...")
        cbs = await conn.fetch("""
            SELECT cb.id, c.corp_code, cb.bond_name, cb.bond_type, cb.issue_date, cb.maturity_date,
                   cb.issue_amount, cb.interest_rate, cb.conversion_price, cb.conversion_ratio,
                   cb.outstanding_amount, cb.status, cb.source_disclosure_id
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
        """)

        async with driver.session() as session:
            for cb in cbs:
                await session.run("""
                    CREATE (cb:ConvertibleBond {
                        id: $id,
                        bond_name: $bond_name,
                        bond_type: $bond_type,
                        issue_date: $issue_date,
                        maturity_date: $maturity_date,
                        issue_amount: $issue_amount,
                        interest_rate: $interest_rate,
                        conversion_price: $conversion_price,
                        conversion_ratio: $conversion_ratio,
                        outstanding_amount: $outstanding_amount,
                        status: $status,
                        source_disclosure_id: $source_disclosure_id
                    })
                """, {
                    "id": str(cb['id']),
                    "bond_name": cb['bond_name'],
                    "bond_type": cb['bond_type'],
                    "issue_date": str(cb['issue_date']) if cb['issue_date'] else None,
                    "maturity_date": str(cb['maturity_date']) if cb['maturity_date'] else None,
                    "issue_amount": float(cb['issue_amount']) if cb['issue_amount'] else None,
                    "interest_rate": float(cb['interest_rate']) if cb['interest_rate'] else None,
                    "conversion_price": float(cb['conversion_price']) if cb['conversion_price'] else None,
                    "conversion_ratio": float(cb['conversion_ratio']) if cb['conversion_ratio'] else None,
                    "outstanding_amount": float(cb['outstanding_amount']) if cb['outstanding_amount'] else None,
                    "status": cb['status'],
                    "source_disclosure_id": cb['source_disclosure_id'],
                })

                # Company → CB 관계 생성 (corp_code 기준)
                await session.run("""
                    MATCH (c:Company {corp_code: $corp_code})
                    MATCH (cb:ConvertibleBond {id: $cb_id})
                    CREATE (c)-[:ISSUED {
                        issue_date: $issue_date,
                        amount: $issue_amount
                    }]->(cb)
                """, {
                    "corp_code": cb['corp_code'],
                    "cb_id": str(cb['id']),
                    "issue_date": str(cb['issue_date']) if cb['issue_date'] else None,
                    "issue_amount": float(cb['issue_amount']) if cb['issue_amount'] else None,
                })
        logger.info(f"  CB {len(cbs)}개 임포트 완료")

        # 4. 인수자 임포트 (법인정보 포함)
        logger.info("[4/5] 인수자 임포트 (법인정보 포함)...")
        subscribers = await conn.fetch("""
            SELECT id, cb_id, subscriber_name, subscriber_type,
                   subscription_amount, subscription_quantity,
                   relationship_to_company, is_related_party, selection_rationale,
                   representative_name, representative_share,
                   gp_name, gp_share,
                   largest_shareholder_name, largest_shareholder_share
            FROM cb_subscribers
        """)

        # 인수자명으로 그룹핑
        subscriber_map = {}
        for sub in subscribers:
            name = sub['subscriber_name']
            if name not in subscriber_map:
                subscriber_map[name] = {
                    "id": str(sub['id']),
                    "name": name,
                    "type": sub['subscriber_type'],
                    "representative_name": sub['representative_name'],
                    "gp_name": sub['gp_name'],
                    "largest_shareholder_name": sub['largest_shareholder_name'],
                    "subscriptions": []
                }
            else:
                # 법인정보가 없으면 업데이트
                if not subscriber_map[name]["representative_name"] and sub['representative_name']:
                    subscriber_map[name]["representative_name"] = sub['representative_name']
                if not subscriber_map[name]["gp_name"] and sub['gp_name']:
                    subscriber_map[name]["gp_name"] = sub['gp_name']
                if not subscriber_map[name]["largest_shareholder_name"] and sub['largest_shareholder_name']:
                    subscriber_map[name]["largest_shareholder_name"] = sub['largest_shareholder_name']
            subscriber_map[name]["subscriptions"].append(sub)

        async with driver.session() as session:
            for sub_name, sub_info in subscriber_map.items():
                # Subscriber 노드 생성 (법인정보 포함)
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

                # 각 CB에 대한 SUBSCRIBED 관계 생성
                for sub in sub_info["subscriptions"]:
                    await session.run("""
                        MATCH (s:Subscriber {name: $subscriber_name})
                        MATCH (cb:ConvertibleBond {id: $cb_id})
                        CREATE (s)-[:SUBSCRIBED {
                            subscription_id: $subscription_id,
                            amount: $amount,
                            quantity: $quantity,
                            relationship: $relationship,
                            is_related_party: $is_related_party,
                            selection_rationale: $rationale
                        }]->(cb)
                    """, {
                        "subscriber_name": sub['subscriber_name'],
                        "cb_id": str(sub['cb_id']),
                        "subscription_id": str(sub['id']),
                        "amount": float(sub['subscription_amount']) if sub['subscription_amount'] else None,
                        "quantity": float(sub['subscription_quantity']) if sub['subscription_quantity'] else None,
                        "relationship": sub['relationship_to_company'],
                        "is_related_party": sub['is_related_party'],
                        "rationale": sub['selection_rationale'],
                    })

        logger.info(f"  인수자 {len(subscriber_map)}명 임포트 완료")
        logger.info(f"  SUBSCRIBED 관계 {len(subscribers)}개 생성 완료")

        # 5. 파생 관계 생성: INVESTED_IN
        logger.info("[5/5] INVESTED_IN 관계 생성...")
        async with driver.session() as session:
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
        logger.info(f"  INVESTED_IN 관계 {count}개 생성 완료")

        # 6. 통계 확인
        logger.info("=" * 60)
        logger.info("Neo4j CB 네트워크 통계")
        logger.info("=" * 60)

        async with driver.session() as session:
            result = await session.run("MATCH (c:Company) RETURN COUNT(c) as count")
            company_count = (await result.single())["count"]

            result = await session.run("MATCH (cb:ConvertibleBond) RETURN COUNT(cb) as count")
            cb_count = (await result.single())["count"]

            result = await session.run("MATCH (s:Subscriber) RETURN COUNT(s) as count")
            subscriber_count = (await result.single())["count"]

            result = await session.run("MATCH ()-[r:ISSUED]->() RETURN COUNT(r) as count")
            issued_count = (await result.single())["count"]

            result = await session.run("MATCH ()-[r:SUBSCRIBED]->() RETURN COUNT(r) as count")
            subscribed_count = (await result.single())["count"]

            result = await session.run("MATCH ()-[r:INVESTED_IN]->() RETURN COUNT(r) as count")
            invested_count = (await result.single())["count"]

            # 법인정보 있는 인수자 수
            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE s.representative_name IS NOT NULL
                   OR s.gp_name IS NOT NULL
                   OR s.largest_shareholder_name IS NOT NULL
                RETURN COUNT(s) as count
            """)
            entity_info_count = (await result.single())["count"]

        logger.info(f"  회사 (Company):           {company_count:,}개")
        logger.info(f"  전환사채 (CB):            {cb_count:,}개")
        logger.info(f"  인수자 (Subscriber):       {subscriber_count:,}명")
        logger.info(f"    - 법인정보 있음:        {entity_info_count:,}명")
        logger.info(f"  ISSUED 관계:              {issued_count:,}개")
        logger.info(f"  SUBSCRIBED 관계:          {subscribed_count:,}개")
        logger.info(f"  INVESTED_IN 관계:         {invested_count:,}개")
        logger.info("=" * 60)
        logger.info("CB 네트워크 동기화 완료!")

    finally:
        await conn.close()
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
