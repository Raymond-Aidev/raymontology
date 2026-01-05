# 데이터 파이프라인 개선 계획

> **버전**: v3.0 (2026-01-04 전체 구현 완료)
> **작성자**: Claude Code
> **상태**: Phase 1, 2, 3.1, 3.2, 4 모두 완료

## 개요

### 목표
1. **통일된 파일 형식**: ZIP + meta.json 표준화
2. **통합 파서 개발**: 기존 시행착오를 모두 반영한 전용 파서
3. **데이터 품질 문제 해결**: 임원 이력 중복 등 기존 문제 해결
4. **분기별 자동화**: Q1~Q4 데이터 추가 프로세스 표준화

### 현황 분석 요약

| 항목 | 현재 상태 | 완료 내용 |
|------|----------|--------|
| 파일 형식 | ✅ ZIP + meta.json 통일 | 300,857개 파일 v2.0 스키마 마이그레이션 |
| 파서 | ✅ **통합 파서 완료** | `scripts/parsers/` 모듈화 (5개 모듈) |
| 데이터 품질 | ✅ **임원 중복 해결** | position_history JSONB, 새 Unique 제약 |
| 프로세스 | ✅ **파이프라인 자동화** | `scripts/pipeline/` (6개 스크립트) |

### 임원 중복 문제 상세 분석 (2026-01-04)

**DB 분석 결과**: `position_count >= 5`인 케이스 분석

| 임원명 | 회사 | 총 포지션 | 고유 직책 | 고유 임기 | 고유 공시 |
|--------|------|----------|----------|----------|----------|
| 안종석 | 세종텔레콤 | 7 | 7 | 5 | 7 |
| 천병태 | 에이엘티 | 6 | 4 | 2 | 6 |
| 김동욱 | 인피니트헬스케어 | 6 | 4 | 2 | 6 |
| 최승인 | 바이오플러스 | 6 | 6 | 0 | 6 |

**패턴 분석**:
- `unique_terms = 2, unique_disclosures = 6`: 2개 임기에 6개 공시 → 공시마다 별도 레코드 생성 (문제)
- `unique_terms = 0`: term_end_date가 모두 NULL → 임기 정보 누락
- `unique_positions > unique_terms`: 동일 임기 내 직책 변동 (정상적 승진 이력)

**이전 Unique 제약조건** (문제):
```sql
UNIQUE (officer_id, company_id, term_start_date, source_disclosure_id)
```
→ `source_disclosure_id` 포함으로 **공시마다 새 레코드 생성됨**

**✅ 해결된 Unique 제약조건** (2026-01-04):
```sql
UNIQUE (officer_id, company_id, term_start_date)
```
→ source_disclosure_id 제외, position_history JSONB로 직책 변동 기록

---

## Phase 1: meta.json 스키마 통일 (1단계)

### 1.1 통일 스키마 정의

```json
{
  "rcept_no": "20240409002052",
  "corp_code": "00100957",
  "corp_name": "회사명",
  "stock_code": "012720",
  "report_type": "annual_2023",
  "report_nm": "사업보고서 (2023.12)",
  "rcept_dt": "20240409",
  "flr_nm": "제출자명",
  "file_size": 54885,
  "xml_count": 1,
  "downloaded_at": "2025-11-16T13:09:23.792942",
  "schema_version": "2.0"
}
```

### 1.2 report_type 표준화

| report_type | 설명 | 예시 |
|-------------|------|------|
| `annual_YYYY` | 사업보고서 | `annual_2023` |
| `q1_YYYY` | 1분기보고서 | `q1_2024` |
| `q2_YYYY` | 반기보고서 | `q2_2024` |
| `q3_YYYY` | 3분기보고서 | `q3_2024` |
| `audit_YYYY` | 감사보고서 | `audit_2023` |
| `cb_disclosure` | CB 발행결정 | `cb_disclosure` |

### 1.3 마이그레이션 스크립트

**파일**: `scripts/migrate_meta_schema.py`

