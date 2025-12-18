-- Raymontology Database Schema
-- Direct SQL initialization

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Drop existing tables
DROP TABLE IF EXISTS financial_statements CASCADE;
DROP TABLE IF EXISTS cb_subscribers CASCADE;
DROP TABLE IF EXISTS convertible_bonds CASCADE;
DROP TABLE IF EXISTS affiliates CASCADE;
DROP TABLE IF EXISTS risk_signals CASCADE;
DROP TABLE IF EXISTS ontology_links CASCADE;
DROP TABLE IF EXISTS ontology_objects CASCADE;
DROP TABLE IF EXISTS officers CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS disclosure_documents CASCADE;

-- Companies table
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
);

CREATE INDEX idx_company_ticker ON companies(ticker);
CREATE INDEX idx_company_name ON companies(name);
CREATE INDEX idx_company_corp_code ON companies(corp_code);
CREATE INDEX idx_company_name_trigram ON companies USING gin(name gin_trgm_ops);

-- Officers table
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
);

CREATE INDEX idx_officer_name ON officers(name);
CREATE INDEX idx_officer_current_company ON officers(current_company_id);

-- Convertible Bonds table
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
);

CREATE INDEX idx_cb_company ON convertible_bonds(company_id);
CREATE INDEX idx_cb_issue_date ON convertible_bonds(issue_date);

-- CB Subscribers table
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
);

CREATE INDEX idx_cb_subscriber_cb ON cb_subscribers(cb_id);
CREATE INDEX idx_cb_subscriber_name ON cb_subscribers(subscriber_name);

-- Affiliates table
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
);

CREATE INDEX idx_affiliate_parent ON affiliates(parent_company_id);
CREATE INDEX idx_affiliate_child ON affiliates(affiliate_company_id);

-- Financial Statements table
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
);

CREATE INDEX idx_financial_company ON financial_statements(company_id);
CREATE INDEX idx_financial_year ON financial_statements(fiscal_year);

-- Risk Signals table
CREATE TABLE risk_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(200),
    risk_score INTEGER NOT NULL,
    severity VARCHAR(20),
    details JSONB DEFAULT '{}',
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_company ON risk_signals(company_id);
CREATE INDEX idx_risk_pattern ON risk_signals(pattern_type);
CREATE INDEX idx_risk_detected ON risk_signals(detected_at);

-- Users table
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
);

CREATE INDEX idx_user_email ON users(email);

-- Disclosure Documents table
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
);

CREATE INDEX idx_disclosure_corp_code ON disclosure_documents(corp_code);
CREATE INDEX idx_disclosure_rcept_no ON disclosure_documents(rcept_no);
CREATE INDEX idx_disclosure_rcept_dt ON disclosure_documents(rcept_dt);

-- Ontology Objects table
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
);

-- Ontology Links table
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
);

CREATE INDEX idx_ontology_link_source ON ontology_links(source_object_id);
CREATE INDEX idx_ontology_link_target ON ontology_links(target_object_id);

-- Alembic version table
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('16ab7b40051b')
ON CONFLICT (version_num) DO NOTHING;
