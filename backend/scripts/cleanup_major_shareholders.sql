-- ============================================================================
-- major_shareholders 테이블 데이터 품질 정제 스크립트
-- 작성일: 2025-12-31
-- 목적: 잘못 파싱된 주주 데이터 정제
-- ============================================================================

-- 실행 전 백업 권장:
-- CREATE TABLE major_shareholders_backup_20251231 AS SELECT * FROM major_shareholders;

BEGIN;

-- ============================================================================
-- STEP 1: 정제 전 현황 확인
-- ============================================================================

-- 1.1 전체 레코드 수
SELECT '정제 전 전체 레코드 수' as metric, COUNT(*) as value FROM major_shareholders;

-- 1.2 이슈별 현황
SELECT
  'issue_1_numeric_name' as issue_type,
  COUNT(*) as record_count,
  COUNT(DISTINCT company_id) as company_count
FROM major_shareholders
WHERE shareholder_name ~ '^\d'
UNION ALL
SELECT
  'issue_2_financial_item_name',
  COUNT(*),
  COUNT(DISTINCT company_id)
FROM major_shareholders
WHERE shareholder_name ~ '(선급금|장기대여금|유동성사채|단기차입금|신탁 체결|채권형|금융자산|이자비용|감가상각비|매출원가|판관비|자본금|자본잉여금|이익잉여금|미수금|미지급금|예수금|가수금|선수금|퇴직급여|복리후생비|외화환산|대손상각비|재고자산|유형자산|무형자산)'
UNION ALL
SELECT
  'issue_3_abnormal_share_count',
  COUNT(*),
  COUNT(DISTINCT company_id)
FROM major_shareholders
WHERE share_count > 10000000000;  -- 100억주 초과

-- ============================================================================
-- STEP 2: 문제 데이터 삭제
-- ============================================================================

-- 2.1 주주명이 숫자로 시작하는 레코드 삭제 (주식수/금액 오파싱)
DELETE FROM major_shareholders
WHERE shareholder_name ~ '^\d+[,.]?\d*$';  -- 순수 숫자 또는 숫자,숫자 형태만

-- 2.2 주주명이 재무항목인 레코드 삭제
DELETE FROM major_shareholders
WHERE shareholder_name IN (
  '선급금', '장기대여금', '유동성사채', '단기차입금', '신탁 체결',
  '채권형', '금융자산', '이자비용', '감가상각비', '매출원가',
  '판관비', '자본금', '자본잉여금', '이익잉여금', '미수금',
  '미지급금', '예수금', '가수금', '선수금', '퇴직급여',
  '복리후생비', '외화환산', '대손상각비', '재고자산', '유형자산', '무형자산'
);

-- 2.3 비정상적으로 큰 주식수 (100억주 초과) 레코드 삭제
DELETE FROM major_shareholders
WHERE share_count > 10000000000;

-- ============================================================================
-- STEP 3: 정제 후 현황 확인
-- ============================================================================

SELECT '정제 후 전체 레코드 수' as metric, COUNT(*) as value FROM major_shareholders;

-- 남은 이슈 확인
SELECT
  'remaining_numeric_name' as issue_type,
  COUNT(*) as record_count
FROM major_shareholders
WHERE shareholder_name ~ '^\d'
UNION ALL
SELECT
  'remaining_financial_item_name',
  COUNT(*)
FROM major_shareholders
WHERE shareholder_name ~ '(선급금|장기대여금|유동성사채|단기차입금)';

COMMIT;

-- ============================================================================
-- 롤백이 필요한 경우:
-- ROLLBACK;
-- ============================================================================
