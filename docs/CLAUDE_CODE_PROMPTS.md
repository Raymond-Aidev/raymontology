# RaymondsIndex 통합 - Claude Code 실행 프롬프트

## 사용법
각 프롬프트를 Claude Code 터미널에 복사하여 순차 실행

**데이터 수집 기간: 2022-2024 (3개년)**

---

## PROMPT 1: 데이터베이스 스키마 생성

```
프로젝트에 RaymondsIndex(자본배분효율성지수) 기능을 추가한다.

1단계: PostgreSQL 테이블 생성

1. financial_details 테이블 생성:
- company_id (UUID, FK → companies)
- fiscal_year, fiscal_quarter
- 재무상태표: cash_and_equivalents, short_term_investments, tangible_assets, total_assets, total_liabilities, total_equity (모두 BIGINT)
- 손익계산서: revenue, operating_income, net_income
- 현금흐름표: operating_cash_flow, capex, dividend_paid, stock_issuance, bond_issuance
- created_at, updated_at
- UNIQUE(company_id, fiscal_year, fiscal_quarter)

2. raymonds_index 테이블 생성:
- company_id (UUID, FK → companies)
- calculation_date, fiscal_year
- total_score (DECIMAL 0-100), grade (A+/A/B/C/D)
- Sub-Index: cei_score, rii_score, cgi_score, mai_score
- 핵심지표: investment_gap, cash_cagr, capex_growth, idle_cash_ratio
- flags: red_flags (JSONB), yellow_flags (JSONB)
- verdict, key_risk, watch_trigger (TEXT)
- UNIQUE(company_id, fiscal_year)

3. 인덱스 생성

기존 DB 연결 설정 사용해서 마이그레이션 파일 또는 직접 SQL 실행
```

---

## PROMPT 2: DART 재무 파서 구현

```
backend/app/services/dart_financial_parser.py 파일 생성

DARTFinancialParser 클래스 구현:

1. DART OpenAPI fnlttSinglAcnt 엔드포인트 사용
2. 계정과목 매핑 (동일 의미 다른 표현 처리):
   - 현금및현금성자산: ['현금및현금성자산', '현금및현금등가물']
   - 단기금융상품: ['단기금융상품', '단기금융자산']
   - 유형자산의취득: ['유형자산의 취득', '유형자산의취득', '유형자산 취득']
   등

3. 메서드:
   - async fetch_financial_details(corp_code: str, year: int) -> dict
   - parse_balance_sheet(data: list) -> dict
   - parse_income_statement(data: list) -> dict  
   - parse_cash_flow(data: list) -> dict
   - find_account_value(data: list, account_names: list) -> int

4. 연결재무제표 우선, 없으면 별도재무제표
5. httpx 또는 aiohttp 비동기 요청
6. 에러 핸들링, 로깅

기존 backend/app/services/dart_service.py 스타일 참고
```

---

## PROMPT 3: 배치 수집 스크립트 (2022-2024)

```
backend/scripts/collect_financial_details.py 스크립트 생성

기능:
1. companies 테이블에서 모든 상장사 조회
2. 각 회사별 2022-2024년 (3개년) 재무데이터 수집 (DARTFinancialParser 사용)
3. financial_details 테이블에 upsert
4. Rate limiting: 분당 1000건 제한 준수 (asyncio.sleep)
5. 진행상황 출력: 매 100개사
6. 실패 건 로깅 및 마지막에 재시도
7. asyncio.gather로 동시 5개 요청

CLI 인자:
--start-year (default: 2022)
--end-year (default: 2024)
--batch-size (default: 100)
--retry-failed (실패 건만 재시도)

예상:
- 대상: 3,922사 × 3년 = 11,766건
- 소요시간: 약 4-5시간

기존 backend/scripts/ 스크립트 스타일 참고
```

---

## PROMPT 4: RaymondsIndex 계산 엔진