```python
# 기존 meta.json을 읽어서 통일 스키마로 변환
# 1. report_nm에서 report_type 추출
# 2. file_size 추가 (ZIP 파일 크기)
# 3. xml_count 추가 (ZIP 내 XML 개수)
# 4. schema_version 추가
# 5. crawled_at → downloaded_at 표준화
```

**예상 작업량**: 299,926개 파일 × 2개(ZIP + meta) = ~600,000 파일 처리

---

## Phase 2: 통합 파서 개발 (2단계)

### 2.1 통합 파서 아키텍처

```
DARTUnifiedParser
├── BaseParser (공통 기능) - 검증된 v2.1 로직 재사용
│   ├── extract_xml_from_zip()     # ZIP 해제 (ACODE=11011 우선) ✅ 재사용
│   ├── _decode_xml()              # 인코딩 감지 (UTF-8/EUC-KR/CP949) ✅ 재사용
│   ├── _detect_unit_from_content()# 섹션별 단위 감지 ✅ 재사용
│   ├── _parse_amount()            # 금액 파싱 및 정규화 ✅ 재사용
│   └── _clean_xml_text()          # XML 태그 제거 ✅ 재사용
│
├── FinancialParser (재무제표) - v2.1 로직 재사용
│   ├── _extract_values_from_all_statements() # 3개 섹션 독립 파싱 ✅
│   ├── ACCOUNT_MAPPING            # 230+ 한글 계정과목 매핑 ✅
│   └── upsert_financial_details() # ON CONFLICT UPSERT ✅
│
├── OfficerParser (임원정보) - v2.1 로직 + 개선
│   ├── parse_officer_table()      # 임원현황 테이블 파싱 ✅ 재사용
│   ├── find_or_create_officer()   # 동일인 식별 (name+birth_date) ✅ 재사용
│   ├── track_position_changes()   # 직책 변동 추적 🔧 개선 필요
│   └── upsert_position()          # UPSERT 로직 🔧 개선 필요
│
├── CBParser (전환사채) - 기존 로직 재사용
│   ├── parse_cb_info()            # CB 정보 ✅ 재사용
│   └── parse_subscribers()        # 인수자 정보 ✅ 재사용
│
└── Validators (데이터 검증) - 신규 개발
    ├── validate_financial_data()  # 재무 데이터 검증 🆕
    ├── validate_officer_data()    # 임원 데이터 검증 🆕
    └── generate_quality_report()  # 품질 보고서 생성 🆕
```

### 2.1.1 재사용 가능한 검증된 로직 (v2.1 기준)

| 기능 | 원본 파일 | 행 번호 | 재사용성 |
|------|----------|--------|---------|
| ZIP XML 추출 | parse_local_financial_details.py | 324-364 | ⭐⭐⭐⭐⭐ |
| 다중 인코딩 감지 | parse_local_financial_details.py | 366-376 | ⭐⭐⭐⭐⭐ |
| 단위 감지 (텍스트 패턴) | parse_local_financial_details.py | 575-612 | ⭐⭐⭐⭐⭐ |
| 금액 파싱 및 정규화 | parse_local_financial_details.py | 753-786 | ⭐⭐⭐⭐⭐ |
| 계정과목 매핑 (230+) | parse_local_financial_details.py | 52-271 | ⭐⭐⭐⭐ |
| 임원 동일인 식별 | parse_officers_from_local.py | 304-372 | ⭐⭐⭐⭐⭐ |
| 시계열 재취임 감지 | parse_officers_from_local.py | 388-404 | ⭐⭐⭐⭐ |
| UPSERT 패턴 | parse_officers_from_local.py | 417-445 | ⭐⭐⭐⭐⭐ |

### 2.2 기존 시행착오 반영 목록

#### 재무제표 파싱

| 문제 | 원인 | 해결책 (v2.0 반영) |
|------|------|-------------------|
| 손익계산서/현금흐름표 누락 | 재무상태표만 추출 | 3개 섹션 독립 파싱 |
| 단위 혼동 (백만원 vs 원) | 문서 전체 첫 단위 사용 | 섹션별 단위 감지 |
| 사업보고서/감사보고서 혼동 | XML 임의 선택 | ACODE="11011" 우선 |
| 연결/별도 재무제표 혼동 | fs_type 미구분 | CFS/OFS 명시적 구분 |

