# ML 파이프라인 결함 및 개선사항 보고서

**작성일**: 2026-02-08
**버전**: v1.0
**작성자**: Claude Code Analysis

---

## 1. 요약

### 1.1 현재 모델 성능

| 지표 | 실제 값 | MVP 기준 | 상태 |
|------|---------|---------|------|
| AUC-ROC | 0.8142 | ≥ 0.70 | ✅ 통과 |
| Precision@10% | 0.7049 | ≥ 0.50 | ✅ 통과 |
| Recall | 0.7826 | ≥ 0.70 | ✅ 통과 |
| Brier Score | 0.1773 | ≤ 0.25 | ✅ 통과 |

### 1.2 핵심 결함 요약

| 심각도 | 결함 | 영향 |
|--------|------|------|
| 🔴 **CRITICAL** | `shareholder_change_1y` 100% NULL | 피처 완전 비활성화 |
| 🔴 **CRITICAL** | `exec_managed_connection` 분산 없음 | 피처 의미 없음 (전부 0) |
| 🟠 **HIGH** | `exec_avg_tenure` 65.3% NULL | 피처 신뢰도 저하 |
| 🟠 **HIGH** | `related_party_ratio` 48.1% NULL | 피처 커버리지 부족 |
| 🟡 **MEDIUM** | Index 피처 ~15% NULL | 일부 기업 데이터 누락 |

---

## 2. 상세 결함 분석

### 2.1 데이터 품질 결함

#### 🔴 [CRITICAL-1] shareholder_change_1y: 100% NULL

**원인 분석**:
```python
# shareholder_features.py:51-63
def _shareholder_change_1y(self, company_id: str) -> Optional[float]:
    """S02: 최대주주 지분 변동폭 (current - previous, %p)"""
    result = self.conn.execute(text("""
        SELECT share_ratio - previous_share_ratio as change_1y
        FROM major_shareholders
        WHERE company_id = :cid
          AND is_largest_shareholder = TRUE
          AND previous_share_ratio IS NOT NULL  -- ⚠️ 이 조건에서 모두 필터링됨
    """))
```

**근본 원인**: `major_shareholders.previous_share_ratio` 컬럼이 파싱 단계에서 적재되지 않음

**영향**:
- 피처 설계에서 "중요도: HIGH"로 지정된 피처가 완전 비활성화
- 최대주주 지분 변동이라는 핵심 위험 시그널 누락
- 모델이 대주주 안정성 변화를 감지하지 못함

**해결 방안**:
1. `major_shareholders` 파서에서 전분기/전년 동기 지분율 비교 로직 추가
2. 또는: 같은 기업의 이전 보고서에서 지분율 조회하여 계산

---

#### 🔴 [CRITICAL-2] exec_managed_connection: 분산 없음 (전부 0)

**원인 분석**:
```python
# officer_features.py:129-144
def _exec_managed_connection(self, company_id: str) -> Optional[int]:
    """E07: 임원이 재직했던 관리종목 기업 수"""
    result = self.conn.execute(text("""
        ...
        WHERE c.is_managed = 'Y'  -- ⚠️ is_managed가 항상 'N'
    """))
```

**근본 원인**: `companies.is_managed` 컬럼이 항상 'N'으로 설정됨. 관리종목 정보 수집이 이루어지지 않음.

**영향**:
- 관리종목 연결 피처가 상수값(0)이 되어 모델에 정보 제공 불가
- 임원 네트워크 분석에서 중요한 위험 신호 누락

**해결 방안**:
1. KRX 관리종목 목록 수집 스크립트 구현
2. companies 테이블 is_managed 컬럼 주기적 업데이트

---

#### 🟠 [HIGH-1] exec_avg_tenure: 65.3% NULL

**원인 분석**:
```python
# officer_features.py:77-88
def _exec_avg_tenure(self, company_id: str) -> Optional[float]:
    result = self.conn.execute(text("""
        SELECT AVG(...)
        FROM officer_positions
        WHERE term_start_date IS NOT NULL  -- ⚠️ 65%가 NULL
          AND is_current = TRUE
    """))
```

