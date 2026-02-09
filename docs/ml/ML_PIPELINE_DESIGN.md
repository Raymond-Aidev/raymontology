# 관계형 리스크 악화가능성 예측 ML 파이프라인 설계

> 버전: 3.0 | 작성일: 2026-02-05 | 수정일: 2026-02-08 | 상태: **구현 완료 (Phase 0-7)**
>
> **v3.0 변경사항**: 전체 파이프라인 구현 완료 반영, CatBoost 비활성화 (Python 3.14 미지원), API 엔드포인트 확정, 디렉토리 구조 실제 반영
> **v2.2 변경사항**: Phase 6b 거래정지 기업 검증 단계 추가 (기업별 예측값 확인 + 오류 분석 + 재학습 루프)
> **v2.1 변경사항**: 배치 추론 → DB 저장 파이프라인 추가, end-to-end 흐름 명시
> **v2.0 변경사항**: DB 검증 결과 반영, CSV 피처 정의서 기준 동기화, 라벨 실데이터 반영, Temporal Split 전략 추가

---

## 1. 프로젝트 개요

### 1.1 목표
한국 상장기업의 **관계형 리스크(Relational Risk)**가 향후 악화될 확률을 0-100%로 예측하는 ML 모델 개발

### 1.2 핵심 흐름 (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ML 파이프라인 전체 흐름                            │
│                                                                      │
│  [Phase 0-4] 데이터 준비                                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ SUSPENDED │    │ 26개 피처 │    │ 라벨 생성 │    │ 피처 스토어│      │
│  │ 사유 분류 │ →  │ 추출 모듈 │ →  │ 모듈     │ →  │ DB 적재   │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│                                                                      │
│  [Phase 5-6] 모델 학습 + 평가                                       │
│  ┌──────────────────────────────────────────────────┐               │
│  │ ml_features → Temporal Split → 앙상블 학습         │               │
│  │ → 6a: 정량 평가 (AUC ≥ 0.70)                      │               │
│  │ → 6b: 거래정지 기업 검증 (TYPE_A 기업별 예측 확인) │               │
│  │ → 합격 시 saved_models/ 저장                       │               │
│  └──────────────────────────────────────────────────┘               │
│                                                                      │
│  [Phase 7] 배치 추론 + DB 저장  ← ⭐ 핵심 산출물                    │
│  ┌──────────────────────────────────────────────────┐               │
│  │ LISTED 3,021개 기업 전체 순회                       │               │
│  │   → 피처 추출 → 모델 추론 → 악화확률(%) 산출       │               │
│  │   → risk_predictions 테이블 INSERT                 │               │
│  │                                                    │               │
│  │ 결과 예시:                                          │               │
│  │   삼성전자: 악화확률 12% (LOW)                      │               │
│  │   ○○기업: 악화확률 73% (HIGH)                      │               │
│  └──────────────────────────────────────────────────┘               │
│                                                                      │
│  [Phase 8] API 서빙 (risk-web 등에서 DB 조회)                       │
│  ┌──────────────────────────────────────────────────┐               │
│  │ GET /api/companies/{id} → risk_predictions 조회    │               │
│  │ → {"deterioration_probability": 0.73, ...}         │               │
│  └──────────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 출력 형식
```
악화가능성: 73%
위험단계: 높음 (70-100%)
```

### 1.4 비즈니스 가치
- 투자자: 리스크 악화 전 선제적 포트폴리오 조정
- 기업: 지배구조 개선 필요성 인지
- 금융기관: 여신 심사 시 선행 지표 활용

---

## 2. 데이터 가용성 검증 결과

### 2.1 현재 DB 현황 (2026-02-05 검증)

| 테이블 | 레코드 수 | ML 활용 목적 |
|--------|----------|--------------|
| `companies` | 3,109 | 기업 마스터, 라벨 (LISTED 3,021 + ETF 88) |
| `officers` | 49,446 | 임원 네트워크 피처 |
| `officer_positions` | 75,059 | 겸직, 경력 피처 |
| `convertible_bonds` | 1,128 | CB 피처 |
| `cb_subscribers` | 7,021 | CB 투자자 피처 |
| `major_shareholders` | 60,214 | 대주주 피처 |
| `raymonds_index` | 5,354 | 인덱스 피처 (2024: 2,707건, 2025: 2,590건) |
| `risk_scores` | 3,100 | 현재 리스크 점수 |
| `financial_statements` | 9,820 | 적자 라벨 |
| `financial_details` | 10,288 | 재무비율 피처 |
| `dispute_officers` | 391 | ⚠️ officer_id 전수 NULL (회사 수준만 73개사) |

### 2.2 라벨 데이터 분포 (DB 검증 완료)

| 라벨 유형 | 건수 | 상태 | 설명 |
|----------|------|------|------|
| **거래정지 (SUSPENDED)** | **354건** | ✅ 사용 가능 | `trading_status = 'SUSPENDED'` |
| **연속 적자 2년+** | **473건** | ✅ 사용 가능 | 2023-2024 `net_income < 0` 연속 |
| **인덱스 YoY 급락** | **2,550건 비교 가능** | ✅ 사용 가능 | 2024-2025 양쪽 데이터 보유 기업 |
| **관리종목** | **0건** | ❌ 데이터 없음 | 전체 3,021 LISTED가 is_managed='N' |
| **상장폐지** | — | ❌ 사용 불가 | 774건 삭제됨 (피처 데이터 0) |

### 2.3 SUSPENDED 기업 데이터 풍부도 (ML 핵심 양성 라벨)

354개 거래정지 기업의 데이터 보유 현황:

| 데이터 수준 | 기업 수 | 비율 | ML 활용 |
|------------|--------|------|---------|
| **A: 풍부** (재무3+, 인덱스2+) | 88 | 25% | 전체 피처 추출 가능 |
| **B: 보통** (일부 재무/인덱스) | 42 | 12% | 부분 피처 추출 가능 |
| **C: 임원만** | 207 | 58% | 임원 네트워크 피처만 |
| **D: 데이터 없음** | 17 | 5% | 사용 불가 |

테이블별 보유:
- risk_scores: 349건 (98.6%)
- officer_positions (현재 임원): 323건 (91.2%)
- financial_details: 130건 (36.7%)
- raymonds_index: 105건 (29.7%)
- convertible_bonds: 64건 (18.1%)

**주의**: SUSPENDED 기업 중 합병/자진상폐 (HD현대인프라코어, 락앤락, 세아특수강 등)와 재무악화/횡령 (금양, 효성화학, 바이온 등)을 구분해야 함. → Phase 0에서 사유 분류 필요.

### 2.4 데이터 품질 제약사항 (DB 검증 결과)

| 항목 | 문제 | 영향 |
|------|------|------|
| `officer_positions.term_start_date` | 19% (14,288/75,059)만 값 있음 | E02 이직률, E03 재직기간 계산 제한적 |
| `officer_positions.term_end_date` | 48% (36,365/75,059)만 값 있음 | 이직률 proxy 필요 |
| `officer_positions.is_current` | 99.4% (74,616/75,059)가 TRUE | 시계열 변화 추적 어려움 |
| `dispute_officers.officer_id` | **전수 NULL** (0/391건) | 임원 단위 분쟁 비율 계산 불가 → 회사 단위로 변경 |
| `is_managed` 컬럼 | 3,021건 전부 'N' | 관리종목 라벨 사용 불가 → KRX 데이터 보강 필요 |
| `major_shareholders` 2024년 | 1,172개사만 보유 (2025: 2,479) | YoY 지분 변동 계산 범위 제한 |