#### 임원 파싱

| 문제 | 원인 | 해결책 (신규 반영 필요) |
|------|------|----------------------|
| 동일인 다른 직책 중복 | source_disclosure_id 기준 UPSERT | **직책 변동 이력 통합** |
| 재취임 감지 오류 | term_start_date NULL | **이전 공시 비교 로직** |
| 출생년월 NULL 동명이인 | 데이터 부재 | **fuzzy matching 추가** |

### 2.3 임원 이력 중복 문제 상세

**현재 상태 (세아메카닉스 이성욱 예시)**:
```
source_disclosure_id | position | term_end_date
20220331000692       | 상무이사 | 2024-05-31
20220513000972       | 전무이사 | 2024-05-31
20230811001479       | 전무이사 | 2024-05-31
20231113000079       | 부대표   | 2024-05-31
20240320000738       | 부대표   | 2024-05-31
20241113000355       | 부대표   | 2027-03-28
20251114000987       | 대표이사 | 2027-03-28
```

**문제**: 동일인의 직책 변동이 **별도 레코드**로 저장됨
- 상무 → 전무 → 부대표 → 대표이사 승진 이력
- 각 공시마다 새 레코드 생성 (Unique: officer_id + company_id + term_start_date + source_disclosure_id)

**해결 방안 비교**:

| 방안 | 장점 | 단점 | 권장 |
|------|------|------|------|
| **A. 새 테이블 (officer_position_history)** | 이력 완전 보존, 스키마 명확 | 마이그레이션 복잡, 조회 로직 변경 | ❌ |
| **B. 기존 테이블 정리 (최신 직책만)** | 단순, 즉시 적용 | 이력 손실 | ⚠️ |
| **C. Unique 제약 변경 + 이력 컬럼 추가** | 이력 보존 + 중복 방지 | 스키마 변경 필요 | ✅ 권장 |

**권장안 C 상세**:
```sql
-- 1. 새 컬럼 추가: 직책 이력을 JSONB로 저장
ALTER TABLE officer_positions
ADD COLUMN position_history JSONB DEFAULT '[]';

-- 2. Unique 제약 변경: source_disclosure_id 제외
-- 기존: (officer_id, company_id, term_start_date, source_disclosure_id)
-- 변경: (officer_id, company_id, term_start_date)
DROP INDEX IF EXISTS uq_officer_position_term;
CREATE UNIQUE INDEX uq_officer_position_term_v2
ON officer_positions (officer_id, company_id, COALESCE(term_start_date, '1900-01-01'));

-- 3. UPSERT 시 position_history 업데이트
-- 새 공시에서 직책이 변경되면 이전 직책을 history에 추가
UPDATE officer_positions SET
  position = '대표이사',
  position_history = position_history || jsonb_build_object(
    'position', '부대표',
    'effective_until', '2024-12-31',
    'source_disclosure_id', '20240320000738'
  )::jsonb
WHERE officer_id = $1 AND company_id = $2;
```

**position_history JSONB 구조**:
```json
[
  {"position": "상무이사", "effective_until": "2022-05-31", "source_disclosure_id": "20220331000692"},
  {"position": "전무이사", "effective_until": "2023-11-30", "source_disclosure_id": "20230811001479"},
  {"position": "부대표", "effective_until": "2024-12-31", "source_disclosure_id": "20240320000738"}
]
```

**예상 결과 (세아메카닉스 이성욱)**:
```
Before: 7 레코드
After:  1 레코드 (현재 직책: 대표이사, position_history: 3개 이전 직책)
```

### 2.4 통합 파서 구현 파일

**위치**: `backend/scripts/parsers/`

```
parsers/
├── __init__.py
├── base.py              # BaseParser
├── financial.py         # FinancialParser
├── officer.py           # OfficerParser
├── cb.py               # CBParser
├── unified.py          # DARTUnifiedParser (통합)
└── validators.py       # 데이터 검증 로직
```