```
backend/app/services/raymonds_index_calculator.py 파일 생성

RaymondsIndexCalculator 클래스 구현:

1. Sub-Index 4개:
   - CEI (20%): 자산회전율(매출/자산), 현금수익률(영업이익/현금)
   - RII (35%): 투자괴리율 = 현금CAGR - CAPEX증가율 (핵심!)
   - CGI (25%): 유휴현금비율(단기금융상품/총현금), 자금활용률
   - MAI (20%): 매출성장률 vs 투자성장률 동조성

2. 핵심 공식 (RII):
   cash_cagr = ((cash_end / cash_start) ** (1/years) - 1) * 100
   capex_growth = ((capex_late / capex_early) - 1) * 100
   investment_gap = cash_cagr - capex_growth
   
   if investment_gap > 30: 심각 (현금만 쌓음)
   if investment_gap < -15: 적극 투자

3. 등급:
   A+ (80-100), A (60-79), B (40-59), C (20-39), D (0-19)

4. Flag 생성:
   - 투자괴리율 > 30%p → Red Flag
   - 유휴현금비율 > 50% → Yellow Flag
   - 증자/사채 자금 미활용 → Red Flag

5. 메서드:
   - calculate(company_id: UUID) -> RaymondsIndexResult
   - _calc_cei(data: dict) -> float
   - _calc_rii(data: dict) -> float
   - _calc_cgi(data: dict) -> float
   - _calc_mai(data: dict) -> float
   - _generate_flags(metrics: dict) -> tuple[list, list]
   - _determine_grade(score: float) -> str

6. 최소 3개년 데이터 필요 (2022-2024 충족)

pydantic 모델로 결과 정의
```

---

## PROMPT 5: 배치 계산 스크립트

```
backend/scripts/calculate_raymonds_index.py 스크립트 생성

기능:
1. financial_details에 3개년 이상 데이터 있는 회사 조회 (2022-2024)
2. RaymondsIndexCalculator로 각 회사 계산
3. raymonds_index 테이블에 저장 (upsert)
4. risk_scores 테이블과 연동 (raymonds_grade 업데이트)
5. 진행상황 로깅
6. 통계 출력: 등급별 분포

CLI 인자:
--year (분석 기준 연도, default: 2024)
--company-id (특정 회사만)
--dry-run (저장 안 함)
```

---

## PROMPT 6: FastAPI 라우터

```
backend/app/api/raymonds_index.py 파일 생성

라우터: /api/raymonds-index

엔드포인트:

1. GET /{company_id}
   - 특정 회사 RaymondsIndex 조회
   - 응답: total_score, grade, sub_indices, key_metrics, flags, verdict

2. GET /search
   - 쿼리: grade, min_score, max_score, limit, offset
   - 등급/점수 기준 검색

3. GET /ranking
   - 쿼리: top (상위 N개), bottom (하위 N개), industry_code
   - 랭킹 조회

4. GET /{company_id}/history
   - 연도별 점수 추이

5. POST /{company_id}/calculate (관리자용)
   - 특정 회사 재계산

기존 backend/app/api/report.py 스타일 참고
main.py에 라우터 등록 추가
```

---

## PROMPT 7: 기존 Report API 확장

```
backend/app/api/report.py 수정

GET /api/report/name/{company_name} 응답에 RaymondsIndex 추가:

기존 risk_score 객체 내에:
{
  "risk_score": {
    ... 기존 필드 ...
    
    "raymonds_index": {
      "total_score": 21.8,
      "grade": "C",
      "investment_gap": 80.3,
      "cei_score": 46.3,
      "rii_score": 5.0,
      "cgi_score": 15.0,
      "mai_score": 35.0,
      "verdict": "현금-투자 균형 점검 필요",
      "red_flags": [...],
      "yellow_flags": [...]
    }
  }
}

raymonds_index 테이블에서 조회해서 추가
```

---

## PROMPT 8: React 컴포넌트 - Card

```
frontend/src/components/RaymondsIndex/RaymondsIndexCard.tsx 생성

Props:
- score: number (0-100)
- grade: 'A+' | 'A' | 'B' | 'C' | 'D'
- investmentGap: number
- verdict: string

기능:
1. 종합 점수 게이지 (반원형 또는 원형)
2. 등급 배지 (색상: A+초록, A연두, B노랑, C주황, D빨강)
3. 투자괴리율 표시
4. 한 줄 판정

shadcn/ui Card 컴포넌트 사용
Tailwind CSS 스타일링
```

---

## PROMPT 9: React 컴포넌트 - 차트

```
frontend/src/components/RaymondsIndex/SubIndexChart.tsx 생성

Props:
- cei: number
- rii: number  
- cgi: number
- mai: number

D3.js 레이더 차트:
- 4개 축 (CEI, RII, CGI, MAI)
- 0-100 스케일
- 현재 값 영역 표시
- 호버 시 상세 점수

recharts 라이브러리 사용 가능
```

---

## PROMPT 10: React 컴포넌트 - 투자괴리율 미터

```
frontend/src/components/RaymondsIndex/InvestmentGapMeter.tsx 생성

Props:
- value: number (투자괴리율 %)
- cashGrowth: number
- capexGrowth: number

스펙트럼 바:
[-50% ... 0% ... +50%]
과잉투자 ← 균형 → 현금정체

- 빨강(좌): 과잉투자 위험
- 초록(중앙): 균형
- 주황(우): 현금 정체

현재 위치 마커 표시
수치 레이블
```

---

