#!/usr/bin/env python3
"""
Neo4j 임원 데이터 재동기화 스크립트

문제: PostgreSQL과 Neo4j의 officer ID가 불일치
- Neo4j에서 새 UUID 생성하여 ID 불일치
- birth_date가 NULL인 임원 11,497명 (Neo4j)
- PostgreSQL에는 38,081명이 birth_date 보유

해결:
1. Neo4j 기존 Officer 노드 및 WORKS_AT 관계 삭제
2. PostgreSQL 데이터로 재생성 (PostgreSQL ID 사용)
3. birth_date 형식 통일: YYYYMM → YYYY.MM
"""
import logging
import sys
from datetime import datetime
from typing import List, Dict, Optional

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


def normalize_birth_date(birth_date: Optional[str]) -> Optional[str]:
    """
    birth_date 형식 정규화: YYYYMM → YYYY.MM

    입력 예시:
    - "197410" → "1974.10"
    - "1974.10" → "1974.10" (유지)
    - "1974년 10월" → "1974.10"
    - None → None
    """
    if not birth_date:
        return None

    birth_date = str(birth_date).strip()

    # 이미 YYYY.MM 형식
    if '.' in birth_date and len(birth_date) == 7:
        return birth_date

    # YYYYMM 형식 (6자리 숫자)
    if birth_date.isdigit() and len(birth_date) == 6:
        return f"{birth_date[:4]}.{birth_date[4:6]}"

    # YYYY년 MM월 형식
    if '년' in birth_date:
        import re
        match = re.search(r'(\d{4})년?\s*(\d{1,2})월?', birth_date)
        if match:
            year, month = match.groups()
            return f"{year}.{int(month):02d}"

    # 기타 형식은 그대로 반환
    return birth_date


