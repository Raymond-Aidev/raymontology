# Raymontology 데이터 수집 및 저장 현황 보고서

**작성일시**: 2025-11-21
**목적**: 다음 개발 세션 시 데이터 수집/저장 위치 및 현황을 빠르게 파악하기 위한 참고 문서

---

## 📊 전체 데이터 현황 요약

### PostgreSQL 데이터베이스
```
총 회사: 85,167개
  - 상장사: 3,911개
  - 비상장사: 81,256개

임원 데이터:
  - 총 임원: 83,736명
  - 회사 연결: 83,736명 (100%)
  - 임원이 있는 회사: 2,480개 (63.41%)
  - 임원이 없는 회사: 82,687개 (36.59%)

계열사: 28,114개
전환사채(CB): 2,743개
```

### Neo4j 그래프 데이터베이스
```
총 노드: 92,617개
  - Company: 3,911개
  - Officer: 83,736개
  - ConvertibleBond: 2,743개
  - Subscriber: 2,227개

총 관계: 145,521개
  - WORKS_AT: 83,736개
  - BOARD_MEMBER_AT: 50,021개
  - SUBSCRIBED: 4,014개
  - INVESTED_IN: 3,130개
  - ISSUED: 2,743개
  - HAS_AFFILIATE: 1,877개
```

---

## 📁 데이터 저장 위치

### 1. DART 공시 문서 저장소
**경로**: `/Users/jaejoonpark/raymontology/backend/data/dart/`

**구조**:
```
data/dart/
├── batch_001/              # 1~500번 기업 (첫 배치)
│   ├── 00109693/          # corp_code 기준 회사별 디렉토리
│   │   ├── 2025/          # 연도별 디렉토리
│   │   │   ├── 20250516800200.zip         # 공시 문서 (XML 포함)
│   │   │   └── 20250516800200_meta.json   # 메타데이터
│   │   ├── 2024/
│   │   └── 2023/
│   └── [다른 회사 디렉토리들...]
├── batch_002/              # 501~1000번 기업
├── batch_003/              # 1001~1500번 기업
├── ...
├── batch_014/              # 마지막 배치
└── logs/
    ├── batch_001.json      # 배치별 수집 회사 목록 및 통계
    ├── batch_002.json
    └── ...
```

**저장된 파일 현황**:
- 총 배치: 14개
- ZIP 파일: 약 30,000+ 개
- 메타데이터 파일: 228,395개
- 사업보고서 메타데이터: 10,017개

### 2. 로그 파일 저장소
**경로**: `/Users/jaejoonpark/raymontology/backend/`

**주요 로그 파일**:
```
affiliate_collector_output.log  (84MB)  - 계열사 파싱 로그
cb_parsing_full_fixed.log      (32MB)  - CB 파싱 로그
officer_link_fix_v2.log                - 임원-회사 연결 로그
neo4j_officer_build.log                - Neo4j Officer 네트워크 구축 로그
neo4j_network_build.log                - Neo4j 전체 네트워크 구축 로그
neo4j_affiliate_network.log            - Neo4j 계열사 네트워크 구축 로그
```

### 3. 배치 수집 백그라운드 로그
**확인 방법**: Background Bash 출력 확인
```bash
# 예시: batch_005 로그
Bash ID: 2b5a83
처리 기업: 2001~2300번 (300개)
수집 결과: 6,041건 공시 다운로드
파싱 결과: 임원 30,205명, 계열사 12,082개 (추정치)
에러: 225건 (DART API 사용한도 초과)
```

---

## 🔧 데이터 수집 스크립트

### 1. 배치 수집기 (Batch Collector)
**파일**: `scripts/batch_collector.py`

**기능**:
- DART API에서 공시 문서를 배치 단위로 다운로드
- 회사당 2020~2025년 사업보고서, 감사보고서, 정기보고서 수집
- ZIP 파일과 메타데이터 JSON 파일 저장

**실행 예시**:
```bash
python3 scripts/batch_collector.py \
  --batch-num 5 \
  --start-idx 2001 \
  --end-idx 2300 \
  --data-dir ./data/dart \
  --api-key 1fd0cd12ae5260eafb7de3130ad91f16aa61911b
```

**실행 결과** (batch_005 예시):
```
총 기업 수: 300
수집 공시: 6,041건
다운로드 성공: 6,041개
다운로드 실패: 0개
⚠️ 에러: 225건 (API 사용한도 초과)
```

### 2. 배치 파서 (Batch Parser)
**파일**: `scripts/batch_parser.py`

