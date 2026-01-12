# Raymontology 프로젝트 - Claude Code 필수 규칙

## 세션 시작 시 `/sc:load` 실행하세요

---

## 상태: 기업 유형 분류 시스템 구현 v2.7 (2026-01-12)
전체 18개 테이블 데이터 적재 완료. **RaymondsIndex 계산 완료 (5,257건)**.
**RaymondsIndex 독립 사이트**: https://raymondsindex.konnect-ai.net 배포 완료.
**RaymondsRisk 앱인토스**: 토스 로그인 연동 완료, 샌드박스 테스트 진행 중.
**최근 업데이트**: company_type/trading_status 컬럼 추가, SPAC/REIT/ETF 필터링 구현 (2026-01-12)

---

## 핵심 참조 문서 (필수 확인)

| 문서 | 용도 | 경로 |
|------|------|------|
| **프로젝트 설정** | **구현 현황 및 환경 설정** | **`PROJECT_SETUP.md`** |
| 환경 변수 | 프로덕션 DB 접속정보 | `.env.production` |
| 스키마 레지스트리 | 모든 테이블명/컬럼명 참조 | `scripts/SCHEMA_REGISTRY.md` |
| 표준 작업 프로세스 | 모든 DB 작업 체크리스트 | `scripts/STANDARD_PROCESS.md` |
| 파싱 상태 | 상세 파싱 진행 상황 | `scripts/PARSING_STATUS.md` |
| **앱인토스 가이드** | **토스 앱인앱 연동 개발** | **`docs/APPS_IN_TOSS_GUIDE.md`** |
| **RaymondsIndex 화면기획** | **독립 사이트 UI/UX 설계** | **`docs/RAYMONDSINDEX_UI_SPEC_v2.md`** |
| **RaymondsIndex 개발계획** | **독립 사이트 개발 일정** | **`docs/RAYMONDSINDEX_DEVELOPMENT_PLAN.md`** |
| **파이프라인 개선 계획** | **데이터 수집/파싱 자동화** | **`docs/DATA_PIPELINE_IMPROVEMENT_PLAN.md`** |
| 시장 표시 계획 | KOSPI/KOSDAQ/KONEX 표시 | `docs/MARKET_DISPLAY_PLAN.md` |
| 기업 유형 필터 계획 | SPAC/REIT/ETF 필터링 | `docs/COMPANY_TYPE_FILTER_PLAN.md` |

---

## 프로젝트 맵 (멀티 애플리케이션 구조) ⭐

Raymontology는 **4개의 독립 애플리케이션**을 포함합니다.

| # | 프로젝트 | 경로 | 기술 스택 | 배포/용도 |
|---|----------|------|-----------|-----------|
| 1 | **RaymondsRisk (웹)** | `frontend/` | Vite + React 18 + Tailwind | www.konnect-ai.net |
| 2 | **RaymondsIndex** | `raymondsindex-web/` | Next.js 16 + React 19 + shadcn | raymondsindex.konnect-ai.net |
| 3 | **앱인토스 앱** | `raymondsrisk-app/` | Vite + React 18 + @apps-in-toss/web-framework | 토스 앱인앱 |
| 4 | **Android 앱** | `android/` | Kotlin + WebView | 네이티브 앱 |

### 프로젝트 식별 방법 (중요!)

| 프로젝트 | 식별 파일 | 확인 명령어 |
|----------|-----------|-------------|
| 앱인토스 | `granite.config.ts` | `ls raymondsrisk-app/granite.config.ts` |
| Next.js | `next.config.*` | `ls raymondsindex-web/next.config.*` |
| Vite | `vite.config.*` | `ls frontend/vite.config.*` |
| Android | `build.gradle.kts` | `ls android/app/build.gradle.kts` |

### 작업 시 주의사항 (필수 준수!)
- 앱인토스 작업 → **반드시** `raymondsrisk-app/` 디렉토리 확인
- `www.konnect-ai.net` 관련 작업 → `frontend/` 디렉토리 수정
- `raymondsindex.konnect-ai.net` 관련 작업 → `raymondsindex-web/` 디렉토리 수정
- **외부 폴더 (`/Users/jaejoonpark/RaymondsRisk` 등) 혼동 금지!**
- **두 서비스를 혼동하지 말 것!**

