# 거래소 표시 개발 계획 (KOSPI/KOSDAQ/KONEX/거래정지)

## 작성일: 2026-01-11

---

## 1. 현재 상황

### 1.1 DB 현황
- `market` 컬럼: KOSPI, KOSDAQ, KONEX, ETF 구분 **이미 존재**
- `listing_status` 컬럼: LISTED, ETF만 있음 (거래정지 미구분)

```
market  | listing_status | count
--------|----------------|-------
ETF     | ETF            | 1,149
KONEX   | LISTED         |   117
KOSDAQ  | LISTED         | 1,810
KOSPI   | LISTED         |   846
```

### 1.2 API 현황
- 대부분 API에서 `market` 반환 중
- `/search` API에서 `listing_status` 누락

### 1.3 프론트엔드 현황
- **거래소 배지 컴포넌트 없음**
- **스크리너 거래소 필터 없음**
- `raymondsindex-web/lib/types.ts`에 `market` 필드 없음

---

## 2. 개발 작업 목록

### Phase 1: DB 스키마 확장

```sql
-- 거래정지/관리종목 상태 추가
ALTER TABLE companies
  ADD COLUMN trading_status VARCHAR(20) DEFAULT 'NORMAL',
  ADD COLUMN trading_halt_date TIMESTAMP,
  ADD COLUMN is_managed BOOLEAN DEFAULT FALSE;

-- trading_status 값: NORMAL, SUSPENDED, TRADING_HALT
```

**파일:**
- `alembic/versions/xxx_add_trading_status.py`
- `backend/app/models/companies.py`
- `backend/app/schemas/company.py`

### Phase 2: 프론트엔드 MarketBadge 컴포넌트

**색상 규격:**
| 거래소 | 배경색 | 비고 |
|--------|--------|------|
| KOSPI | `#3B82F6` (blue-500) | 대표지수 |
| KOSDAQ | `#22C55E` (green-500) | 성장주 |
| KONEX | `#6B7280` (gray-500) | 중소기업 |
| 거래정지 | `#EF4444` (red-500) | 경고 |

**파일:**
- `frontend/src/components/common/MarketBadge.tsx` (신규)
- `raymondsindex-web/components/market-badge.tsx` (신규)

### Phase 3: 스크리너 거래소 필터

**파일:**
- `raymondsindex-web/app/screener/page.tsx`
- `raymondsindex-web/lib/types.ts` (market 필드 추가)

### Phase 4: 타입 정의 확장

**raymondsindex-web/lib/types.ts 수정:**
```typescript
export interface RaymondsIndexResponse {
  // ... 기존 필드
  market?: string;           // 추가
  trading_status?: string;   // 추가
}
```

---

## 3. 구현 순서

1. ✅ 분석 완료
2. ⏳ DB 스키마 확장 (company_type과 함께)
3. ⏳ MarketBadge 컴포넌트 생성
4. ⏳ 타입 정의 확장
5. ⏳ 스크리너 필터 추가
6. ⏳ 거래정지 데이터 수집 (외부 연동)

---

## 4. 참조 파일

| 파일 | 용도 |
|------|------|
| `backend/app/models/companies.py` | Company 모델 |
| `backend/app/schemas/company.py` | Pydantic 스키마 |
| `backend/app/api/endpoints/companies.py` | 회사 API |
| `raymondsindex-web/lib/types.ts` | 프론트엔드 타입 |
| `raymondsindex-web/app/screener/page.tsx` | 스크리너 페이지 |
| `raymondsindex-web/components/top-companies-table.tsx` | TOP 10 테이블 |