---

## Phase 3: 데이터 품질 개선 (3단계)

### 3.1 임원 이력 정리

**스크립트**: `scripts/maintenance/consolidate_officer_positions.py`

```python
"""
임원 포지션 통합 스크립트

목표: 동일 임원 + 동일 회사 + 동일 임기의 중복 레코드를 1개로 통합
      직책 변동 이력은 position_history JSONB 컬럼에 보존

실행 순서:
1. position_history 컬럼 추가 (없는 경우)
2. 중복 그룹 식별 (officer_id + company_id + term_start_date)
3. 각 그룹에서:
   - 최신 공시 기준 레코드를 primary로 선정
   - 나머지 레코드의 직책을 position_history에 추가
   - 중복 레코드 삭제
4. Unique 제약 조건 변경 (source_disclosure_id 제외)
5. 검증: position_count > 3인 케이스 재확인
"""

async def consolidate_positions(conn):
    # Step 1: 중복 그룹 식별
    duplicates = await conn.fetch('''
        SELECT officer_id, company_id, term_start_date,
               array_agg(id ORDER BY source_disclosure_id DESC) as position_ids,
               array_agg(position ORDER BY source_disclosure_id DESC) as positions,
               array_agg(source_disclosure_id ORDER BY source_disclosure_id DESC) as disclosures
        FROM officer_positions
        GROUP BY officer_id, company_id, term_start_date
        HAVING COUNT(*) > 1
    ''')

    # Step 2: 각 그룹 통합
    for group in duplicates:
        primary_id = group['position_ids'][0]  # 최신 공시 기준
        history = []

        for i, pos_id in enumerate(group['position_ids'][1:], 1):
            history.append({
                'position': group['positions'][i],
                'source_disclosure_id': group['disclosures'][i]
            })
            await conn.execute('DELETE FROM officer_positions WHERE id = $1', pos_id)

        await conn.execute('''
            UPDATE officer_positions
            SET position_history = $1::jsonb
            WHERE id = $2
        ''', json.dumps(history), primary_id)

    return len(duplicates)
```

**마이그레이션 SQL**:
```sql
-- 실행 전 백업
CREATE TABLE officer_positions_backup_20260104 AS
SELECT * FROM officer_positions;

-- 1. 컬럼 추가
ALTER TABLE officer_positions
ADD COLUMN IF NOT EXISTS position_history JSONB DEFAULT '[]';

-- 2. 통합 스크립트 실행 후 Unique 제약 변경
DROP INDEX IF EXISTS uq_officer_position_term;
CREATE UNIQUE INDEX uq_officer_position_term_v2
ON officer_positions (officer_id, company_id, COALESCE(term_start_date, '1900-01-01'));
```

**예상 결과**:
```
Before: 64,265 레코드, 중복 그룹 ~500개
After:  63,765 레코드 (-500), position_count > 3 케이스 0건
```

### 3.2 데이터 검증 시스템

**스크립트**: `scripts/maintenance/validate_data_quality.py`

**검증 항목 상세**:

| 카테고리 | 검증 항목 | 기준 | 액션 |
|----------|----------|------|------|
| **재무 데이터** | revenue 유효성 | > 0 | 경고 로그 |
| | total_assets 유효성 | > 0 | 경고 로그 |
| | 자산 = 부채 + 자본 | 오차 < 1% | 경고 로그 |
| | 단위 이상값 | < 100조 | 의심 플래그 |
| **임원 데이터** | 동일 회사 포지션 수 | ≤ 3 | 중복 의심 |
| | 임기 논리 검증 | start ≤ end | 오류 플래그 |
| | 출생년월 유효성 | 1920-2010 | 오류 플래그 |
| **CB 데이터** | 중복 검사 | company + bond_name | 중복 제거 |
| | 금액 유효성 | 발행액 > 0 | 경고 로그 |

