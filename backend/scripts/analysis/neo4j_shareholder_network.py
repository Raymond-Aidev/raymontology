"""
Neo4j 대주주 네트워크 구축

PostgreSQL의 major_shareholders 데이터를 Neo4j 그래프로 임포트하여
대주주 → 회사 관계망 구축
"""
import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime

from neo4j import AsyncGraphDatabase
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "raymontology_dev"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "dev_password"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

BATCH_SIZE = 500


class Neo4jShareholderNetworkBuilder:
    """
    Neo4j 대주주 네트워크 구축기

    그래프 스키마:
    - (Shareholder)-[:SHAREHOLDER_OF]->(Company)
    """

    def __init__(self):
        self.driver = None
        self.pg_conn = None
        self.company_id_map: Dict[str, str] = {}  # pg_id -> corp_code
        self.stats = {
            "shareholders": 0,
            "shareholder_rels": 0,
            "skipped": 0,
        }

    def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info(f"✓ Neo4j 연결 성공: {NEO4J_URI}")

        self.pg_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        logger.info("✓ PostgreSQL 연결 성공")

    async def close(self):
        if self.driver:
            await self.driver.close()
        if self.pg_conn:
            self.pg_conn.close()

    def load_company_mapping(self):
        """PostgreSQL company ID → corp_code 매핑 로드"""
        logger.info("=" * 60)
        logger.info("Company ID → corp_code 매핑 로드...")

        cursor = self.pg_conn.cursor()
        cursor.execute("SELECT id::text, corp_code FROM companies WHERE corp_code IS NOT NULL")
        rows = cursor.fetchall()

        for row in rows:
            self.company_id_map[row[0]] = row[1]

        cursor.close()
        logger.info(f"✓ 매핑 로드 완료: {len(self.company_id_map):,}개 회사")

    async def clear_shareholder_network(self):
        """기존 Shareholder 네트워크 데이터 삭제"""
        async with self.driver.session() as session:
            # Shareholder 노드와 관계 삭제
            result = await session.run("""
                MATCH (s:Shareholder)
                DETACH DELETE s
                RETURN count(*) as deleted
            """)
            deleted = (await result.single())["deleted"]
            logger.info(f"✓ 기존 Shareholder 노드 삭제 완료: {deleted}개")

    async def create_constraints(self):
        """Neo4j 제약 조건 및 인덱스 생성"""
        async with self.driver.session() as session:
            # Shareholder 유니크 제약
            await session.run("""
                CREATE CONSTRAINT shareholder_id IF NOT EXISTS
                FOR (s:Shareholder) REQUIRE s.id IS UNIQUE
            """)

            # Shareholder 이름 인덱스
            await session.run("""
                CREATE INDEX shareholder_name IF NOT EXISTS
                FOR (s:Shareholder) ON (s.name)
            """)

            # Shareholder 타입 인덱스
            await session.run("""
                CREATE INDEX shareholder_type IF NOT EXISTS
                FOR (s:Shareholder) ON (s.type)
            """)

            logger.info("✓ Shareholder 제약 조건 및 인덱스 생성 완료")

    async def import_shareholders(self):
        """대주주 데이터 임포트"""
        logger.info("=" * 60)
        logger.info("대주주 데이터 임포트 중...")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM major_shareholders")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL major_shareholders: {total:,}개")

        offset = 0
        created_shareholders = 0
        created_rels = 0
        skipped = 0

        while offset < total:
            cursor.execute(f"""
                SELECT
                    ms.id::text,
                    ms.company_id::text,
                    ms.shareholder_name,
                    ms.shareholder_name_normalized,
                    ms.shareholder_type,
                    ms.share_count,
                    ms.share_ratio::float,
                    ms.is_largest_shareholder,
                    ms.is_related_party,
                    ms.report_date::text,
                    ms.report_year,
                    ms.report_quarter,
                    ms.change_reason,
                    ms.previous_share_ratio::float
                FROM major_shareholders ms
                ORDER BY ms.id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            shareholders_data = []
            for row in rows:
                shareholder_id = row[0]
                company_pg_id = row[1]

                # PostgreSQL company ID → corp_code 변환
                corp_code = self.company_id_map.get(company_pg_id)
                if not corp_code:
                    skipped += 1
                    continue

                shareholders_data.append({
                    "id": shareholder_id,
                    "corp_code": corp_code,
                    "name": row[2] or "Unknown",
                    "name_normalized": row[3],
                    "type": row[4] or "UNKNOWN",
                    "share_count": row[5],
                    "share_ratio": row[6],
                    "is_largest": row[7] or False,
                    "is_related_party": row[8] or False,
                    "report_date": row[9],
                    "report_year": row[10],
                    "report_quarter": row[11],
                    "change_reason": row[12],
                    "previous_ratio": row[13],
                })

            if shareholders_data:
                async with self.driver.session() as session:
                    # Shareholder 노드 생성 및 SHAREHOLDER_OF 관계 생성
                    result = await session.run("""
                        UNWIND $shareholders AS sh
                        MATCH (c:Company {corp_code: sh.corp_code})
                        MERGE (s:Shareholder {id: sh.id})
                        SET s.name = sh.name,
                            s.name_normalized = sh.name_normalized,
                            s.type = sh.type,
                            s.share_count = sh.share_count,
                            s.share_ratio = sh.share_ratio,
                            s.is_largest = sh.is_largest,
                            s.is_related_party = sh.is_related_party,
                            s.report_date = sh.report_date,
                            s.report_year = sh.report_year,
                            s.report_quarter = sh.report_quarter,
                            s.change_reason = sh.change_reason,
                            s.previous_ratio = sh.previous_ratio,
                            s.synced_at = datetime()
                        MERGE (s)-[r:SHAREHOLDER_OF]->(c)
                        SET r.share_ratio = sh.share_ratio,
                            r.share_count = sh.share_count,
                            r.is_largest = sh.is_largest,
                            r.report_date = sh.report_date
                        RETURN count(DISTINCT s) as shareholders, count(r) as rels
                    """, shareholders=shareholders_data)

                    record = await result.single()
                    created_shareholders += record["shareholders"]
                    created_rels += record["rels"]

            offset += BATCH_SIZE
            if offset % 1000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total):,}/{total:,} (주주: {created_shareholders:,}, 관계: {created_rels:,}, 스킵: {skipped:,})")

        cursor.close()
        self.stats["shareholders"] = created_shareholders
        self.stats["shareholder_rels"] = created_rels
        self.stats["skipped"] = skipped
        logger.info(f"✓ Shareholder 임포트 완료: {created_shareholders:,}개 노드, {created_rels:,}개 관계")

    async def verify_network(self):
        """네트워크 통계 확인"""
        async with self.driver.session() as session:
            # 노드 카운트
            result = await session.run("""
                MATCH (s:Shareholder) RETURN COUNT(s) as count
            """)
            shareholder_count = (await result.single())["count"]

            # 관계 카운트
            result = await session.run("""
                MATCH ()-[r:SHAREHOLDER_OF]->() RETURN COUNT(r) as count
            """)
            rel_count = (await result.single())["count"]

            # 주주 타입별 분포
            result = await session.run("""
                MATCH (s:Shareholder)
                RETURN s.type as type, COUNT(s) as count
                ORDER BY count DESC
            """)
            type_dist = []
            async for record in result:
                type_dist.append({
                    "type": record["type"],
                    "count": record["count"]
                })

            # 최대 지분 보유 주주 TOP 5
            result = await session.run("""
                MATCH (s:Shareholder)-[r:SHAREHOLDER_OF]->(c:Company)
                WHERE s.share_ratio IS NOT NULL
                RETURN s.name as shareholder, c.name as company, s.share_ratio as ratio
                ORDER BY s.share_ratio DESC
                LIMIT 5
            """)
            top_shareholders = []
            async for record in result:
                top_shareholders.append({
                    "shareholder": record["shareholder"],
                    "company": record["company"],
                    "ratio": record["ratio"]
                })

            logger.info("=" * 60)
            logger.info("Neo4j 대주주 네트워크 통계")
            logger.info("=" * 60)
            logger.info(f"  Shareholder 노드:          {shareholder_count:,}개")
            logger.info(f"  SHAREHOLDER_OF 관계:       {rel_count:,}개")
            logger.info("")
            logger.info("  주주 타입별 분포:")
            for item in type_dist:
                logger.info(f"    {item['type']}: {item['count']}개")
            logger.info("")
            logger.info("  최대 지분 보유 주주 TOP 5:")
            for item in top_shareholders:
                logger.info(f"    {item['shareholder']}: {item['ratio']:.2f}% ({item['company']})")
            logger.info("=" * 60)

    async def build_network(self):
        """전체 네트워크 구축 프로세스"""
        logger.info("대주주 네트워크 구축 시작...")

        # 1. 회사 매핑 로드
        logger.info("[1/4] 회사 매핑 로드...")
        self.load_company_mapping()

        # 2. 기존 데이터 삭제
        logger.info("[2/4] 기존 Shareholder 데이터 삭제...")
        await self.clear_shareholder_network()

        # 3. 제약 조건 생성
        logger.info("[3/4] 제약 조건 및 인덱스 생성...")
        await self.create_constraints()

        # 4. 대주주 임포트
        logger.info("[4/4] 대주주 데이터 임포트...")
        await self.import_shareholders()

        # 검증
        await self.verify_network()

        logger.info("✓ 대주주 네트워크 구축 완료!")


async def main():
    builder = Neo4jShareholderNetworkBuilder()
    try:
        builder.connect()
        await builder.build_network()
    finally:
        await builder.close()


if __name__ == "__main__":
    asyncio.run(main())
