#!/usr/bin/env python3
"""
Neo4j → PostgreSQL 완전 동기화 스크립트
팔란티어 온톨로지 기반 데이터 마이그레이션

Author: Claude Code (Full-Stack & DB Expert)
Date: 2025-11-25
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncpg
from neo4j import GraphDatabase

# 설정
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
POSTGRES_DSN = "postgresql://postgres:dev_password@localhost:5432/raymontology_dev"

class Neo4jToPostgresSync:
    def __init__(self):
        self.neo4j_driver = None
        self.pg_pool = None
        self.company_id_map: Dict[str, str] = {}  # neo4j_id -> pg_uuid
        self.officer_id_map: Dict[str, str] = {}  # neo4j_id -> pg_uuid
        self.cb_id_map: Dict[str, str] = {}  # neo4j_id -> pg_uuid

    async def connect(self):
        """DB 연결"""
        print("🔌 Connecting to databases...")
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.pg_pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=5, max_size=20)
        print("✅ Connected")

    async def close(self):
        """연결 종료"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.pg_pool:
            await self.pg_pool.close()

    async def truncate_tables(self):
        """PostgreSQL 테이블 초기화"""
        print("\n🗑️  Truncating PostgreSQL tables...")
        async with self.pg_pool.acquire() as conn:
            # FK 제약조건 때문에 순서 중요
            await conn.execute("TRUNCATE cb_subscribers CASCADE")
            await conn.execute("TRUNCATE convertible_bonds CASCADE")
            await conn.execute("TRUNCATE officer_positions CASCADE")
            await conn.execute("TRUNCATE officers CASCADE")
            await conn.execute("TRUNCATE affiliates CASCADE")
            await conn.execute("TRUNCATE companies CASCADE")
        print("✅ Tables truncated")

    async def sync_companies(self):
        """Company 노드 동기화"""
        print("\n📦 Syncing Companies...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                RETURN c.id as id, c.name as name, c.corp_code as corp_code,
                       c.ticker as ticker, c.updated_at as updated_at
            """)
            companies = list(result)

        print(f"   Found {len(companies)} companies in Neo4j")

        async with self.pg_pool.acquire() as conn:
            inserted = 0
            for c in companies:
                pg_uuid = str(uuid.uuid4())
                self.company_id_map[c['id']] = pg_uuid

                await conn.execute("""
                    INSERT INTO companies (id, name, corp_code, ticker, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """, pg_uuid, c['name'], c['corp_code'], c['ticker'])
                inserted += 1

                if inserted % 500 == 0:
                    print(f"   ... {inserted} companies")

        print(f"✅ Synced {inserted} companies")

    async def sync_officers(self):
        """Officer 노드 동기화"""
        print("\n👤 Syncing Officers...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Officer)
                RETURN o.id as id, o.name as name, o.position as position,
                       o.board_count as board_count, o.career_count as career_count,
                       o.influence_score as influence_score, o.created_at as created_at
            """)
            officers = list(result)

        print(f"   Found {len(officers)} officers in Neo4j")

        async with self.pg_pool.acquire() as conn:
            inserted = 0
            for o in officers:
                pg_uuid = str(uuid.uuid4())
                self.officer_id_map[o['id']] = pg_uuid

                # 이름 정제 (&cr; 등 제거)
                name = o['name'].replace('&cr;', ' ').strip() if o['name'] else 'Unknown'
                position = o['position'].replace('&cr;', ' ').strip() if o['position'] else None

                await conn.execute("""
                    INSERT INTO officers (id, name, position, board_count,
                                         network_centrality, influence_score,
                                         created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """, pg_uuid, name, position,
                    o['board_count'] or 0,
                    o['career_count'] or 0.0,
                    o['influence_score'] or 0.0)
                inserted += 1

                if inserted % 5000 == 0:
                    print(f"   ... {inserted} officers")

        print(f"✅ Synced {inserted} officers")

    async def sync_officer_positions(self):
        """WORKS_AT 관계 → officer_positions 동기화"""
        print("\n🔗 Syncing Officer Positions (WORKS_AT relationships)...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Officer)-[r:WORKS_AT]->(c:Company)
                RETURN o.id as officer_id, c.id as company_id,
                       r.position as position, r.is_current as is_current,
                       r.created_at as created_at, r.board_count as board_count
            """)
            positions = list(result)

        print(f"   Found {len(positions)} WORKS_AT relationships in Neo4j")

        async with self.pg_pool.acquire() as conn:
            inserted = 0
            skipped = 0

            for p in positions:
                officer_pg_id = self.officer_id_map.get(p['officer_id'])
                company_pg_id = self.company_id_map.get(p['company_id'])

                if not officer_pg_id or not company_pg_id:
                    skipped += 1
                    continue

                # position 정제
                position = p['position'].replace('&cr;', ' ').strip() if p['position'] else '임원'
                is_current = p['is_current'] if p['is_current'] is not None else True

                await conn.execute("""
                    INSERT INTO officer_positions
                    (id, officer_id, company_id, position, is_current,
                     created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), $6)
                    ON CONFLICT DO NOTHING
                """, str(uuid.uuid4()), officer_pg_id, company_pg_id,
                    position, is_current,
                    '{"source": "neo4j_sync", "sync_date": "2025-11-25"}')
                inserted += 1

                if inserted % 5000 == 0:
                    print(f"   ... {inserted} positions")

        print(f"✅ Synced {inserted} positions (skipped {skipped})")

    async def sync_convertible_bonds(self):
        """ConvertibleBond 노드 + ISSUED 관계 동기화"""
        print("\n💰 Syncing Convertible Bonds...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[r:ISSUED]->(cb:ConvertibleBond)
                RETURN cb.id as id, cb.bond_name as bond_name, cb.bond_type as bond_type,
                       cb.issue_amount as issue_amount, cb.status as status,
                       cb.source_disclosure_id as source_disclosure_id,
                       cb.created_at as created_at, c.id as company_id,
                       r.amount as rel_amount
            """)
            bonds = list(result)

        print(f"   Found {len(bonds)} convertible bonds in Neo4j")

        async with self.pg_pool.acquire() as conn:
            inserted = 0
            skipped = 0

            for cb in bonds:
                company_pg_id = self.company_id_map.get(cb['company_id'])

                if not company_pg_id:
                    skipped += 1
                    continue

                pg_uuid = str(uuid.uuid4())
                self.cb_id_map[cb['id']] = pg_uuid

                # issue_amount 처리
                issue_amount = None
                if cb['issue_amount']:
                    try:
                        issue_amount = float(str(cb['issue_amount']).replace(',', ''))
                    except:
                        pass

                await conn.execute("""
                    INSERT INTO convertible_bonds
                    (id, company_id, bond_name, bond_type, issue_amount, status,
                     source_disclosure_id, created_at, updated_at, properties)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW(), $8)
                    ON CONFLICT DO NOTHING
                """, pg_uuid, company_pg_id, cb['bond_name'], cb['bond_type'],
                    issue_amount, cb['status'], cb['source_disclosure_id'],
                    '{"source": "neo4j_sync", "sync_date": "2025-11-25"}')
                inserted += 1

                if inserted % 500 == 0:
                    print(f"   ... {inserted} bonds")

        print(f"✅ Synced {inserted} convertible bonds (skipped {skipped})")

    async def sync_cb_subscribers(self):
        """Subscriber 노드 + SUBSCRIBED 관계 동기화"""
        print("\n🧾 Syncing CB Subscribers...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Subscriber)-[r:SUBSCRIBED]->(cb:ConvertibleBond)
                RETURN s.id as subscriber_id, s.name as subscriber_name,
                       cb.id as cb_id, r.amount as amount,
                       r.is_related_party as is_related_party,
                       r.relationship as relationship,
                       r.selection_rationale as selection_rationale,
                       r.subscribed_at as subscribed_at,
                       r.subscription_id as subscription_id
            """)
            subscriptions = list(result)

        print(f"   Found {len(subscriptions)} subscriptions in Neo4j")

        async with self.pg_pool.acquire() as conn:
            inserted = 0
            skipped = 0

            for sub in subscriptions:
                cb_pg_id = self.cb_id_map.get(sub['cb_id'])

                if not cb_pg_id:
                    skipped += 1
                    continue

                # amount 처리
                amount = None
                if sub['amount']:
                    try:
                        amount = float(str(sub['amount']).replace(',', ''))
                    except:
                        pass

                # is_related_party 처리
                is_related = 'N'
                if sub['is_related_party']:
                    val = str(sub['is_related_party']).lower()
                    if val in ['y', 'yes', 'true', '1', '예', '있음']:
                        is_related = 'Y'

                await conn.execute("""
                    INSERT INTO cb_subscribers
                    (id, cb_id, subscriber_name, subscription_amount,
                     is_related_party, relationship_to_company,
                     selection_rationale, source_disclosure_id,
                     created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), $9)
                    ON CONFLICT DO NOTHING
                """, str(uuid.uuid4()), cb_pg_id, sub['subscriber_name'],
                    amount, is_related, sub['relationship'],
                    sub['selection_rationale'], sub['subscription_id'],
                    '{"source": "neo4j_sync", "sync_date": "2025-11-25"}')
                inserted += 1

                if inserted % 500 == 0:
                    print(f"   ... {inserted} subscribers")

        print(f"✅ Synced {inserted} subscribers (skipped {skipped})")

    async def verify_sync(self):
        """동기화 결과 검증"""
        print("\n📊 Verifying sync results...")

        # Neo4j 카운트
        with self.neo4j_driver.session() as session:
            neo4j_counts = {}
            for label in ['Company', 'Officer', 'ConvertibleBond', 'Subscriber']:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as cnt")
                neo4j_counts[label] = result.single()['cnt']

            result = session.run("MATCH ()-[r:WORKS_AT]->() RETURN count(r) as cnt")
            neo4j_counts['WORKS_AT'] = result.single()['cnt']

            result = session.run("MATCH ()-[r:SUBSCRIBED]->() RETURN count(r) as cnt")
            neo4j_counts['SUBSCRIBED'] = result.single()['cnt']

        # PostgreSQL 카운트
        async with self.pg_pool.acquire() as conn:
            pg_counts = {}
            pg_counts['companies'] = await conn.fetchval("SELECT count(*) FROM companies")
            pg_counts['officers'] = await conn.fetchval("SELECT count(*) FROM officers")
            pg_counts['officer_positions'] = await conn.fetchval("SELECT count(*) FROM officer_positions")
            pg_counts['convertible_bonds'] = await conn.fetchval("SELECT count(*) FROM convertible_bonds")
            pg_counts['cb_subscribers'] = await conn.fetchval("SELECT count(*) FROM cb_subscribers")

        print("\n" + "="*60)
        print("동기화 결과 비교")
        print("="*60)
        print(f"{'데이터':<25} {'Neo4j':>12} {'PostgreSQL':>12} {'일치':>8}")
        print("-"*60)
        print(f"{'Company → companies':<25} {neo4j_counts['Company']:>12,} {pg_counts['companies']:>12,} {'✅' if neo4j_counts['Company'] == pg_counts['companies'] else '⚠️':>8}")
        print(f"{'Officer → officers':<25} {neo4j_counts['Officer']:>12,} {pg_counts['officers']:>12,} {'✅' if neo4j_counts['Officer'] == pg_counts['officers'] else '⚠️':>8}")
        print(f"{'WORKS_AT → positions':<25} {neo4j_counts['WORKS_AT']:>12,} {pg_counts['officer_positions']:>12,} {'✅' if neo4j_counts['WORKS_AT'] == pg_counts['officer_positions'] else '⚠️':>8}")
        print(f"{'ConvertibleBond → cb':<25} {neo4j_counts['ConvertibleBond']:>12,} {pg_counts['convertible_bonds']:>12,} {'✅' if neo4j_counts['ConvertibleBond'] == pg_counts['convertible_bonds'] else '⚠️':>8}")
        print(f"{'SUBSCRIBED → subscribers':<25} {neo4j_counts['SUBSCRIBED']:>12,} {pg_counts['cb_subscribers']:>12,} {'✅' if neo4j_counts['SUBSCRIBED'] == pg_counts['cb_subscribers'] else '⚠️':>8}")
        print("="*60)

        return pg_counts

    async def run(self):
        """전체 동기화 실행"""
        start_time = datetime.now()
        print("="*60)
        print("Neo4j → PostgreSQL 동기화 시작")
        print(f"시작 시간: {start_time}")
        print("="*60)

        try:
            await self.connect()
            await self.truncate_tables()
            await self.sync_companies()
            await self.sync_officers()
            await self.sync_officer_positions()
            await self.sync_convertible_bonds()
            await self.sync_cb_subscribers()
            results = await self.verify_sync()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"\n✅ 동기화 완료!")
            print(f"   소요 시간: {duration:.1f}초")
            print(f"   총 레코드: {sum(results.values()):,}개")

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await self.close()


if __name__ == "__main__":
    sync = Neo4jToPostgresSync()
    asyncio.run(sync.run())