**품질 보고서 출력 예시**:
```
📊 데이터 품질 보고서 (2026-01-04)
=====================================

✅ 재무 데이터 (financial_details)
   - 총 레코드: 7,689
   - revenue > 0: 7,650 (99.5%)
   - 의심 레코드: 39 (0.5%)

⚠️ 임원 데이터 (officer_positions)
   - 총 레코드: 64,265
   - 중복 의심 (position_count > 3): 15 케이스
   - 임기 오류: 0

✅ CB 데이터 (convertible_bonds)
   - 총 레코드: 1,133
   - 중복: 0

📈 개선 필요 항목:
   1. 임원 중복 15건 정리 필요
   2. 재무 데이터 의심 39건 검토 필요
```

---

## Phase 4: 분기별 프로세스 자동화 (4단계)

### 4.1 표준 파이프라인

```
[분기 종료 + 45일 후]
    ↓
1. DART에서 분기보고서 다운로드
   scripts/download_quarterly_reports.py --quarter Q1 --year 2025
    ↓
2. 통합 파서로 데이터 추출
   scripts/run_unified_parser.py --source q1_2025
    ↓
3. 데이터 품질 검증
   scripts/validate_parsed_data.py --source q1_2025
    ↓
4. DB 적재 (UPSERT)
   scripts/load_to_database.py --source q1_2025
    ↓
5. RaymondsIndex 재계산
   scripts/calculate_raymonds_index.py --year 2025
    ↓
6. 품질 보고서 생성
   scripts/generate_data_quality_report.py
```

### 4.2 분기별 일정

| 분기 | 보고서 마감 | 파싱 실행 | 비고 |
|------|------------|----------|------|
| Q1 | 5월 15일 | 5월 20일 | |
| Q2 (반기) | 8월 14일 | 8월 20일 | |
| Q3 | 11월 14일 | 11월 20일 | |
| Q4 (사업보고서) | 3월 31일 | 4월 5일 | 연간 데이터 확정 |

### 4.3 자동화 스크립트

**파일**: `scripts/run_quarterly_pipeline.py`

```python
# 인자: --quarter Q1 --year 2025
# 1~6단계 순차 실행
# 각 단계별 로그 및 에러 핸들링
# 완료 후 Slack/Email 알림 (선택)
```

---

## Phase 5: 문서화 및 모니터링 (5단계)

### 5.1 문서 업데이트

| 문서 | 업데이트 내용 |
|------|-------------|
| `SCHEMA_REGISTRY.md` | 새 테이블/컬럼 추가 |
| `STANDARD_PROCESS.md` | 분기별 파이프라인 추가 |
| `PARSING_STATUS.md` | 마지막 실행 일시, 통계 |

### 5.2 모니터링 대시보드

**관리자 페이지 추가 기능**:
- 파싱 실행 이력
- 데이터 품질 지표 (누락률, 오류율)
- 분기별 데이터 현황

---

## 구현 우선순위 (수정됨)

| 순위 | Phase | 작업 | 세부 작업 | 의존성 |
|------|-------|------|----------|--------|
| **1** | 3.1 | 임원 이력 중복 정리 | 스키마 변경 + 마이그레이션 스크립트 | 없음 |
| **2** | 2 | 통합 파서 개발 | BaseParser → FinancialParser → OfficerParser | Phase 3.1 |
| **3** | 3.2 | 데이터 검증 시스템 | validate_data_quality.py | Phase 2 |
| **4** | 1 | meta.json 스키마 통일 | 마이그레이션 스크립트 | 없음 (병렬 가능) |
| **5** | 4 | 분기별 파이프라인 | 다운로드 → 파싱 → 검증 → 적재 | Phase 2, 3 |
| **6** | 5 | 문서화 및 모니터링 | STANDARD_PROCESS 업데이트 | Phase 4 |

### 단계별 구현 계획

