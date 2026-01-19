#!/usr/bin/env python3
"""
PostgreSQL의 모든 회사 데이터를 Neo4j로 동기화하는 스크립트

기존 회사 노드는 업데이트하고, 없는 회사는 새로 생성합니다.
"""
import asyncio
import sys
from pathlib import Path
import logging
from typing import List, Dict, Any

# Python path 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from neo4j import AsyncGraphDatabase

from app.database import AsyncSessionLocal
from app.models.companies import Company
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompanySyncer:
    """회사 데이터 PostgreSQL → Neo4j 동기화"""

    def __init__(self):
        self.neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.stats = {
            "pg_total": 0,
            "neo4j_before": 0,
            "neo4j_after": 0,
            "created": 0,
            "updated": 0,
            "errors": 0
        }

    async def close(self):
        """드라이버 종료"""
        await self.neo4j_driver.close()

    async def run(self):
        """동기화 실행"""
        print("=" * 60)
        print("🔄 PostgreSQL → Neo4j 회사 데이터 동기화 시작")
        print("=" * 60)

        try:
            # 1. PostgreSQL에서 모든 회사 조회
            print("\n📊 PostgreSQL에서 회사 데이터 조회 중...")
            companies = await self._fetch_companies_from_pg()
            self.stats["pg_total"] = len(companies)
            print(f"  PostgreSQL 회사: {len(companies)}개")

            # 2. Neo4j 현재 상태 확인
            print("\n📊 Neo4j 현재 상태 확인 중...")
            neo4j_count_before = await self._count_neo4j_companies()
            self.stats["neo4j_before"] = neo4j_count_before
            print(f"  Neo4j 회사 (동기화 전): {neo4j_count_before}개")

            # 3. Neo4j로 동기화
            print(f"\n🔄 Neo4j로 {len(companies)}개 회사 동기화 중...")
            await self._sync_to_neo4j(companies)

            # 4. Neo4j 최종 상태 확인
            print("\n📊 Neo4j 최종 상태 확인 중...")
            neo4j_count_after = await self._count_neo4j_companies()
            self.stats["neo4j_after"] = neo4j_count_after
            print(f"  Neo4j 회사 (동기화 후): {neo4j_count_after}개")

            # 5. 삼성전자 검증
            print("\n✅ 삼성전자 동기화 검증 중...")
            await self._verify_samsung()

            # 6. 통계 출력
            self._print_stats()

        except Exception as e:
            logger.error(f"동기화 실패: {e}", exc_info=True)
            raise
        finally:
            await self.close()

    async def _fetch_companies_from_pg(self) -> List[Dict[str, Any]]:
        """PostgreSQL에서 모든 회사 조회"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Company).order_by(Company.name)
            )
            companies_orm = result.scalars().all()

            companies = []
            for company in companies_orm:
                companies.append({
                    "id": str(company.id),
                    "name": company.name,
                    "ticker": company.ticker,
                    "corp_code": company.corp_code,
                    "name_en": company.name_en,
                    "business_number": company.business_number,
                    "sector": company.sector,
                    "industry": company.industry,
                    "market": company.market,
                })

            return companies

    async def _count_neo4j_companies(self) -> int:
        """Neo4j 회사 노드 개수 조회"""
        async with self.neo4j_driver.session() as session:
            result = await session.run("MATCH (c:Company) RETURN count(c) as total")
            record = await result.single()
            return record["total"] if record else 0

    async def _sync_to_neo4j(self, companies: List[Dict[str, Any]]):
        """회사 데이터를 Neo4j로 동기화"""
        async with self.neo4j_driver.session() as session:
            batch_size = 100
            total = len(companies)

            for i in range(0, total, batch_size):
                batch = companies[i:i + batch_size]

                try:
                    # MERGE를 사용하여 존재하면 업데이트, 없으면 생성
                    query = """
                    UNWIND $companies AS company
                    MERGE (c:Company {id: company.id})
                    ON CREATE SET
                        c.name = company.name,
                        c.ticker = company.ticker,
                        c.corp_code = company.corp_code,
                        c.name_en = company.name_en,
                        c.business_number = company.business_number,
                        c.sector = company.sector,
                        c.industry = company.industry,
                        c.market = company.market,
                        c.created_at = datetime()
                    ON MATCH SET
                        c.name = company.name,
                        c.ticker = company.ticker,
                        c.corp_code = company.corp_code,
                        c.name_en = company.name_en,
                        c.business_number = company.business_number,
                        c.sector = company.sector,
                        c.industry = company.industry,
                        c.market = company.market,
                        c.updated_at = datetime()
                    RETURN count(c) as processed
                    """

                    result = await session.run(query, companies=batch)
                    record = await result.single()
                    processed = record["processed"] if record else 0

                    # 통계 업데이트 (정확한 생성/업데이트 구분은 어려우므로 대략적으로)
                    if i + batch_size < total:
                        self.stats["created"] += processed

                    print(f"  {i + batch_size}/{total} 처리됨...")

                except Exception as e:
                    logger.error(f"배치 {i}-{i+batch_size} 동기화 실패: {e}")
                    self.stats["errors"] += len(batch)

            # 최종 통계 계산
            created = max(0, self.stats["neo4j_after"] - self.stats["neo4j_before"])
            updated = self.stats["pg_total"] - created
            self.stats["created"] = created
            self.stats["updated"] = updated

    async def _verify_samsung(self):
        """삼성전자가 Neo4j에 정상 동기화되었는지 검증"""
        async with self.neo4j_driver.session() as session:
            result = await session.run(
                "MATCH (c:Company) WHERE c.ticker = '005930' RETURN c.name, c.id LIMIT 1"
            )
            record = await result.single()

            if record:
                print(f"  ✅ 삼성전자 발견: {record['c.name']}, id={record['c.id']}")
            else:
                print(f"  ❌ 삼성전자 미발견 (ticker: 005930)")
                logger.warning("삼성전자가 Neo4j에 동기화되지 않았습니다!")

    def _print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 동기화 완료")
        print("=" * 60)
        print(f"PostgreSQL 회사: {self.stats['pg_total']:,}개")
        print(f"Neo4j 회사 (동기화 전): {self.stats['neo4j_before']:,}개")
        print(f"Neo4j 회사 (동기화 후): {self.stats['neo4j_after']:,}개")
        print(f"신규 생성: {self.stats['created']:,}개")
        print(f"업데이트: {self.stats['updated']:,}개")
        print(f"에러: {self.stats['errors']:,}건")
        print("=" * 60)


async def main():
    """메인"""
    syncer = CompanySyncer()
    await syncer.run()


if __name__ == "__main__":
    asyncio.run(main())