### 2.5 피처 데이터 통계

| 피처 그룹 | 핵심 통계 | 데이터 소스 |
|----------|----------|------------|
| **임원 겸직** | 3,514명 (2개사+), 475명 (3개사+, 고위험) | PostgreSQL + Neo4j |
| **CB 발행** | 643개사, 2023-2025 집중 (882건/466개사) | PostgreSQL |
| **4대 인덱스** | CEI, CGI, RII, MAI (0-100점) | `raymonds_index` |
| **인덱스 확장** | roic, debt_to_ebitda, idle_cash_ratio 등 | `raymonds_index` |

---

## 3. 피처 엔지니어링 설계

> **기준 문서**: `RaymondsRisk_ML_Feature_Selection.csv`
> 피처 ID 체계: E(임원), C(CB), S(대주주), I(인덱스)

### 3.1 피처 그룹 구조 (총 26개)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Engineering (26개)                     │
├─────────────────────────────────────────────────────────────────┤
│  [A] 임원 네트워크 (10)          │  [B] CB 투자자 (8)            │
│  E01 exec_count            [M]  │  C01 cb_count_1y         [H]  │
│  E02 exec_turnover_rate    [H]  │  C02 cb_total_amount_1y  [H]  │
│  E03 exec_avg_tenure       [M]  │  C03 cb_subscriber_count [M]  │
│  E04 exec_other_company_count[H]│  C04 cb_high_risk_sub_r  [C]  │
│  E05 exec_avg_other_companies[H]│  C05 cb_sub_avg_invest   [H]  │
│  E06 exec_delisted_connection[C]│  C06 cb_loss_company_conn[C]  │
│  E07 exec_managed_connection [C]│  C07 cb_delisted_conn    [C]  │
│  E08 exec_concurrent_positions[H]│ C08 cb_repeat_sub_ratio  [M]  │
│  E09 exec_network_density  [M]  │                               │
│  E10 exec_high_risk_ratio  [H]  │  [C]=CRITICAL [H]=HIGH        │
├─────────────────────────────────────────────────────────────────┤
│  [C] 대주주 (4)                  │  [D] 4대 인덱스 (4)           │
│  S01 largest_shareholder_ratio[M]│  I01 CEI (임원집중도)    [H]  │
│  S02 shareholder_change_1y [H]  │  I02 CGI (지배구조)      [M]  │
│  S03 related_party_ratio   [M]  │  I03 RII (관계강도)      [H]  │
│  S04 shareholder_count     [L]  │  I04 MAI (시장이상)      [H]  │
│                                  │  [M]=MEDIUM [L]=LOW           │
└─────────────────────────────────────────────────────────────────┘
```

**중요도 분포**: CRITICAL 5개, HIGH 11개, MEDIUM 8개, LOW 2개

### 3.2 피처 상세 정의

#### [A] 임원 네트워크 피처 (10개)

| ID | 피처명 | 설명 | 계산 로직 | 데이터 소스 | 중요도 |
|----|--------|------|----------|------------|--------|
| E01 | `exec_count` | 임원 수 | `COUNT(DISTINCT officer_id)` | officer_positions | MEDIUM |
| E02 | `exec_turnover_rate` | 임원 이직률 | 최근 1년 퇴임 임원 / 전체 임원 | officer_positions | HIGH |
| E03 | `exec_avg_tenure` | 평균 재직 기간(월) | `AVG(current_date - term_start_date)` | officer_positions | MEDIUM |
| E04 | `exec_other_company_count` | 타사 재직 건수 합계 | 모든 임원의 타사 재직 건수 총합 | Neo4j WORKS_AT | HIGH |
| E05 | `exec_avg_other_companies` | 임원당 평균 타사 재직 | E04 / E01 | Neo4j WORKS_AT | HIGH |
| E06 | `exec_delisted_connection` | 상장폐지 기업 연결 수 | 임원이 재직했던 상장폐지/거래정지 기업 수 | Neo4j + companies | **CRITICAL** |
| E07 | `exec_managed_connection` | 관리종목 기업 연결 수 | 임원이 재직했던 관리종목 기업 수 | Neo4j + companies | **CRITICAL** |
| E08 | `exec_concurrent_positions` | 겸직 임원 수 | 현재 타사 겸직 중인 임원 수 | Neo4j WORKS_AT | HIGH |
| E09 | `exec_network_density` | 네트워크 밀도 | actual_edges / possible_edges | Neo4j | MEDIUM |
| E10 | `exec_high_risk_ratio` | 고위험 임원 비율 | 타사 5개사 이상 재직 임원 / E01 | Neo4j WORKS_AT | HIGH |

**v1.0 대비 변경사항**:
- ~~`dispute_officer_ratio`~~ 제거: `dispute_officers.officer_id` 전수 NULL로 계산 불가
- ~~`related_party_ratio`~~ (성씨 매칭) 제거: 한국 성씨 편중 (김/이/박 = 45%)으로 오탐율 극히 높음
- ~~`ceo_change_count`, `board_independence`~~ → `exec_concurrent_positions`, `exec_network_density`, `exec_high_risk_ratio`로 대체
- 신규 추가: E06 상장폐지 연결, E07 관리종목 연결, E09 네트워크 밀도

**E02/E03 데이터 제약**: `term_start_date` 19%, `term_end_date` 48%만 값 존재. 보고서별 임원 변동을 proxy로 사용하거나, 날짜가 있는 레코드만으로 샘플 기반 추정 필요.

#### [B] CB 투자자 피처 (8개)

| ID | 피처명 | 설명 | 계산 로직 | 데이터 소스 | 중요도 |
|----|--------|------|----------|------------|--------|
| C01 | `cb_count_1y` | CB 발행 횟수 (최근 1년) | `COUNT(cb WHERE issue_date >= 1year_ago)` | convertible_bonds | HIGH |
| C02 | `cb_total_amount_1y` | CB 발행 총액 (최근 1년, 억원) | `SUM(amount) / 1억 WHERE 1year` | convertible_bonds | HIGH |
| C03 | `cb_subscriber_count` | CB 참여자 수 (전체 기간) | `COUNT(DISTINCT subscriber_name)` | cb_subscribers | MEDIUM |
| C04 | `cb_high_risk_subscriber_ratio` | 고위험 투자자 비율 | 적자기업 투자비율 50%+ 투자자 / C03 | cb_subscribers + Neo4j | **CRITICAL** |
| C05 | `cb_subscriber_avg_investments` | 투자자 평균 투자 건수 | CB 참여자들의 평균 타사 투자 건수 | Neo4j INVESTED_IN | HIGH |
| C06 | `cb_loss_company_connections` | 적자기업 연결 수 | CB 투자자들이 투자한 적자기업 수 (중복제거) | Neo4j + financial_statements | **CRITICAL** |
| C07 | `cb_delisted_connections` | 상장폐지 연결 수 | CB 투자자들이 투자한 상장폐지/거래정지 기업 수 | Neo4j + companies | **CRITICAL** |
| C08 | `cb_repeat_subscriber_ratio` | 반복 투자자 비율 | 2회 이상 참여 투자자 / C03 | cb_subscribers | MEDIUM |

**v1.0 대비 변경사항**:
- `cb_count` → `cb_count_1y` (최근 1년 고정 기간으로 변경, 관찰기간 왜곡 방지)
- `cb_total_amount` → `cb_total_amount_1y` (동일 이유)
- ~~`subscriber_diversity`~~ (Shannon Entropy) → `cb_repeat_subscriber_ratio` (더 직관적)
- ~~`cb_frequency`~~ (연간 빈도) → C01로 통합
- `high_risk_subscriber_ratio` 기준 변경: "다중 CB 참여" → "적자기업 투자비율 50%+"
- 신규 추가: C07 상장폐지 연결

#### [C] 대주주 피처 (4개)

| ID | 피처명 | 설명 | 계산 로직 | 데이터 소스 | 중요도 |
|----|--------|------|----------|------------|--------|
| S01 | `largest_shareholder_ratio` | 최대주주 지분율 (%) | `MAX(share_ratio) WHERE is_largest=TRUE` | major_shareholders | MEDIUM |
| S02 | `shareholder_change_1y` | 지분 변동폭 (1년, %p) | `current_ratio - previous_share_ratio` | major_shareholders | HIGH |
| S03 | `related_party_ratio` | 특수관계인 지분율 | `SUM(share_ratio WHERE is_related_party=TRUE)` | major_shareholders | MEDIUM |
| S04 | `shareholder_count` | 주요주주 수 (5%+) | `COUNT(WHERE share_ratio >= 5)` | major_shareholders | LOW |

**v1.0 대비 변경사항**:
- `ownership_change` → `shareholder_change_1y` (명칭 명확화, `previous_share_ratio` 컬럼 직접 활용)
- `related_party_ratio`: 성씨 매칭 → **`is_related_party` DB 컬럼 기반**으로 변경
- ~~`insider_ownership`~~ → `related_party_ratio`로 통합

#### [D] 4대 인덱스 피처 (4개)

| ID | 피처명 | 범위 | 설명 | 데이터 소스 | 중요도 |
|----|--------|------|------|------------|--------|
| I01 | `cei_score` | 0-100 | 임원집중도지수 | `raymonds_index.cei_score` | HIGH |
| I02 | `cgi_score` | 0-100 | 지배구조지수 | `raymonds_index.cgi_score` | MEDIUM |
| I03 | `rii_score` | 0-100 | 관계강도지수 | `raymonds_index.rii_score` | HIGH |
| I04 | `mai_score` | 0-100 | 시장이상지수 | `raymonds_index.mai_score` | HIGH |

### 3.3 Neo4j 의존 피처 (구현 시 주의)

아래 10개 피처는 **Neo4j 그래프 쿼리**가 필요합니다. PostgreSQL fallback으로 대체 가능하나 성능 및 정확도가 낮아집니다.

| 피처 ID | Neo4j 관계 | PostgreSQL fallback 가능 여부 |
|---------|-----------|------------------------------|
| E04, E05, E08, E10 | `WORKS_AT` | ✅ officer_positions JOIN으로 대체 가능 |
| E06, E07 | `WORKS_AT` + companies.status | ✅ 대체 가능 (성능 저하) |
| E09 | 그래프 밀도 계산 | ⚠️ 근사치만 가능 |
| C04, C05, C06, C07 | `INVESTED_IN` | ⚠️ cb_subscribers JOIN으로 부분 대체 |

---

## 4. 라벨 정의 (Supervised Learning)

### 4.1 악화 이벤트 정의 (DB 검증 반영)

| 우선순위 | 이벤트 | 탐지 방법 | 가중치 | 데이터 건수 | 상태 |
|---------|--------|----------|--------|-----------|------|
| 1 | **거래정지 (재무악화)** | `trading_status = 'SUSPENDED'` + 사유 분류 | **1.0** | ~250건 (추정) | ✅ Phase 0에서 분류 |
| 2 | **거래정지 (합병/자진상폐)** | `trading_status = 'SUSPENDED'` + 사유 분류 | **제외** | ~100건 (추정) | ✅ 양성 라벨에서 제외 |
| 3 | **인덱스 20% 이상 하락** | `total_score` YoY 비교 (2024→2025) | 0.4 | 2,550건 비교 가능 | ✅ 사용 가능 |
| 4 | **연속 적자 (2년+)** | `net_income < 0` 2023-2024 연속 | 0.3 | 473건 | ✅ 사용 가능 |
| 5 | ~~관리종목 지정~~ | ~~`is_managed = 'Y'`~~ | ~~0.6~~ | **0건** | ❌ 비활성화 |
| 6 | ~~상장폐지~~ | ~~`listing_status` 변경~~ | ~~1.0~~ | **0건** (삭제됨) | ❌ 비활성화 |

**핵심 변경**: 상장폐지/관리종목 라벨은 데이터 부재로 비활성화. 거래정지(SUSPENDED)가 사실상 최고 수준 양성 라벨. 단, **합병/자진상폐 사유의 거래정지는 반드시 제외**해야 함.

### 4.2 거래정지 사유 분류 (Phase 0 선행 작업)

SUSPENDED 354개 기업을 아래 기준으로 분류:

| 분류 | 설명 | ML 라벨 | 예시 |
|------|------|---------|------|
| **TYPE_A: 재무악화** | 감사의견 거절, 자본잠식, 횡령 등 | ✅ 양성 (1.0) | 금양, 효성화학, 바이온 |
| **TYPE_B: 합병/인수** | 합병 상장폐지, 자진 상장폐지 | ❌ 제외 | HD현대인프라코어, 락앤락 |
| **TYPE_C: 기타** | SPAC 합병, 거래재개 대기 | 개별 판단 | 스팩 기업들 |

분류 방법:
- 1차: `company_type = 'SPAC'` → TYPE_C
- 2차: risk_score < 15 + 대기업 → TYPE_B (합병 가능성)
- 3차: 수동 분류 (공시 확인)

### 4.3 라벨 생성 로직

```python
def create_label(company_id: str, lookforward_months: int = 12) -> float:
    """
    향후 N개월 내 악화 이벤트 발생 여부를 0-1 확률로 반환

    Returns:
        0.0: 악화 없음
        0.3-1.0: 악화 심각도에 따른 가중치
    """
    events = []

    # 1. 거래정지 체크 (TYPE_A만, 합병/자진상폐 제외)
    if check_suspension(company_id, lookforward_months, exclude_merger=True):
        events.append(('suspension', 1.0))

    # 2. 관리종목 체크 (Phase 0에서 KRX 데이터 보강 후 활성화)
    # if check_managed(company_id, lookforward_months):
    #     events.append(('managed', 0.6))

    # 3. 인덱스 급락 체크
    if check_index_drop(company_id, lookforward_months, threshold=0.2):
        events.append(('index_drop', 0.4))

    # 4. 연속 적자 체크
    if check_consecutive_loss(company_id, years=2):
        events.append(('consecutive_loss', 0.3))

    # 최대 가중치 반환 (다중 이벤트 시)
    return max([w for _, w in events]) if events else 0.0
