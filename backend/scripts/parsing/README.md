# Parsing Scripts (데이터 파싱)

DART 공시 원시 데이터를 구조화된 형식으로 파싱하는 스크립트입니다.

## 파일 패턴
- `parse_*` - 원시 데이터 파싱
- `reparse_*` - 기존 데이터 재파싱

## ⚠️ 권장사항

**새로운 파싱 작업은 `parsers/` 모듈 또는 `pipeline/` 사용을 권장합니다.**

```bash
# 권장: 통합 파서 사용
python -m scripts.parsers.unified --year 2024 --type all

# 권장: 파이프라인 사용
python -m scripts.pipeline.run_quarterly_pipeline --quarter Q1 --year 2025
```

## 레거시 스크립트 목록

| 스크립트 | 용도 | 대체 방법 |
|---------|------|----------|
| `parse_officers_from_local.py` | 임원 파싱 | `parsers/officer.py` |
| `parse_local_financial_details.py` | 재무 파싱 | `parsers/financial.py` |
| `parse_major_shareholders.py` | 대주주 파싱 | `parsers/shareholder.py` |
| `parse_cb_disclosures.py` | CB 파싱 | - |

## 버전 관리
- `_v2.py`, `_v3.py` 등 버전 접미사가 있는 경우 최신 버전 사용
- 예: `parse_426_officers.py` → `parse_426_officers_v3.py` 사용
