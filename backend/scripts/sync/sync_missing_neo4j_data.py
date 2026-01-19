#!/usr/bin/env python3
"""
Neo4j 누락 데이터 동기화 스크립트 (동기 버전)

PostgreSQL의 데이터를 Neo4j로 동기화:
- Officers: 38,125개
- ConvertibleBonds: 1,435개
- CBSubscribers: 8,656개
- OfficerPositions: WORKS_AT 관계

배치 처리로 메모리 효율적 처리
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set

import psycopg2
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URLs - Docker PostgreSQL 연결
# Docker 컨테이너에서 노출된 포트 사용 (docker-compose.yml 참조)
POSTGRES_HOST = "localhost"  # Docker PostgreSQL은 localhost:5432로 노출됨
POSTGRES_PORT = 5432
POSTGRES_DB = "raymontology_dev"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "dev_password"

# Docker PostgreSQL로 연결 여부 확인을 위한 설정
# docker-compose에서 postgres 컨테이너가 5432 포트를 호스트에 노출하므로
# 실제로는 Docker PostgreSQL에 연결됨

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

BATCH_SIZE = 500


class Neo4jSyncer:
    def __init__(self):
        self.neo4j_driver = None
        self.pg_conn = None
        self.stats = {
            "officers": 0,
            "officer_positions": 0,
            "convertible_bonds": 0,
            "cb_subscribers": 0,
            "works_at": 0,
            "issued": 0,
            "subscribed": 0,
        }

    def connect(self):
        """데이터베이스 연결"""
        # Neo4j
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.neo4j_driver.verify_connectivity()
        logger.info("✓ Neo4j 연결 성공")

        # PostgreSQL
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

    def create_constraints(self):
        """Neo4j 제약조건 및 인덱스 생성"""
        with self.neo4j_driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT officer_id IF NOT EXISTS FOR (o:Officer) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT cb_id IF NOT EXISTS FOR (cb:ConvertibleBond) REQUIRE cb.id IS UNIQUE",
                "CREATE CONSTRAINT subscriber_id IF NOT EXISTS FOR (s:Subscriber) REQUIRE s.id IS UNIQUE",
                "CREATE INDEX officer_name IF NOT EXISTS FOR (o:Officer) ON (o.name)",
                "CREATE INDEX cb_company IF NOT EXISTS FOR (cb:ConvertibleBond) ON (cb.company_id)",
                "CREATE INDEX subscriber_name IF NOT EXISTS FOR (s:Subscriber) ON (s.name)",
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"제약조건 생성 경고: {e}")
            logger.info("✓ 제약조건 및 인덱스 생성 완료")

    def get_existing_neo4j_ids(self, label: str) -> Set[str]:
        """Neo4j에 이미 존재하는 ID 조회"""
        with self.neo4j_driver.session() as session:
            result = session.run(f"MATCH (n:{label}) RETURN n.id as id")
            return {record["id"] for record in result}

    def sync_officers(self):
        """임원 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("임원(Officer) 동기화 시작...")

        existing_ids = self.get_existing_neo4j_ids("Officer")
        logger.info(f"  Neo4j 기존 Officer: {len(existing_ids)}개")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM officers")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 Officer: {total}개")

        offset = 0
        synced = 0

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

            # 새로운 데이터만 필터링
            new_officers = []
            for row in rows:
                if row[0] not in existing_ids:
                    new_officers.append({
                        "id": row[0],
                        "name": row[1] or "Unknown",
                        "position": row[2],
                        "company_id": row[3],
                        "birth_date": str(row[4]) if row[4] else None,
                        "gender": row[5],
                    })

            if new_officers:
                with self.neo4j_driver.session() as session:
                    session.run("""
                        UNWIND $officers AS o
                        MERGE (officer:Officer {id: o.id})
                        SET officer.name = o.name,
                            officer.position = o.position,
                            officer.company_id = o.company_id,
                            officer.birth_date = o.birth_date,
                            officer.gender = o.gender,
                            officer.synced_at = datetime()
                    """, officers=new_officers)
                    synced += len(new_officers)

            offset += BATCH_SIZE
            if offset % 5000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total} (신규: {synced}개)")

        cursor.close()
        self.stats["officers"] = synced
        logger.info(f"✓ Officer 동기화 완료: {synced}개 추가")

    def sync_officer_positions(self):
        """임원-회사 관계(WORKS_AT) 동기화"""
        logger.info("=" * 60)
        logger.info("임원직책(WORKS_AT) 관계 동기화 시작...")

        cursor = self.pg_conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM officer_positions")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 officer_positions: {total}개")

        offset = 0
        synced = 0

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
                    # WORKS_AT 관계 생성
                    session.run("""
                        UNWIND $positions AS p
                        MATCH (o:Officer {id: p.officer_id})
                        MATCH (c:Company {id: p.company_id})
                        MERGE (o)-[r:WORKS_AT]->(c)
                        SET r.position = p.position,
                            r.start_date = p.start_date,
                            r.end_date = p.end_date,
                            r.is_current = p.is_current,
                            r.synced_at = datetime()
                    """, positions=positions)
                    synced += len(positions)

            offset += BATCH_SIZE
            if offset % 10000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        cursor.close()
        self.stats["works_at"] = synced
        logger.info(f"✓ WORKS_AT 관계 동기화 완료: {synced}개")

    def sync_convertible_bonds(self):
        """전환사채 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("전환사채(ConvertibleBond) 동기화 시작...")

        existing_ids = self.get_existing_neo4j_ids("ConvertibleBond")
        logger.info(f"  Neo4j 기존 CB: {len(existing_ids)}개")

        cursor = self.pg_conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM convertible_bonds")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 CB: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            cursor.execute(f"""
                SELECT id::text, company_id::text, bond_name, bond_type,
                       issue_date, maturity_date, issue_amount,
                       interest_rate, conversion_price, status
                FROM convertible_bonds
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            new_cbs = []
            for row in rows:
                if row[0] not in existing_ids:
                    new_cbs.append({
                        "id": row[0],
                        "company_id": row[1],
                        "bond_name": row[2] or "전환사채",
                        "bond_type": row[3],
                        "issue_date": str(row[4]) if row[4] else None,
                        "maturity_date": str(row[5]) if row[5] else None,
                        "issue_amount": float(row[6]) if row[6] else None,
                        "interest_rate": float(row[7]) if row[7] else None,
                        "conversion_price": float(row[8]) if row[8] else None,
                        "status": row[9],
                    })

            if new_cbs:
                with self.neo4j_driver.session() as session:
                    # CB 노드 생성
                    session.run("""
                        UNWIND $cbs AS cb
                        MERGE (c:ConvertibleBond {id: cb.id})
                        SET c.company_id = cb.company_id,
                            c.bond_name = cb.bond_name,
                            c.bond_type = cb.bond_type,
                            c.issue_date = cb.issue_date,
                            c.maturity_date = cb.maturity_date,
                            c.issue_amount = cb.issue_amount,
                            c.interest_rate = cb.interest_rate,
                            c.conversion_price = cb.conversion_price,
                            c.status = cb.status,
                            c.synced_at = datetime()
                    """, cbs=new_cbs)

                    # ISSUED 관계 생성
                    session.run("""
                        UNWIND $cbs AS cb
                        MATCH (company:Company {id: cb.company_id})
                        MATCH (bond:ConvertibleBond {id: cb.id})
                        MERGE (company)-[r:ISSUED]->(bond)
                        SET r.synced_at = datetime()
                    """, cbs=new_cbs)

                    synced += len(new_cbs)

            offset += BATCH_SIZE
            if offset % 1000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total} (신규: {synced}개)")

        cursor.close()
        self.stats["convertible_bonds"] = synced
        self.stats["issued"] = synced
        logger.info(f"✓ ConvertibleBond 동기화 완료: {synced}개 추가")

    def sync_subscribers(self):
        """CB 인수자 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("인수자(Subscriber) 동기화 시작...")

        existing_ids = self.get_existing_neo4j_ids("Subscriber")
        logger.info(f"  Neo4j 기존 Subscriber: {len(existing_ids)}개")

        cursor = self.pg_conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM cb_subscribers")
        total = cursor.fetchone()[0]
        logger.info(f"  PostgreSQL 전체 cb_subscribers: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            cursor.execute(f"""
                SELECT s.id::text, s.cb_id::text, s.subscriber_name,
                       s.subscriber_type, s.is_related_party,
                       s.subscription_amount, cb.company_id::text
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON s.cb_id = cb.id
                ORDER BY s.id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            rows = cursor.fetchall()

            if not rows:
                break

            new_subs = []
            for row in rows:
                if row[0] not in existing_ids:
                    new_subs.append({
                        "id": row[0],
                        "cb_id": row[1],
                        "name": row[2] or "Unknown",
                        "type": row[3],
                        "is_related_party": row[4] if row[4] else "N",
                        "subscription_amount": float(row[5]) if row[5] else None,
                        "company_id": row[6],
                    })

            if new_subs:
                with self.neo4j_driver.session() as session:
                    # Subscriber 노드 생성
                    session.run("""
                        UNWIND $subs AS s
                        MERGE (sub:Subscriber {id: s.id})
                        SET sub.name = s.name,
                            sub.type = s.type,
                            sub.is_related_party = s.is_related_party,
                            sub.subscription_amount = s.subscription_amount,
                            sub.cb_id = s.cb_id,
                            sub.synced_at = datetime()
                    """, subs=new_subs)

                    # SUBSCRIBED 관계 생성 (Subscriber -> CB)
                    session.run("""
                        UNWIND $subs AS s
                        MATCH (sub:Subscriber {id: s.id})
                        MATCH (cb:ConvertibleBond {id: s.cb_id})
                        MERGE (sub)-[r:SUBSCRIBED]->(cb)
                        SET r.amount = s.subscription_amount,
                            r.synced_at = datetime()
                    """, subs=new_subs)

                    # INVESTED_IN 관계 생성 (Subscriber -> Company)
                    session.run("""
                        UNWIND $subs AS s
                        MATCH (sub:Subscriber {id: s.id})
                        MATCH (company:Company {id: s.company_id})
                        MERGE (sub)-[r:INVESTED_IN]->(company)
                        ON CREATE SET r.total_amount = s.subscription_amount,
                                      r.investment_count = 1,
                                      r.synced_at = datetime()
                        ON MATCH SET r.total_amount = r.total_amount + coalesce(s.subscription_amount, 0),
                                     r.investment_count = r.investment_count + 1,
                                     r.synced_at = datetime()
                    """, subs=new_subs)

                    synced += len(new_subs)

            offset += BATCH_SIZE
            if offset % 2000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total} (신규: {synced}개)")

        cursor.close()
        self.stats["cb_subscribers"] = synced
        self.stats["subscribed"] = synced
        logger.info(f"✓ Subscriber 동기화 완료: {synced}개 추가")

    def verify_sync(self):
        """동기화 결과 검증"""
        logger.info("=" * 60)
        logger.info("동기화 결과 검증...")

        with self.neo4j_driver.session() as session:
            # 노드 카운트
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as cnt
                ORDER BY cnt DESC
            """)
            records = list(result)
            logger.info("\n[Neo4j 노드 현황]")
            for r in records:
                logger.info(f"  {r['label']}: {r['cnt']:,}개")

            # 관계 카운트
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as cnt
                ORDER BY cnt DESC
            """)
            records = list(result)
            logger.info("\n[Neo4j 관계 현황]")
            for r in records:
                logger.info(f"  {r['type']}: {r['cnt']:,}개")

    def run(self):
        """전체 동기화 실행"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Neo4j 누락 데이터 동기화 시작")
        logger.info(f"시작 시간: {start_time}")
        logger.info("=" * 60)

        try:
            self.connect()
            self.create_constraints()

            # 순서대로 동기화 (Company는 이미 동기화됨)
            self.sync_officers()
            self.sync_officer_positions()
            self.sync_convertible_bonds()
            self.sync_subscribers()
            self.verify_sync()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("동기화 완료!")
            logger.info(f"소요 시간: {duration}")
            logger.info("\n[동기화 통계]")
            for key, value in self.stats.items():
                logger.info(f"  {key}: {value:,}개")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"동기화 실패: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    syncer = Neo4jSyncer()
    syncer.run()


if __name__ == "__main__":
    main()
