#!/usr/bin/env python3
"""
Complete Neo4j to PostgreSQL Data Sync
Syncs Officers, ConvertibleBonds, and Subscribers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from neo4j import GraphDatabase
import subprocess
import uuid
from datetime import datetime

# Neo4j Configuration
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# PostgreSQL via Docker
DOCKER_CONTAINER = "raymontology-postgres"
PG_USER = "postgres"
PG_DB = "raymontology_dev"

class DataSyncManager:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.company_mapping = {}  # Neo4j ID -> PostgreSQL UUID mapping

    def exec_sql(self, sql):
        """Execute SQL via docker exec"""
        try:
            result = subprocess.run(
                ['docker', 'exec', DOCKER_CONTAINER, 'psql', '-U', PG_USER, '-d', PG_DB, '-c', sql],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)

    def load_company_mapping(self):
        """Load Company ID mapping: Neo4j ID -> PostgreSQL UUID"""
        print("📋 Loading company ID mappings...")
        success, stdout, stderr = self.exec_sql(
            "SELECT id::text FROM companies"
        )

        if success:
            # Get Neo4j company IDs that match PostgreSQL UUIDs
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (c:Company)
                    WHERE c.id IS NOT NULL
                    RETURN c.id as neo4j_id
                """)

                for record in result:
                    neo4j_id = record['neo4j_id']
                    # Assume Neo4j IDs are already UUIDs matching PostgreSQL
                    self.company_mapping[neo4j_id] = neo4j_id

            print(f"✓ Loaded {len(self.company_mapping)} company mappings")
        else:
            print(f"⚠️  Failed to load company mappings: {stderr}")

    def sync_officers(self):
        """Sync Officers from Neo4j to PostgreSQL"""
        print("\n" + "="*70)
        print("👔 Syncing Officers")
        print("="*70)

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Officer)
                OPTIONAL MATCH (o)-[:WORKS_AT]->(c:Company)
                RETURN o.id as id,
                       o.name as name,
                       o.name_en as name_en,
                       o.position as position,
                       c.id as company_id,
                       o.properties as properties
                LIMIT 10000
            """)

            officers = []
            for record in result:
                officers.append(dict(record))

            print(f"📊 Found {len(officers)} officers in Neo4j")

            inserted = 0
            skipped = 0

            for i, officer in enumerate(officers, 1):
                if i % 1000 == 0:
                    print(f"  Progress: {i}/{len(officers)} ({inserted} inserted, {skipped} skipped)")

                officer_id = officer.get('id') or str(uuid.uuid4())
                name = (officer.get('name') or 'Unknown').replace("'", "''")
                name_en = officer.get('name_en')
                if name_en:
                    name_en_escaped = name_en.replace("'", "''")
                    name_en_sql = f"'{name_en_escaped}'"
                else:
                    name_en_sql = 'NULL'
                position = (officer.get('position') or '').replace("'", "''")
                company_id = officer.get('company_id')

                # Map company ID
                if company_id and company_id in self.company_mapping:
                    company_uuid = self.company_mapping[company_id]
                    company_sql = f"'{company_uuid}'"
                else:
                    company_sql = 'NULL'

                sql = f"""
                INSERT INTO officers (id, name, name_en, position, current_company_id, created_at, updated_at)
                VALUES (
                    '{officer_id}',
                    '{name}',
                    {name_en_sql},
                    '{position}',
                    {company_sql},
                    NOW(),
                    NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    position = EXCLUDED.position,
                    updated_at = NOW();
                """

                success, _, _ = self.exec_sql(sql)
                if success:
                    inserted += 1
                else:
                    skipped += 1

            print(f"✅ Officers sync complete: {inserted} inserted, {skipped} skipped")
            return inserted

    def sync_convertible_bonds(self):
        """Sync Convertible Bonds from Neo4j to PostgreSQL"""
        print("\n" + "="*70)
        print("💰 Syncing Convertible Bonds")
        print("="*70)

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
                       cb.interest_rate as interest_rate,
                       cb.properties as properties
                LIMIT 5000
            """)

            bonds = []
            for record in result:
                bonds.append(dict(record))

            print(f"📊 Found {len(bonds)} convertible bonds in Neo4j")

            inserted = 0
            skipped = 0

            for i, bond in enumerate(bonds, 1):
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(bonds)} ({inserted} inserted, {skipped} skipped)")

                bond_id = bond.get('id') or str(uuid.uuid4())
                company_id = bond.get('company_id')

                # Skip if company not found
                if not company_id or company_id not in self.company_mapping:
                    skipped += 1
                    continue

                company_uuid = self.company_mapping[company_id]
                bond_name = (bond.get('bond_name') or 'Unnamed Bond').replace("'", "''")
                issue_date = bond.get('issue_date') or 'NULL'
                maturity_date = bond.get('maturity_date') or 'NULL'
                issue_amount = bond.get('issue_amount') or 0
                conversion_price = bond.get('conversion_price') or 0
                interest_rate = bond.get('interest_rate') or 0.0

                # Format dates
                if issue_date != 'NULL':
                    issue_date = f"'{issue_date}'"
                if maturity_date != 'NULL':
                    maturity_date = f"'{maturity_date}'"

                sql = f"""
                INSERT INTO convertible_bonds (
                    id, company_id, bond_name, issue_date, maturity_date,
                    issue_amount, conversion_price, interest_rate, created_at, updated_at
                )
                VALUES (
                    '{bond_id}',
                    '{company_uuid}',
                    '{bond_name}',
                    {issue_date},
                    {maturity_date},
                    {issue_amount},
                    {conversion_price},
                    {interest_rate},
                    NOW(),
                    NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    bond_name = EXCLUDED.bond_name,
                    updated_at = NOW();
                """

                success, _, _ = self.exec_sql(sql)
                if success:
                    inserted += 1
                else:
                    skipped += 1

            print(f"✅ Convertible Bonds sync complete: {inserted} inserted, {skipped} skipped")
            return inserted

    def sync_subscribers(self):
        """Sync CB Subscribers from Neo4j to PostgreSQL"""
        print("\n" + "="*70)
        print("🏢 Syncing CB Subscribers")
        print("="*70)

        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb:ConvertibleBond)
                RETURN s.id as id,
                       cb.id as cb_id,
                       s.name as subscriber_name,
                       s.subscriber_type as subscriber_type,
                       s.subscription_amount as subscription_amount,
                       s.subscription_ratio as subscription_ratio,
                       s.subscription_date as subscription_date,
                       s.is_related_party as is_related_party,
                       s.relationship as relationship
                LIMIT 5000
            """)

            subscribers = []
            for record in result:
                subscribers.append(dict(record))

            print(f"📊 Found {len(subscribers)} subscribers in Neo4j")

            inserted = 0
            skipped = 0

            # First, get CB ID mapping
            cb_mapping = {}
            success, stdout, _ = self.exec_sql("SELECT id::text FROM convertible_bonds")
            if success:
                cb_ids = [line.strip() for line in stdout.split('\n') if line.strip() and not line.startswith('id') and '---' not in line and 'row' not in line]
                for cb_id in cb_ids:
                    cb_mapping[cb_id] = cb_id

            print(f"  Loaded {len(cb_mapping)} CB mappings")

            for i, subscriber in enumerate(subscribers, 1):
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(subscribers)} ({inserted} inserted, {skipped} skipped)")

                subscriber_id = subscriber.get('id') or str(uuid.uuid4())
                cb_id = subscriber.get('cb_id')

                # Skip if CB not found
                if not cb_id or cb_id not in cb_mapping:
                    skipped += 1
                    continue

                cb_uuid = cb_mapping[cb_id]
                subscriber_name = (subscriber.get('subscriber_name') or 'Unknown').replace("'", "''")
                subscriber_type = (subscriber.get('subscriber_type') or '').replace("'", "''")
                subscription_amount = subscriber.get('subscription_amount') or 0
                subscription_ratio = subscriber.get('subscription_ratio') or 0.0
                subscription_date = subscriber.get('subscription_date')
                is_related_party = subscriber.get('is_related_party') or False
                relationship = (subscriber.get('relationship') or '').replace("'", "''")

                # Format date
                if subscription_date:
                    subscription_date_sql = f"'{subscription_date}'"
                else:
                    subscription_date_sql = 'NULL'

                sql = f"""
                INSERT INTO cb_subscribers (
                    id, cb_id, subscriber_name, subscriber_type,
                    subscription_amount, subscription_ratio, subscription_date,
                    is_related_party, relationship, created_at
                )
                VALUES (
                    '{subscriber_id}',
                    '{cb_uuid}',
                    '{subscriber_name}',
                    '{subscriber_type}',
                    {subscription_amount},
                    {subscription_ratio},
                    {subscription_date_sql},
                    {is_related_party},
                    '{relationship}',
                    NOW()
                )
                ON CONFLICT (id) DO NOTHING;
                """

                success, _, _ = self.exec_sql(sql)
                if success:
                    inserted += 1
                else:
                    skipped += 1

            print(f"✅ Subscribers sync complete: {inserted} inserted, {skipped} skipped")
            return inserted

    def run(self):
        """Run complete data sync"""
        print("="*70)
        print("🔄 Complete Data Synchronization: Neo4j → PostgreSQL")
        print("="*70)

        try:
            # Load company mappings first
            self.load_company_mapping()

            # Sync all data types
            officers_count = self.sync_officers()
            bonds_count = self.sync_convertible_bonds()
            subscribers_count = self.sync_subscribers()

            # Final summary
            print("\n" + "="*70)
            print("✅ Complete Data Sync Summary")
            print("="*70)
            print(f"  Officers:     {officers_count:,}")
            print(f"  CBs:          {bonds_count:,}")
            print(f"  Subscribers:  {subscribers_count:,}")
            print("="*70)

            return True

        except Exception as e:
            print(f"\n❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.neo4j_driver.close()

if __name__ == "__main__":
    manager = DataSyncManager()
    success = manager.run()
    sys.exit(0 if success else 1)
