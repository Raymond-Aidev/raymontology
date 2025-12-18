# 데이터 파싱 및 적재 상태 (2025-12-09 최종)

## 현재 DB 상태

| 테이블 | 레코드 수 | 목표 | 상태 | 비고 |
|--------|----------|------|------|------|
| companies | 3,922 | 3,922 | ✅ 완료 | 상장사 전체 |
| officers | 38,125 | ~40,000 | ✅ 완료 | 95% 달성 |
| officer_positions | 240,320 | ~250,000 | ✅ 완료 | 96% 달성 |
| disclosures | 206,767 | ~228,000 | ✅ 완료 | 91% 달성 |
| convertible_bonds | 1,435 | ~1,700 | ✅ 완료 | 84% 달성 |
| cb_subscribers | 8,656 | ~10,000 | ✅ 완료 | 87% 달성 |
| financial_statements | 9,432 | ~12,000 | ✅ 완료 | 79% 달성 |
| risk_signals | 1,412 | N/A | ✅ 완료 | 5개 패턴 적용 |
| risk_scores | 3,912 | 3,922 | ✅ 완료 | 99.7% 회사 커버 |
| major_shareholders | 1,130 | N/A | ✅ 완료 | 사업보고서 기준 |
| affiliates | 1,245 | N/A | ✅ 완료 | 계열회사 연결 |

---

## 완료된 작업 내역

### Phase 1: 기본 데이터 적재
- [x] companies: 3,922개 상장사 등록
- [x] disclosures: 206,767건 공시 메타데이터 적재
- [x] officers: 38,125명 임원 정보 파싱
- [x] officer_positions: 240,320건 임원 직책 이력

### Phase 2: CB 데이터 적재
- [x] convertible_bonds: 1,435건 전환사채 발행 정보
- [x] cb_subscribers: 8,656건 CB 인수인 정보

### Phase 3: 재무 데이터 적재
- [x] financial_statements: 9,432건 재무제표
  - 2022-2024: 사업보고서 (연간)
  - 2025: 반기보고서 (Q2)

### Phase 4: 리스크 분석 데이터
- [x] risk_signals: 1,412건 (5개 패턴)
  - CB_NETWORK_CLUSTER: 180건
  - SERIAL_CB_ISSUER: 497건
  - SERIAL_CB_INVESTOR: 83건
  - CONNECTED_LOSS_COMPANIES: 450건
  - EXECUTIVE_HIGH_TURNOVER: 202건
- [x] risk_scores: 3,912건 (PRD v3.2.1 기준)
  - RaymondsRisk = 인적리스크(25%) + CB리스크(25%) + 재무건전성(50%)
  - 투자등급: AAA ~ D

### Phase 5: 추가 관계 데이터
- [x] major_shareholders: 1,130건 (최대주주/주요주주)
- [x] affiliates: 1,245건 (계열회사 관계)

---

## 스크립트 목록

### 실행 완료 스크립트 (정상 동작)

| 스크립트 | 기능 | 적재 건수 |
|---------|------|----------|
| `parse_officers_from_local.py` | 임원 정보 파싱 | 38,125 + 240,320 |
| `parse_cb_from_local.py` | CB 정보 파싱 | 1,435 + 8,656 |
| `parse_financial_from_local.py` | 재무제표 파싱 | 9,432 |
| `parse_shareholders_affiliates.py` | 주주/계열회사 파싱 | 1,130 + 1,245 |
| `load_disclosures_metadata.py` | 공시 메타데이터 | 206,767 |
| `generate_risk_signals.py` | 리스크 신호 생성 | 677 (기본 패턴) |
| `generate_additional_risk_signals.py` | 추가 리스크 신호 | 735 (3개 패턴) |
| `calculate_risk_scores.py` | 리스크 점수 계산 | 3,912 |

### 사용 금지 스크립트 (`_deprecated/` 폴더)

| 스크립트 | 위험 요소 |
|---------|----------|
| `sync_neo4j_to_postgres.py` | PostgreSQL TRUNCATE CASCADE |
| `init_database.py` | DROP TABLE CASCADE |
| `db_migrate.py --action=reset` | drop_all() |

---

## 로컬 원시 데이터 현황