```
Week 1: 기반 작업
├── Day 1-2: Phase 3.1 임원 이력 중복 정리
│   ├── position_history 컬럼 추가
│   ├── 중복 그룹 통합 스크립트 개발
│   └── Unique 제약 조건 변경
│
├── Day 3-4: Phase 2 통합 파서 (BaseParser)
│   ├── parsers/ 디렉토리 구조 생성
│   ├── base.py - 공통 기능 모듈화
│   └── validators.py - 검증 로직
│
└── Day 5: Phase 1 meta.json 스키마 통일 (병렬)
    └── migrate_meta_schema.py

Week 2: 파서 개발
├── Day 1-2: Phase 2 FinancialParser
│   └── 기존 v2.1 로직 모듈화
│
├── Day 3: Phase 2 OfficerParser
│   └── 개선된 UPSERT 로직 적용
│
└── Day 4-5: Phase 3.2 데이터 검증 시스템
    └── validate_data_quality.py

Week 3: 자동화 및 문서화
├── Day 1-2: Phase 4 분기별 파이프라인
│   └── run_quarterly_pipeline.py
│
└── Day 3: Phase 5 문서화
    └── STANDARD_PROCESS.md 업데이트
```

---

## 파일 구조 (완료 후)

```
backend/scripts/
├── parsers/                    # 통합 파서 모듈
│   ├── __init__.py
│   ├── base.py
│   ├── financial.py
│   ├── officer.py
│   ├── cb.py
│   ├── unified.py
│   └── validators.py
│
├── pipeline/                   # 파이프라인 스크립트
│   ├── download_quarterly_reports.py
│   ├── run_unified_parser.py
│   ├── validate_parsed_data.py
│   ├── load_to_database.py
│   └── run_quarterly_pipeline.py
│
├── maintenance/                # 유지보수 스크립트
│   ├── migrate_meta_schema.py
│   ├── cleanup_officer_duplicates.py
│   └── generate_data_quality_report.py
│
└── _deprecated/                # 기존 스크립트 (사용 중지)
    ├── parse_local_financial_details.py
    ├── parse_officers_from_local.py
    └── ...
```

---

## 성공 기준

1. **meta.json 통일**: 모든 파일이 schema_version 2.0
2. **임원 중복 해소**: position_count > 3인 케이스 0건
3. **파서 통일**: 단일 진입점 (DARTUnifiedParser)
4. **분기 파이프라인**: 5단계 자동 실행 가능
5. **품질 보고서**: 월간 자동 생성

---

## 위험 요소 및 대응 방안

| 위험 | 영향도 | 대응 방안 |
|------|-------|----------|
| **DB 스키마 변경 실패** | 높음 | 백업 테이블 생성 후 작업, 롤백 스크립트 준비 |
| **meta.json 마이그레이션 중 오류** | 중간 | 배치 처리 + 체크포인트 저장 |
| **통합 파서 호환성 문제** | 중간 | 기존 파서와 병렬 실행하여 결과 비교 |
| **분기 파이프라인 DART API 제한** | 낮음 | Rate limiting + 재시도 로직 |

## 롤백 계획

```bash
# Phase 3.1 롤백 (임원 이력 스키마 변경)
psql -c "DROP TABLE officer_positions;"
psql -c "ALTER TABLE officer_positions_backup_20260104 RENAME TO officer_positions;"

# Phase 1 롤백 (meta.json)
# 각 _meta.json.bak 파일로 복원
find /backend/data/dart -name "*_meta.json.bak" -exec sh -c 'mv "$1" "${1%.bak}"' _ {} \;
```

---

## 다음 단계

이 계획서를 검토하신 후:
1. **즉시 시작**: Phase 3.1 (임원 이력 중복 정리) - 가장 시급
2. **병렬 진행 가능**: Phase 1 (meta.json 스키마 통일)
3. **순차 진행**: Phase 2 → 3.2 → 4 → 5

**승인 시 첫 번째 작업**:
```bash
# 1. 백업 생성
psql -c "CREATE TABLE officer_positions_backup_20260104 AS SELECT * FROM officer_positions;"

# 2. position_history 컬럼 추가
psql -c "ALTER TABLE officer_positions ADD COLUMN IF NOT EXISTS position_history JSONB DEFAULT '[]';"

# 3. 중복 통합 스크립트 실행
python scripts/maintenance/consolidate_officer_positions.py --dry-run  # 테스트
python scripts/maintenance/consolidate_officer_positions.py            # 실행
```
