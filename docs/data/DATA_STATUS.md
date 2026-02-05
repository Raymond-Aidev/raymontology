# Raymontology 데이터 현황

> 단일 진실 공급원 (Single Source of Truth) - 마지막 업데이트: 2026-02-05

---

## 기업 관리 현황

### 관리 대상 기업

| 구분 | 기업 수 | 비고 |
|------|--------|------|
| **LISTED (일반)** | 3,021 | 서비스 대상 |
| **ETF** | 88 | 제한적 관리 |
| **총 관리 기업** | **3,109** | |

### 삭제된 기업 (2026-01-21)

| 구분 | 기업 수 | 사유 |
|------|--------|------|
| 유령 기업 | 39 | LISTED이나 사업보고서 0건 |
| 상장폐지 기업 | 774 | DELISTED + 사업보고서 0건 |
| **총 삭제** | **813** | |

---

## 데이터베이스 테이블 현황 (45개 테이블)

### 기업/임원 (7개)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `companies` | 3,109 | 기업 마스터 |
| `officers` | 49,446 | 임원 정보 |
| `officer_positions` | 75,059 | 임원 직위 이력 |
| `major_shareholders` | 60,214 | 대주주 정보 |
| `largest_shareholder_info` | 4,599 | 최대주주 법인 정보 |
| `affiliates` | 858 | 계열사 정보 |
| `company_labels` | - | 기업 라벨 |

### 재무 (3개)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `financial_statements` | 9,820 | 재무제표 요약 |
| `financial_details` | 9,761 | 재무제표 상세 (XBRL) |
| `financial_ratios` | - | 재무비율 |

### 리스크 (4개)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `risk_scores` | 3,100 | 리스크 점수 (RaymondsRisk) |
| `risk_signals` | 1,408 | 리스크 신호 |
| `convertible_bonds` | 1,128 | 전환사채 발행 |
| `cb_subscribers` | 7,021 | CB 인수인 |

### RaymondsIndex (2개)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `raymonds_index` | 5,354 | 자본배분효율성 지수 v2 |
| `raymonds_index_v3` | - | 자본배분효율성 지수 v3 |

### 경영분쟁/임시주총 (2개) ⭐신규

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `egm_disclosures` | 393 | 임시주주총회 공시 |
| `dispute_officers` | 391 | 경영분쟁 선임 임원 |

### 사용자/인증 (4개)

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 계정 |
| `toss_users` | 토스 사용자 |
| `password_reset_tokens` | 비밀번호 재설정 토큰 |
| `email_verification_tokens` | 이메일 인증 토큰 |

### 구독/결제 (3개)

| 테이블 | 설명 |
|--------|------|
| `user_query_usage` | 조회 사용량 |
| `subscription_payments` | 결제 내역 |
| `company_view_history` | 기업 조회 이력 |

### 크레딧 시스템 - 토스 (3개)

| 테이블 | 설명 |
|--------|------|
| `credit_transactions` | 크레딧 거래 |
| `report_views` | 리포트 조회 |
| `credit_products` | 크레딧 상품 |

### 뉴스 (5개)

| 테이블 | 설명 |
|--------|------|
| `news_articles` | 뉴스 기사 |
| `news_entities` | 뉴스 엔티티 |
| `news_relations` | 뉴스 관계 |
| `news_risks` | 뉴스 리스크 |
| `news_company_complexity` | 뉴스 기업 복잡도 |

### 운영/기타 (12개)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `disclosures` | 279,148 | DART 공시 |
| `disclosure_parsed_data` | - | 공시 파싱 데이터 |
| `crawl_jobs` | - | 크롤링 작업 |
| `stock_prices` | 129,150 | 주가 데이터 |
| `service_applications` | - | 서비스 신청 |
| `page_contents` | - | 페이지 콘텐츠 |
| `site_settings` | - | 사이트 설정 |
| `pipeline_runs` | - | 파이프라인 실행 |
| `script_execution_log` | - | 스크립트 실행 로그 |
| `ontology_objects` | - | 온톨로지 객체 |
| `ontology_links` | - | 온톨로지 관계 |
| `alembic_version` | - | 마이그레이션 이력 |

---

## RaymondsIndex 등급 분포

| 등급 | 점수 범위 | 기업 수 | 비율 |
|------|----------|--------|------|
| A++ | 95+ | 0 | 0.0% |
| A+ | 90-94 | 0 | 0.0% |
| A | 85-89 | 0 | 0.0% |
| A- | 80-84 | 11 | 0.2% |
| B+ | 70-79 | 101 | 1.9% |
| B | 60-69 | 311 | 5.9% |
| B- | 50-59 | 917 | 17.4% |
| C+ | 40-49 | 1,213 | 23.1% |
| C | <40 | 2,704 | 51.5% |
| **총계** | | **5,257** | 100% |

