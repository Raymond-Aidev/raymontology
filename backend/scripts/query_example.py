#!/usr/bin/env python3
"""
Neo4j 쿼리 예제 스크립트
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from app.config import settings


async def query_company_info(company_name: str):
    """특정 회사의 정보 조회"""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    async with driver.session() as session:
        # 회사 기본 정보
        result = await session.run("""
            MATCH (c:Company {name: $company_name})
            OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
            OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(a:Company)
            OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
            RETURN c.name as company,
                   COUNT(DISTINCT o) as officer_count,
                   COUNT(DISTINCT a) as affiliate_count,
                   COUNT(DISTINCT cb) as cb_count
        """, company_name=company_name)

        info = await result.single()
        if info:
            print(f"회사명: {info['company']}")
            print(f"  임원: {info['officer_count']:,}명")
            print(f"  계열사: {info['affiliate_count']:,}개")
            print(f"  CB 발행: {info['cb_count']:,}개")
            print()

        # 임원 명단
        result = await session.run("""
            MATCH (c:Company {name: $company_name})<-[:WORKS_AT]-(o:Officer)
            RETURN o.name as name, o.position as position
            LIMIT 10
        """, company_name=company_name)

        print("주요 임원:")
        async for record in result:
            print(f"  - {record['name']} ({record['position']})")

    await driver.close()


async def search_companies(keyword: str):
    """회사 검색"""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    async with driver.session() as session:
        result = await session.run("""
            MATCH (c:Company)
            WHERE c.name CONTAINS $keyword
            RETURN c.name as name
            LIMIT 10
        """, keyword=keyword)

        print(f"'{keyword}' 검색 결과:")
        async for record in result:
            print(f"  - {record['name']}")

    await driver.close()


async def top_companies_by_officers():
    """임원이 많은 회사 TOP 10"""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    async with driver.session() as session:
        result = await session.run("""
            MATCH (c:Company)<-[:WORKS_AT]-(o:Officer)
            WITH c, COUNT(o) as officer_count
            RETURN c.name as company, officer_count
            ORDER BY officer_count DESC
            LIMIT 10
        """)

        print("임원이 많은 회사 TOP 10:")
        rank = 1
        async for record in result:
            print(f"{rank:2d}. {record['company']}: {record['officer_count']:,}명")
            rank += 1

    await driver.close()


async def main():
    """메인 함수"""
    import sys

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python query_example.py top              - 임원이 많은 회사 TOP 10")
        print("  python query_example.py search 삼성       - 회사 검색")
        print("  python query_example.py info LG전자       - 회사 상세 정보")
        return

    command = sys.argv[1]

    if command == "top":
        await top_companies_by_officers()
    elif command == "search" and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        await search_companies(keyword)
    elif command == "info" and len(sys.argv) >= 3:
        company_name = sys.argv[2]
        await query_company_info(company_name)
    else:
        print("잘못된 명령입니다.")


if __name__ == "__main__":
    asyncio.run(main())
