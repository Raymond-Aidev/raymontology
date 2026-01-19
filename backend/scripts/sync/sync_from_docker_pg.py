#!/usr/bin/env python3
"""
Docker PostgreSQL에서 Neo4j로 전체 동기화 스크립트

Docker PostgreSQL (raymontology-postgres 컨테이너)의 데이터를 Neo4j로 동기화:
- Companies: 3,911개
- Officers: 96,294개
- ConvertibleBonds: 1,953개
- CBSubscribers: 10,003개

Docker PostgreSQL에 직접 연결하여 동기화
"""
import logging
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Set

from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Neo4j 설정
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

BATCH_SIZE = 500


def docker_psql(query: str) -> str:
    """Docker PostgreSQL에서 쿼리 실행"""
    cmd = [
        "docker", "exec", "raymontology-postgres",
        "psql", "-U", "postgres", "-d", "raymontology_dev",
        "-t", "-A", "-c", query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"PostgreSQL query failed: {result.stderr}")
    return result.stdout.strip()


def docker_psql_json(query: str) -> List[Dict]:
    """Docker PostgreSQL에서 쿼리 실행 후 JSON으로 파싱"""
    # JSON 배열로 반환하는 쿼리
    json_query = f"SELECT json_agg(t) FROM ({query}) t"
    result = docker_psql(json_query)
    if not result or result == '':
        return []
    return json.loads(result) or []