### 프로젝트 경로 확인 체크리스트
```bash
# 앱인토스 프로젝트 확인
ls /Users/jaejoonpark/raymontology/raymondsrisk-app/granite.config.ts
ls /Users/jaejoonpark/raymontology/raymondsrisk-app/package.json

# SDK 설치 확인
grep "@apps-in-toss/web-framework" /Users/jaejoonpark/raymontology/raymondsrisk-app/package.json
```

---

## 앱인토스(Apps in Toss) 개발 규칙

**앱인토스는 RaymondsRisk 서비스 전용** (`raymondsrisk-app/` 디렉토리)

| 항목 | 값 |
|------|-----|
| 앱 이름 | `raymondsrisk` |
| 스킴 | `intoss://raymondsrisk` |
| 현재 상태 | 샌드박스 테스트 진행 중 |

**⚠️ 앱인토스 작업 전 반드시 `docs/APPS_IN_TOSS_GUIDE.md` 참조**

TDS 컴포넌트는 **비필수** (현재 인라인 스타일 방식 승인됨)

```bash
cd raymondsrisk-app && npm run dev        # 개발 서버
cd raymondsrisk-app && npm run granite:build  # .ait 빌드
```

---

## 테이블명 규칙 (필수)

테이블명은 반드시 `scripts/SCHEMA_REGISTRY.md` 참조 후 사용. 테이블명 추측 금지.

| 틀린 이름 | 올바른 이름 |
|----------|------------|
| company | **companies** |
| officer | **officers** |
| position | **officer_positions** |
| cb | **convertible_bonds** |
| subscriber | **cb_subscribers** |

---

## 표준 작업 프로세스 (필수)

**모든 DB 작업은 `scripts/STANDARD_PROCESS.md` 체크리스트 준수**

---

## 절대 금지 사항

### 1. 백그라운드 실행 금지
```
금지: python script.py &
금지: python script.py 2>&1 &
필수: python script.py (포그라운드에서 완료까지 대기)
```

### 2. "시작했습니다" 보고 금지
```
금지: "파싱을 시작했습니다"
금지: "스크립트를 실행했습니다"
금지: "백그라운드에서 실행 중입니다"
```

### 3. 검증 없는 완료 보고 금지
```
금지: 스크립트 실행만 하고 "완료"
금지: DB COUNT 확인 없이 성공 주장
```

---

## 현재 DB 상태 (2026-01-11 기준)

| 테이블 | 레코드 수 | 상태 |
|--------|----------|------|
| companies | 3,922 | ✅ |
| officers | 47,444 | ✅ (+2,423 from 426개 기업 보완) |
| officer_positions | 62,141 | ✅ (+8,670 from 426개 기업 보완) |
| disclosures | 279,258 | ✅ (+65,954 from 426개 기업 보완) |
| convertible_bonds | 1,133 | ✅ |
| cb_subscribers | 7,026 | ✅ |
| financial_statements | 9,820 | ✅ (+386 from 426개 기업 보완) |
| risk_signals | 1,412 | ✅ |
| risk_scores | 3,912 | ✅ |
| major_shareholders | 44,574 | ✅ |
| affiliates | 973 | ✅ |
| financial_details | 10,288 | ✅ (XBRL v3.0 파서 적용) |
| **raymonds_index** | **5,257** | ✅ 계산 완료 |
| **stock_prices** | **127,324** | ✅ |
| **largest_shareholder_info** | **4,599** | ✅ |
| user_query_usage | - | ✅ |
| page_contents | - | ✅ |

---

## 임원 API 규칙

임원 조회는 `officer_positions` 테이블 사용 (`officers.current_company_id`는 대부분 NULL)

