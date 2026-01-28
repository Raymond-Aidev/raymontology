# BACKEND (Raymontology API 서버)

> 경로: `backend/` | 배포: https://raymontology-production.up.railway.app | 완성도: 95%

---

## 개요

Raymontology 서비스의 백엔드 API 서버입니다. FastAPI 기반으로 PostgreSQL과 Neo4j를 사용합니다.

---

## 기술 스택

| 카테고리 | 기술 | 버전 |
|----------|------|------|
| 프레임워크 | FastAPI | 최신 |
| 주 데이터베이스 | PostgreSQL | 15 |
| 그래프 데이터베이스 | Neo4j | 5.x |
| ORM | SQLAlchemy | 2.x |
| 캐시 | Redis | (옵션) |
| 호스팅 | Railway | - |

---

## 데이터베이스 모델 (38개 클래스 / 43개 테이블)

### 핵심 모델
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `Company` | `companies` | 기업 마스터 |
| `Officer` | `officers` | 임원 정보 |
| `OfficerPosition` | `officer_positions` | 임원 직위 이력 |
| `Disclosure` | `disclosures` | DART 공시 |
| `DisclosureParsedData` | `disclosure_parsed_data` | 공시 파싱 데이터 |
| `CrawlJob` | `crawl_jobs` | 크롤링 작업 |
| `FinancialStatement` | `financial_statements` | 재무제표 요약 |
| `FinancialDetails` | `financial_details` | 재무제표 상세 (XBRL) |
| `StockPrice` | `stock_prices` | 주가 데이터 |

### 리스크 관련
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `RiskScore` | `risk_scores` | 리스크 점수 |
| `RiskSignal` | `risk_signals` | 리스크 신호 |
| `ConvertibleBond` | `convertible_bonds` | 전환사채 |
| `CBSubscriber` | `cb_subscribers` | CB 인수인 |
| `MajorShareholder` | `major_shareholders` | 대주주 |
| `LargestShareholderInfo` | `largest_shareholder_info` | 최대주주 법인 정보 |
| `Affiliate` | `affiliates` | 계열사 |

### RaymondsIndex 관련
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `RaymondsIndex` | `raymonds_index` | 자본배분효율성 지수 v2 |
| `RaymondsIndexV3` | `raymonds_index_v3` | 자본배분효율성 지수 v3 |
| `FinancialRatios` | `financial_ratios` | 재무비율 |

### 사용자/인증
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `User` | `users` | 사용자 |
| `PasswordResetToken` | `password_reset_tokens` | 비밀번호 재설정 토큰 |
| `EmailVerificationToken` | `email_verification_tokens` | 이메일 인증 토큰 |
| `TossUser` | `toss_users` | 토스 사용자 |

### 구독/결제
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `UserQueryUsage` | `user_query_usage` | 조회 사용량 |
| `SubscriptionPayment` | `subscription_payments` | 결제 내역 |
| `CompanyViewHistory` | `company_view_history` | 기업 조회 이력 |

### 크레딧 시스템 (토스)
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `CreditTransaction` | `credit_transactions` | 크레딧 거래 |
| `ReportView` | `report_views` | 리포트 조회 |
| `CreditProduct` | `credit_products` | 크레딧 상품 |

### 뉴스
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `NewsArticle` | `news_articles` | 뉴스 기사 |
| `NewsEntity` | `news_entities` | 뉴스 엔티티 |
| `NewsRelation` | `news_relations` | 뉴스 관계 |
| `NewsRisk` | `news_risks` | 뉴스 리스크 |
| `NewsCompanyComplexity` | `news_company_complexity` | 뉴스 기업 복잡도 |

### 운영/기타
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `ServiceApplication` | `service_applications` | 서비스 신청 |
| `PageContent` | `page_contents` | 페이지 콘텐츠 |
| `SiteSetting` | `site_settings` | 사이트 설정 |
| `PipelineRun` | `pipeline_runs` | 파이프라인 실행 이력 |
| - | `company_labels` | 기업 라벨 |
| - | `script_execution_log` | 스크립트 실행 로그 |

### 온톨로지
| 모델 | 테이블 | 설명 |
|------|--------|------|
| `OntologyObject` | `ontology_objects` | 온톨로지 객체 |
| `OntologyLink` | `ontology_links` | 온톨로지 관계 |

---

## API 엔드포인트 (13개 모듈)

### 기업 정보
| 엔드포인트 | 파일 | 설명 |
|-----------|------|------|
| `/api/companies` | `companies.py` | 기업 검색/조회/고위험 기업 |
| `/api/company-report` | `company_report.py` | 기업 상세 리포트 |
| `/api/officers` | `officers.py` | 임원 정보 |

### 재무/리스크
| 엔드포인트 | 파일 | 설명 |
|-----------|------|------|
| `/api/financials` | `financials.py` | 재무제표 |
| `/api/financial-ratios` | `financial_ratios.py` | 재무비율 |
| `/api/risks` | `risks.py` | 리스크 신호/점수 |
| `/api/convertible-bonds` | `convertible_bonds.py` | 전환사채 |
| `/api/cb-subscribers` | `cb_subscribers.py` | CB 인수인 |

### RaymondsIndex
| 엔드포인트 | 파일 | 설명 |
|-----------|------|------|
| `/api/raymonds-index` | `raymonds_index.py` | 인덱스 조회/스크리너/랭킹 |

### 그래프/기타
| 엔드포인트 | 파일 | 설명 |
|-----------|------|------|
| `/api/graph` | `graph.py` | Neo4j 그래프 쿼리 |
| `/api/graph-fallback` | `graph_fallback.py` | PostgreSQL 폴백 |
| `/api/stock-prices` | `stock_prices.py` | 주가 데이터 |
| `/api/news` | `news.py` | 뉴스 |

