# 기업 데이터 관리 문서

> **마지막 업데이트**: 2026-01-21
> **문서 목적**: 데이터 수집/파싱 파이프라인 실행 전 반드시 참조

---

## 1. 관리 대상 기업 현황 (2026-01-21 기준)

### 1.1 전체 현황

| 구분 | 기업 수 | 설명 |
|------|--------|------|
| **LISTED (상장)** | 3,021 | 서비스 대상 기업 |
| **ETF** | 88 | 상장지수펀드 (제한적 관리) |
| **총계** | 3,109 | 현재 DB 보유 기업 |

### 1.2 시장별 분포 (LISTED 기업)

| 시장 | 기업 수 |
|------|--------|
| KOSPI | ~1,900 |
| KOSDAQ | ~1,100 |
| KONEX | 소수 |

### 1.3 기업 유형별 분포

| company_type | 설명 | 데이터 수집 | 비고 |
|--------------|------|------------|------|
| NORMAL | 일반 상장사 | ✅ 전체 | 임원, 재무, CB 등 |
| SPAC | 기업인수목적회사 | ⚠️ 제한적 | 임원/재무 구조 상이 |
| REIT | 부동산투자회사 | ⚠️ 제한적 | 임원/재무 구조 상이 |
| ETF | 상장지수펀드 | ❌ 제외 | 수집 대상 아님 |

---

## 2. 삭제된 기업 이력 (2026-01-21)

### 2.1 삭제 요약

| 구분 | 삭제 수 | 사유 |
|------|--------|------|
| 유령 기업 | 39 | LISTED이나 사업보고서 0건 |
| 상장폐지 기업 | 774 | DELISTED + 사업보고서 0건 |
| **총 삭제** | **813** | |

### 2.2 유령 기업 (39개) - 삭제됨

**정의**: `listing_status = 'LISTED'` AND `company_type = 'NORMAL'` 이면서:
- 임원 정보 0건
- 재무제표 0건
- 공시 5건 이하
- 사업보고서 0건

**삭제 스크립트**: `backend/scripts/maintenance/delete_ghost_companies.py`

### 2.3 상장폐지 기업 (774개) - 삭제됨

**정의**: `listing_status = 'DELISTED'` AND 사업보고서 0건

**시장 분포**:
- KOSPI: 763개
- KOSDAQ: 11개

**공통 특징**:
- 임원 정보: 0건
- 재무제표: 0건
- 공시: 0건
- 사업보고서: 0건

**삭제 스크립트**: `backend/scripts/maintenance/delete_delisted_companies.py`

### 2.4 함께 삭제된 연관 데이터

| 테이블 | 삭제 건수 | 비고 |
|--------|----------|------|
| risk_scores | 774 | |
| stock_prices | 818 | |
| affiliates | 109 | |
| company_view_history | 1 | |
| cb_subscribers | 0 | |
| convertible_bonds | 0 | |
| risk_signals | 0 | |
| disclosures | 0 | |
| largest_shareholder_info | 0 | |
| officer_positions | 0 | |
| financial_statements | 0 | |
| financial_details | 0 | |
| raymonds_index | 0 | |
| major_shareholders | 0 | |

---

## 3. 데이터 파이프라인 실행 규칙

### 3.1 수집/파싱 대상 기업 조건

```sql
-- 데이터 수집 대상 기업 쿼리
SELECT id, ticker, name, market
FROM companies
WHERE listing_status = 'LISTED'
  AND company_type IN ('NORMAL', 'SPAC', 'REIT')
  -- ETF 제외
  AND company_type != 'ETF'
```

### 3.2 company_filter 유틸리티 사용 (권장)

```python
from scripts.utils.company_filter import (
    should_parse_officers,      # SPAC, REIT, ETF 제외
    should_parse_shareholders,  # ETF만 제외
    should_parse_financials,    # ETF만 제외
    should_calculate_index,     # SPAC, REIT, ETF 제외
)

# 사용 예시
for company in companies:
    if should_parse_officers(company):
        parse_officers(company)
```