class OfficerResyncer:
    def __init__(self):
        self.neo4j_driver = None
        self.pg_conn = None
        self.stats = {
            "deleted_officers": 0,
            "deleted_works_at": 0,
            "created_officers": 0,
            "created_works_at": 0,
            "officers_with_birth": 0,
        }

    def connect(self):
        """데이터베이스 연결"""
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

    def backup_stats(self):
        """기존 데이터 통계 백업"""
        logger.info("=" * 60)
        logger.info("기존 Neo4j 데이터 통계")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Officer)
                RETURN
                    count(*) as total,
                    count(o.birth_date) as has_birth,
                    count(CASE WHEN o.birth_date IS NULL THEN 1 END) as no_birth
            """)
            record = result.single()
            logger.info(f"  Officer 전체: {record['total']:,}개")
            logger.info(f"  birth_date 있음: {record['has_birth']:,}개")
            logger.info(f"  birth_date 없음: {record['no_birth']:,}개")

            result = session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as cnt")
            cnt = result.single()["cnt"]
            logger.info(f"  WORKS_AT 관계: {cnt:,}개")

    def delete_existing_officers(self):
        """기존 Officer 노드 및 WORKS_AT 관계 삭제"""
        logger.info("=" * 60)
        logger.info("기존 Officer 데이터 삭제 시작...")

        with self.neo4j_driver.session() as session:
            # WORKS_AT 관계 삭제
            result = session.run("""
                MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                WITH r LIMIT 10000
                DELETE r
                RETURN count(*) as deleted
            """)

            total_deleted_rels = 0
            while True:
                result = session.run("""
                    MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                    WITH r LIMIT 10000
                    DELETE r
                    RETURN count(*) as deleted
                """)
                deleted = result.single()["deleted"]
                total_deleted_rels += deleted
                if deleted == 0:
                    break
                logger.info(f"  WORKS_AT 삭제 진행: {total_deleted_rels:,}개")

            self.stats["deleted_works_at"] = total_deleted_rels
            logger.info(f"✓ WORKS_AT 관계 삭제 완료: {total_deleted_rels:,}개")

            # Officer 노드 삭제 (배치 처리)
            total_deleted = 0
            while True:
                result = session.run("""
                    MATCH (o:Officer)
                    WHERE NOT (o)--()
                    WITH o LIMIT 10000
                    DELETE o
                    RETURN count(*) as deleted
                """)
                deleted = result.single()["deleted"]
                total_deleted += deleted
                if deleted == 0:
                    break
                logger.info(f"  Officer 삭제 진행: {total_deleted:,}개")

            # 관계가 있는 Officer도 삭제 (DETACH DELETE)
            result = session.run("""
                MATCH (o:Officer)
                DETACH DELETE o
                RETURN count(*) as deleted
            """)
            remaining = result.single()["deleted"]
            total_deleted += remaining

            self.stats["deleted_officers"] = total_deleted
            logger.info(f"✓ Officer 노드 삭제 완료: {total_deleted:,}개")

    def sync_officers(self):
        """PostgreSQL에서 Officer 노드 재생성"""
        logger.info("=" * 60)
        logger.info("Officer 노드 재생성 시작...")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM officers")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 Officer: {total:,}개")

        offset = 0
        synced = 0
        with_birth = 0

        while offset < total:
            cursor.execute(f"""
                SELECT id::text, name, position, current_company_id::text,
                       birth_date, gender
                FROM officers
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            officers = []
            for row in rows:
                birth_date = normalize_birth_date(row[4])
                if birth_date:
                    with_birth += 1

                officers.append({
                    "id": row[0],
                    "name": row[1] or "Unknown",
                    "position": row[2],
                    "company_id": row[3],
                    "birth_date": birth_date,
                    "gender": row[5],
                })

            if officers:
                with self.neo4j_driver.session() as session:
                    session.run("""
                        UNWIND $officers AS o
                        CREATE (officer:Officer {
                            id: o.id,
                            name: o.name,
                            position: o.position,
                            company_id: o.company_id,
                            birth_date: o.birth_date,
                            gender: o.gender,
                            synced_at: datetime()
                        })
                    """, officers=officers)
                    synced += len(officers)

            offset += BATCH_SIZE
            if offset % 5000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total):,}/{total:,} (생성: {synced:,}개)")

        cursor.close()
        self.stats["created_officers"] = synced
        self.stats["officers_with_birth"] = with_birth
        logger.info(f"✓ Officer 노드 생성 완료: {synced:,}개 (birth_date: {with_birth:,}개)")

    def sync_works_at(self):
        """WORKS_AT 관계 재생성"""
        logger.info("=" * 60)
        logger.info("WORKS_AT 관계 재생성 시작...")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM officer_positions")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 officer_positions: {total:,}개")

        offset = 0
        synced = 0

        while offset < total:
            cursor.execute(f"""
                SELECT op.officer_id::text, op.company_id::text, op.position,
                       op.term_start_date, op.term_end_date, op.is_current,
                       op.birth_date, op.gender
                FROM officer_positions op
                ORDER BY op.id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            positions = []
            for row in rows:
                positions.append({
                    "officer_id": row[0],
                    "company_id": row[1],
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
                        MATCH (c:Company {id: p.company_id})
                        CREATE (o)-[r:WORKS_AT {
                            position: p.position,
                            start_date: p.start_date,
                            end_date: p.end_date,
                            is_current: p.is_current,
                            synced_at: datetime()
                        }]->(c)
                        RETURN count(r) as created
                    """, positions=positions)
                    created = result.single()["created"]
                    synced += created

            offset += BATCH_SIZE
            if offset % 10000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total):,}/{total:,} (생성: {synced:,}개)")

        cursor.close()
        self.stats["created_works_at"] = synced
        logger.info(f"✓ WORKS_AT 관계 생성 완료: {synced:,}개")

    def create_indexes(self):
        """인덱스 재생성"""
        logger.info("=" * 60)
        logger.info("인덱스 생성...")

        with self.neo4j_driver.session() as session:
            indexes = [
                "CREATE CONSTRAINT officer_id IF NOT EXISTS FOR (o:Officer) REQUIRE o.id IS UNIQUE",
                "CREATE INDEX officer_name IF NOT EXISTS FOR (o:Officer) ON (o.name)",
                "CREATE INDEX officer_birth IF NOT EXISTS FOR (o:Officer) ON (o.birth_date)",
            ]
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"인덱스 생성 경고: {e}")
            logger.info("✓ 인덱스 생성 완료")

    def verify(self):
        """동기화 결과 검증"""
        logger.info("=" * 60)
        logger.info("동기화 결과 검증")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Officer)
                RETURN
                    count(*) as total,
                    count(o.birth_date) as has_birth,
                    count(CASE WHEN o.birth_date IS NULL THEN 1 END) as no_birth
            """)
            record = result.single()
            logger.info(f"  Officer 전체: {record['total']:,}개")
            logger.info(f"  birth_date 있음: {record['has_birth']:,}개")
            logger.info(f"  birth_date 없음: {record['no_birth']:,}개")

            result = session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as cnt")
            cnt = result.single()["cnt"]
            logger.info(f"  WORKS_AT 관계: {cnt:,}개")

            # 샘플 확인
            result = session.run("""
                MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
                WHERE o.birth_date IS NOT NULL
                RETURN o.name, o.birth_date, c.name as company
                LIMIT 5
            """)
            logger.info("\n  샘플 데이터:")
            for r in result:
                logger.info(f"    {r['name']} ({r['birth_date']}) - {r['company']}")

    def run(self):
        """전체 재동기화 실행"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Neo4j Officer 재동기화 시작")
        logger.info(f"시작 시간: {start_time}")
        logger.info("=" * 60)

        try:
            self.connect()
            self.backup_stats()
            self.delete_existing_officers()
            self.sync_officers()
            self.create_indexes()
            self.sync_works_at()
            self.verify()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("재동기화 완료!")
            logger.info(f"소요 시간: {duration}")
            logger.info("\n[통계]")
            for key, value in self.stats.items():
                logger.info(f"  {key}: {value:,}개")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"재동기화 실패: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Neo4j Officer 재동기화")
    parser.add_argument("--dry-run", action="store_true", help="실제 실행 없이 통계만 확인")
    args = parser.parse_args()

    resyncer = OfficerResyncer()

    if args.dry_run:
        resyncer.connect()
        resyncer.backup_stats()
        resyncer.close()
    else:
        resyncer.run()


if __name__ == "__main__":
    main()