---

## Routes (15개 모듈)

### 인증/사용자
| 라우트 | 파일 | 설명 |
|--------|------|------|
| `/auth` | `auth.py` | 로그인/로그아웃/토큰 갱신 |
| `/oauth` | `oauth.py` | Google/Kakao/Naver OAuth |
| `/toss-auth` | `toss_auth.py` | 토스 로그인 연동 |

### 구독/결제
| 라우트 | 파일 | 설명 |
|--------|------|------|
| `/subscription` | `subscription.py` | 구독 관리/결제 |
| `/credits` | `credits.py` | 크레딧 충전/사용 |

### 데이터/콘텐츠
| 라우트 | 파일 | 설명 |
|--------|------|------|
| `/companies` | `companies.py` | 기업 라우트 |
| `/disclosures` | `disclosures.py` | 공시 조회 |
| `/content` | `content.py` | 페이지 콘텐츠 |
| `/view-history` | `view_history.py` | 조회 이력 |

### 관리/운영
| 라우트 | 파일 | 설명 |
|--------|------|------|
| `/admin` | `admin.py` | 관리자 기능 |
| `/monitoring` | `monitoring.py` | 시스템 모니터링 |
| `/service-application` | `service_application.py` | 서비스 신청 |

### 내부 도구
| 라우트 | 파일 | 설명 |
|--------|------|------|
| `/risk` | `risk.py` | 리스크 계산 트리거 |
| `/parser` | `parser.py` | 파서 실행 |
| `/crawl` | `crawl.py` | 크롤링 실행 |

---

## 서비스 모듈 (14개)

| 서비스 | 파일 | 설명 |
|--------|------|------|
| `company_service` | `company_service.py` | 기업 비즈니스 로직 |
| `risk_engine` | `risk_engine.py` | 리스크 분석 엔진 |
| `risk_detection` | `risk_detection.py` | 리스크 신호 탐지 |
| `raymonds_index_calculator` | `raymonds_index_calculator.py` | 인덱스 계산 |
| `financial_metrics` | `financial_metrics.py` | 재무 지표 계산 |
| `financial_ratios_calculator` | `financial_ratios_calculator.py` | 재무비율 계산 |
| `dart_financial_parser` | `dart_financial_parser.py` | DART 재무 파싱 |
| `stock_price_collector` | `stock_price_collector.py` | 주가 수집 |
| `usage_service` | `usage_service.py` | 조회 이력/제한 관리 |
| `payment_service` | `payment_service.py` | 결제 처리 |
| `email_service` | `email_service.py` | 이메일 발송 |
| `slack_notifier` | `slack_notifier.py` | Slack 알림 |
| `cache_service` | `cache_service.py` | Redis 캐시 |
| `toss_api_client` | `toss_api_client.py` | 토스 API 클라이언트 |

---

## 스크립트 구조 (127개)

### 테마별 폴더
| 폴더 | 스크립트 수 | 용도 |
|------|------------|------|
| `pipeline/` | 9 | 분기별 데이터 처리 자동화 |
| `parsers/` | 9 | 구조화된 파서 모듈 |
| `parsing/` | 25 | 레거시 파싱 스크립트 |
| `collection/` | 15 | 데이터 수집 |
| `analysis/` | 12 | 데이터 분석 |
| `sync/` | 9 | DB 동기화 |
| `enrichment/` | 8 | 데이터 보강 |
| `maintenance/` | 15 | 유지보수 |
| `utils/` | 4 | 유틸리티 |
| `_deprecated/` | 10 | 사용 금지 |

### 주요 파이프라인 스크립트
```bash
# 분기별 전체 파이프라인
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025

# 개별 단계
python -m scripts.pipeline.download_quarterly_reports --quarter Q1 --year 2025
python -m scripts.pipeline.run_unified_parser --quarter Q1 --year 2025
python -m scripts.pipeline.validate_parsed_data --quarter Q1 --year 2025
python -m scripts.pipeline.calculate_index --year 2025
```

---

## 개발 명령어

```bash
cd backend

# 가상환경 활성화
source .venv/bin/activate

# 개발 서버
uvicorn app.main:app --reload --port 8000

# 프로덕션 서버
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 테스트
pytest

# 린트
ruff check .
```

---

## 환경 변수

```env
# 데이터베이스
DATABASE_URL=postgresql://user:pass@host:port/db
NEO4J_URI=bolt://host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# 외부 API
DART_API_KEY=...
TOSS_CLIENT_ID=...
TOSS_CLIENT_SECRET=...

# 인증
JWT_SECRET=...
GOOGLE_CLIENT_ID=...
KAKAO_CLIENT_ID=...

# 기타
REDIS_URL=...
SLACK_WEBHOOK_URL=...
```

---

## 배포 (Railway)

- **프로덕션 URL**: https://raymontology-production.up.railway.app
- **자동 배포**: main 브랜치 push 시 자동 배포
- **환경 변수**: Railway 대시보드에서 관리

---

## 데이터 흐름

```
DART API → 다운로드 → 파싱 → PostgreSQL → Neo4j 동기화
                              ↓
                        API 서비스
                              ↓
                    프론트엔드 (RISK-WEB, INDEX-WEB, RISK-APP)
```

---

## 관련 문서

- [SCHEMA_REGISTRY.md](../../scripts/SCHEMA_REGISTRY.md) - 테이블 스키마
- [STANDARD_PROCESS.md](../../scripts/STANDARD_PROCESS.md) - 표준 작업 프로세스
- [COMPANY_MANAGEMENT.md](../../scripts/COMPANY_MANAGEMENT.md) - 기업 관리
- [SRD_Database.md](../../technical/SRD_Database.md) - DB 스키마 상세

---

*마지막 업데이트: 2026-01-24*