### 3.3 파이프라인별 적용 필터

| 파이프라인 | 필터 조건 | 유틸리티 함수 |
|-----------|----------|--------------|
| 임원 파싱 | LISTED + NORMAL만 | `should_parse_officers()` |
| 재무 파싱 | LISTED + (NORMAL, SPAC, REIT) | `should_parse_financials()` |
| 대주주 파싱 | LISTED + (NORMAL, SPAC, REIT) | `should_parse_shareholders()` |
| RaymondsIndex | LISTED + NORMAL만 | `should_calculate_index()` |
| CB 파싱 | LISTED + (NORMAL, SPAC) | 별도 필터 |

---

## 4. 신규 기업 추가/제외 절차

### 4.1 신규 상장 기업 추가

1. DART에서 신규 상장 기업 목록 확인
2. `companies` 테이블에 INSERT (listing_status='LISTED')
3. 분기별 파이프라인 자동 수집

### 4.2 상장폐지 기업 처리

**즉시 삭제하지 않음** - 다음 분기 정리 시점에 일괄 처리

1. `listing_status = 'DELISTED'`로 UPDATE
2. 분기별 정리 스크립트로 검토 후 삭제
3. 삭제 시 이 문서에 이력 기록

### 4.3 관리종목 지정 기업

1. `is_managed = 'Y'`로 UPDATE
2. 데이터 수집은 계속 (삭제하지 않음)
3. 프론트엔드에서 경고 표시

---

## 5. 데이터 품질 기준

### 5.1 정상 기업 기준

- 사업보고서 ≥ 1건 (최근 5년)
- 임원 정보 ≥ 1건
- 재무제표 ≥ 1건

### 5.2 유령 기업 판별 기준

다음 조건 모두 충족 시 "유령 기업"으로 분류:
- listing_status = 'LISTED'
- company_type = 'NORMAL'
- 임원 정보 0건
- 재무제표 0건
- 공시 ≤ 5건
- 사업보고서 0건

### 5.3 분기별 데이터 품질 검증

```bash
# 유령 기업 확인 쿼리
SELECT c.id, c.name, c.ticker, c.market
FROM companies c
WHERE c.listing_status = 'LISTED'
  AND c.company_type = 'NORMAL'
  AND c.id NOT IN (SELECT DISTINCT company_id FROM officer_positions WHERE company_id IS NOT NULL)
  AND c.id NOT IN (SELECT DISTINCT company_id FROM financial_statements WHERE company_id IS NOT NULL)
  AND (SELECT COUNT(*) FROM disclosures d WHERE d.stock_code = c.ticker) <= 5
  AND NOT EXISTS (
      SELECT 1 FROM disclosures d
      WHERE d.stock_code = c.ticker AND d.report_nm LIKE '%사업보고서%'
  )
ORDER BY c.ticker;
```

---

## 6. 관련 스크립트 목록

| 스크립트 | 용도 | 실행 주기 |
|---------|------|----------|
| `maintenance/delete_ghost_companies.py` | 유령 기업 삭제 | 분기별 |
| `maintenance/delete_delisted_companies.py` | 상장폐지 기업 삭제 | 분기별 |
| `maintenance/fix_etf_misclassification.py` | ETF 오분류 정상화 | 필요시 |
| `maintenance/fix_delisted_market.py` | DELISTED 시장 정상화 | 필요시 |
| `utils/company_filter.py` | 기업 필터 유틸리티 | 상시 |

---

## 7. 변경 이력

| 날짜 | 작업 | 삭제/변경 수 | 담당 |
|------|------|-------------|------|
| 2026-01-21 | 유령 기업 삭제 | 39개 삭제 | Claude |
| 2026-01-21 | 상장폐지 기업 삭제 | 774개 삭제 | Claude |
| 2026-01-21 | 최초 문서 작성 | - | Claude |
