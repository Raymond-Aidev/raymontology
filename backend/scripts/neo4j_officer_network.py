#!/usr/bin/env python3
"""
Neo4j 임원 네트워크 구축

PostgreSQL의 officer_positions 테이블 데이터를 Neo4j 그래프로 임포트하여
임원 → 회사 관계망 구축

수정 이력:
- 2025-12-17: officer_positions 테이블 기반으로 변경 (officers.current_company_id가 NULL이므로)
"""
import asyncio
import logging
import sys
from typing import Dict, List
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Company, Officer
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jOfficerNetworkBuilder:
    """
    Neo4j 임원 네트워크 구축기

    그래프 스키마:
    - (Officer)-[:WORKS_AT]->(Company)
    - (Officer)-[:BOARD_MEMBER_AT]->(Company)  # 이사회 멤버인 경우
    """

    def __init__(self):
        self.driver = None
        self.stats = {
            "officers": 0,
            "companies": 0,
            "works_at_rels": 0,
            "board_member_rels": 0,
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

    async def create_constraints(self):
        """제약 조건 및 인덱스 생성"""
        async with self.driver.session() as session:
            # Officer 유니크 제약
            await session.run("""
                CREATE CONSTRAINT officer_id IF NOT EXISTS
                FOR (o:Officer) REQUIRE o.id IS UNIQUE
            """)

            # Company 제약 (이미 존재할 수 있음)
            try:
                await session.run("""
                    CREATE CONSTRAINT company_id IF NOT EXISTS
                    FOR (c:Company) REQUIRE c.id IS UNIQUE
                """)
            except Exception:
                pass  # 이미 존재

            # 인덱스
            await session.run("""
                CREATE INDEX officer_name IF NOT EXISTS
                FOR (o:Officer) ON (o.name)
            """)

            await session.run("""
                CREATE INDEX officer_position IF NOT EXISTS
                FOR (o:Officer) ON (o.position)
            """)

            logger.info("✓ Neo4j 제약 조건 및 인덱스 생성 완료")

    async def clear_officer_network(self):
        """기존 임원 네트워크 데이터 삭제"""
        async with self.driver.session() as session:
            # Officer 노드와 관계 삭제
            result = await session.run("""
                MATCH (o:Officer)
                DETACH DELETE o
                RETURN count(*) as deleted
            """)
            deleted = (await result.single())["deleted"]
            logger.info(f"✓ 기존 Officer 노드 삭제 완료: {deleted}개")

    async def import_officers_with_companies(self, db: AsyncSession):
        """officer_positions 테이블에서 임원 임포트"""
        # officer_positions 기반 쿼리 (officers.current_company_id가 NULL이므로)
        result = await db.execute(
            text("""
                SELECT
                    o.id as officer_id,
                    o.name as officer_name,
                    o.birth_date as officer_birth_date,
                    o.gender as officer_gender,
                    o.board_count,
                    o.influence_score,
                    o.created_at as officer_created_at,
                    op.company_id,
                    op.position,
                    op.is_current,
                    op.term_start_date,
                    op.term_end_date,
                    c.corp_code
                FROM officer_positions op
                JOIN officers o ON op.officer_id = o.id
                JOIN companies c ON op.company_id = c.id
                WHERE c.corp_code IS NOT NULL
                ORDER BY op.company_id, o.id
            """)
        )
        rows = result.fetchall()

        logger.info(f"  officer_positions에서 {len(rows):,}개 레코드 로드")

        processed_officers = set()
        processed_rels = set()

        async with self.driver.session() as session:
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]

                for row in batch:
                    officer_id = str(row.officer_id)
                    company_id = str(row.company_id)

                    # Officer 노드 생성 (중복 방지)
                    if officer_id not in processed_officers:
                        await session.run("""
                            MERGE (o:Officer {id: $id})
                            SET o.name = $name,
                                o.birth_date = $birth_date,
                                o.gender = $gender,
                                o.board_count = $board_count,
                                o.influence_score = $influence_score,
                                o.created_at = CASE WHEN $created_at IS NOT NULL THEN datetime($created_at) ELSE NULL END
                        """, {
                            "id": officer_id,
                            "name": row.officer_name,
                            "birth_date": row.officer_birth_date,
                            "gender": row.officer_gender,
                            "board_count": row.board_count or 0,
                            "influence_score": float(row.influence_score) if row.influence_score else 0.0,
                            "created_at": row.officer_created_at.isoformat() if row.officer_created_at else None,
                        })
                        processed_officers.add(officer_id)
                        self.stats["officers"] += 1

                    # Officer -> Company 관계 생성 (중복 방지)
                    rel_key = f"{officer_id}:{company_id}:{row.position}"
                    if rel_key not in processed_rels:
                        is_board_member = any(
                            keyword in (row.position or "")
                            for keyword in ["이사", "감사", "director", "board"]
                        )

                        # is_current 속성 포함
                        await session.run("""
                            MATCH (o:Officer {id: $officer_id})
                            MATCH (c:Company {id: $company_id})
                            MERGE (o)-[r:WORKS_AT {position: $position}]->(c)
                            SET r.is_current = $is_current,
                                r.start_date = CASE WHEN $start_date IS NOT NULL THEN date($start_date) ELSE NULL END,
                                r.end_date = CASE WHEN $end_date IS NOT NULL THEN date($end_date) ELSE NULL END,
                                r.board_count = $board_count
                        """, {
                            "officer_id": officer_id,
                            "company_id": company_id,
                            "position": row.position,
                            "is_current": row.is_current if row.is_current is not None else True,
                            "start_date": row.term_start_date.isoformat() if row.term_start_date else None,
                            "end_date": row.term_end_date.isoformat() if row.term_end_date else None,
                            "board_count": row.board_count or 0,
                        })

                        processed_rels.add(rel_key)
                        self.stats["works_at_rels"] += 1

                        # 이사회 멤버 관계
                        if is_board_member:
                            await session.run("""
                                MATCH (o:Officer {id: $officer_id})
                                MATCH (c:Company {id: $company_id})
                                MERGE (o)-[r:BOARD_MEMBER_AT]->(c)
                                SET r.position = $position,
                                    r.is_current = $is_current
                            """, {
                                "officer_id": officer_id,
                                "company_id": company_id,
                                "position": row.position,
                                "is_current": row.is_current if row.is_current is not None else True,
                            })
                            self.stats["board_member_rels"] += 1

                if (i + batch_size) % 5000 == 0 or i + batch_size >= len(rows):
                    logger.info(f"  진행: {min(i + batch_size, len(rows)):,}/{len(rows):,}")

        logger.info(f"✓ {self.stats['officers']:,}명 임원 임포트 완료")
        logger.info(f"✓ {self.stats['works_at_rels']:,}개 WORKS_AT 관계 생성 완료")
        logger.info(f"✓ {self.stats['board_member_rels']:,}개 BOARD_MEMBER_AT 관계 생성 완료")

    async def create_officer_indexes(self):
        """임원 관계 인덱스 생성"""
        async with self.driver.session() as session:
            await session.run("""
                CREATE INDEX officer_influence IF NOT EXISTS
                FOR (o:Officer) ON (o.influence_score)
            """)

            logger.info("✓ 임원 인덱스 생성 완료")

    async def analyze_officer_network(self):
        """임원 네트워크 분석"""
        async with self.driver.session() as session:
            # 여러 회사에 임원으로 있는 사람 (겸직)
            result = await session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                WITH o, COUNT(DISTINCT c) as company_count
                WHERE company_count > 1
                RETURN o.name as officer, company_count
                ORDER BY company_count DESC
                LIMIT 10
            """)

            concurrent_officers = []
            async for record in result:
                concurrent_officers.append({
                    "officer": record["officer"],
                    "count": record["company_count"]
                })

            if concurrent_officers:
                logger.info("=" * 60)
                logger.info("여러 회사에 겸직 중인 임원 TOP 10:")
                for item in concurrent_officers:
                    logger.info(f"  {item['officer']}: {item['count']}개 회사")
                logger.info("=" * 60)

    async def verify_network(self):
        """네트워크 통계 확인"""
        async with self.driver.session() as session:
            # 노드 카운트
            result = await session.run("""
                MATCH (o:Officer) RETURN COUNT(o) as count
            """)
            officer_count = (await result.single())["count"]

            result = await session.run("""
                MATCH (c:Company) RETURN COUNT(c) as count
            """)
            company_count = (await result.single())["count"]

            # 관계 카운트
            result = await session.run("""
                MATCH ()-[r:WORKS_AT]->() RETURN COUNT(r) as count
            """)
            works_at_count = (await result.single())["count"]

            result = await session.run("""
                MATCH ()-[r:BOARD_MEMBER_AT]->() RETURN COUNT(r) as count
            """)
            board_member_count = (await result.single())["count"]

            # 임원이 많은 회사 TOP 5
            result = await session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                RETURN c.name as company, COUNT(o) as officer_count
                ORDER BY officer_count DESC
                LIMIT 5
            """)
            top_companies = []
            async for record in result:
                top_companies.append({
                    "company": record["company"],
                    "count": record["officer_count"]
                })

            logger.info("=" * 60)
            logger.info("Neo4j 임원 네트워크 통계")
            logger.info("=" * 60)
            logger.info(f"  임원 (Officer):           {officer_count:,}명")
            logger.info(f"  회사 (Company):           {company_count:,}개")
            logger.info(f"  WORKS_AT 관계:            {works_at_count:,}개")
            logger.info(f"  BOARD_MEMBER_AT 관계:     {board_member_count:,}개")
            logger.info("")
            logger.info("  임원이 많은 회사 TOP 5:")
            for company in top_companies:
                logger.info(f"    {company['company']}: {company['count']}명")
            logger.info("=" * 60)

    async def build_network(self):
        """전체 네트워크 구축 프로세스"""
        logger.info("임원 네트워크 구축 시작...")

        async with AsyncSessionLocal() as db:
            # 1. 기존 데이터 삭제
            logger.info("[1/5] 기존 Officer 데이터 삭제 중...")
            await self.clear_officer_network()

            # 2. 제약 조건 생성
            logger.info("[2/5] Neo4j 제약 조건 및 인덱스 생성 중...")
            await self.create_constraints()

            # 3. 임원 임포트
            logger.info("[3/5] 임원 임포트 중 (officer_positions 테이블 기반)...")
            await self.import_officers_with_companies(db)

            # 4. 인덱스 생성
            logger.info("[4/5] 인덱스 생성 중...")
            await self.create_officer_indexes()

            # 5. 임원 네트워크 분석
            logger.info("[5/5] 임원 네트워크 분석 중...")
            await self.analyze_officer_network()

        # 검증
        await self.verify_network()

        logger.info("✓ 임원 네트워크 구축 완료!")


async def main():
    async with Neo4jOfficerNetworkBuilder() as builder:
        await builder.build_network()


if __name__ == "__main__":
    asyncio.run(main())