class DockerNeo4jSyncer:
    def __init__(self):
        self.neo4j_driver = None
        self.stats = {
            "companies": 0,
            "officers": 0,
            "officer_positions": 0,
            "convertible_bonds": 0,
            "cb_subscribers": 0,
            "works_at": 0,
            "issued": 0,
            "subscribed": 0,
        }

    def connect(self):
        """Neo4j 연결"""
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self.neo4j_driver.verify_connectivity()
        logger.info("✓ Neo4j 연결 성공")

        # Docker PostgreSQL 연결 테스트
        count = docker_psql("SELECT COUNT(*) FROM companies")
        logger.info(f"✓ Docker PostgreSQL 연결 성공 (companies: {count}개)")

    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()

    def clear_neo4j(self):
        """Neo4j 전체 초기화"""
        logger.info("Neo4j 초기화 중...")
        with self.neo4j_driver.session() as session:
            # 모든 노드 및 관계 삭제 (배치 처리)
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("✓ Neo4j 초기화 완료")

    def create_constraints(self):
        """Neo4j 제약조건 및 인덱스 생성"""
        with self.neo4j_driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT officer_id IF NOT EXISTS FOR (o:Officer) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT cb_id IF NOT EXISTS FOR (cb:ConvertibleBond) REQUIRE cb.id IS UNIQUE",
                "CREATE CONSTRAINT subscriber_id IF NOT EXISTS FOR (s:Subscriber) REQUIRE s.id IS UNIQUE",
                "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
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

    def sync_companies(self):
        """회사 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("회사(Company) 동기화 시작...")

        total = int(docker_psql("SELECT COUNT(*) FROM companies"))
        logger.info(f"  Docker PostgreSQL 전체 Company: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            query = f"""
                SELECT id::text, name, ticker, sector, market, corp_code
                FROM companies
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """
            rows = docker_psql_json(query)

            if not rows:
                break

            companies = []
            for row in rows:
                companies.append({
                    "id": row["id"],
                    "name": row["name"] or "Unknown",
                    "ticker": row["ticker"],
                    "sector": row["sector"],
                    "market": row["market"],
                    "corp_code": row["corp_code"],
                })

            if companies:
                with self.neo4j_driver.session() as session:
                    session.run("""
                        UNWIND $companies AS c
                        MERGE (company:Company {id: c.id})
                        SET company.name = c.name,
                            company.ticker = c.ticker,
                            company.sector = c.sector,
                            company.market = c.market,
                            company.corp_code = c.corp_code,
                            company.synced_at = datetime()
                    """, companies=companies)
                    synced += len(companies)

            offset += BATCH_SIZE
            if offset % 2000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        self.stats["companies"] = synced
        logger.info(f"✓ Company 동기화 완료: {synced}개")

    def sync_officers(self):
        """임원 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("임원(Officer) 동기화 시작...")

        total = int(docker_psql("SELECT COUNT(*) FROM officers"))
        logger.info(f"  Docker PostgreSQL 전체 Officer: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            query = f"""
                SELECT id::text, name, position, current_company_id::text,
                       birth_date::text, gender
                FROM officers
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """
            rows = docker_psql_json(query)

            if not rows:
                break

            officers = []
            for row in rows:
                officers.append({
                    "id": row["id"],
                    "name": row["name"] or "Unknown",
                    "position": row["position"],
                    "company_id": row["current_company_id"],
                    "birth_date": row["birth_date"],
                    "gender": row["gender"],
                })

            if officers:
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
                    """, officers=officers)
                    synced += len(officers)

            offset += BATCH_SIZE
            if offset % 10000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        self.stats["officers"] = synced
        logger.info(f"✓ Officer 동기화 완료: {synced}개")

    def sync_officer_positions(self):
        """임원-회사 관계(WORKS_AT) 동기화"""
        logger.info("=" * 60)
        logger.info("임원직책(WORKS_AT) 관계 동기화 시작...")

        total = int(docker_psql("SELECT COUNT(*) FROM officer_positions"))
        logger.info(f"  Docker PostgreSQL 전체 officer_positions: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            query = f"""
                SELECT officer_id::text, company_id::text, position,
                       term_start_date::text, term_end_date::text, is_current
                FROM officer_positions
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """
            rows = docker_psql_json(query)

            if not rows:
                break

            positions = []
            for row in rows:
                positions.append({
                    "officer_id": row["officer_id"],
                    "company_id": row["company_id"],
                    "position": row["position"] or "임원",
                    "start_date": row["term_start_date"],
                    "end_date": row["term_end_date"],
                    "is_current": row["is_current"] if row["is_current"] is not None else True,
                })

            if positions:
                with self.neo4j_driver.session() as session:
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
            if offset % 20000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        self.stats["works_at"] = synced
        logger.info(f"✓ WORKS_AT 관계 동기화 완료: {synced}개")

    def sync_convertible_bonds(self):
        """전환사채 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("전환사채(ConvertibleBond) 동기화 시작...")

        total = int(docker_psql("SELECT COUNT(*) FROM convertible_bonds"))
        logger.info(f"  Docker PostgreSQL 전체 CB: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            query = f"""
                SELECT id::text, company_id::text, bond_name, bond_type,
                       issue_date::text, maturity_date::text, issue_amount,
                       interest_rate, conversion_price, status
                FROM convertible_bonds
                ORDER BY id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """
            rows = docker_psql_json(query)

            if not rows:
                break

            cbs = []
            for row in rows:
                cbs.append({
                    "id": row["id"],
                    "company_id": row["company_id"],
                    "bond_name": row["bond_name"] or "전환사채",
                    "bond_type": row["bond_type"],
                    "issue_date": row["issue_date"],
                    "maturity_date": row["maturity_date"],
                    "issue_amount": float(row["issue_amount"]) if row["issue_amount"] else None,
                    "interest_rate": float(row["interest_rate"]) if row["interest_rate"] else None,
                    "conversion_price": float(row["conversion_price"]) if row["conversion_price"] else None,
                    "status": row["status"],
                })

            if cbs:
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
                    """, cbs=cbs)

                    # ISSUED 관계 생성
                    session.run("""
                        UNWIND $cbs AS cb
                        MATCH (company:Company {id: cb.company_id})
                        MATCH (bond:ConvertibleBond {id: cb.id})
                        MERGE (company)-[r:ISSUED]->(bond)
                        SET r.synced_at = datetime()
                    """, cbs=cbs)

                    synced += len(cbs)

            offset += BATCH_SIZE
            if offset % 1000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        self.stats["convertible_bonds"] = synced
        self.stats["issued"] = synced
        logger.info(f"✓ ConvertibleBond 동기화 완료: {synced}개")

    def sync_subscribers(self):
        """CB 인수자 데이터 동기화"""
        logger.info("=" * 60)
        logger.info("인수자(Subscriber) 동기화 시작...")

        total = int(docker_psql("SELECT COUNT(*) FROM cb_subscribers"))
        logger.info(f"  Docker PostgreSQL 전체 cb_subscribers: {total}개")

        offset = 0
        synced = 0

        while offset < total:
            query = f"""
                SELECT s.id::text, s.cb_id::text, s.subscriber_name,
                       s.subscriber_type, s.is_related_party,
                       s.subscription_amount, cb.company_id::text
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON s.cb_id = cb.id
                ORDER BY s.id
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """
            rows = docker_psql_json(query)

            if not rows:
                break

            subs = []
            for row in rows:
                subs.append({
                    "id": row["id"],
                    "cb_id": row["cb_id"],
                    "name": row["subscriber_name"] or "Unknown",
                    "type": row["subscriber_type"],
                    "is_related_party": row["is_related_party"] if row["is_related_party"] else "N",
                    "subscription_amount": float(row["subscription_amount"]) if row["subscription_amount"] else None,
                    "company_id": row["company_id"],
                })

            if subs:
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
                    """, subs=subs)

                    # SUBSCRIBED 관계 생성 (Subscriber -> CB)
                    session.run("""
                        UNWIND $subs AS s
                        MATCH (sub:Subscriber {id: s.id})
                        MATCH (cb:ConvertibleBond {id: s.cb_id})
                        MERGE (sub)-[r:SUBSCRIBED]->(cb)
                        SET r.amount = s.subscription_amount,
                            r.synced_at = datetime()
                    """, subs=subs)

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
                    """, subs=subs)

                    synced += len(subs)

            offset += BATCH_SIZE
            if offset % 3000 == 0 or offset >= total:
                logger.info(f"  진행: {min(offset, total)}/{total}")

        self.stats["cb_subscribers"] = synced
        self.stats["subscribed"] = synced
        logger.info(f"✓ Subscriber 동기화 완료: {synced}개")

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

    def run(self, clear_first: bool = True):
        """전체 동기화 실행"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Docker PostgreSQL → Neo4j 전체 동기화 시작")
        logger.info(f"시작 시간: {start_time}")
        logger.info("=" * 60)

        try:
            self.connect()

            if clear_first:
                self.clear_neo4j()

            self.create_constraints()

            # 순서대로 동기화
            self.sync_companies()
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
    import sys
    clear_first = "--no-clear" not in sys.argv
    syncer = DockerNeo4jSyncer()
    syncer.run(clear_first=clear_first)


if __name__ == "__main__":
    main()
