# Collection Scripts (데이터 수집)

외부 API, 파일 시스템에서 데이터를 수집하는 스크립트입니다.

## 파일 패턴
- `download_*` - DART API에서 공시 다운로드
- `collect_*` - 외부 소스에서 데이터 수집
- `fetch_*` - API 데이터 조회
- `load_*` - 로컬 파일 로딩
- `import_*` - 외부 데이터 import
- `populate_*` - DB 초기 데이터 적재

## 주요 스크립트

| 스크립트 | 용도 |
|---------|------|
| `download_business_reports.py` | 사업보고서 일괄 다운로드 |
| `download_q3_reports_2025.py` | 2025년 3분기 보고서 |
| `collect_stock_prices.py` | KRX 주가 데이터 수집 |
| `collect_missing_officers.py` | 누락 임원 데이터 수집 |
| `fetch_all_companies.py` | 전체 상장사 목록 조회 |

## 사용 예시
```bash
cd backend
source .venv/bin/activate

# DART API 키 필요
export DART_API_KEY="your-api-key"
python scripts/collection/download_business_reports.py --year 2024
```

## 주의사항
- 대부분의 스크립트는 `DART_API_KEY` 환경변수 필요
- **분기별 수집은 `pipeline/run_quarterly_pipeline.py` 사용 권장**