```

### 4.4 시계열 라벨 매트릭스

```
기준시점(T)    T+3M    T+6M    T+9M    T+12M
    ↓           ↓       ↓       ↓        ↓
┌──────────────────────────────────────────┐
│ Features(T) │      Label Window          │
│ X₁, X₂...Xₙ │  → 악화 이벤트 발생?       │
└──────────────────────────────────────────┘
```

---

## 5. 모델 아키텍처

### 5.1 앙상블 구조 (v3.0 업데이트)

> **⚠️ CatBoost 비활성화**: Python 3.14에서 CatBoost가 지원되지 않아 XGBoost + LightGBM 2-모델 앙상블로 구현

```
                    ┌─────────────────┐
                    │   Raw Features  │
                    │    (26개)       │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
       ┌──────────┐                 ┌──────────┐
       │ XGBoost  │                 │LightGBM  │
       │ (순위)   │                 │ (속도)   │
       └────┬─────┘                 └────┬─────┘
            │                            │
            └──────────────┬─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Weighted   │
                    │  Average    │
                    │(AUC 기반)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ 악화확률(%)  │
                    │   0-100     │
                    └─────────────┘
```

**구현된 앙상블 방식**: AUC 기반 가중 평균 (Stacking 대신 단순 가중 평균 적용)

### 5.2 Temporal Split 전략 (v2.0 신규)

**시간적 데이터 누수(Temporal Leakage) 방지**를 위해 시간 기반 분할 사용:

```
┌──────────────────────────────────────────────────────┐
│  2024년 피처(X)  →  2025년 라벨(Y)                     │
│                                                       │
│  Train: 2024 피처 + 2025 라벨 (80%)                   │
│  Validation: 시간순 후반 20%                           │
│  Test: 최신 데이터 holdout                             │
│                                                       │
│  ⚠️ 랜덤 분할 금지! 미래 정보 유입 방지               │
└──────────────────────────────────────────────────────┘
```

- **학습 X (피처)**: 2024년 시점 전체 기업 데이터 (SUSPENDED 포함 — 악화 전 시점의 피처)
- **학습 Y (라벨)**: 2025년에 거래정지(TYPE_A)/적자/인덱스 급락 발생 여부
- **핵심**: SUSPENDED 기업은 학습 시 양성 라벨(Y=1)의 교사 데이터. 추론 시에만 제외.
- **검증**: TimeSeriesSplit 또는 시간순 후반 20% 분리
- **테스트**: 최신 분기 데이터 홀드아웃

### 5.3 하이퍼파라미터 (v3.0 구현 반영)

```python
# config.py에서 정의
XGBOOST_PARAMS = {
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'early_stopping_rounds': 10,
    'scale_pos_weight': 8,      # 클래스 불균형 대응 (~8.3% 양성)
    'random_state': 42,
}