---

## RaymondsRisk 종합등급 분포 (4등급 체계)

| 등급 | 점수 범위 | 기업 수 | 평균 CB리스크 | 평균 총점 |
|------|----------|--------|--------------|----------|
| LOW_RISK (저위험) | 0-19 | 1,510 | 3.6점 | 8.0점 |
| RISK (위험) | 20-34 | 784 | 4.5점 | 28.1점 |
| MEDIUM_RISK (중위험) | 35-49 | 644 | 13.8점 | 40.9점 |
| HIGH_RISK (고위험) | 50+ | 162 | 24.0점 | 55.5점 |
| **총계** | | **3,100** | | |

### CB 리스크 점수 구성 (2026-02 개편)

| 항목 | 배점 | 계산 기준 |
|------|------|----------|
| 발행 빈도 | 25점 | CB 발행 횟수 (4회+ → 25점) |
| 발행 규모 | 25점 | 총 발행금액 (200억+ → 25점) |
| **투자자 품질** | **30점** | **인수대상자 수량 기반 (2026-02 개편)** |
| 적자기업 연결 | 20점 | 관련 적자기업 수 |

**투자자품질 점수 기준:**
- 50명 이상: 30점 (초대규모 네트워크)
- 20-49명: 25점 (대규모)
- 10-19명: 20점 (중대규모)
- 5-9명: 15점 (중규모)
- 2-4명: 10점 (소규모)
- 1명: 5점 (단독)

---

## 기업 유형별 분류

| company_type | 설명 | 기업 수 |
|--------------|------|--------|
| NORMAL | 일반 상장사 | ~2,600 |
| SPAC | 기업인수목적회사 | 80 |
| REIT | 부동산투자회사 | 42 |
| ETF | 상장지수펀드 | 88 (관리 대상) |

### 파싱 제외 규칙

| 데이터 유형 | 제외 유형 |
|------------|----------|
| 임원 (officers) | SPAC, REIT, ETF |
| 대주주 (shareholders) | ETF |
| 재무 (financials) | ETF |
| RaymondsIndex | SPAC, REIT, ETF |

---

## Neo4j 그래프 데이터

| 노드/관계 | 개수 | 설명 |
|----------|------|------|
| Company 노드 | 3,109 | 기업 |
| Officer 노드 | 49,446 | 임원 |
| WORKS_AT 관계 | 75,059 | 재직 이력 |
| OWNS_SHARES 관계 | 60,214 | 지분 보유 |
| SUBSCRIBES_CB 관계 | 7,021 | CB 인수 |

---

## 데이터 파이프라인 일정

| 분기 | 보고서 마감 | 파이프라인 실행 |
|------|------------|----------------|
| Q1 | 5월 15일 | 5월 20일 |
| Q2 (반기) | 8월 14일 | 8월 20일 |
| Q3 | 11월 14일 | 11월 20일 |
| Q4 (사업보고서) | 3월 31일 | 4월 5일 |

---

## 데이터 검증 쿼리

```sql
-- 전체 테이블 목록 확인
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 주요 테이블 레코드 수 확인
SELECT
  'companies' as table_name, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'raymonds_index', COUNT(*) FROM raymonds_index
UNION ALL SELECT 'financial_details', COUNT(*) FROM financial_details
ORDER BY table_name;

-- 기업 유형별 현황
SELECT
  listing_status,
  company_type,
  COUNT(*)
FROM companies
GROUP BY listing_status, company_type
ORDER BY listing_status, company_type;
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-02-05 | **경영분쟁 임원 수집 시스템 추가** (egm_disclosures 393건, dispute_officers 391건) |
| 2026-02-05 | 그래프 UI에 경영분쟁 참여 배지 표시 기능 추가 |
| 2026-02-02 | CB 투자자품질 점수 계산식 개편 (high_risk_ratio → subscriber_count) |
| 2026-02-02 | RaymondsRisk 종합등급 분포 섹션 추가 |
| 2026-01-24 | 문서 재구조화: 43개 테이블 전체 목록 반영 |
| 2026-01-21 | 유령기업 39개 + 상장폐지 774개 삭제 (총 813개) |
| 2026-01-21 | RaymondsIndex v2.1 계산 완료 (5,257건) |
| 2026-01-15 | financial_details XBRL v3.0 파서 적용 |

---

## 관련 문서

- [SRD_Database.md](../technical/SRD_Database.md) - 테이블 스키마 상세
- [BACKEND README](../apps/backend/README.md) - 백엔드 모델 목록

---

*이 문서는 데이터 현황의 단일 진실 공급원입니다. DB 변경 시 반드시 업데이트하세요.*
