# RaymondsIndex 통합 - Superclaude 원샷 프롬프트

## 전체 작업을 한 번에 실행하는 통합 프롬프트

**데이터 수집 기간: 2022-2024 (3개년)**

---

## SUPERCLAUDE 원샷 프롬프트

```
@task RaymondsIndex 기능을 Raymontology 시스템에 통합

@context
- 기존 시스템: FastAPI + PostgreSQL + Neo4j + React
- 기존 테이블: companies(3922), financial_statements(9432), risk_scores(3912)
- 기존 CB 데이터: 2022-2025 (동일 기간)
- 목표: 자본배분효율성지수(RaymondsIndex) 추가하여 기업의 현금-투자 균형 분석

@definition RaymondsIndex
- 핵심 공식: Investment Gap = Cash CAGR - CAPEX Growth Rate
- 양수 = 현금만 쌓음 (위험), 음수 = 적극 투자 (양호)
- Sub-Index 4개: CEI(20%), RII(35%), CGI(25%), MAI(20%)
- 등급: A+(80-100), A(60-79), B(40-59), C(20-39), D(0-19)

@data_collection
- 수집 기간: 2022-2024 (3개년)
- 대상: 3,922개 상장사
- 총 건수: 11,766건
- 예상 시간: 4-5시간

@backend
1. DB 스키마:
   - financial_details 테이블 (현금흐름표 포함 상세 재무데이터)
   - raymonds_index 테이블 (지수 계산 결과 저장)

2. 서비스:
   - backend/app/services/dart_financial_parser.py
     * DART API로 재무상태표, 손익계산서, 현금흐름표 파싱
     * 계정과목 매핑 (유형자산의취득 등 변형 처리)
   
   - backend/app/services/raymonds_index_calculator.py
     * CEI: 자산회전율, 현금수익률
     * RII: 투자괴리율 (핵심!)
     * CGI: 유휴현금비율, 자금활용률
     * MAI: 매출-투자 동조성
     * Red/Yellow Flag 자동 생성

3. 스크립트:
   - backend/scripts/collect_financial_details.py
     * --start-year 2022 --end-year 2024
     * 배치 수집, Rate Limiting 적용
   - backend/scripts/calculate_raymonds_index.py (배치 계산)

4. API:
   - GET /api/raymonds-index/{company_id}
   - GET /api/raymonds-index/search?grade=&min_score=
   - GET /api/raymonds-index/ranking?top=&bottom=
   - 기존 /api/report에 raymonds_index 필드 추가

@frontend
1. 컴포넌트 (frontend/src/components/RaymondsIndex/):
   - RaymondsIndexCard.tsx (점수 게이지 + 등급)
   - SubIndexChart.tsx (레이더 차트, D3/recharts)
   - InvestmentGapMeter.tsx (스펙트럼 바)
   - RiskFlagsPanel.tsx (Red/Yellow 플래그)

2. 페이지:
   - RaymondsIndexRankingPage.tsx (랭킹 테이블)

3. 통합:
   - Sidebar에 메뉴 추가
   - ReportPage에 RaymondsIndex 섹션 추가
   - App.tsx 라우트 추가

@dataflow
DART API → dart_financial_parser → financial_details 테이블
→ raymonds_index_calculator → raymonds_index 테이블
→ FastAPI → React 컴포넌트

@constraints
- DART API Rate Limit: 분당 1000건
- 최소 3개년 데이터 필요 (2022-2024 충족)
- 연결재무제표 우선
- 기존 risk_scores와 연동

@output
- 모든 상장사 3922개 RaymondsIndex 계산
- 등급별 분포 통계
- 테스트: 더본코리아(C), 삼성전자(A), 엑시온그룹(D)

@execute 순차적으로 백엔드 → 데이터수집 → 프론트엔드 구현
```

---

## 단계별 실행이 필요한 경우

### Step 1: 백엔드 인프라

```
@task 백엔드 인프라 구축

PostgreSQL 테이블 생성:
1. financial_details - 현금흐름표 포함 상세 재무데이터
2. raymonds_index - 지수 계산 결과

서비스 파일 생성:
1. dart_financial_parser.py - DART 재무데이터 파서
2. raymonds_index_calculator.py - 지수 계산 엔진

기존 backend/app/services/ 스타일 따르기
asyncio, pydantic 사용
```