LIGHTGBM_PARAMS = {
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'binary',
    'metric': 'auc',
    'is_unbalance': True,       # 클래스 불균형 대응
    'random_state': 42,
    'verbose': -1,
}

# CatBoost 비활성화 (Python 3.14 미지원)
# CATBOOST_PARAMS = {...}
```

### 5.4 클래스 불균형 처리 전략 (v2.0 보강)

예상 양성 비율: 거래정지(TYPE_A) ~250/3,021 = **~8.3%**

| 전략 | 적용 대상 | 설명 |
|------|----------|------|
| **class_weight / scale_pos_weight** | XGBoost, LightGBM | 기본 전략 (v2.0 추가) |
| **SMOTE** | 학습 데이터 | 소수 클래스 오버샘플링 (ratio=0.5) |
| **Focal Loss** | 대안 | 어려운 샘플에 가중치 집중 |
| **Threshold 조정** | 추론 시 | 0.5 대신 최적 threshold 탐색 |

### 5.5 평가 지표

| 지표 | 목표값 | MVP 기준 | 설명 |
|------|--------|----------|------|
| **AUC-ROC** | ≥ 0.75 | ≥ 0.70 | 분류 성능 |
| **Precision@10%** | ≥ 0.50 | ≥ 0.40 | 상위 10% 정밀도 |
| **Recall** | ≥ 0.70 | ≥ 0.60 | 악화 기업 탐지율 |
| **Brier Score** | ≤ 0.15 | ≤ 0.20 | 확률 보정 정확도 |

### 5.6 거래정지 기업 검증 (Phase 6b) ⭐

> 정량 평가(AUC, Recall)만으로는 부족합니다. 테스트셋에 포함된 거래정지(TYPE_A) 기업을
> **한 건씩 찍어보고** 모델이 실제 악화 기업을 올바르게 탐지하는지 확인합니다.

#### 검증 흐름

```
학습 완료 (Phase 5)
    ↓
정량 평가 (Phase 6a): AUC, Recall 등 숫자 지표
    ↓
거래정지 기업 검증 (Phase 6b):
    ↓
    테스트셋 내 TYPE_A 기업 추출
    ↓
    기업별 예측값 확인
    ┌──────────────────────────────────────────────┐
    │ 기업명       │ 실제 │ 예측   │ 판정          │
    │──────────────│──────│────────│───────────────│
    │ 금양         │ Y=1  │ 87%    │ ✅ 정상 탐지   │
    │ 효성화학     │ Y=1  │ 72%    │ ✅ 정상 탐지   │
    │ 바이온       │ Y=1  │ 30%    │ ❌ 미탐지      │
    │ ○○기업      │ Y=1  │ 15%    │ ❌ 미탐지      │
    └──────────────────────────────────────────────┘
    ↓
    미탐지 기업 오류 분석 → 대응 결정
```

#### 미탐지(False Negative) 대응 판단 기준

| 미탐지 원인 | 분석 방법 | 대응 |
|------------|----------|------|
| **피처 데이터 부족** | 해당 기업의 26개 피처 중 NULL 비율 확인 | 피처 부족 기업은 학습에서 제외, 커버리지 허용 |
| **라벨 오분류** | 해당 기업이 실제 재무악화인지 재확인 (합병/자진상폐?) | suspension_classifications 수정 → 재학습 |
| **피처가 패턴을 못 잡음** | SHAP 분석으로 해당 기업의 피처 기여도 확인 | 피처 추가/조정 검토 → 재학습 |
| **모델 한계** | 유사 패턴 기업이 학습 데이터에 부족 | SMOTE 비율 조정, threshold 하향 검토 |

#### 합격 기준

```python
# Phase 6b 합격 조건
VALIDATION_CRITERIA = {
    # 테스트셋 내 TYPE_A 기업 중 50% 이상에서 예측값 ≥ 0.50
    'min_detection_rate_at_50pct': 0.50,

    # 테스트셋 내 TYPE_A 기업 중 70% 이상에서 예측값 ≥ 0.30
    'min_detection_rate_at_30pct': 0.70,

    # 미탐지(예측 < 0.30) 기업이 전체 TYPE_A의 30% 이하
    'max_false_negative_rate': 0.30,
}
```

#### 불합격 시 반복

```
Phase 6b 불합격
    ↓
    오류 분석 결과에 따라:
    ├─ 라벨 수정 → Phase 0으로 돌아가 재분류 → 재학습
    ├─ 피처 조정 → Phase 2로 돌아가 피처 변경 → 재학습
    └─ 모델 튜닝 → Phase 5로 돌아가 하이퍼파라미터 조정 → 재학습
    ↓
