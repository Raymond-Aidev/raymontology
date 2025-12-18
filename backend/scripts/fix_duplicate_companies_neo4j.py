#!/usr/bin/env python3
"""
Neo4j에서 중복 회사 노드를 병합하는 스크립트

문제: 동일한 corp_code를 가진 회사 노드가 여러 개 존재
- 임원 동기화에서 생성된 노드 (officers 관계)
- CB 동기화에서 생성된 노드 (CB/subscriber 관계)

해결: corp_code 기준으로 노드를 병합하고 모든 관계를 하나의 노드로 이전
"""
import asyncio
import logging
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"


async def main():
    logger.info("Neo4j 중복 회사 노드 병합 시작...")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # 1. 중복 회사 노드 찾기
            logger.info("[1/5] 중복 회사 노드 검색...")
            result = await session.run("""
                MATCH (c:Company)
                WHERE c.corp_code IS NOT NULL
                WITH c.corp_code as corp_code, collect(c) as nodes
                WHERE size(nodes) > 1
                RETURN corp_code, [n in nodes | n.id] as node_ids, size(nodes) as count
            """)

            duplicates = []
            async for record in result:
                duplicates.append({
                    'corp_code': record['corp_code'],
                    'node_ids': record['node_ids'],
                    'count': record['count']
                })

            logger.info(f"  중복 회사: {len(duplicates)}개 corp_code")

            if not duplicates:
                logger.info("중복 노드 없음. 완료.")
                return

            # 2. 각 중복 그룹에서 노드 병합
            logger.info("[2/5] 관계 이전 시작...")
            merged_count = 0

            for dup in duplicates:
                corp_code = dup['corp_code']
                node_ids = [nid for nid in dup['node_ids'] if nid is not None]

                if len(node_ids) < 2:
                    continue

                # 첫 번째 노드를 primary로 선택
                primary_id = node_ids[0]
                other_ids = node_ids[1:]

                for other_id in other_ids:
                    # WORKS_AT 관계 이전 (Officer -> Company)
                    await session.run("""
                        MATCH (o:Officer)-[r:WORKS_AT]->(c:Company {id: $other_id})
                        MATCH (primary:Company {id: $primary_id})
                        MERGE (o)-[new_r:WORKS_AT]->(primary)
                        SET new_r = properties(r)
                        DELETE r
                    """, other_id=other_id, primary_id=primary_id)

                    # WORKED_AT 관계 이전
                    await session.run("""
                        MATCH (o:Officer)-[r:WORKED_AT]->(c:Company {id: $other_id})
                        MATCH (primary:Company {id: $primary_id})
                        MERGE (o)-[new_r:WORKED_AT]->(primary)
                        SET new_r = properties(r)
                        DELETE r
                    """, other_id=other_id, primary_id=primary_id)

                    # ISSUED 관계 이전 (Company -> CB)
                    await session.run("""
                        MATCH (c:Company {id: $other_id})-[r:ISSUED]->(cb:ConvertibleBond)
                        MATCH (primary:Company {id: $primary_id})
                        MERGE (primary)-[new_r:ISSUED]->(cb)
                        SET new_r = properties(r)
                        DELETE r
                    """, other_id=other_id, primary_id=primary_id)

                    # AFFILIATE_OF 관계 이전
                    await session.run("""
                        MATCH (c:Company {id: $other_id})-[r:AFFILIATE_OF]-(other:Company)
                        MATCH (primary:Company {id: $primary_id})
                        WHERE other.id <> $primary_id
                        MERGE (primary)-[new_r:AFFILIATE_OF]-(other)
                        SET new_r = properties(r)
                        DELETE r
                    """, other_id=other_id, primary_id=primary_id)

                    # 중복 노드 삭제
                    await session.run("""
                        MATCH (c:Company {id: $other_id})
                        WHERE NOT (c)--()
                        DELETE c
                    """, other_id=other_id)

                    # 연결이 남아있으면 강제 삭제
                    await session.run("""
                        MATCH (c:Company {id: $other_id})
                        DETACH DELETE c
                    """, other_id=other_id)

                merged_count += 1

                if merged_count % 50 == 0:
                    logger.info(f"  {merged_count}/{len(duplicates)} 병합 완료...")

            logger.info(f"  총 {merged_count}개 corp_code 병합 완료")

            # 3. 결과 확인
            logger.info("[3/5] 병합 결과 확인...")
            result = await session.run("""
                MATCH (c:Company)
                WITH c.corp_code as corp_code, count(c) as cnt
                WHERE cnt > 1
                RETURN count(corp_code) as remaining_duplicates
            """)
            record = await result.single()
            remaining = record['remaining_duplicates'] if record else 0
            logger.info(f"  남은 중복: {remaining}개")

            # 4. 통계
            logger.info("[4/5] 최종 통계...")
            stats_result = await session.run("""
                MATCH (c:Company) RETURN count(c) as companies
            """)
            stats = await stats_result.single()
            logger.info(f"  총 회사 노드: {stats['companies']}개")

            # 5. 나노캠텍 검증
            logger.info("[5/5] 나노캠텍 검증...")
            verify_result = await session.run("""
                MATCH (c:Company {corp_code: '00542074'})
                OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
                OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
                RETURN c.name, count(DISTINCT o) as officers, count(DISTINCT cb) as cbs
            """)
            verify = await verify_result.single()
            if verify:
                logger.info(f"  나노캠텍: 임원 {verify['officers']}명, CB {verify['cbs']}개")

    finally:
        await driver.close()

    logger.info("병합 완료!")


if __name__ == "__main__":
    asyncio.run(main())
