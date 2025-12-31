-- 토스 인앱결제(IAP) 컬럼 추가 마이그레이션
-- 실행일: 2025-12-31

-- ============================================================================
-- 1. credit_transactions: order_id 컬럼 추가
-- ============================================================================
ALTER TABLE credit_transactions
ADD COLUMN IF NOT EXISTS order_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS ix_credit_transactions_order_id
ON credit_transactions(order_id);

-- payment_method 컬럼 크기 확장 (toss_iap 지원)
ALTER TABLE credit_transactions
ALTER COLUMN payment_method TYPE VARCHAR(30);

-- ============================================================================
-- 2. credit_products: toss_sku 컬럼 추가
-- ============================================================================
ALTER TABLE credit_products
ADD COLUMN IF NOT EXISTS toss_sku VARCHAR(100);

-- ============================================================================
-- 3. 기존 상품에 toss_sku 업데이트
-- ============================================================================
UPDATE credit_products SET toss_sku = 'report_1' WHERE id = 'report_1';
UPDATE credit_products SET toss_sku = 'report_10' WHERE id = 'report_10';
UPDATE credit_products SET toss_sku = 'report_30' WHERE id = 'report_30';

-- ============================================================================
-- 완료 메시지
-- ============================================================================
SELECT 'Migration completed: order_id, toss_sku columns added' AS result;
