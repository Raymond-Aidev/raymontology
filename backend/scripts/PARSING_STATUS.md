# 데이터 파싱 및 적재 상태 (2025-12-26 기준)

## 현재 DB 상태

| 테이블 | 레코드 수 | 상태 | 비고 |
|--------|----------|------|------|
| companies | 3,922 | ✅ 완료 | 상장사 전체 |
| officers | 44,679 | ✅ 완료 | |
| officer_positions | 64,265 | ✅ 완료 | 중복 제거 완료 |
| disclosures | 213,304 | ✅ 완료 | |
| convertible_bonds | 1,463 | ✅ 완료 | |
| cb_subscribers | 7,490 | ✅ 완료 | |
| financial_statements | 9,432 | ✅ 완료 | |
| risk_signals | 1,412 | ✅ 완료 | 5개 패턴 |
| risk_scores | 3,912 | ✅ 완료 | |
| major_shareholders | 47,453 | ✅ 완료 | |
| affiliates | 973 | ✅ 완료 | |
| **financial_details** | **10,314** | ✅ 완료 | 2025 Q3 보고서 기반 |
| **raymonds_index** | **7,646** | ✅ 완료 | 자본 배분 효율성 지수 (2025 Q3 포함) |

---

## 완료된 작업 내역

### Phase 1: 기본 데이터 적재
- [x] companies: 3,922개 상장사 등록
- [x] disclosures: 213,304건 공시 메타데이터 적재
- [x] officers: 44,679명 임원 정보 파싱
- [x] officer_positions: 64,265건 (중복 제거 완료)

### Phase 2: CB 데이터 적재
- [x] convertible_bonds: 1,463건 전환사채 발행 정보
- [x] cb_subscribers: 7,490건 CB 인수인 정보

### Phase 3: 재무 데이터 적재
- [x] financial_statements: 9,432건 재무제표

### Phase 4: 리스크 분석 데이터
- [x] risk_signals: 1,412건 (5개 패턴)
- [x] risk_scores: 3,912건

### Phase 5: 추가 관계 데이터
- [x] major_shareholders: 47,453건
- [x] affiliates: 973건

### Phase 6: RaymondsIndex 시스템 (2025-12-26)
- [x] Q3 2025 보고서 다운로드: 2,671개 ZIP
- [x] financial_details 파싱: 10,314건
- [x] raymonds_index 계산: 7,646건
  - 등급 분포: A(121), B(1,740), C(3,722), D(2,063)

---

## 스크립트 목록

### 실행 완료 스크립트 (정상 동작)

| 스크립트 | 기능 | 적재 건수 |
|---------|------|----------|
| `parse_officers_from_local.py` | 임원 정보 파싱 | 44,679 + 64,265 |
| `parse_cb_from_local.py` | CB 정보 파싱 | 1,463 + 7,490 |
| `parse_financial_from_local.py` | 재무제표 파싱 | 9,432 |
| `parse_shareholders_affiliates.py` | 주주/계열회사 파싱 | 47,453 + 973 |
| `load_disclosures_metadata.py` | 공시 메타데이터 | 213,304 |
| `generate_risk_signals.py` | 리스크 신호 생성 | 1,412 |
| `calculate_risk_scores.py` | 리스크 점수 계산 | 3,912 |
| **`download_q3_reports_2025.py`** | Q3 보고서 다운로드 | 2,671 ZIP |
| **`parse_q3_reports_2025.py`** | Q3 재무데이터 파싱 | 10,314 |
| **`calculate_raymonds_index.py`** | RaymondsIndex 계산 | 4,951 |

### 사용 금지 스크립트 (`_deprecated/` 폴더)

| 스크립트 | 위험 요소 |
|---------|----------|
| `sync_neo4j_to_postgres.py` | PostgreSQL TRUNCATE |
| `init_database.py` | DROP TABLE |
| `db_migrate.py --action=reset` | drop_all() |

---

## 로컬 원시 데이터 현황

### DART 공시 파일
- **위치**: `backend/data/dart/`
- **총 ZIP 파일**: 228,395개
- **데이터 크기**: 9.2GB

### Q3 2025 보고서
- **위치**: `backend/data/q3_reports_2025/`
- **총 ZIP 파일**: 2,671개
- **회사 수**: 2,671개

### CB 공시 JSON
- **위치**: `backend/data/cb_disclosures_by_company_full.json`
- **전체**: 4,913건

---

## RaymondsIndex 등급 분포 (2025-12-26 기준)

| 등급 | 점수 범위 | 기업 수 |
|------|----------|--------|
| A | 70+ | 121 |
| B | 40-69 | 1,740 |
| C | 20-39 | 3,722 |
| D | <20 | 2,063 |

**Top 10**: 한솔케미칼(77.7), 피제이전자(76.0), 삼화콘덴서공업(73.2), 서연(73.2), 푸드웰(73.2)

---

## 주의사항

- `scripts/_deprecated/` 폴더의 스크립트 실행 금지
- PostgreSQL 데이터 삭제 금지
- 백그라운드 실행 후 검증 없이 완료 보고 금지
- 상세 절차는 `scripts/STANDARD_PROCESS.md` 참조

---

## 수정 이력

| 일시 | 수정 내용 |
|------|----------|
| 2025-12-26 | RaymondsIndex 시스템 완료 - financial_details, raymonds_index 적재 |
| 2025-12-24 | 임원 API 리팩토링, 중복 제거 |
| 2025-12-09 | 전체 데이터 적재 완료 |
| 2025-12-08 | 초기 작성 |
