# Enrichment Scripts (데이터 보강)

기존 데이터에 추가 정보를 보강하는 스크립트입니다.

## 파일 패턴
- `enrich_*` - 데이터 보강
- `update_*` - 데이터 업데이트
- `supplement_*` - 보충 데이터 추가
- `data_enrichment.py` - 범용 보강

## 주요 스크립트

| 스크립트 | 용도 |
|---------|------|
| `enrich_listed_companies.py` | 상장사 정보 보강 |
| `enrich_company_market.py` | 시장 구분 추가 |
| `enrich_officers_from_reports.py` | 임원 정보 보강 |
| `enrich_cb_issue_date.py` | CB 발행일 보강 |
| `update_market_classification.py` | 시장 분류 업데이트 |
| `supplement_cb_details.py` | CB 상세정보 보충 |

## 사용 예시
```bash
cd backend
source .venv/bin/activate

# 상장사 정보 보강
DATABASE_URL="..." python scripts/enrichment/enrich_listed_companies.py

# 시장 분류 업데이트
DATABASE_URL="..." python scripts/enrichment/update_market_classification.py
```