Phase 6a + 6b 재검증
    ↓
합격 시 → Phase 7 배치 추론 진행
```

---

## 6. 파이프라인 구현 계획

### 6.1 디렉토리 구조 (v3.0 실제 구현 반영)

```
backend/ml/
├── __init__.py
├── config.py                    # ✅ 설정값 (피처, 모델, 평가 설정)
├── api/
│   ├── __init__.py
│   └── prediction_routes.py     # ✅ API 라우트 (미사용, app/api/endpoints/ml_predictions.py 사용)
├── data_prep/
│   ├── __init__.py
│   └── classify_suspended.py    # ✅ Phase 0: SUSPENDED 기업 사유 분류
├── features/
│   ├── __init__.py
│   ├── officer_features.py      # ✅ 임원 네트워크 피처 (E01-E10)
│   ├── cb_features.py           # ✅ CB 투자자 피처 (C01-C08)
│   ├── shareholder_features.py  # ✅ 대주주 피처 (S01-S04)
│   ├── index_features.py        # ✅ 4대 인덱스 피처 (I01-I04)
│   ├── feature_store.py         # ✅ 피처 통합 추출 + ml_features 저장
│   ├── resume_feature_store.py  # ✅ 중단된 피처 추출 재개 지원
│   └── batch_processor.py       # ✅ 대량 피처 추출 배치 처리
├── labels/
│   ├── __init__.py
│   └── label_generator.py       # ✅ 라벨 생성 (suspension + loss + index_drop)
├── models/
│   └── __init__.py
├── training/
│   ├── __init__.py
│   ├── trainer.py               # ✅ Phase 5: XGBoost + LightGBM 앙상블 학습
│   ├── evaluator.py             # ✅ Phase 6a+6b: 정량 평가 + 거래정지 기업 검증
│   └── batch_predictor.py       # ✅ Phase 7: 배치 추론 + risk_predictions 저장
├── inference/
│   └── __init__.py
├── evaluation/
│   └── __init__.py
└── saved_models/                # 학습된 모델 저장 (.pkl)
    └── ensemble_*.pkl

backend/app/models/              # ORM 모델 (SQLAlchemy)
├── ml_features.py               # ✅ ml_features 테이블
├── ml_models.py                 # ✅ ml_models 테이블
├── risk_predictions.py          # ✅ risk_predictions 테이블
└── suspension_classifications.py # ✅ suspension_classifications 테이블

backend/app/api/endpoints/
└── ml_predictions.py            # ✅ ML 예측 API (/api/ml/predictions)
```

### 6.2 DB 스키마 추가

```sql
-- 피처 저장 테이블
CREATE TABLE ml_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    feature_date DATE NOT NULL,

    -- 임원 네트워크 피처 (E01-E10)
    exec_count INTEGER,                       -- E01
    exec_turnover_rate NUMERIC(5,4),          -- E02
    exec_avg_tenure NUMERIC(6,2),             -- E03
    exec_other_company_count INTEGER,         -- E04
    exec_avg_other_companies NUMERIC(5,2),    -- E05
    exec_delisted_connection INTEGER,         -- E06
    exec_managed_connection INTEGER,          -- E07
    exec_concurrent_positions INTEGER,        -- E08
    exec_network_density NUMERIC(5,4),        -- E09
    exec_high_risk_ratio NUMERIC(5,4),        -- E10

    -- CB 투자자 피처 (C01-C08)
    cb_count_1y INTEGER,                      -- C01
    cb_total_amount_1y BIGINT,                -- C02
    cb_subscriber_count INTEGER,              -- C03
    cb_high_risk_subscriber_ratio NUMERIC(5,4), -- C04
    cb_subscriber_avg_investments NUMERIC(5,2), -- C05
    cb_loss_company_connections INTEGER,       -- C06
    cb_delisted_connections INTEGER,           -- C07
    cb_repeat_subscriber_ratio NUMERIC(5,4),   -- C08

    -- 대주주 피처 (S01-S04)
    largest_shareholder_ratio NUMERIC(5,2),    -- S01
    shareholder_change_1y NUMERIC(6,2),        -- S02
    related_party_ratio NUMERIC(5,2),          -- S03
    shareholder_count INTEGER,                 -- S04

    -- 4대 인덱스 (I01-I04)
    cei_score NUMERIC(5,2),                    -- I01
    cgi_score NUMERIC(5,2),                    -- I02
    rii_score NUMERIC(5,2),                    -- I03
    mai_score NUMERIC(5,2),                    -- I04

    -- 메타데이터
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id, feature_date)
);

-- 예측 결과 저장 테이블
CREATE TABLE risk_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    prediction_date DATE NOT NULL,

    -- 예측 결과
    deterioration_probability NUMERIC(5,4) NOT NULL,  -- 0.0000 ~ 1.0000
    risk_level VARCHAR(20) NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    confidence_score NUMERIC(5,4),

    -- 피처 중요도 (SHAP)
    top_risk_factors JSONB,  -- [{"feature": "cb_count_1y", "contribution": 0.15}, ...]

    -- 모델 정보
    model_version VARCHAR(50) NOT NULL,
    feature_snapshot_id UUID REFERENCES ml_features(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id, prediction_date, model_version)
);

-- 모델 메타데이터 테이블
CREATE TABLE ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version VARCHAR(50) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,  -- 'ensemble_xgb_lgb_cat'

    -- 성능 지표
    auc_roc NUMERIC(5,4),
    precision_at_10 NUMERIC(5,4),
    recall NUMERIC(5,4),
    brier_score NUMERIC(5,4),

    -- 학습 정보
    training_samples INTEGER,
    positive_samples INTEGER,    -- v2.0: 양성 라벨 수
    feature_count INTEGER,
    training_date DATE,

    -- 모델 파일
    model_path TEXT,  -- backend/ml/saved_models/{version}_{type}_{date}.pkl

    -- 상태
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 거래정지 사유 분류 테이블 (v2.0 신규)
CREATE TABLE suspension_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    suspension_type VARCHAR(20) NOT NULL,  -- TYPE_A, TYPE_B, TYPE_C
    suspension_reason TEXT,                -- 거래정지 사유 상세
    classified_by VARCHAR(50),             -- 'auto' 또는 'manual'
    classified_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id)
);