**근본 원인**: `officer_positions.term_start_date` 파싱 미흡
- 사업보고서에서 취임일 정보 추출 실패
- "YYYY년 MM월" 형식 외 다른 형식 미지원

**영향**:
- 1,974개 기업의 평균 재직기간 피처 누락
- 임원 안정성 평가 정확도 저하

**해결 방안**:
1. 임원 파서에서 취임일 추출 패턴 확장
2. 연임/재선임 정보 활용하여 추정

---

#### 🟠 [HIGH-2] related_party_ratio: 48.1% NULL

**원인 분석**:
```python
# shareholder_features.py:65-76
def _related_party_ratio(self, company_id: str) -> Optional[float]:
    result = self.conn.execute(text("""
        SELECT SUM(share_ratio)
        FROM major_shareholders
        WHERE is_related_party = TRUE  -- ⚠️ 플래그 미설정
    """))
```

**근본 원인**: `major_shareholders.is_related_party` 플래그가 파싱 시 설정되지 않음

**영향**:
- 특수관계인 지분 집중도 분석 불가
- 지배구조 위험 평가 정확도 저하

---

#### 🟡 [MEDIUM-1] Index 피처 ~15% NULL

- `cei_score`: 14.7% NULL
- `cgi_score`: 14.7% NULL
- `rii_score`: 14.7% NULL
- `mai_score`: 14.7% NULL

**원인**: RaymondsIndex 계산 대상에서 제외된 기업 (SPAC, REIT, 재무데이터 부족 등)

**영향**: 허용 가능한 수준이나, NULL 대체 전략 필요

---

### 2.2 피처 설계 결함

#### [DESIGN-1] 피처 중요도 vs 실제 기여도 불일치

**피처 셀렉션 문서의 중요도**:
| 피처 | 설계 중요도 | 실제 상태 |
|------|------------|----------|
| shareholder_change_1y | HIGH | 100% NULL (비활성) |
| largest_shareholder_ratio | CRITICAL | 23.6% NULL |
| exec_managed_connection | HIGH | 분산 0 (상수) |

**문제점**: 중요도가 높은 피처일수록 데이터 품질 이슈가 심각

---

#### [DESIGN-2] NULL 처리 전략 부재

**현재 상태**:
- XGBoost/LightGBM은 NULL 자체 처리 가능
- 하지만 65%+ NULL인 피처는 사실상 정보량 부족

**권장**:
```python
# 피처별 NULL 임계치 적용
MAX_NULL_RATE = 0.30  # 30% 초과 시 경고
FEATURE_DISABLE_THRESHOLD = 0.80  # 80% 초과 시 비활성화
```

---

#### [DESIGN-3] Temporal Leakage 점검 필요

**설계**: 2024년 피처 → 2025년 라벨 (Temporal Split)

**잠재 문제점**:
1. `is_current = TRUE` 조건이 현재 시점 기준
2. 일부 인덱스 피처가 2024년 외 연도 참조 가능

**권장**: 피처 추출 시점 파라미터화 및 Temporal Validation 강화

---

### 2.3 모델 아키텍처 결함

#### [MODEL-1] CatBoost 비활성화

**원인**: Python 3.14 호환성 이슈 (catboost 미지원)

**영향**:
- 3-모델 앙상블 → 2-모델 앙상블로 축소
- 범주형 피처 활용도 저하 (CatBoost 특화 기능 미사용)

**대안**: Python 3.13 다운그레이드 또는 catboost 업데이트 대기

---

#### [MODEL-2] 앙상블 가중치 고정

**현재 방식**:
```python
# AUC 기반 가중 평균
weights = np.array([xgb_auc, lgb_auc])
final_proba = np.average([xgb_proba, lgb_proba], weights=weights)
```