```python
# 올바른 방법
query = (
    select(Officer, OfficerPosition.position)
    .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
    .where(OfficerPosition.company_id == company_id)
    .where(OfficerPosition.is_current == True)
)
```

Neo4j 미설정 시 `graph.py`가 자동으로 PostgreSQL fallback 사용

### 임원 경력 표시 v2.4 (2026-01-07) ⭐

**이중 표시 방식**:
1. **상장사 임원 DB** (구조화된 `career_history`): 前/現/전/현 패턴 파싱 결과
2. **사업보고서 주요경력 원문** (`career_raw_text`): 파싱 실패 시에도 원문 표시

| 컬럼 | 용도 | 데이터 형식 |
|------|------|------------|
| `career_history` | 구조화된 경력 (기존) | JSONB `[{text, status}]` |
| `career_raw_text` | 원문 표시 (v2.4 신규) | TEXT (□→• 변환) |

**경력 데이터 파싱 패턴**:
- **한자 패턴**: `前)`, `現)` (기존)
- **한글 패턴**: `전)`, `현)` (v2.3 추가)
- **연속 패턴**: `현) A현) B` → 2개 경력으로 분리

**관련 파일**:
- 파서: `scripts/parsers/officer.py`
- 재파싱: `scripts/maintenance/reparse_officer_careers.py`
- API: `app/api/endpoints/graph_fallback.py`
- 프론트엔드: `frontend/src/components/graph/NodeDetailPanel.tsx`

**재파싱 스크립트**:
```bash
# 테스트 (샘플 5개 기업)
DATABASE_URL="..." python scripts/maintenance/reparse_officer_careers.py --sample 5 --dry-run

# 전체 실행 (career_history + career_raw_text 업데이트)
DATABASE_URL="..." python scripts/maintenance/reparse_officer_careers.py
```

---

## 임원 주의 표시 기준 (그래프 UI)

| 표시 | 조건 | 색상 | 파일 |
|------|------|------|------|
| **붉은색 노드** | 상장사 경력 ≥ 3개 | `#EF4444` (red-500) | `ForceGraph.tsx:48-55` |
| **"주의" 배지** | 적자기업 경력 ≥ 1개 | `#F97316` (orange-500) | `ForceGraph.tsx:337-365` |

### 계산 로직 (`graph_fallback.py`)
- **상장사 경력**: `COUNT(DISTINCT company_id)` - 동일 회사 재임은 1회로 계산
- **적자기업**: `financial_statements`에서 최근 2년 `net_income < 0`인 회사
- **동명이인 방지**: `이름 + 출생년월` 조합으로 동일인 식별

---

## 주의 필요 기업 API

### 엔드포인트
```
GET /api/companies/high-risk
```

### 파라미터
| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `limit` | 6 | 결과 개수 (1-50) |
| `min_grade` | B | 최소 등급 (B, CCC, CC, C, D) |
| `has_cb` | true | CB 발행 여부 필터 |

### 동작 방식
- `risk_scores.investment_grade` 기준 필터링
- `ORDER BY RANDOM()` 으로 매번 다른 기업 표시
- 상장폐지 기업 제외 (`listing_status = 'LISTED'`)

관련 파일: `backend/app/api/endpoints/companies.py:363-451`

---

## 구독 시스템

| 이용권 | 가격 | 월 조회 제한 |
|--------|------|-------------|
| Free | 무료 | 5건 |
| Light | 3,000원/월 | 30건 |
| Max | 30,000원/월 | 무제한 |

관련: `backend/app/services/usage_service.py`, `backend/app/routes/subscription.py`

---

## RaymondsIndex 시스템

자본 배분 효율성 지수. 5,257개 기업 평가 완료 (v2.1).

| 등급 | 점수 범위 | 기업 수 |
|------|----------|--------|
| A- | 80-84 | 11 |
| B+ | 70-79 | 101 |
| B | 60-69 | 311 |
| B- | 50-59 | 917 |
| C+ | 40-49 | 1,213 |
| C | <40 | 145 |