## PROMPT 11: React 컴포넌트 - 플래그 패널

```
frontend/src/components/RaymondsIndex/RiskFlagsPanel.tsx 생성

Props:
- redFlags: string[]
- yellowFlags: string[]

레이아웃:
- Red Flags 섹션 (빨간 아이콘 + 텍스트)
- Yellow Flags 섹션 (노란 아이콘 + 텍스트)
- 비어있으면 "특이사항 없음"

lucide-react 아이콘 사용 (AlertTriangle, AlertCircle)
```

---

## PROMPT 12: 랭킹 페이지

```
frontend/src/pages/RaymondsIndexRankingPage.tsx 생성

기능:
1. 상단: 필터 바
   - 등급 선택 (A+, A, B, C, D, 전체)
   - 업종 선택
   - 검색 입력

2. 테이블:
   - 순위, 회사명, 업종, 점수, 등급, 투자괴리율, 주요플래그
   - 정렬 가능
   - 페이지네이션

3. 클릭 → /report/{companyId}로 이동

4. 상위 10 / 하위 10 탭

useQuery로 /api/raymonds-index/ranking 호출
shadcn/ui Table 컴포넌트 사용
```

---

## PROMPT 13: 라우터 및 메뉴 통합

```
프론트엔드 통합 작업:

1. frontend/src/App.tsx
   - Route 추가: /raymonds-index → RaymondsIndexRankingPage

2. frontend/src/components/Sidebar.tsx (또는 Navigation)
   - 메뉴 항목 추가: "RaymondsIndex 랭킹"
   - 아이콘: BarChart3 (lucide-react)
   - 경로: /raymonds-index

3. frontend/src/api/raymondsIndex.ts
   - getRaymondsIndex(companyId)
   - searchRaymondsIndex(params)
   - getRaymondsIndexRanking(params)

4. frontend/src/hooks/useRaymondsIndex.ts
   - useRaymondsIndex(companyId)
   - useRaymondsIndexRanking(params)

5. frontend/src/types/raymondsIndex.ts
   - RaymondsIndex, SubIndices, RaymondsIndexSearchParams 타입
```

---

## PROMPT 14: Report 페이지에 RaymondsIndex 추가

```
frontend/src/pages/ReportPage.tsx 수정

기존 리스크 점수 섹션 아래에 RaymondsIndex 섹션 추가:

레이아웃:
<Section title="자본배분 효율성 (RaymondsIndex)">
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <RaymondsIndexCard ... />
    <SubIndexChart ... />
  </div>
  <InvestmentGapMeter ... />
  <RiskFlagsPanel ... />
</Section>

API 응답의 risk_score.raymonds_index 데이터 사용
```

---

## PROMPT 15: 테스트 작성

```
테스트 파일 생성:

1. backend/tests/test_raymonds_index_calculator.py
   - test_cei_calculation
   - test_rii_investment_gap
   - test_grade_determination
   - test_flag_generation

2. backend/tests/test_raymonds_index_api.py
   - test_get_raymonds_index
   - test_search_by_grade
   - test_ranking

3. frontend/src/components/RaymondsIndex/__tests__/
   - RaymondsIndexCard.test.tsx
   - SubIndexChart.test.tsx

테스트 케이스:
- 더본코리아 (예상 C등급, 투자괴리율 +80%)
- 삼성전자 (예상 A등급)
- 엑시온그룹 (예상 D등급)

pytest, vitest 사용
```

---

## 실행 순서 요약

```bash
# 1. DB 스키마
→ PROMPT 1 실행

# 2. 백엔드 서비스
→ PROMPT 2 (파서)
→ PROMPT 3 (수집 스크립트)
→ PROMPT 4 (계산 엔진)
→ PROMPT 5 (계산 스크립트)

# 3. 데이터 수집 및 계산 (터미널에서)
python backend/scripts/collect_financial_details.py --start-year 2022 --end-year 2024
python backend/scripts/calculate_raymonds_index.py --year 2024

# 4. API
→ PROMPT 6 (신규 라우터)
→ PROMPT 7 (기존 Report 확장)

# 5. 프론트엔드
→ PROMPT 8-11 (컴포넌트)
→ PROMPT 12 (랭킹 페이지)
→ PROMPT 13 (통합)
→ PROMPT 14 (Report 페이지)

# 6. 테스트
→ PROMPT 15
```

---

## 데이터 수집 상세

| 항목 | 값 |
|------|-----|
| 수집 기간 | 2022-2024 (3개년) |
| 대상 기업 | 3,922개 상장사 |
| 총 건수 | 11,766건 |
| 예상 시간 | 4-5시간 |
| 기존 CB 데이터 | 2022-2025 (동일 기간) |

---

## 끝
