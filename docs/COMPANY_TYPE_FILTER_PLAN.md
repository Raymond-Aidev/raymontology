# SPAC/ETF/리츠 파싱 예외처리 개발 계획

## 작성일: 2026-01-11

---

## 1. 현재 문제

### 1.1 기업 유형별 현황

| 유형 | 기업 수 | 문제점 |
|------|---------|--------|
| 일반 기업 | 2,661 | 분석 대상 |
| ETF | 1,149 | 펀드라 임원/재무 무의미 |
| SPAC | 80 | 합병 전 껍데기 회사 |
| 리츠/인프라 | 42 | 특수 구조 |

### 1.2 비효율 패턴

```
[현재 플로우]
1. SPAC 기업에서 사업보고서 파싱 시도
2. "임원 데이터 없음" 또는 "재무 데이터 불충분"
3. 재시도 로직 실행 (3-5회)
4. 결국 "데이터 없음" 결론
5. 다음 SPAC 기업에서 동일 과정 반복
   → 80개 SPAC × 5회 재시도 = 400회 불필요 호출
```

### 1.3 현재 예외처리 현황

| 스크립트 | SPAC | ETF | 리츠 |
|----------|------|-----|------|
| collect_missing_officers.py | ✅ 이름 필터 | ❌ | ✅ 이름 필터 |
| parse_officers_from_local.py | ❌ | ⚠️ | ❌ |
| parse_major_shareholders.py | ❌ | ❌ | ❌ |
| parse_local_financial_details.py | ❌ | ✅ | ❌ |
| pipeline/calculate_index.py | ❌ | ⚠️ | ❌ |

**문제:** 각 스크립트마다 이름으로 체크 → 일관성 없음

---

## 2. 해결 방안

### Phase 1: DB 스키마 확장

```sql
ALTER TABLE companies
  ADD COLUMN company_type VARCHAR(20) DEFAULT 'NORMAL';

-- 값: NORMAL, SPAC, REIT, ETF, HOLDING, FINANCIAL
CREATE INDEX idx_company_type ON companies(company_type);
```

### Phase 2: 데이터 마이그레이션

```sql
UPDATE companies SET company_type = 'SPAC'
WHERE name LIKE '%스팩%' OR name LIKE '%SPAC%';

UPDATE companies SET company_type = 'REIT'
WHERE name LIKE '%리츠%' OR name LIKE '%인프라%';

UPDATE companies SET company_type = 'ETF'
WHERE market = 'ETF';
```

### Phase 3: 공통 필터 유틸리티

**신규 파일: `backend/scripts/utils/company_filter.py`**

```python
"""기업 유형 필터링 유틸리티"""

EXCLUDED_FROM_OFFICER_PARSING = {'SPAC', 'REIT', 'ETF'}
EXCLUDED_FROM_SHAREHOLDER_PARSING = {'ETF'}
EXCLUDED_FROM_INDEX_CALCULATION = {'SPAC', 'REIT', 'ETF'}

def should_parse_officers(company: dict) -> bool:
    return company.get('company_type', 'NORMAL') not in EXCLUDED_FROM_OFFICER_PARSING

def should_parse_shareholders(company: dict) -> bool:
    return company.get('company_type', 'NORMAL') not in EXCLUDED_FROM_SHAREHOLDER_PARSING

def should_calculate_index(company: dict) -> bool:
    return company.get('company_type', 'NORMAL') not in EXCLUDED_FROM_INDEX_CALCULATION

def get_excluded_reason(company: dict) -> str | None:
    company_type = company.get('company_type', 'NORMAL')
    reasons = {
        'SPAC': 'SPAC은 합병 전 데이터가 의미 없음',
        'REIT': '리츠는 별도 분석 필요',
        'ETF': 'ETF는 펀드라 재무 분석 대상 아님'
    }
    return reasons.get(company_type)
```

### Phase 4: 파싱 스크립트 수정

**수정 대상 파일:**
| 파일 | 수정 내용 |
|------|----------|
| `scripts/parse_officers_from_local.py` | 쿼리에 `company_type` 필터 |
| `scripts/collect_missing_officers.py` | 이름 체크 → DB 컬럼 체크 |
| `scripts/parse_major_shareholders.py` | ETF 제외 필터 |
| `scripts/parse_local_financial_details.py` | SPAC/리츠 필터 추가 |
| `scripts/pipeline/calculate_index.py` | `company_type` 필터 |

**쿼리 수정 예시:**
```python
# Before
query = """
    SELECT id, corp_code, name FROM companies
    WHERE listing_status = 'LISTED'
"""

# After
query = """
    SELECT id, corp_code, name, company_type FROM companies
    WHERE listing_status = 'LISTED'
      AND company_type NOT IN ('SPAC', 'REIT', 'ETF')
"""
```

---

## 3. 예상 효과

| 항목 | Before | After | 개선율 |
|------|--------|-------|--------|
| 임원 파싱 대상 | 3,922개 | 2,661개 | -32% |
| 불필요 재시도 | ~1,000회/분기 | 0회 | -100% |
| 파싱 시간 | 약 2시간 | 약 1.3시간 | -35% |

---

## 4. 구현 순서

1. ✅ 분석 완료
2. ⏳ DB 스키마 확장 (`company_type` 컬럼)
3. ⏳ 데이터 마이그레이션 (SPAC/ETF/리츠 분류)
4. ⏳ 공통 필터 유틸리티 생성
5. ⏳ 파싱 스크립트 수정 (5개)
6. ⏳ 기존 SPAC 불필요 데이터 정리 (선택)

---

## 5. 참조 파일

| 파일 | 용도 |
|------|------|
| `backend/app/models/companies.py` | Company 모델 |
| `backend/scripts/collect_missing_officers.py:127-133` | 현재 SPAC 이름 필터 예시 |
| `backend/scripts/parse_officers_from_local.py` | 임원 파싱 |
| `backend/scripts/parse_major_shareholders.py` | 대주주 파싱 |
| `backend/scripts/parse_local_financial_details.py` | 재무 파싱 |
| `backend/scripts/pipeline/calculate_index.py` | RaymondsIndex 계산 |
