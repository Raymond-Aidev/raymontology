#!/usr/bin/env python3
"""
Direct Database Initialization Script
Bypasses Alembic for quick setup
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os

# Database connection parameters
DB_HOST = "127.0.0.1"  # Use IPv4 explicitly
DB_PORT = 5432
DB_NAME = "raymontology_dev"
DB_USER = "postgres"
DB_PASSWORD = "dev_password"

def get_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def execute_sql(cursor, sql, description):
    """Execute SQL with error handling"""
    try:
        cursor.execute(sql)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def main():
    print("=" * 70)
    print("🚀 Initializing PostgreSQL Database Schema")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor()

    # Enable extensions
    execute_sql(cursor, 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"', "Enable UUID extension")
    execute_sql(cursor, 'CREATE EXTENSION IF NOT EXISTS "pg_trgm"', "Enable trigram search extension")

    # Drop existing tables (cascade)
    print("\n📋 Dropping existing tables...")
    execute_sql(cursor, "DROP TABLE IF EXISTS financial_statements CASCADE", "Drop financial_statements")
    execute_sql(cursor, "DROP TABLE IF EXISTS cb_subscribers CASCADE", "Drop cb_subscribers")
    execute_sql(cursor, "DROP TABLE IF EXISTS convertible_bonds CASCADE", "Drop convertible_bonds")
    execute_sql(cursor, "DROP TABLE IF EXISTS affiliates CASCADE", "Drop affiliates")
    execute_sql(cursor, "DROP TABLE IF EXISTS risk_signals CASCADE", "Drop risk_signals")
    execute_sql(cursor, "DROP TABLE IF EXISTS ontology_links CASCADE", "Drop ontology_links")
    execute_sql(cursor, "DROP TABLE IF EXISTS ontology_objects CASCADE", "Drop ontology_objects")
    execute_sql(cursor, "DROP TABLE IF EXISTS officers CASCADE", "Drop officers")
    execute_sql(cursor, "DROP TABLE IF EXISTS companies CASCADE", "Drop companies")
    execute_sql(cursor, "DROP TABLE IF EXISTS users CASCADE", "Drop users")
    execute_sql(cursor, "DROP TABLE IF EXISTS disclosure_documents CASCADE", "Drop disclosure_documents")

    # Create companies table
    print("\n📋 Creating tables...")
    execute_sql(cursor, """
        CREATE TABLE companies (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            ticker VARCHAR(20) UNIQUE,
            name VARCHAR(200) NOT NULL,
            name_en VARCHAR(200),
            business_number VARCHAR(20) UNIQUE,
            corp_code VARCHAR(8),
            sector VARCHAR(100),
            industry VARCHAR(100),
            market VARCHAR(20),
            market_cap FLOAT,
            revenue FLOAT,
            net_income FLOAT,
            total_assets FLOAT,
            ownership_concentration FLOAT,
            affiliate_transaction_ratio FLOAT,
            cb_issuance_count INTEGER DEFAULT 0,
            risk_score FLOAT DEFAULT 0.0,
            risk_grade VARCHAR(20),
            risk_updated_at TIMESTAMP,
            ontology_object_id VARCHAR(50) UNIQUE,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create companies table")

    execute_sql(cursor, "CREATE INDEX idx_company_ticker ON companies(ticker)", "Index: company ticker")
    execute_sql(cursor, "CREATE INDEX idx_company_name ON companies(name)", "Index: company name")
    execute_sql(cursor, "CREATE INDEX idx_company_corp_code ON companies(corp_code)", "Index: company corp_code")
    execute_sql(cursor, "CREATE INDEX idx_company_name_trigram ON companies USING gin(name gin_trgm_ops)", "Index: company name trigram")

    # Create officers table
    execute_sql(cursor, """
        CREATE TABLE officers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(100) NOT NULL,
            name_en VARCHAR(100),
            resident_number_hash VARCHAR(64) UNIQUE,
            position VARCHAR(100),
            current_company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            career_history JSONB DEFAULT '[]',
            education TEXT[],
            board_count INTEGER DEFAULT 0,
            network_centrality FLOAT,
            influence_score FLOAT DEFAULT 0.0,
            has_conflict_of_interest BOOLEAN DEFAULT FALSE,
            insider_trading_count INTEGER DEFAULT 0,
            ontology_object_id VARCHAR(50) UNIQUE,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create officers table")

    execute_sql(cursor, "CREATE INDEX idx_officer_name ON officers(name)", "Index: officer name")
    execute_sql(cursor, "CREATE INDEX idx_officer_current_company ON officers(current_company_id)", "Index: officer company")

    # Create convertible_bonds table
    execute_sql(cursor, """
        CREATE TABLE convertible_bonds (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            bond_name VARCHAR(200) NOT NULL,
            issue_date DATE,
            maturity_date DATE,
            issue_amount BIGINT,
            conversion_price BIGINT,
            interest_rate FLOAT,
            conversion_ratio FLOAT,
            underwriter VARCHAR(200),
            use_of_proceeds TEXT,
            status VARCHAR(50),
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create convertible_bonds table")

    execute_sql(cursor, "CREATE INDEX idx_cb_company ON convertible_bonds(company_id)", "Index: CB company")
    execute_sql(cursor, "CREATE INDEX idx_cb_issue_date ON convertible_bonds(issue_date)", "Index: CB issue date")

    # Create cb_subscribers table
    execute_sql(cursor, """
        CREATE TABLE cb_subscribers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            cb_id UUID NOT NULL REFERENCES convertible_bonds(id) ON DELETE CASCADE,
            subscriber_name VARCHAR(200) NOT NULL,
            subscriber_type VARCHAR(50),
            subscription_amount BIGINT,
            subscription_ratio FLOAT,
            subscription_date DATE,
            is_related_party BOOLEAN DEFAULT FALSE,
            relationship VARCHAR(200),
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create cb_subscribers table")

    execute_sql(cursor, "CREATE INDEX idx_cb_subscriber_cb ON cb_subscribers(cb_id)", "Index: subscriber CB")
    execute_sql(cursor, "CREATE INDEX idx_cb_subscriber_name ON cb_subscribers(subscriber_name)", "Index: subscriber name")

    # Create affiliates table
    execute_sql(cursor, """
        CREATE TABLE affiliates (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            parent_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            affiliate_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50),
            ownership_percentage FLOAT,
            effective_from DATE,
            effective_until DATE,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(parent_company_id, affiliate_company_id)
        )
    """, "Create affiliates table")

    execute_sql(cursor, "CREATE INDEX idx_affiliate_parent ON affiliates(parent_company_id)", "Index: affiliate parent")
    execute_sql(cursor, "CREATE INDEX idx_affiliate_child ON affiliates(affiliate_company_id)", "Index: affiliate child")

    # Create financial_statements table
    execute_sql(cursor, """
        CREATE TABLE financial_statements (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            fiscal_year INTEGER NOT NULL,
            quarter VARCHAR(2),
            statement_date DATE NOT NULL,
            cash_and_equivalents BIGINT,
            accounts_receivable BIGINT,
            inventory BIGINT,
            current_assets BIGINT,
            total_assets BIGINT,
            current_liabilities BIGINT,
            total_liabilities BIGINT,
            total_equity BIGINT,
            revenue BIGINT,
            cost_of_sales BIGINT,
            operating_income BIGINT,
            net_income BIGINT,
            accounts_payable BIGINT,
            data_source VARCHAR(50),
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(company_id, fiscal_year, quarter)
        )
    """, "Create financial_statements table")

    execute_sql(cursor, "CREATE INDEX idx_financial_company ON financial_statements(company_id)", "Index: financial company")
    execute_sql(cursor, "CREATE INDEX idx_financial_year ON financial_statements(fiscal_year)", "Index: financial year")

    # Create risk_signals table
    execute_sql(cursor, """
        CREATE TABLE risk_signals (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            pattern_type VARCHAR(50) NOT NULL,
            pattern_name VARCHAR(200),
            risk_score INTEGER NOT NULL,
            severity VARCHAR(20),
            details JSONB DEFAULT '{}',
            detected_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create risk_signals table")

    execute_sql(cursor, "CREATE INDEX idx_risk_company ON risk_signals(company_id)", "Index: risk company")
    execute_sql(cursor, "CREATE INDEX idx_risk_pattern ON risk_signals(pattern_type)", "Index: risk pattern")
    execute_sql(cursor, "CREATE INDEX idx_risk_detected ON risk_signals(detected_at)", "Index: risk detected date")

    # Create users table (for authentication)
    execute_sql(cursor, """
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            subscription_plan VARCHAR(20) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create users table")

    execute_sql(cursor, "CREATE INDEX idx_user_email ON users(email)", "Index: user email")

    # Create disclosure_documents table
    execute_sql(cursor, """
        CREATE TABLE disclosure_documents (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            corp_code VARCHAR(8) NOT NULL,
            rcept_no VARCHAR(20) UNIQUE NOT NULL,
            report_nm VARCHAR(200) NOT NULL,
            rcept_dt VARCHAR(8),
            flr_nm VARCHAR(200),
            rm TEXT,
            xml_url TEXT,
            pdf_url TEXT,
            html_url TEXT,
            local_xml_path TEXT,
            local_pdf_path TEXT,
            parsed BOOLEAN DEFAULT FALSE,
            parsed_at TIMESTAMP,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create disclosure_documents table")

    execute_sql(cursor, "CREATE INDEX idx_disclosure_corp_code ON disclosure_documents(corp_code)", "Index: disclosure corp_code")
    execute_sql(cursor, "CREATE INDEX idx_disclosure_rcept_no ON disclosure_documents(rcept_no)", "Index: disclosure rcept_no")
    execute_sql(cursor, "CREATE INDEX idx_disclosure_rcept_dt ON disclosure_documents(rcept_dt)", "Index: disclosure date")

    # Create ontology_objects and ontology_links tables
    execute_sql(cursor, """
        CREATE TABLE ontology_objects (
            object_id VARCHAR(50) PRIMARY KEY,
            object_type VARCHAR(50) NOT NULL,
            valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
            valid_until TIMESTAMP,
            version INTEGER NOT NULL DEFAULT 1,
            source_documents TEXT[],
            confidence FLOAT NOT NULL DEFAULT 1.0,
            properties JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create ontology_objects table")

    execute_sql(cursor, """
        CREATE TABLE ontology_links (
            link_id VARCHAR(50) PRIMARY KEY,
            link_type VARCHAR(50) NOT NULL,
            source_object_id VARCHAR(50) NOT NULL REFERENCES ontology_objects(object_id) ON DELETE CASCADE,
            target_object_id VARCHAR(50) NOT NULL REFERENCES ontology_objects(object_id) ON DELETE CASCADE,
            valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
            valid_until TIMESTAMP,
            version INTEGER NOT NULL DEFAULT 1,
            source_documents TEXT[],
            confidence FLOAT NOT NULL DEFAULT 1.0,
            properties JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, "Create ontology_links table")

    execute_sql(cursor, "CREATE INDEX idx_ontology_link_source ON ontology_links(source_object_id)", "Index: link source")
    execute_sql(cursor, "CREATE INDEX idx_ontology_link_target ON ontology_links(target_object_id)", "Index: link target")

    # Create alembic_version table
    execute_sql(cursor, """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    """, "Create alembic_version table")

    execute_sql(cursor, """
        INSERT INTO alembic_version (version_num) VALUES ('16ab7b40051b')
        ON CONFLICT (version_num) DO NOTHING
    """, "Set alembic version")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✅ Database initialization completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
