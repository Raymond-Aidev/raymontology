#!/usr/bin/env python3
"""
Neo4j 데이터 검증 스크립트
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from app.config import settings

async def verify_neo4j():
    """Neo4j 그래프 데이터 검증"""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        await driver.verify_connectivity()
        print("✓ Neo4j 연결 성공")
        print("=" * 60)

        async with driver.session() as session:
            # 노드 카운트
            print("노드 통계:")
            for label in ["Company", "Officer", "ConvertibleBond", "Subscriber"]:
                result = await session.run(f"MATCH (n:{label}) RETURN COUNT(n) as count")
                count = (await result.single())["count"]
                print(f"  {label:20s}: {count:,}개")

            print()
            print("관계 통계:")
            # 관계 카운트
            relationships = [
                "WORKS_AT",
                "BOARD_MEMBER_AT",
                "HAS_AFFILIATE",
                "CONTROLS",
                "ISSUED",
                "SUBSCRIBED",
                "INVESTED_IN"
            ]

            for rel_type in relationships:
                result = await session.run(f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count")
                count = (await result.single())["count"]
                print(f"  {rel_type:20s}: {count:,}개")

            print("=" * 60)

            # 데이터 무결성 체크
            print("\n데이터 무결성 체크:")

            # 1. Officers without company
            result = await session.run("""
                MATCH (o:Officer)
                WHERE NOT (o)-[:WORKS_AT]->(:Company)
                RETURN COUNT(o) as count
            """)
            orphan_officers = (await result.single())["count"]
            if orphan_officers > 0:
                print(f"  ⚠ 회사 연결 없는 임원: {orphan_officers:,}명")
            else:
                print(f"  ✓ 모든 임원이 회사에 연결됨")

            # 2. CBs without issuer
            result = await session.run("""
                MATCH (cb:ConvertibleBond)
                WHERE NOT (:Company)-[:ISSUED]->(cb)
                RETURN COUNT(cb) as count
            """)
            orphan_cbs = (await result.single())["count"]
            if orphan_cbs > 0:
                print(f"  ⚠ 발행사 없는 CB: {orphan_cbs:,}개")
            else:
                print(f"  ✓ 모든 CB가 발행사에 연결됨")

            # 3. Subscribers without CB
            result = await session.run("""
                MATCH (s:Subscriber)
                WHERE NOT (s)-[:SUBSCRIBED]->(:ConvertibleBond)
                RETURN COUNT(s) as count
            """)
            orphan_subs = (await result.single())["count"]
            if orphan_subs > 0:
                print(f"  ⚠ CB 연결 없는 인수자: {orphan_subs:,}명")
            else:
                print(f"  ✓ 모든 인수자가 CB에 연결됨")

            print("=" * 60)

    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(verify_neo4j())
