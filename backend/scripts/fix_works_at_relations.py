#!/usr/bin/env python3
"""
WORKS_AT 관계 재생성 스크립트

문제:
- Officer는 PostgreSQL ID로 생성됨
- Company는 기존 Neo4j ID 사용 (PostgreSQL ID와 다름)
- officer_positions.company_id는 PostgreSQL company ID
- WORKS_AT 관계가 생성되지 않음 (ID 불일치)

해결:
- corp_code를 통해 매핑
- officer_positions → officers.id + companies.corp_code → Neo4j WORKS_AT
"""
import logging
from datetime import datetime
from typing import Dict

import psycopg2
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "raymontology_dev"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "dev_password"

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

BATCH_SIZE = 1000


class WorksAtFixer:
    def __init__(self):
        self.neo4j_driver = None
        self.pg_conn = None
        self.company_id_map: Dict[str, str] = {}  # pg_id -> corp_code
        self.stats = {
            "deleted_works_at": 0,
            "created_works_at": 0,
            "skipped": 0,
        }

    def connect(self):
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.neo4j_driver.verify_connectivity()
        logger.info("✓ Neo4j 연결 성공")

        self.pg_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        logger.info("✓ PostgreSQL 연결 성공")

    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
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

    def delete_existing_works_at(self):
        """기존 WORKS_AT 관계 삭제"""
        logger.info("=" * 60)
        logger.info("기존 WORKS_AT 관계 삭제...")

        with self.neo4j_driver.session() as session:
            total_deleted = 0
            while True:
                result = session.run("""
                    MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                    WITH r LIMIT 10000
                    DELETE r
                    RETURN count(*) as deleted
                """)
                deleted = result.single()["deleted"]
                total_deleted += deleted
                if deleted == 0:
                    break
                logger.info(f"  삭제 진행: {total_deleted:,}개")

            self.stats["deleted_works_at"] = total_deleted
            logger.info(f"✓ WORKS_AT 삭제 완료: {total_deleted:,}개")

    def create_works_at(self):
        """corp_code 기반 WORKS_AT 관계 생성"""
        logger.info("=" * 60)
        logger.info("WORKS_AT 관계 재생성 (corp_code 기반)...")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM officer_positions")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL officer_positions: {total:,}개")

        offset = 0
        created = 0
        skipped = 0

        while offset < total:
            cursor.execute(f"""
                SELECT op.officer_id::text, op.company_id::text, op.position,
                       op.term_start_date, op.term_end_date, op.is_current
                FROM officer_positions op
                ORDER BY op.id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            positions = []
            for row in rows:
                officer_id = row[0]
                company_pg_id = row[1]

                # PostgreSQL company ID → corp_code 변환
                corp_code = self.company_id_map.get(company_pg_id)
                if not corp_code:
                    skipped += 1
                    continue

                positions.append({
                    "officer_id": officer_id,
                    "corp_code": corp_code,
                    "position": row[2] or "임원",
                    "start_date": str(row[3]) if row[3] else None,
                    "end_date": str(row[4]) if row[4] else None,
                    "is_current": row[5] if row[5] is not None else True,
                })

            if positions:
                with self.neo4j_driver.session() as session:
                    result = session.run("""
                        UNWIND $positions AS p
                        MATCH (o:Officer {id: p.officer_id})
                        MATCH (c:Company {corp_code: p.corp_code})
                        CREATE (o)-[r:WORKS_AT {
                            position: p.position,
                            start_date: p.start_date,
                            end_date: p.end_date,
                            is_current: p.is_current,
                            synced_at: datetime()
                        }]->(c)
                        RETURN count(r) as cnt
                    """, positions=positions)
                    cnt = result.single()["cnt"]
                    created += cnt

            offset += BATCH_SIZE
            if offset % 10000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total):,}/{total:,} (생성: {created:,}, 스킵: {skipped:,})")

        cursor.close()
        self.stats["created_works_at"] = created
        self.stats["skipped"] = skipped
        logger.info(f"✓ WORKS_AT 생성 완료: {created:,}개 (스킵: {skipped:,}개)")

    def verify(self):
        """결과 검증"""
        logger.info("=" * 60)
        logger.info("결과 검증...")

        with self.neo4j_driver.session() as session:
            result = session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as cnt")
            cnt = result.single()["cnt"]
            logger.info(f"  WORKS_AT 관계: {cnt:,}개")

            # 아세아제지 김동규 확인
            result = session.run("""
                MATCH (c:Company {corp_code: '00138729'})<-[r:WORKS_AT]-(o:Officer)
                WHERE o.name = '김동규'
                RETURN o.name, o.birth_date, o.position, c.name
            """)
            records = list(result)
            if records:
                logger.info("\n  [아세아제지 김동규 확인]")
                for r in records:
                    logger.info(f"    {r['o.name']} ({r['o.birth_date']}) - {r['o.position']} @ {r['c.name']}")
            else:
                logger.warning("  아세아제지 김동규를 찾을 수 없음")

            # 샘플
            result = session.run("""
                MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                WHERE o.birth_date IS NOT NULL
                RETURN o.name, o.birth_date, c.name
                LIMIT 5
            """)
            logger.info("\n  [샘플 데이터]")
            for r in result:
                logger.info(f"    {r['o.name']} ({r['o.birth_date']}) - {r['c.name']}")

    def run(self):
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("WORKS_AT 관계 재생성 시작")
        logger.info(f"시작 시간: {start_time}")
        logger.info("=" * 60)

        try:
            self.connect()
            self.load_company_mapping()
            self.delete_existing_works_at()
            self.create_works_at()
            self.verify()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("완료!")
            logger.info(f"소요 시간: {duration}")
            logger.info("\n[통계]")
            for key, value in self.stats.items():
                logger.info(f"  {key}: {value:,}개")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"실패: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    fixer = WorksAtFixer()
    fixer.run()


if __name__ == "__main__":
    main()