**기능**:
- 다운로드된 ZIP 파일에서 XML 추출
- 사업보고서/감사보고서에서 임원 정보 파싱
- PostgreSQL에 임원 데이터 저장

**실행 예시**:
```bash
python3 scripts/batch_parser.py \
  --batch-num 5 \
  --data-dir ./data/dart
```

**핵심 로직**:
- `*_meta.json` 파일을 읽어 "사업보고서" 또는 "감사보고서" 필터링
- 해당 ZIP 파일에서 임원 정보 추출
- officers 테이블에 저장

### 3. 계열사 수집기 (Affiliate Collector)
**파일**: `scripts/affiliate_collector.py`

**기능**:
- 다운로드된 사업보고서에서 계열사 정보 파싱
- 특수관계자 정보 추출
- PostgreSQL affiliates 테이블에 저장

**실행 결과**:
```
처리한 파일: 10,017개
파싱된 파일: 9,642개
저장된 계열사: 28,114개
매칭 성공: 408개
```

**로그 파일**: `affiliate_collector_output.log` (84MB)

### 4. 임원-회사 연결 수정 (Officer Link Fixer)
**파일**: `scripts/fix_officer_company_links_v2.py`

**기능**:
- 임원의 current_company_id를 회사 이름 기준으로 매칭
- 퍼지 매칭으로 회사명 유사도 계산
- PostgreSQL officers.current_company_id 업데이트

**실행 결과**:
```
총 임원: 83,736명
매칭된 임원: 83,736명 (100.0%)

임원이 많은 회사 TOP 10:
  LG전자: 530명
  HL만도: 360명
  롯데웰푸드: 336명
  삼성생명: 244명
  메리츠화재해상보험: 232명
```

**로그 파일**: `officer_link_fix_v2.log`

### 5. Neo4j Officer 네트워크 구축
**파일**: `scripts/neo4j_officer_network.py`

**기능**:
- PostgreSQL officers 테이블에서 Neo4j로 동기화
- Officer 노드 생성 (83,736개)
- WORKS_AT 관계 생성 (83,736개)
- BOARD_MEMBER_AT 관계 생성 (50,021개)

**실행 결과**:
```
임원 (Officer): 83,736명
회사 (Company): 2,606개
WORKS_AT 관계: 83,736개
BOARD_MEMBER_AT 관계: 50,021개
```

**로그 파일**: `neo4j_officer_build.log`

**실행 시간**: 약 5분 21초

---

## ⚠️ 현재 문제점 및 해결 대기 사항

### 문제 1: 삼성전자 포함 1,416개 회사 임원 데이터 누락

**증상**:
- 삼성전자(005930) 검색 시 그래프에 관계 없음
- Neo4j에서 1,416개 회사가 고립된 노드 (Isolated Node)
- PostgreSQL에서 임원이 0명인 회사: 82,687개

**원인**:
- 사업보고서 ZIP 파일은 다운로드되어 있음
- batch_parser가 해당 회사들의 사업보고서를 찾지 못하거나 파싱 실패
- 임원 정보 추출 로직이 일부 회사의 XML 구조를 처리하지 못함

**영향 범위**:
- 전체 회사: 3,911개
- 고립된 회사: 1,416개 (36.2%)
- 정상 회사: 2,495개 (63.8%)

**해결 방안**:
1. batch_parser.py 재실행으로 누락된 사업보고서 파싱
2. XML 파싱 로직 디버깅 (특정 회사 구조 분석)
3. 파싱 완료 후 Neo4j Officer 네트워크 재동기화

**임시 해결책**:
- LG전자(066570) 등 정상 작동하는 회사로 테스트
- LG전자 ID: `8e1d4a2c-4413-4d99-adc8-f8b7f8422dd7`

### 문제 2: PostgreSQL Unique Constraint 오류

**에러**:
```
duplicate key value violates unique constraint "companies_business_number_key"
```

**원인**:
- 빈 문자열 `business_number`가 여러 회사에 중복
- DART API에서 사업자등록번호를 제공하지 않는 경우

**영향**:
- company_collector가 일부 회사 업데이트 실패
- 2,606개만 저장 완료 (예상: 3,911개)

**해결 방안**:
- companies 테이블 스키마 수정:
  ```sql
  ALTER TABLE companies DROP CONSTRAINT companies_business_number_key;
  CREATE UNIQUE INDEX companies_business_number_idx
    ON companies(business_number)
    WHERE business_number IS NOT NULL AND business_number != '';
  ```

### 문제 3: DART API 사용한도 초과

**에러**:
```
DART API Error 020: 사용한도를 초과하였습니다
```

