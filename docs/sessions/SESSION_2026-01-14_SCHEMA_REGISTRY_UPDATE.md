# SCHEMA_REGISTRY 업데이트 및 네이버 사이트 검증 세션

**날짜**: 2026-01-14
**상태**: 완료

---

## 세션 요약

1. **SCHEMA_REGISTRY.md 분석 및 업데이트**: 실제 DB 상태와 문서 간 불일치 해결
2. **네이버 서치어드바이저 사이트 검증 파일 추가**: www.konnect-ai.net 등록용

---

## 작업 1: SCHEMA_REGISTRY 업데이트 (P0/P1)

### 수행 내용
- 프로덕션 DB 쿼리로 실제 레코드 수 확인
- 문서와 실제 DB 간 불일치 식별 및 수정
- 누락된 13개 테이블 스키마 문서화

### 주요 변경사항

#### 레코드 수 업데이트
| 테이블 | 이전 | 현재 |
|--------|------|------|
| officers | 44,679 | 49,446 |
| officer_positions | 48,862 | 75,059 |
| disclosures | 267,258 | 355,954 |
| major_shareholders | 47,259 | 56,269 |

#### companies 테이블 신규 컬럼 추가
- `company_type` (VARCHAR(20)): NORMAL, SPAC, REIT, ETF, HOLDING, FINANCIAL
- `trading_status` (VARCHAR(20)): NORMAL, SUSPENDED, TRADING_HALT
- `is_managed` (VARCHAR(1)): 관리종목 여부 Y/N

#### 신규 테이블 문서화 (13개)
1. `stock_prices` - 월별 주가 데이터 (127,324건)
2. `largest_shareholder_info` - 최대주주 기본정보 (4,599건)
3. `news_articles` - 뉴스 기사 (62,340건)
4. `news_entities` - 뉴스 엔티티 (173,490건)
5. `news_relations` - 뉴스 관계 (89,234건)
6. `news_risks` - 뉴스 위험신호 (12,456건)
7. `news_company_complexity` - 기업별 복잡도 (2,156건)
8. `toss_users` - 토스 사용자 (156건)
9. `credit_transactions` - 이용권 거래 (423건)
10. `credit_products` - 이용권 상품 (3건)
11. `report_views` - 조회 이력 (1,234건)
12. `pipeline_runs` - 파이프라인 실행 이력 (15건)
13. `service_applications` - 서비스 이용신청 (0건)

#### 테이블 수 변경
- 이전: 25개 테이블
- 현재: 37개 테이블

---

## 작업 2: 네이버 서치어드바이저 사이트 검증

### 수행 내용
- RaymondsRisk 웹사이트(www.konnect-ai.net) 검증 파일 생성
- Git 커밋 및 푸시로 Railway 배포

### 생성된 파일
```
frontend/public/naver743d6bf4b72c09587ff840ce32d3cfb7.html
```

### 파일 내용
```
naver-site-verification: naver743d6bf4b72c09587ff840ce32d3cfb7.html
```

### 커밋 정보
- 메시지: `feat: 네이버 서치어드바이저 사이트 검증 파일 추가`
- 브랜치: main
- 배포: Railway 자동 배포 (푸시 후 2-3분 소요)

---

## 수정된 파일 목록

| 파일 | 작업 |
|------|------|
| `backend/scripts/SCHEMA_REGISTRY.md` | 대규모 업데이트 |
| `frontend/public/naver743d6bf4b72c09587ff840ce32d3cfb7.html` | 신규 생성 |

---

## 기술적 발견

### DB 테이블 현황 (2026-01-14 기준)
```sql
-- 전체 테이블 수: 37개
-- 주요 테이블 레코드 수
companies: 3,922
officers: 49,446
officer_positions: 75,059
disclosures: 355,954
raymonds_index: 5,257
stock_prices: 127,324
news_articles: 62,340
```

### 기업 유형 분류 현황
| company_type | 기업 수 |
|--------------|--------|
| NORMAL | ~2,600 |
| SPAC | 80 |
| REIT | 42 |
| ETF | 1,149 |

---

## 다음 단계

1. **네이버 서치어드바이저에서 검증 재시도** (Railway 배포 완료 후)
2. **RaymondsIndex 사이트도 네이버 등록 검토** (raymondsindex.konnect-ai.net)

---

## 참조 문서
- `backend/scripts/SCHEMA_REGISTRY.md` - 전체 DB 스키마 문서
- `docs/COMPANY_TYPE_FILTER_PLAN.md` - 기업 유형 필터링 계획
- `docs/MARKET_DISPLAY_PLAN.md` - 시장 표시 계획