관련 파일:
- `backend/app/models/financial_details.py`
- `backend/app/models/raymonds_index.py`
- `backend/app/services/raymonds_index_calculator.py`
- `frontend/src/pages/RaymondsIndexRankingPage.tsx`

---

## RaymondsIndex 독립 사이트 (배포 완료 ✅)

### 프로덕션 URL
- **사이트**: https://raymondsindex.konnect-ai.net
- **백엔드 API**: https://raymontology-production.up.railway.app/api

### 프로젝트 정보
- **프로젝트 경로**: `raymondsindex-web/` (별도 디렉토리)
- **기술 스택**: Next.js 14+, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **인증**: Zustand 기반 (JWT 토큰)
- **배포**: Railway

### 구현 완료 기능 (2025-12-31)
| 기능 | 상태 | 비고 |
|------|------|------|
| 홈페이지 (Hero + TOP 10 + 등급분포) | ✅ | |
| 스크리너 (필터, 정렬, 페이징) | ✅ | |
| 기업 상세 (레이더 차트, 지표 카드) | ✅ | |
| 평가 방법론 | ✅ | |
| 기업 검색 (자동완성) | ✅ | `/search/companies` API 사용 |
| 회원가입/로그인 | ✅ | 이용약관 모달 포함 |
| 관리자 페이지 | ✅ | superuser 전용 |
| HTTPS/SSL | ✅ | HSTS, CSP 보안 헤더 포함 |
| 지표 Tooltip 설명 | ✅ | Sub-Index, 핵심 지표 '?' 버튼 |
| 위험신호 패널 개선 | ✅ | 정상 상태 UI, 상태별 설명 |
| 투자괴리율 v2 계산 | ✅ | 재무상태표 기준 CAPEX |
| **데이터 품질 모니터링** | ✅ | 관리자 대시보드 (2025-12-31) |
| **관계도 전체화면 모드** | ✅ | ESC/빈영역 클릭 복귀 (2025-12-31) |

### 9등급 체계
| 등급 | 점수 범위 | 색상 |
|------|----------|------|
| A++ | 95+ | #1E40AF |
| A+ | 90-94 | #2563EB |
| A | 85-89 | #3B82F6 |
| A- | 80-84 | #60A5FA |
| B+ | 70-79 | #22C55E |
| B | 60-69 | #84CC16 |
| B- | 50-59 | #EAB308 |
| C+ | 40-49 | #F97316 |
| C | <40 | #EF4444 |

### 페이지 구조
- `/` - 홈 (Hero + TOP 10 + 등급분포)
- `/screener` - 기업 스크리닝
- `/company/[id]` - 기업 상세
- `/methodology` - 평가 방법론
- `/login` - 로그인
- `/signup` - 회원가입
- `/admin` - 관리자 (superuser 전용)

---

## DB 접속 정보

```bash
# 로컬 (개발)
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev

# 프로덕션 (Railway)
PGPASSWORD=ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR psql -h hopper.proxy.rlwy.net -p 41316 -U postgres -d railway

# API URL
https://raymontology-production.up.railway.app
```

---

## 원시 데이터 위치

- **DART 공시**: `backend/data/dart/` (9.2GB, 228,395 ZIP)
- **Q3 2025 보고서**: `backend/data/q3_reports_2025/` (2,671 ZIP)
- **CB 공시 JSON**: `backend/data/cb_disclosures_by_company_full.json`

---

## 아키텍처 규칙

```
원시 파일 (DART) → PostgreSQL (마스터) → Neo4j (파생)
                        ↑
                   절대 삭제 금지
```

---

## 분기별 데이터 파이프라인 (2026-01-04 구현)

### 파이프라인 개요
새로운 분기 데이터 수집/파싱/적재를 자동화하는 통합 파이프라인입니다.

```
다운로드 → 파싱 → 검증 → 적재 → RaymondsIndex 계산 → 보고서
```

### 전체 파이프라인 실행 (권장)
```bash
cd backend
source .venv/bin/activate

# 전체 파이프라인 실행
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025

# 테스트 모드 (샘플만)
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --sample 10 --dry-run

# 특정 단계부터 시작
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025 --start-from parse
```