### Step 2: 데이터 수집 (2022-2024)

```
@task 재무 데이터 배치 수집

스크립트: backend/scripts/collect_financial_details.py

작업:
1. companies 테이블에서 상장사 목록 조회
2. 각 회사별 2022-2024 (3개년) 재무데이터 DART에서 수집
3. financial_details 테이블에 저장
4. Rate limiting 적용 (asyncio.sleep)
5. 진행상황 로깅

실행: python collect_financial_details.py --start-year 2022 --end-year 2024

예상:
- 대상: 3,922사 × 3년 = 11,766건
- 소요시간: 약 4-5시간
```

### Step 3: 지수 계산

```
@task RaymondsIndex 배치 계산

스크립트: backend/scripts/calculate_raymonds_index.py

작업:
1. financial_details에서 3개년 이상 데이터 있는 회사 조회 (2022-2024)
2. RaymondsIndexCalculator로 계산
3. raymonds_index 테이블에 저장
4. risk_scores 테이블 연동

실행: python calculate_raymonds_index.py --year 2024
```

### Step 4: API

```
@task API 엔드포인트 구현

신규 라우터: backend/app/api/raymonds_index.py
- GET /{company_id} - 특정 회사 조회
- GET /search - 등급/점수 검색
- GET /ranking - 상위/하위 랭킹

기존 수정: backend/app/api/report.py
- risk_score 응답에 raymonds_index 추가

main.py에 라우터 등록
```

### Step 5: 프론트엔드

```
@task 프론트엔드 구현

컴포넌트 (frontend/src/components/RaymondsIndex/):
- RaymondsIndexCard.tsx
- SubIndexChart.tsx (recharts 레이더)
- InvestmentGapMeter.tsx
- RiskFlagsPanel.tsx

페이지:
- RaymondsIndexRankingPage.tsx

통합:
- Sidebar 메뉴 추가
- ReportPage에 섹션 추가
- App.tsx 라우트 추가
- API 클라이언트 + React Query 훅
```

---

## 검증 프롬프트

```
@task RaymondsIndex 통합 검증

테스트:
1. 더본코리아 조회 → C등급, 투자괴리율 +80%p 예상
2. 삼성전자 조회 → A등급 예상
3. 랭킹 API → 상위10, 하위10 정상 조회
4. Report 페이지 → RaymondsIndex 섹션 표시

통계:
- 전체 계산 완료 회사 수
- 등급별 분포 (A+, A, B, C, D)
- 데이터 부족으로 계산 불가 회사 수
```

---

## 롤백 프롬프트 (문제 발생 시)

```
@task RaymondsIndex 롤백

1. raymonds_index 테이블 DROP
2. financial_details 테이블 DROP
3. raymonds_index.py 라우터 제거
4. 프론트엔드 RaymondsIndex 컴포넌트 제거
5. Sidebar 메뉴 원복
6. ReportPage 원복
```

---

## 데이터 수집 요약

| 항목 | 값 |
|------|-----|
| **수집 기간** | 2022-2024 (3개년) |
| **대상 기업** | 3,922개 상장사 |
| **총 건수** | 11,766건 |
| **예상 시간** | 4-5시간 |
| **기존 CB 데이터** | 2022-2025 (동일 기간 ✅) |

---

## 실행 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: DB 스키마 생성                                      │
│  - financial_details, raymonds_index 테이블                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: DART 파서 구현                                      │
│  - dart_financial_parser.py                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: 데이터 수집 (2022-2024)                            │
│  - collect_financial_details.py                             │
│  - 약 4-5시간 소요                                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 계산 엔진 구현                                      │
│  - raymonds_index_calculator.py                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: 배치 계산                                          │
│  - calculate_raymonds_index.py --year 2024                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: API 구현                                           │
│  - raymonds_index.py 라우터                                 │
│  - report.py 확장                                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: 프론트엔드 구현                                     │
│  - 컴포넌트, 페이지, 메뉴 통합                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 8: 테스트 및 검증                                      │
│  - 더본코리아(C), 삼성전자(A), 엑시온그룹(D)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 끝