**개선 가능**:
- Stacking Ensemble로 전환
- 검증 세트 기반 동적 가중치 학습

---

## 3. 예측 결과 분포 분석

### 3.1 리스크 등급 분포

| 등급 | 확률 범위 | 기업 수 | 비율 |
|------|----------|--------|------|
| CRITICAL | 70%+ | 887 | 29.4% |
| HIGH | 50-70% | 233 | 7.7% |
| MEDIUM | 30-50% | 283 | 9.4% |
| LOW | 0-30% | 1,618 | 53.6% |

### 3.2 거래정지 기업 탐지율

```
CRITICAL 등급 887개 중:
- NORMAL 거래: 582개 (65.6%)
- SUSPENDED: 305개 (34.4%)

전체 SUSPENDED 기업 중:
- CRITICAL 분류: 86.2%
- TYPE_A (재무악화) 중 CRITICAL: 92.8%
```

### 3.3 분포 이상 여부

- **CRITICAL 29.4%는 과다**: 일반적으로 고위험 등급은 5-10% 권장
- **원인 추정**: 불완전한 피처로 인해 판별력 저하, 높은 확률로 수렴

---

## 4. 우선순위별 개선 권장사항

### 🔴 긴급 (P0) - 피처 데이터 복구

| # | 작업 | 기대 효과 | 예상 난이도 |
|---|------|----------|------------|
| 1 | `previous_share_ratio` 파싱 추가 | shareholder_change_1y 활성화 | 중 |
| 2 | KRX 관리종목 수집 | exec_managed_connection 활성화 | 중 |
| 3 | 임원 취임일 파싱 개선 | exec_avg_tenure NULL 감소 | 상 |

### 🟠 중요 (P1) - 품질 개선

| # | 작업 | 기대 효과 |
|---|------|----------|
| 4 | `is_related_party` 플래그 파싱 | related_party_ratio 활성화 |
| 5 | `is_largest_shareholder` 정확도 향상 | 최대주주 피처 커버리지 증가 |
| 6 | NULL 대체 전략 구현 (Imputation) | 모델 안정성 향상 |

### 🟡 권장 (P2) - 구조 개선

| # | 작업 | 기대 효과 |
|---|------|----------|
| 7 | Temporal Validation 강화 | Leakage 방지 |
| 8 | Stacking Ensemble 도입 | 앙상블 성능 향상 |
| 9 | 리스크 등급 임계치 재조정 | CRITICAL 비율 정상화 |
| 10 | 피처 중요도 재평가 | 실제 기여도 기반 정렬 |

---

## 5. 재학습 로드맵

### Phase 1: 데이터 복구 (1-2주)
1. `shareholder_change_1y` 피처 복구
2. `exec_managed_connection` 피처 복구
3. NULL 비율 50% 초과 피처 비활성화 또는 Imputation

### Phase 2: 재학습 (3-5일)
1. 복구된 피처로 피처 스토어 재구축
2. 모델 재학습 및 성능 비교
3. A/B 테스트 (기존 모델 vs 신규 모델)

### Phase 3: 모니터링 (지속)
1. 피처 품질 대시보드 구축
2. NULL 비율 알림 설정
3. 분기별 피처 재평가

---

## 6. 결론

현재 ML 파이프라인은 MVP 성능 기준을 충족하지만, **26개 피처 중 2개가 완전 비활성화**(shareholder_change_1y, exec_managed_connection)되어 있고, **추가 2개가 50% 이상 NULL**(exec_avg_tenure, related_party_ratio)입니다.

이는 설계 시 의도한 피처 기여도의 약 20%가 손실된 상태이며, 데이터 파이프라인 개선을 통해 모델 성능을 추가로 5-10% 향상시킬 수 있을 것으로 예상됩니다.

**즉각적인 조치**: P0 작업 3개를 우선 진행하여 핵심 피처를 복구하고, 복구된 피처로 모델을 재학습하는 것을 권장합니다.