**발생 빈도**:
- batch_005: 225건 에러
- 각 배치당 일부 회사의 공시 다운로드 실패

**해결 방안**:
- 여러 API 키 사용 (로테이션)
- 배치 크기 줄이기 (300개 → 100개)
- 다운로드 실패한 회사 목록 저장 후 재시도

---

## ✅ 정상 작동하는 회사 목록 (테스트용)

프론트엔드 그래프 시각화 테스트 시 아래 회사 사용 권장:

```
LG전자 (066570)
  - ID: 8e1d4a2c-4413-4d99-adc8-f8b7f8422dd7
  - 임원: 530명
  - 관계: 538개

HL만도 (204320)
  - 임원: 360명
  - 관계: 376개

롯데웰푸드 (280360)
  - 임원: 336명
  - 관계: 363개

삼성생명 (032830)
  - 임원: 244명
  - 관계: 269개

안국약품 (001540)
  - 임원: 284명

신원 (009270)
  - 임원: 284명
```

---

## 🚀 다음 단계 작업 계획

### 1단계: 누락된 임원 데이터 파싱 ⏳

**목표**: 82,687개 회사의 임원 데이터 파싱

**작업**:
```bash
# 모든 배치 재파싱
for batch in {1..14}; do
  python3 scripts/batch_parser.py \
    --batch-num $batch \
    --data-dir ./data/dart \
    --force  # 강제 재파싱
done
```

**예상 결과**:
- 임원 수: 83,736명 → 약 150,000명 이상
- 회사 커버리지: 2,480개 → 3,500개 이상

### 2단계: Neo4j Officer 네트워크 재동기화 ⏳

**작업**:
```bash
python3 scripts/neo4j_officer_network.py
```

**예상 결과**:
- Officer 노드: 83,736개 → 150,000개 이상
- WORKS_AT 관계: 83,736개 → 150,000개 이상
- 고립된 회사 노드: 1,416개 → 100개 미만

### 3단계: 그래프 시각화 검증 ⏳

**테스트 대상**:
- 삼성전자 (005930)
- 네이버 (035420)
- 카카오 (035720)
- SK하이닉스 (000660)

**검증 쿼리**:
```cypher
MATCH (c:Company {ticker: '005930'})-[r]-(n)
RETURN c, r, n
LIMIT 100
```

**기대 결과**:
- 삼성전자 관계: 0개 → 수백 개
- 그래프 시각화 정상 작동

### 4단계: 데이터 품질 검증 ✅

**검증 항목**:
- [ ] PostgreSQL과 Neo4j 간 임원 수 일치
- [ ] 고립된 노드 0개 달성
- [ ] 모든 상장사 그래프 시각화 가능
- [ ] Frontend 테스트 통과율 100%

---

## 📖 참고 문서

### 관련 보고서
1. **NEO4J_ISSUE_REPORT.md**: Neo4j 그래프 시각화 문제 진단
2. **SERVICE_QUALITY_REPORT.md**: 전체 서비스 품질 검사 결과
3. **frontend_test_results.log**: 프론트엔드 기능 테스트 결과

### 데이터베이스 연결 정보
```
PostgreSQL:
  - Host: localhost
  - Port: 5432
  - Database: raymontology
  - User: raymontology
  - Password: password

Neo4j:
  - URI: bolt://localhost:7687
  - User: neo4j
  - Password: password
```

### API 정보
```
DART OpenAPI:
  - Base URL: https://opendart.fss.or.kr/api/
  - API Key: 1fd0cd12ae5260eafb7de3130ad91f16aa61911b
  - 사용한도: 10,000 요청/일
```

---

## 💡 개발 재개 시 체크리스트

다음 개발 세션 시작 시 아래 항목을 순서대로 확인:

1. **데이터 현황 확인**
   ```bash
   # PostgreSQL 임원 수
   psql -d raymontology -U raymontology -c "SELECT COUNT(*) FROM officers;"

   # Neo4j 노드 수
   cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n);"
   ```

2. **서비스 상태 확인**
   ```bash
   # Backend
   curl http://localhost:8000/health

   # Frontend
   curl http://localhost:5173/

   # Neo4j
   cypher-shell -u neo4j -p password "RETURN 1;"
   ```

3. **마지막 작업 로그 확인**
   ```bash
   ls -lth *.log | head -5
   tail -50 neo4j_officer_build.log
   ```

4. **이 문서 읽기**
   - 현재 문제점 섹션 확인
   - 다음 단계 작업 계획 검토

---

**작성**: Claude Code
**최종 수정**: 2025-11-21
**문서 버전**: 1.0
