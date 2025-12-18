#!/usr/bin/env python3
"""
Temporal Data Sync Script
Neo4j → PostgreSQL 동기화 (Temporal 데이터 처리)

전략:
- Officers: 동일 인물의 여러 임기를 officer_positions 테이블에 저장
- ConvertibleBonds: 동일 회사의 여러 CB 발행을 각각 저장
- CB Subscribers: 각 CB별 인수자를 별개로 저장, officer/company 링크
- UPSERT 로직으로 중복 방지
"""
import sys
import os
import asyncio
import asyncpg
from neo4j import GraphDatabase
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import uuid

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Configuration
NEO4J_URI = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')

# Parse DATABASE_URL and remove +asyncpg if present
raw_url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@raymontology-postgres:5432/raymontology_dev')
DATABASE_URL = raw_url.replace('postgresql+asyncpg://', 'postgresql://')


class TemporalDataSync:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.pg_conn = None

    async def connect_postgres(self):
        """PostgreSQL 연결"""
        self.pg_conn = await asyncpg.connect(DATABASE_URL)
        print("✓ PostgreSQL 연결 성공")

    async def close_connections(self):
        """연결 종료"""
        if self.pg_conn:
            await self.pg_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()

    def get_neo4j_companies(self) -> List[Dict[str, Any]]:
        """Neo4j에서 회사 데이터 조회"""
        print("\n[1/5] Companies 조회 중...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                RETURN c.id as id,
                       c.name as name,
                       c.corp_code as corp_code,
                       c.business_number as business_number,
                       c.ticker as ticker,
                       c.sector as sector,
                       c.industry as industry,
                       c.market as market
                ORDER BY c.name
            """)

            companies = [dict(record) for record in result]
            print(f"  ✓ {len(companies)}개 회사 발견")
            return companies

    def get_neo4j_officers(self) -> List[Dict[str, Any]]:
        """Neo4j에서 임원 데이터 조회 (temporal 데이터 포함)"""
        print("\n[2/5] Officers 조회 중...")

        with self.neo4j_driver.session() as session:
            # Officer 기본 정보
            result = session.run("""
                MATCH (o:Officer)
                OPTIONAL MATCH (o)-[r:WORKS_AT|WORKED_AT]->(c:Company)
                RETURN o.id as id,
                       o.name as name,
                       o.name_en as name_en,
                       o.resident_number_hash as resident_number_hash,
                       o.position as position,
                       o.career_history as career_history,
                       o.influence_score as influence_score,
                       o.board_count as board_count,
                       c.id as current_company_id,
                       c.name as current_company_name,
                       r.position as relationship_position,
                       r.term_start as term_start,
                       r.term_end as term_end,
                       r.is_current as is_current,
                       r.source_disclosure_id as source_disclosure_id,
                       r.source_report_date as source_report_date
                ORDER BY o.name
            """)

            # 임원별로 그룹화
            officers_dict = {}
            officer_positions = []

            for record in result:
                officer_id = record['id']

                if officer_id not in officers_dict:
                    officers_dict[officer_id] = {
                        'id': officer_id,
                        'name': record['name'],
                        'name_en': record['name_en'],
                        'resident_number_hash': record['resident_number_hash'],
                        'position': record['position'],
                        'career_history': record['career_history'],
                        'influence_score': record['influence_score'],
                        'board_count': record['board_count'],
                        'current_company_id': record['current_company_id']
                    }

                # 각 임기를 별도로 저장
                if record['current_company_id']:
                    officer_positions.append({
                        'officer_id': officer_id,
                        'company_id': record['current_company_id'],
                        'position': record['relationship_position'] or record['position'],
                        'term_start_date': record['term_start'],
                        'term_end_date': record['term_end'],
                        'is_current': record['is_current'] if record['is_current'] is not None else True,
                        'source_disclosure_id': record['source_disclosure_id'],
                        'source_report_date': record['source_report_date']
                    })

            officers = list(officers_dict.values())
            print(f"  ✓ {len(officers)}명 임원, {len(officer_positions)}개 임기 발견")
            return officers, officer_positions

    def get_neo4j_convertible_bonds(self) -> List[Dict[str, Any]]:
        """Neo4j에서 전환사채 데이터 조회"""
        print("\n[3/5] Convertible Bonds 조회 중...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
                RETURN cb.id as id,
                       c.id as company_id,
                       cb.bond_name as bond_name,
                       cb.issue_date as issue_date,
                       cb.maturity_date as maturity_date,
                       cb.issue_amount as issue_amount,
                       cb.conversion_price as conversion_price,
                       cb.conversion_ratio as conversion_ratio,
                       cb.interest_rate as interest_rate,
                       cb.underwriter as underwriter,
                       cb.status as status
                ORDER BY cb.issue_date DESC
            """)

            bonds = [dict(record) for record in result]
            print(f"  ✓ {len(bonds)}개 전환사채 발견")
            return bonds

    def get_neo4j_cb_subscribers(self) -> List[Dict[str, Any]]:
        """Neo4j에서 CB 인수자 데이터 조회"""
        print("\n[4/5] CB Subscribers 조회 중...")

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (cb:ConvertibleBond)<-[:SUBSCRIBED_TO]-(sub:CBSubscriber)
                OPTIONAL MATCH (sub)-[:IS_OFFICER]->(o:Officer)
                OPTIONAL MATCH (sub)-[:IS_COMPANY]->(c:Company)
                RETURN sub.id as id,
                       cb.id as cb_id,
                       sub.subscriber_name as subscriber_name,
                       sub.subscriber_type as subscriber_type,
                       sub.subscription_amount as subscription_amount,
                       sub.is_related_party as is_related_party,
                       sub.relationship_to_company as relationship_to_company,
                       sub.source_disclosure_id as source_disclosure_id,
                       sub.source_date as source_date,
                       o.id as officer_id,
                       c.id as company_id
                ORDER BY sub.subscriber_name
            """)

            subscribers = [dict(record) for record in result]
            print(f"  ✓ {len(subscribers)}명 인수자 발견")
            return subscribers

    async def sync_companies(self, companies: List[Dict[str, Any]]):
        """Companies 동기화 (UPSERT)"""
        print("\n[동기화 1/4] Companies → PostgreSQL")

        inserted = 0
        updated = 0

        for company in companies:
            result = await self.pg_conn.execute("""
                INSERT INTO companies (
                    id, name, corp_code, business_number, ticker,
                    sector, industry, market, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    corp_code = EXCLUDED.corp_code,
                    business_number = EXCLUDED.business_number,
                    ticker = EXCLUDED.ticker,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    market = EXCLUDED.market,
                    updated_at = NOW()
                RETURNING (xmax = 0) as inserted
            """,
                company.get('id') or str(uuid.uuid4()),
                company.get('name'),
                company.get('corp_code'),
                company.get('business_number'),
                company.get('ticker'),
                company.get('sector'),
                company.get('industry'),
                company.get('market')
            )

            if result == 'INSERT 0 1':
                inserted += 1
            else:
                updated += 1

        print(f"  ✓ Companies: {inserted} 신규, {updated} 업데이트")

    async def sync_officers(self, officers: List[Dict[str, Any]]):
        """Officers 동기화 (UPSERT)"""
        print("\n[동기화 2/4] Officers → PostgreSQL")

        inserted = 0
        updated = 0

        for officer in officers:
            await self.pg_conn.execute("""
                INSERT INTO officers (
                    id, name, name_en, resident_number_hash, position,
                    current_company_id, career_history, influence_score,
                    board_count, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    name_en = EXCLUDED.name_en,
                    position = EXCLUDED.position,
                    current_company_id = EXCLUDED.current_company_id,
                    career_history = EXCLUDED.career_history,
                    influence_score = EXCLUDED.influence_score,
                    board_count = EXCLUDED.board_count,
                    updated_at = NOW()
            """,
                officer.get('id') or str(uuid.uuid4()),
                officer.get('name'),
                officer.get('name_en'),
                officer.get('resident_number_hash'),
                officer.get('position'),
                officer.get('current_company_id'),
                officer.get('career_history'),
                officer.get('influence_score', 0.0),
                officer.get('board_count', 0)
            )
            inserted += 1

        print(f"  ✓ Officers: {inserted} 동기화 완료")

    async def sync_officer_positions(self, positions: List[Dict[str, Any]]):
        """Officer Positions 동기화 (UPSERT - Temporal 데이터)"""
        print("\n[동기화 2.5/4] Officer Positions → PostgreSQL (Temporal)")

        inserted = 0
        updated = 0

        for pos in positions:
            # Parse date strings if needed
            term_start = pos.get('term_start_date')
            term_end = pos.get('term_end_date')
            source_report_date = pos.get('source_report_date')

            if isinstance(term_start, str):
                try:
                    term_start = datetime.strptime(term_start, '%Y-%m-%d').date()
                except:
                    term_start = None

            if isinstance(term_end, str):
                try:
                    term_end = datetime.strptime(term_end, '%Y-%m-%d').date()
                except:
                    term_end = None

            if isinstance(source_report_date, str):
                try:
                    source_report_date = datetime.strptime(source_report_date, '%Y-%m-%d').date()
                except:
                    source_report_date = None

            await self.pg_conn.execute("""
                INSERT INTO officer_positions (
                    id, officer_id, company_id, position,
                    term_start_date, term_end_date, is_current,
                    source_disclosure_id, source_report_date,
                    created_at, updated_at
                )
                VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                ON CONFLICT (officer_id, company_id, term_start_date, source_disclosure_id)
                DO UPDATE SET
                    position = EXCLUDED.position,
                    term_end_date = EXCLUDED.term_end_date,
                    is_current = EXCLUDED.is_current,
                    updated_at = NOW()
            """,
                pos['officer_id'],
                pos['company_id'],
                pos['position'],
                term_start,
                term_end,
                pos.get('is_current', True),
                pos.get('source_disclosure_id'),
                source_report_date
            )
            inserted += 1

        print(f"  ✓ Officer Positions: {inserted} 임기 동기화 완료")

    async def sync_convertible_bonds(self, bonds: List[Dict[str, Any]]):
        """Convertible Bonds 동기화 (UPSERT)"""
        print("\n[동기화 3/4] Convertible Bonds → PostgreSQL")

        inserted = 0

        for bond in bonds:
            # Parse dates
            issue_date = bond.get('issue_date')
            maturity_date = bond.get('maturity_date')

            if isinstance(issue_date, str):
                try:
                    issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
                except:
                    issue_date = None

            if isinstance(maturity_date, str):
                try:
                    maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                except:
                    maturity_date = None

            await self.pg_conn.execute("""
                INSERT INTO convertible_bonds (
                    id, company_id, bond_name, issue_date, maturity_date,
                    issue_amount, conversion_price, conversion_ratio,
                    interest_rate, status, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    bond_name = EXCLUDED.bond_name,
                    issue_date = EXCLUDED.issue_date,
                    maturity_date = EXCLUDED.maturity_date,
                    issue_amount = EXCLUDED.issue_amount,
                    conversion_price = EXCLUDED.conversion_price,
                    conversion_ratio = EXCLUDED.conversion_ratio,
                    interest_rate = EXCLUDED.interest_rate,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """,
                bond.get('id') or str(uuid.uuid4()),
                bond['company_id'],
                bond.get('bond_name'),
                issue_date,
                maturity_date,
                bond.get('issue_amount'),
                bond.get('conversion_price'),
                bond.get('conversion_ratio'),
                bond.get('interest_rate'),
                bond.get('status')
            )
            inserted += 1

        print(f"  ✓ Convertible Bonds: {inserted} 동기화 완료")

    async def sync_cb_subscribers(self, subscribers: List[Dict[str, Any]]):
        """CB Subscribers 동기화 (UPSERT, temporal 링크 포함)"""
        print("\n[동기화 4/4] CB Subscribers → PostgreSQL")

        inserted = 0

        for sub in subscribers:
            # Parse source_date
            source_report_date = None
            source_date = sub.get('source_date')
            if source_date:
                try:
                    # source_date가 YYYYMMDD 형식인 경우
                    if len(str(source_date)) == 8:
                        source_report_date = datetime.strptime(str(source_date), '%Y%m%d').date()
                    else:
                        source_report_date = datetime.strptime(source_date, '%Y-%m-%d').date()
                except:
                    source_report_date = None

            await self.pg_conn.execute("""
                INSERT INTO cb_subscribers (
                    id, cb_id, subscriber_name, subscriber_type,
                    subscription_amount, is_related_party, relationship_to_company,
                    source_disclosure_id, source_date,
                    subscriber_officer_id, subscriber_company_id, source_report_date,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    subscriber_name = EXCLUDED.subscriber_name,
                    subscriber_type = EXCLUDED.subscriber_type,
                    subscription_amount = EXCLUDED.subscription_amount,
                    is_related_party = EXCLUDED.is_related_party,
                    relationship_to_company = EXCLUDED.relationship_to_company,
                    subscriber_officer_id = EXCLUDED.subscriber_officer_id,
                    subscriber_company_id = EXCLUDED.subscriber_company_id,
                    source_report_date = EXCLUDED.source_report_date,
                    updated_at = NOW()
            """,
                sub.get('id') or str(uuid.uuid4()),
                sub['cb_id'],
                sub.get('subscriber_name'),
                sub.get('subscriber_type'),
                sub.get('subscription_amount'),
                sub.get('is_related_party'),
                sub.get('relationship_to_company'),
                sub.get('source_disclosure_id'),
                sub.get('source_date'),
                sub.get('officer_id'),  # Link to officer if exists
                sub.get('company_id'),  # Link to company if exists
                source_report_date
            )
            inserted += 1

        print(f"  ✓ CB Subscribers: {inserted} 동기화 완료")

    async def run(self):
        """전체 동기화 실행"""
        print("="*80)
        print("Temporal Data Sync: Neo4j → PostgreSQL")
        print("="*80)

        try:
            # PostgreSQL 연결
            await self.connect_postgres()

            # 1. Companies
            companies = self.get_neo4j_companies()
            await self.sync_companies(companies)

            # 2. Officers + Officer Positions (Temporal)
            officers, officer_positions = self.get_neo4j_officers()
            await self.sync_officers(officers)
            await self.sync_officer_positions(officer_positions)

            # 3. Convertible Bonds
            bonds = self.get_neo4j_convertible_bonds()
            await self.sync_convertible_bonds(bonds)

            # 4. CB Subscribers (with temporal links)
            subscribers = self.get_neo4j_cb_subscribers()
            await self.sync_cb_subscribers(subscribers)

            print("\n" + "="*80)
            print("✓ 전체 동기화 완료!")
            print("="*80)

        except Exception as e:
            print(f"\n✗ 동기화 실패: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_connections()


if __name__ == "__main__":
    sync = TemporalDataSync()
    asyncio.run(sync.run())