### 개별 단계 실행
```bash
# 1. 다운로드 (DART_API_KEY 환경변수 필요)
python -m scripts.pipeline.download_quarterly_reports --quarter Q1 --year 2025

# 2. 파싱
python -m scripts.pipeline.run_unified_parser --quarter Q1 --year 2025

# 3. 검증
python -m scripts.pipeline.validate_parsed_data --quarter Q1 --year 2025

# 4. RaymondsIndex 계산
python -m scripts.pipeline.calculate_index --year 2025

# 5. 보고서 생성
python -m scripts.pipeline.generate_report --quarter Q1 --year 2025 --save
```

### 분기별 일정
| 분기 | 보고서 마감 | 파이프라인 실행 | 비고 |
|------|------------|----------------|------|
| Q1 (1분기) | 5월 15일 | 5월 20일 | |
| Q2 (반기) | 8월 14일 | 8월 20일 | |
| Q3 (3분기) | 11월 14일 | 11월 20일 | |
| Q4 (사업보고서) | 3월 31일 | 4월 5일 | 연간 데이터 확정 |

### 파이프라인 모듈 구조
```
scripts/pipeline/
├── __init__.py                    # 모듈 진입점
├── download_quarterly_reports.py  # DART 다운로드
├── run_unified_parser.py          # 통합 파서 실행
├── validate_parsed_data.py        # 데이터 품질 검증
├── calculate_index.py             # RaymondsIndex 계산
├── generate_report.py             # 보고서 생성
└── run_quarterly_pipeline.py      # 전체 파이프라인 통합
```

### 통합 파서 모듈 구조
```
scripts/parsers/
├── __init__.py           # 모듈 진입점
├── base.py               # BaseParser (공통 기능)
├── financial.py          # FinancialParser (230+ 계정 매핑)
├── officer.py            # OfficerParser (position_history 지원)
├── validators.py         # DataValidator (품질 검증)
├── unified.py            # DARTUnifiedParser (CLI 통합)
├── largest_shareholder.py # LargestShareholderParser (최대주주 기본정보)
└── xbrl_enhancer.py      # XBRLEnhancer (XBRL 데이터 보완)
```

### 통합 파서 사용법
```bash
# CLI 실행
python -m scripts.parsers.unified --year 2024 --type all
python -m scripts.parsers.unified --validate  # 데이터 검증만
python -m scripts.parsers.unified --stats     # 통계만

# Python에서 사용
from scripts.parsers import DARTUnifiedParser

parser = DARTUnifiedParser()
await parser.parse_all(target_years=[2024])
report = await parser.validate()
print(report.to_string())
```

---

## 데이터 수집 규칙 (중요!)

### 핵심 원칙: 파이프라인 사용 우선

**새로운 분기 데이터 수집 시 반드시 파이프라인 사용:**
```bash
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025
```

기존 개별 스크립트 직접 호출 금지 (레거시).

### 로컬 데이터 위치
| 데이터 | 경로 | 용도 |
|--------|------|------|
| **사업보고서 (연간)** | `data/dart/batch_*` | 2022-2024년 연간 재무 데이터 |
| **분기별 보고서** | `data/dart/quarterly/{year}/{quarter}/` | 분기별 데이터 (파이프라인 생성) |
| **3분기보고서 (2025)** | `data/q3_reports_2025/` | 2025년 3분기 재무 데이터 |
| **CB 공시 JSON** | `data/cb_disclosures_by_company_full.json` | 전환사채 정보 |
| **품질 보고서** | `data/reports/` | 파이프라인 실행 보고서 |

### 레거시 스크립트 (직접 호출 비권장)
| 데이터 | 레거시 스크립트 | 권장 대체 방법 |
|--------|----------------|---------------|
| **financial_details** | `parse_local_financial_details.py` | `scripts.parsers.unified` |
| **재파싱** | `reparse_financial_details_v2.py` | `scripts.pipeline.run_unified_parser` |
| **raymonds_index** | `calculate_raymonds_index.py` | `scripts.pipeline.calculate_index` |