### DART 공시 파일
- **위치**: `backend/data/dart/batch_XXX/`
- **총 ZIP 파일**: 228,395개
- **회사 수**: 2,859개
- **데이터 크기**: 9.2GB

### 연도별 분포
| 연도 | ZIP 파일 수 | 파싱 대상 |
|------|------------|----------|
| 2022 | 30,973개 | 사업보고서 |
| 2023 | 51,565개 | 사업보고서 |
| 2024 | 84,655개 | 사업보고서 |
| 2025 | 61,202개 | 반기보고서 |

### CB 공시 JSON
- **위치**: `backend/data/cb_disclosures_by_company_full.json`
- **전체**: 4,913건
- **전환사채 발행결정**: 1,686건

---

## Risk Signals 패턴 상세

| 패턴 | 설명 | 건수 | 심각도 |
|------|------|------|--------|
| CB_NETWORK_CLUSTER | CB 네트워크 클러스터 | 180 | HIGH |
| SERIAL_CB_ISSUER | 반복 CB 발행 회사 | 497 | MEDIUM~HIGH |
| SERIAL_CB_INVESTOR | 반복 CB 투자자 (개인) | 83 | HIGH |
| CONNECTED_LOSS_COMPANIES | 적자기업 임원 연결 | 450 | MEDIUM~HIGH |
| EXECUTIVE_HIGH_TURNOVER | 임원 고속 교체 (10명+/3년) | 202 | MEDIUM~HIGH |

---

## Risk Scores 분포

### 투자등급 분포 (PRD v3.2.1)
| 등급 | 점수 범위 | 의미 |
|------|----------|------|
| AAA | 0-10 | 최우량 |
| AA | 10-20 | 우량 |
| A | 20-30 | 양호 |
| BBB | 30-40 | 보통 |
| BB | 40-50 | 주의 |
| B | 50-60 | 경계 |
| CCC | 60-70 | 위험 |
| CC | 70-80 | 고위험 |
| C | 80-90 | 극도위험 |
| D | 90-100 | 투기등급 |

### 점수 구성
- **RaymondsRisk** (50%)
  - 인적 리스크 (25%): 임원 수 × 타사 재직 배수
  - CB 리스크 (25%): 발행빈도 + 규모 + 참여자품질 + 적자연결
- **재무건전성** (50%): 부채비율 + 영업이익 + 순이익 + 자산규모

---

## DB 접속 정보

```bash
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev
```

### 상태 확인 쿼리
```sql
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
UNION ALL SELECT 'convertible_bonds', COUNT(*) FROM convertible_bonds
UNION ALL SELECT 'cb_subscribers', COUNT(*) FROM cb_subscribers
UNION ALL SELECT 'financial_statements', COUNT(*) FROM financial_statements
UNION ALL SELECT 'risk_signals', COUNT(*) FROM risk_signals
UNION ALL SELECT 'risk_scores', COUNT(*) FROM risk_scores
UNION ALL SELECT 'major_shareholders', COUNT(*) FROM major_shareholders
UNION ALL SELECT 'affiliates', COUNT(*) FROM affiliates
ORDER BY 1;
```

---

## 주의사항

### 절대 금지
- `scripts/_deprecated/` 폴더의 스크립트 실행 금지
- PostgreSQL 데이터 삭제 금지 (TRUNCATE, DROP 등)
- 백그라운드 실행 후 검증 없이 완료 보고 금지

### 필수 프로세스
1. 작업 전 DB COUNT 확인
2. 포그라운드 실행 (완료까지 대기)
3. 에러 확인
4. 작업 후 DB COUNT 확인
5. 증가분 보고

---

## 수정 이력

| 일시 | 수정 내용 |
|------|----------|
| 2025-12-08 | 초기 작성 |
| 2025-12-08 | XML 구조 검증 후 수정 - 임기 역산 로직, 동일인 식별 로직, 경력 파싱 패턴 |
| 2025-12-09 | 전체 데이터 적재 완료 - officers, disclosures, financial_statements 등 |
| 2025-12-09 | PRD 데이터 보완 - risk_scores, major_shareholders, affiliates 테이블 신규 |
| 2025-12-09 | 추가 리스크 패턴 적용 - SERIAL_CB_INVESTOR, CONNECTED_LOSS_COMPANIES, EXECUTIVE_HIGH_TURNOVER |