-- 인덱스
CREATE INDEX idx_ml_features_company_date ON ml_features(company_id, feature_date);
CREATE INDEX idx_risk_predictions_company ON risk_predictions(company_id, prediction_date);
CREATE INDEX idx_risk_predictions_level ON risk_predictions(risk_level);
CREATE INDEX idx_suspension_class_type ON suspension_classifications(suspension_type);
```

### 6.3 구현 단계별 계획 (v3.0 구현 완료 반영)

| 단계 | 작업 | 산출물 | 상태 |
|------|------|--------|------|
| **Phase 0** | 데이터 준비 | SUSPENDED 사유 분류 (`classify_suspended.py`) | ✅ 완료 |
| **Phase 1** | DB 스키마 생성 + ML 의존성 설치 | 4개 ORM 모델, requirements.txt | ✅ 완료 |
| **Phase 2** | 피처 추출 모듈 | `features/*.py` (26개 피처) | ✅ 완료 |
| **Phase 3** | 라벨 생성 모듈 | `labels/label_generator.py` | ✅ 완료 |
| **Phase 4** | 피처 스토어 구축 | `feature_store.py` + ml_features 테이블 | ✅ 완료 |
| **Phase 5** | 모델 학습 (Temporal Split) | `trainer.py` (XGBoost + LightGBM) | ✅ 완료 |
| **Phase 6a** | 정량 평가 | `evaluator.py` (AUC, Recall, Precision@10%) | ✅ 완료 |
| **Phase 6b** | 거래정지 기업 검증 | `evaluator.py` (TYPE_A 탐지율 검증) | ✅ 완료 |
| **Phase 7** | 배치 추론 + DB 저장 | `batch_predictor.py` → risk_predictions | ✅ 완료 |
| **Phase 8** | 조회 API | `GET /api/ml/predictions/{company_id}` | ✅ 완료 |

### 6.4 실행 방법

```bash
# Phase 0: SUSPENDED 기업 분류
cd backend
DATABASE_URL="postgresql://..." python -m ml.data_prep.classify_suspended

# Phase 4: 피처 스토어 구축
DATABASE_URL="postgresql://..." python -m ml.features.feature_store

# Phase 5: 모델 학습
DATABASE_URL="postgresql://..." python -m ml.training.trainer

# Phase 6: 평가
DATABASE_URL="postgresql://..." python -m ml.training.evaluator

# Phase 7: 배치 추론
DATABASE_URL="postgresql://..." python -m ml.training.batch_predictor
```

### 6.5 필요 Python 패키지 (v3.0 업데이트)

```txt
# ML Core
scikit-learn>=1.4.0
xgboost>=2.0.0
lightgbm>=4.0.0
# catboost>=1.2.0  # ⚠️ Python 3.14 미지원으로 비활성화

# 클래스 불균형
imbalanced-learn>=0.12.0

# 설명 가능성
shap>=0.44.0        # 선택적 (현재 미사용)

# 모델 직렬화
joblib>=1.3.0

# 데이터 처리
pandas>=2.1.0
numpy>=1.26.0
```

> **참고**: CatBoost는 Python 3.14에서 지원되지 않아 2-모델 앙상블(XGBoost + LightGBM)로 구현됨

---

## 7. 배치 추론 + DB 저장 (Phase 7) ⭐

> **이 섹션이 ML 파이프라인의 핵심 산출물입니다.**
> 학습된 모델로 현재 DB의 전체 LISTED 기업을 추론하고, 결과(악화확률 %)를 `risk_predictions` 테이블에 저장합니다.

### 7.1 배치 추론 흐름

```
┌──────────────────────────────────────────────────────────────┐
│  batch_predictor.py 실행 흐름                                 │
│                                                               │
│  1. 활성 모델 로드                                            │
│     └─ ml_models WHERE is_active = TRUE                      │
│     └─ saved_models/{version}_ensemble_{date}.pkl            │
│                                                               │
│  2. 대상 기업 조회                                            │
│     └─ companies WHERE listing_status = 'LISTED'             │
│        AND company_type IN ('NORMAL', 'SPAC', 'REIT')        │
│     └─ 약 3,021개 기업                                       │
│                                                               │
│  3. 기업별 피처 추출 (26개)                                   │
│     └─ ml_features 테이블에서 최신 snapshot 조회              │
│     └─ 없으면 실시간 계산 후 ml_features INSERT              │
│                                                               │
│  4. 모델 추론                                                 │
│     └─ ensemble.predict_proba(features) → 0.0000 ~ 1.0000   │
│     └─ SHAP values 계산 → top_risk_factors                   │
│                                                               │
│  5. 결과 DB 저장                                              │
│     └─ risk_predictions 테이블 UPSERT                        │
│        (company_id, prediction_date, model_version) UNIQUE   │
│                                                               │
│  6. 실행 보고서 출력                                          │
│     └─ 추론 기업 수, 등급 분포, 소요 시간                     │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 배치 추론 스크립트 설계

**파일**: `backend/ml/inference/batch_predictor.py`

```python
class BatchPredictor:
    """전체 LISTED 기업 배치 추론 + risk_predictions DB 저장"""

    def __init__(self, db_session, model_path: str = None):
        self.db = db_session
        self.model = self._load_active_model(model_path)
        self.feature_extractor = FeatureStore(db_session)

    def run_batch_prediction(self, prediction_date: date = None) -> dict:
        """
        전체 기업 배치 추론 실행

        Returns:
            {
                "total_companies": 3021,
                "predicted": 2987,
                "skipped": 34,  # 피처 부족
                "distribution": {"LOW": 1823, "MEDIUM": 892, "HIGH": 287, "CRITICAL": 98},
                "model_version": "v1.0.0"
            }
        """
        prediction_date = prediction_date or date.today()

        # 1. 대상 기업 조회 (LISTED만)
        companies = self._get_target_companies()

        # 2. 기업별 추론 + 저장
        results = []
        for company in companies:
            try:
                result = self._predict_single(company, prediction_date)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"추론 실패: {company.name} - {e}")

        # 3. 배치 INSERT/UPSERT
        self._save_predictions(results)

        # 4. 실행 보고서 반환
        return self._generate_report(results, len(companies))

    def _get_target_companies(self) -> list:
        """추론 대상: 현재 정상 거래 중인 LISTED 기업만

        Note: SUSPENDED 기업은 학습 시 양성 라벨(Y=1)로 사용되지만,
              추론 시에는 이미 악화된 기업이므로 예측 대상에서 제외.
        """
        return self.db.query(Company).filter(
            Company.listing_status == 'LISTED',
            Company.company_type.in_(['NORMAL', 'SPAC', 'REIT']),
            Company.trading_status != 'SUSPENDED',
        ).all()

    def _predict_single(self, company, prediction_date) -> dict:
        """단일 기업 추론"""
        # 피처 추출 (ml_features 테이블에서 최신 또는 실시간 계산)
        features = self.feature_extractor.get_features(company.id)
        if features is None:
            return None  # 피처 부족 → skip

        # 모델 추론
        prob = self.model.predict_proba(features)[0]  # 0.0 ~ 1.0
        risk_level = self._get_risk_level(prob)

        # SHAP 기반 주요 위험 요인
        top_factors = self._get_top_factors(features, top_n=5)

        return {
            'company_id': company.id,
            'prediction_date': prediction_date,
            'deterioration_probability': round(prob, 4),
            'risk_level': risk_level,
            'confidence_score': self._calculate_confidence(features),
            'top_risk_factors': top_factors,
            'model_version': self.model.version,
        }

    def _save_predictions(self, results: list):
        """risk_predictions 테이블에 UPSERT"""
        for r in results:
            stmt = insert(RiskPrediction).values(**r)
            stmt = stmt.on_conflict_do_update(
                index_elements=['company_id', 'prediction_date', 'model_version'],
                set_={
                    'deterioration_probability': r['deterioration_probability'],
                    'risk_level': r['risk_level'],
                    'confidence_score': r['confidence_score'],
                    'top_risk_factors': r['top_risk_factors'],
                }
            )
            self.db.execute(stmt)
        self.db.commit()

    @staticmethod
    def _get_risk_level(prob: float) -> str:
        if prob >= 0.70: return 'CRITICAL'
        if prob >= 0.50: return 'HIGH'
        if prob >= 0.30: return 'MEDIUM'
        return 'LOW'
```

### 7.3 실행 방법

```bash
# CLI 실행 (모델 학습 완료 후)
cd backend
python -m ml.inference.batch_predictor

# 특정 날짜 기준 추론
python -m ml.inference.batch_predictor --date 2026-02-05

# dry-run (DB 저장 없이 결과만 확인)
python -m ml.inference.batch_predictor --dry-run

# 특정 모델 버전 지정
python -m ml.inference.batch_predictor --model-version v1.0.0
```

### 7.4 실행 트리거

| 트리거 | 시점 | 설명 |
|--------|------|------|
| **모델 학습 완료 직후** | Phase 5-6 완료 시 | 학습 → 평가 통과 → 자동 배치 추론 |
| **분기별 정기 실행** | 분기 데이터 적재 후 | 새 피처 데이터로 재추론 |
| **수동 실행** | 필요 시 | 모델 교체, 긴급 업데이트 등 |

### 7.5 DB 저장 결과 예시

배치 추론 완료 후 `risk_predictions` 테이블 상태:

```sql
SELECT c.name, c.ticker,
       rp.deterioration_probability,
       rp.risk_level,
       rp.top_risk_factors->0->>'feature' AS top_factor,
       rp.prediction_date
FROM risk_predictions rp
JOIN companies c ON c.id = rp.company_id
WHERE rp.model_version = 'v1.0.0'
ORDER BY rp.deterioration_probability DESC
LIMIT 5;
```

```
name          | ticker | deterioration_probability | risk_level | top_factor              | prediction_date
--------------+--------+--------------------------+------------+-------------------------+----------------
디피코         | 066790 | 0.8734                   | CRITICAL   | cb_count_1y             | 2026-02-05
한창           | 005765 | 0.7621                   | CRITICAL   | exec_delisted_connection| 2026-02-05
○○기업        | 012345 | 0.6512                   | HIGH       | cb_high_risk_sub_ratio  | 2026-02-05
△△기업        | 067890 | 0.4231                   | MEDIUM     | exec_turnover_rate      | 2026-02-05
삼성전자       | 005930 | 0.0312                   | LOW        | mai_score               | 2026-02-05
```

### 7.6 실행 보고서

배치 추론 완료 시 자동 출력:

```
========================================
 배치 추론 완료 보고서
========================================
 모델: v1.0.0 (ensemble_xgb_lgb_cat)
 실행일: 2026-02-05
 대상: LISTED 3,021개 기업
----------------------------------------
 추론 성공: 2,987개 (98.9%)
 피처 부족 스킵: 34개 (1.1%)
----------------------------------------
 등급 분포:
   LOW      (0-30%):  1,823개 (61.0%)
   MEDIUM   (30-50%):   692개 (23.2%)
   HIGH     (50-70%):   374개 (12.5%)
   CRITICAL (70-100%):   98개 ( 3.3%)
----------------------------------------
 risk_predictions 테이블: 2,987건 UPSERT 완료
 소요 시간: -
========================================
```

---

## 8. API 설계 (v3.0 구현 완료)

> **구현 파일**: `backend/app/api/endpoints/ml_predictions.py`

### 8.1 예측 결과 조회 API (단일 기업)

```
GET /api/ml/predictions/{company_id}
```

**Response:**
```json
{
  "company_id": "uuid",
  "company_name": "삼성전자",
  "ticker": "005930",
  "prediction_date": "2026-02-05",
  "deterioration_probability": 0.23,
  "risk_level": "LOW",
  "model_version": "v1.0.0"
}
```

### 8.2 예측 결과 목록 조회 API (페이징)

```
GET /api/ml/predictions?page=1&limit=20&risk_level=HIGH&min_prob=0.5
```

**Query Parameters:**
- `page`: 페이지 번호 (기본: 1)
- `limit`: 결과 수 (기본: 20, 최대: 100)
- `risk_level`: 위험 등급 필터 (LOW, MEDIUM, HIGH, CRITICAL)
- `min_prob`: 최소 확률 필터 (0~1)

**Response:**
```json
{
  "total": 287,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "company_id": "uuid",
      "company_name": "디피코",
      "ticker": "066790",
      "prediction_date": "2026-02-05",
      "deterioration_probability": 0.8734,
      "risk_level": "CRITICAL",
      "model_version": "v1.0.0"
    }
  ]
}
```

### 8.3 고위험 기업 목록 API

```
GET /api/ml/predictions/high-risk?limit=20&min_prob=0.5
```

**Response:**
```json
[
  {
    "company_id": "uuid",
    "company_name": "디피코",
    "ticker": "066790",
    "market": "KOSDAQ",
    "deterioration_probability": 0.8734,
    "risk_level": "CRITICAL"
  }
]
```

---

## 8. 프론트엔드 UI 설계

### 8.1 악화확률 표시 컴포넌트

```typescript
interface DeteriorationBadge {
  probability: number;  // 0-100
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  topFactors: RiskFactor[];
}

// 위험 단계별 색상
const RISK_COLORS = {
  LOW: '#22C55E',      // 초록 (0-30%)
  MEDIUM: '#F59E0B',   // 주황 (30-50%)
  HIGH: '#EF4444',     // 빨강 (50-70%)
  CRITICAL: '#7C2D12', // 진한 빨강 (70-100%)
};
```

### 8.2 UI 배치

```
┌─────────────────────────────────────────┐
│  기업 상세 페이지                        │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │ 현재 리스크  │  │ 악화가능성 예측  │  │
│  │   등급      │  │                 │  │
│  │  MEDIUM     │  │     73%        │  │
│  │  (35점)     │  │   [높음]       │  │
│  └─────────────┘  └─────────────────┘  │
│                                         │
│  주요 위험 요인:                         │
│  • CB 발행 빈도 높음 (+18%)             │
│  • 상장폐지 기업 연결 다수 (+12%)        │
│  • M&A취약성 지수 양호 (-8%)            │
│                                         │
└─────────────────────────────────────────┘
```

---

## 9. 운영 및 모니터링

### 9.1 재학습 주기

| 트리거 | 주기 | 조건 |
|--------|------|------|
| **정기 재학습** | 분기별 | 새 분기 데이터 적재 후 |
| **성능 저하** | 즉시 | AUC < 0.70 감지 시 |
| **대규모 이벤트** | 수동 | 금융위기 등 시장 급변 |

### 9.2 모델 저장 전략 (v3.0 업데이트)

```
backend/ml/saved_models/
├── ensemble_v20260205_123456.pkl   # 앙상블 모델 (XGBoost + LightGBM + 메트릭스)
└── ...
```

**저장 형식** (joblib):
```python
{
    'models': {
        'xgboost': XGBClassifier,
        'lightgbm': LGBMClassifier,
    },
    'metrics': {
        'xgboost_auc': 0.xx,
        'lightgbm_auc': 0.xx,
        'ensemble_auc': 0.xx,
        ...
    },
    'feature_names': [...],
    'config': {...},
    'created_at': 'ISO8601',
}
```

- **직렬화**: `joblib.dump()` / `joblib.load()`
- **버전 관리**: `ml_models` 테이블에서 `is_active = TRUE`인 모델만 서빙
- **배포**: Railway 빌드 시 `saved_models/` 디렉토리 포함

### 9.3 모니터링 대시보드

```
┌─────────────────────────────────────────────────┐
│            ML 모델 모니터링 대시보드             │
├─────────────────────────────────────────────────┤
│                                                 │
│  현재 모델: v1.0.0 (2026-02-01 학습)            │
│                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  AUC-ROC   │ │ Precision   │ │  Recall   │ │
│  │   0.78     │ │    0.52     │ │   0.71    │ │
│  │  (목표:75) │ │  (목표:50)  │ │ (목표:70) │ │
│  └─────────────┘ └─────────────┘ └───────────┘ │
│                                                 │
│  최근 예측 분포:                                 │
│  LOW: 1,823 (59%) | MEDIUM: 892 (29%)          │
│  HIGH: 287 (9%)   | CRITICAL: 98 (3%)          │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 10. 리스크 및 한계점

### 10.1 데이터 한계 (DB 검증 반영)

| 한계 | 영향 | 대응 방안 | 상태 |
|------|------|----------|------|
| 관리종목 데이터 전무 (`is_managed` 전부 'N') | 라벨 비활성화 | KRX 데이터 보강 (Phase 0) | ❌ 미해결 |
| 상장폐지 기업 삭제 (774건, 피처 0) | 라벨 사용 불가 | SUSPENDED를 최고 수준 라벨로 대체 | ✅ 대체 |
| officer_positions 날짜 데이터 부족 (19%) | E02/E03 정확도 저하 | 보고서별 변동 proxy 사용 | ⚠️ 우회 |
| dispute_officers officer_id 전수 NULL | 임원 단위 분쟁 비율 불가 | 피처 제거 (CSV에서 미포함) | ✅ 해결 |
| RaymondsIndex 2개년만 유의미 | YoY 1회만 비교 가능 | 분기별 축적으로 해결 | ⚠️ 시간 필요 |
| SUSPENDED 기업 합병/악성 미분류 | 라벨 오염 | Phase 0에서 사유 분류 | ❌ 미해결 |
| major_shareholders 2024년 커버리지 낮음 (1,172개사) | S02 계산 범위 제한 | `previous_share_ratio` 컬럼 활용 | ⚠️ 우회 |

### 10.2 모델 한계

| 한계 | 설명 | 대응 방안 |
|------|------|----------|
| 외부 충격 미반영 | 금리, 환율 등 매크로 | 외부 데이터 연동 검토 |
| 블랙스완 이벤트 | 예측 불가능한 급변 | 불확실성 구간 표시 |
| 해석 가능성 | 앙상블 모델 복잡성 | SHAP 기반 설명 |
| 시간적 데이터 누수 | 미래 정보 유입 위험 | Temporal Split 적용 (5.2절) |

### 10.3 서비스 품질 이슈 (v2.0 발견)

| 이슈 | 영향 | 권장 조치 |
|------|------|----------|
| SUSPENDED 기업이 RaymondsIndex 스크리너에 A등급으로 표시 | 투자자 오해 | 거래정지 배지 표시 또는 필터링 |
| SUSPENDED 기업이 "주의 필요 기업"에 표시 | 무의미한 정보 | 거래정지 기업 제외 처리 |
| 기업 상세 페이지에 거래정지 상태 미표시 | 정보 부족 | trading_status 배지 추가 |

---

## 11. 결론 및 다음 단계

### 11.1 데이터 가용성 검증 결과 (v2.0 업데이트)

| 항목 | 상태 | 비고 |
|------|------|------|
| 임원 네트워크 데이터 | ✅ 충분 | 49,446명, 75,059 포지션 |
| CB 투자자 데이터 | ✅ 충분 | 643 발행사, 7,021 인수자 |
| 대주주 데이터 | ✅ 충분 | 60,214건 (`is_related_party` 활용) |
| 4대 인덱스 | ✅ 충분 | 5,354건 (2024-2025 YoY 가능) |
| 라벨 (거래정지) | ✅ 핵심 라벨 | 354건 (사유 분류 후 ~250건 양성) |
| 라벨 (연속 적자) | ✅ 사용 가능 | 473건 |
| 라벨 (인덱스 급락) | ✅ 사용 가능 | 2,550건 YoY 비교 가능 |
| 라벨 (관리종목) | ❌ 보강 필요 | 전체 is_managed='N' → KRX 데이터 수집 |
| Neo4j 동기화 | ⚠️ 확인 필요 | CRITICAL 피처 5개가 Neo4j 의존 |

### 11.2 구현 완료 현황 (v3.0)

| Phase | 상태 | 구현 파일 |
|-------|------|----------|
| **Phase 0** | ✅ 완료 | `ml/data_prep/classify_suspended.py` |
| **Phase 1** | ✅ 완료 | `app/models/ml_*.py`, `requirements.txt` |
| **Phase 2** | ✅ 완료 | `ml/features/*.py` (4개 추출기) |
| **Phase 3** | ✅ 완료 | `ml/labels/label_generator.py` |
| **Phase 4** | ✅ 완료 | `ml/features/feature_store.py` |
| **Phase 5** | ✅ 완료 | `ml/training/trainer.py` |
| **Phase 6a** | ✅ 완료 | `ml/training/evaluator.py` |
| **Phase 6b** | ✅ 완료 | `ml/training/evaluator.py` |
| **Phase 7** | ✅ 완료 | `ml/training/batch_predictor.py` |
| **Phase 8** | ✅ 완료 | `app/api/endpoints/ml_predictions.py` |

### 11.3 성공 기준

| 지표 | 목표 | MVP 기준 | 상태 |
|------|------|----------|------|
| AUC-ROC | ≥ 0.75 | ≥ 0.70 | 🔄 학습 실행 필요 |
| 예측 지연 | < 100ms | < 500ms | ✅ DB 조회 방식 |
| 커버리지 | 3,000+ 기업 | 2,000+ 기업 | ✅ 3,021개 지원 |

### 11.4 다음 단계

1. **프로덕션 학습 실행**: 실제 데이터로 모델 학습 및 평가
2. **프론트엔드 연동**: risk-web, index-web에서 예측 결과 표시
3. **모니터링 대시보드**: 관리자 페이지에 모델 성능 지표 표시
4. **분기별 재학습 자동화**: 새 분기 데이터 적재 후 자동 재학습

---

## 부록 A: 피처 정의서 참조

> 피처 상세 정의는 `RaymondsRisk_ML_Feature_Selection.csv` 파일 참조
> - 피처 ID 체계: E(임원), C(CB), S(대주주), I(인덱스)
> - 중요도: CRITICAL > HIGH > MEDIUM > LOW

---

*문서 작성: 2026-02-05 | v3.0 수정: 2026-02-08 (전체 파이프라인 구현 완료 반영)*
*다음 업데이트: 프로덕션 학습 실행 후 (실제 성능 지표 반영)*
