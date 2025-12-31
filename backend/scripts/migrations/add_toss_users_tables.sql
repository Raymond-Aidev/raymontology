-- RaymondsRisk 앱인토스 유료화 테이블 마이그레이션
-- 실행일: 2025-12-30

-- ============================================================================
-- 1. toss_users: 토스 로그인 사용자
-- ============================================================================
CREATE TABLE IF NOT EXISTS toss_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    toss_user_key VARCHAR(100) UNIQUE NOT NULL,

    -- 사용자 정보
    name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(255),

    -- 이용권
    credits INTEGER NOT NULL DEFAULT 0,

    -- 토큰
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,

    -- 상태
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- 메타데이터
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_toss_users_toss_user_key ON toss_users(toss_user_key);
CREATE INDEX IF NOT EXISTS ix_toss_users_access_token ON toss_users(access_token);

-- ============================================================================
-- 2. credit_transactions: 이용권 거래 내역
-- ============================================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES toss_users(id) ON DELETE CASCADE,

    -- 거래 유형
    transaction_type VARCHAR(20) NOT NULL, -- purchase, use, refund, bonus

    -- 금액
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,

    -- 구매 정보
    product_id VARCHAR(50),
    payment_amount INTEGER,
    payment_method VARCHAR(20),
    receipt_data TEXT,

    -- 사용 정보
    company_id VARCHAR(20),
    company_name VARCHAR(200),

    -- 메타데이터
    description VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_credit_transactions_user_type ON credit_transactions(user_id, transaction_type);
CREATE INDEX IF NOT EXISTS ix_credit_transactions_created ON credit_transactions(created_at);

-- ============================================================================
-- 3. report_views: 리포트 조회 기록 (중복 차감 방지)
-- ============================================================================
CREATE TABLE IF NOT EXISTS report_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES toss_users(id) ON DELETE CASCADE,
    company_id VARCHAR(20) NOT NULL,
    company_name VARCHAR(200),

    first_viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    view_count INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_report_views_user_company ON report_views(user_id, company_id);

-- ============================================================================
-- 4. credit_products: 이용권 상품
-- ============================================================================
CREATE TABLE IF NOT EXISTS credit_products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL,
    price INTEGER NOT NULL,

    badge VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,

    apple_product_id VARCHAR(100),
    google_product_id VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. 기본 상품 데이터 삽입
-- ============================================================================
INSERT INTO credit_products (id, name, credits, price, badge, sort_order)
VALUES
    ('report_1', '리포트 1건', 1, 500, NULL, 1),
    ('report_10', '리포트 10건', 10, 3000, '추천', 2),
    ('report_30', '리포트 30건', 30, 7000, '최저가', 3)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 완료 메시지
-- ============================================================================
SELECT 'Migration completed: toss_users, credit_transactions, report_views, credit_products tables created' AS result;
