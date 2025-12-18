# 표준 작업 프로세스

> **모든 데이터 작업은 이 체크리스트를 반드시 따라야 합니다.**
>
> **목적**: 반복적인 "완료 후 데이터 없음" 문제 방지
>
> **적용 범위**: 파싱, 삭제, 수정, 마이그레이션 등 모든 DB 작업

---

## 작업 전 (BEFORE) - 필수

### 1. 현재 DB 상태 확인

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

**결과를 기록해두기** (나중에 비교용)

---

### 2. 대상 테이블 확인

- [ ] `SCHEMA_REGISTRY.md` 참조하여 정확한 테이블명 확인
- [ ] 테이블명 직접 타이핑 금지 (복사-붙여넣기)
- [ ] 필수 컬럼 확인

**자주 틀리는 테이블명**:
| 틀린 이름 | 올바른 이름 |
|----------|------------|
| company | companies |
| officer | officers |
| position | officer_positions |
| cb | convertible_bonds |
| subscriber | cb_subscribers |

---

### 3. 작업 내용 기록

```
작업명: [예: 대호에이엘 CB 파싱]
대상 테이블: [예: convertible_bonds, cb_subscribers]
예상 결과: [예: CB 10건 추가, 인수자 20건 추가]
작업 시작 시각: [예: 2025-12-16 14:30]
```

---

## 작업 중 (DURING) - 필수

### 4. 포그라운드 실행

```bash
# 올바른 방법 (포그라운드)
python3 scripts/my_script.py

# 금지 (백그라운드)
python3 scripts/my_script.py &
```

**백그라운드 실행 금지 이유**: 에러 확인 불가, 완료 시점 알 수 없음

---

### 5. 에러 메시지 전체 확인

- 스크립트 출력 **전체** 읽기
- 에러/Warning 발생 시 즉시 중단
- 부분 성공도 기록

---

### 6. 부분 성공 기록

```
처리 대상: 100건
성공: 95건
실패: 5건 (원인: ...)
```

---

## 작업 후 (AFTER) - 필수

### 7. DB 상태 재확인

```sql
-- 1번과 동일한 쿼리 실행
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
-- ... (전체 테이블)
```

---

### 8. 증감분 계산 및 기록

```
=== 작업 결과 ===
convertible_bonds: 1,123건 → 1,140건 (+17건)
cb_subscribers: 9,672건 → 9,689건 (+17건)
작업 완료 시각: 2025-12-16 14:45
소요 시간: 15분
```

**증감분이 예상과 다르면 원인 파악 필수**

---

### 9. PARSING_STATUS.md 업데이트

`scripts/PARSING_STATUS.md` 파일에 결과 기록

---

### 10. script_execution_log 기록 (선택)

```sql
INSERT INTO script_execution_log (
    script_name,
    table_counts_before,
    table_counts_after,
    records_added,
    status
) VALUES (
    'parse_cb_for_daeho',
    '{"convertible_bonds": 1123, "cb_subscribers": 9672}',
    '{"convertible_bonds": 1140, "cb_subscribers": 9689}',
    17,
    'success'
);
```

---

## 금지 사항 (절대 금지)

### "시작했습니다" 보고 후 종료

```
금지: "파싱을 시작했습니다. 잠시 후 확인해주세요."
필수: 완료까지 대기 후 결과 보고
```

### COUNT 확인 없이 "완료" 선언

```
금지: "스크립트가 성공적으로 실행되었습니다."
필수: "officers: 39,000건 → 39,035건 (+35건)"
```

### 백그라운드 실행

```
금지: python3 script.py &
금지: python3 script.py 2>&1 &
필수: python3 script.py (포그라운드)
```

### 테이블명 추측

```
금지: "company 테이블에서..."
필수: SCHEMA_REGISTRY.md 확인 후 "companies 테이블에서..."
```

---

## 삭제 작업 시 추가 절차

### 백업 필수

```sql
-- 삭제 전 반드시 백업
CREATE TABLE officer_positions_backup_20251216 AS
SELECT * FROM officer_positions;
```

### 삭제 대상 미리 확인

```sql
-- 삭제될 레코드 미리 확인
SELECT COUNT(*) FROM officer_positions
WHERE [삭제 조건];
```

### 소규모 테스트

```sql
-- 1개 기업에 대해서만 먼저 테스트
DELETE FROM officer_positions
WHERE company_id = '[특정 company_id]'
AND [삭제 조건];
```

### 롤백 준비

```sql
-- 문제 발생 시 복구
INSERT INTO officer_positions
SELECT * FROM officer_positions_backup_20251216
WHERE id NOT IN (SELECT id FROM officer_positions);
```

---

## 체크리스트 요약

### 작업 전
- [ ] DB 현재 상태 COUNT 확인 및 기록
- [ ] SCHEMA_REGISTRY.md에서 테이블명 확인
- [ ] 작업 내용 및 예상 결과 기록

### 작업 중
- [ ] 포그라운드 실행 (백그라운드 금지)
- [ ] 에러 메시지 전체 확인
- [ ] 부분 성공 기록

### 작업 후
- [ ] DB 상태 재확인 (동일 COUNT 쿼리)
- [ ] 증감분 계산: "X건 → Y건 (+Z건)"
- [ ] PARSING_STATUS.md 업데이트

### 삭제 시 추가
- [ ] 백업 테이블 생성
- [ ] 삭제 대상 미리 확인
- [ ] 소규모 테스트 먼저

---

## 완료 보고 형식 (필수)

```
=== [작업명] 완료 ===

작업 시각: 2025-12-16 14:30 ~ 14:45 (15분)

[테이블 증감]
- companies: 3,922건 → 3,922건 (변동 없음)
- convertible_bonds: 1,123건 → 1,140건 (+17건)
- cb_subscribers: 9,672건 → 9,689건 (+17건)

[처리 내역]
- 대상: 대호에이엘 (corp_code: 00428729)
- 처리 공시: 17건
- 성공: 17건 / 실패: 0건

[검증 완료]
- verify_data_status.py 실행 확인: PASS
```