### 사용 금지 스크립트
```
금지: collect_financial_details.py (DART API 직접 호출)
금지: collect_financial_statements.py (DART API 직접 호출)
```

---

## 실행 금지 스크립트

| 스크립트 | 위험 |
|---------|------|
| `sync_neo4j_to_postgres.py` | PostgreSQL TRUNCATE |
| `init_database.py` | DROP TABLE |
| `db_migrate.py --action=reset` | drop_all |

**위 스크립트들은 `scripts/_deprecated/`로 이동됨**

---

## 최대주주 기본정보 테이블 (`largest_shareholder_info`)

최대주주가 법인인 경우, 그 법인의 기본정보와 재무현황 저장 (4,599건).

**주요 컬럼**: `shareholder_name`, `investor_count`, `largest_investor_name`, `fin_total_assets` 등

**활용**: 실질 지배구조 파악, 연쇄 리스크 분석, 지배구조 복잡도 측정

---

## 기업 유형 분류 시스템 (2026-01-12 구현) ⭐

### companies 테이블 신규 컬럼

| 컬럼 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `company_type` | VARCHAR(20) | 'NORMAL' | 기업 유형 (NORMAL, SPAC, REIT, ETF, HOLDING, FINANCIAL) |
| `trading_status` | VARCHAR(20) | 'NORMAL' | 거래 상태 (NORMAL, SUSPENDED, TRADING_HALT) |
| `is_managed` | VARCHAR(1) | 'N' | 관리종목 여부 (Y/N) |

### 기업 유형별 현황

| company_type | 설명 | 기업 수 |
|--------------|------|--------|
| NORMAL | 일반 상장사 | ~2,600 |
| SPAC | 기업인수목적회사 | 80 |
| REIT | 부동산투자회사 | 42 |
| ETF | 상장지수펀드 | 1,149 |

### company_filter 유틸리티 모듈

**경로**: `scripts/utils/company_filter.py`

SPAC/ETF/REIT 기업은 임원, 대주주, 재무 데이터 구조가 일반 기업과 다르므로 파싱 대상에서 제외해야 합니다.

```python
from scripts.utils.company_filter import (
    should_parse_officers,      # SPAC, REIT, ETF 제외
    should_parse_shareholders,  # ETF만 제외
    should_parse_financials,    # ETF만 제외
    should_calculate_index,     # SPAC, REIT, ETF 제외
    get_excluded_reason,        # 제외 사유 반환
    get_filter_sql_clause,      # SQL WHERE 절 생성
)

# 사용 예시
if should_parse_officers({'company_type': 'SPAC', 'name': '스팩회사'}):
    parse_officers(company)  # 실행 안 됨

# SQL 쿼리에서 사용
sql_clause = get_filter_sql_clause('officer')  # "company_type NOT IN ('SPAC', 'REIT', 'ETF')"
```

### 적용된 파싱 스크립트

| 스크립트 | 적용 필터 |
|---------|----------|
| `parse_officers_from_local.py` | SPAC, REIT, ETF 제외 |
| `parse_major_shareholders.py` | ETF 제외 |
| `pipeline/calculate_index.py` | SPAC, REIT, ETF 제외 |
| `collect_missing_officers.py` | SPAC, REIT, ETF 제외 |

### 프론트엔드 시장 표시

**MarketBadge 컴포넌트**: `raymondsindex-web/components/market-badge.tsx`

| 시장 | 배지 색상 | 비고 |
|------|----------|------|
| KOSPI | 파란색 (#3B82F6) | |
| KOSDAQ | 초록색 (#22C55E) | |
| KONEX | 회색 (#6B7280) | |
| ETF | 보라색 (#8B5CF6) | |
| 거래정지 | 빨간 테두리 | trading_status='SUSPENDED' |

**스크리너 필터**: `raymondsindex-web/app/screener/page.tsx`
- KOSPI / KOSDAQ / KONEX 시장 필터 추가
- 여러 시장 다중 선택 가능
