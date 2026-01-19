# Maintenance Scripts (유지보수)

데이터 검증, 정리, 관리 스크립트입니다.

## 파일 패턴
- `cleanup_*` - 중복/오류 데이터 정리
- `verify_*` - 데이터 검증
- `validate_*` - 유효성 검사
- `final_*` - 최종 검증
- `create_*` - 관리 데이터 생성
- `consolidate_*` - 데이터 통합

## 주요 스크립트

| 스크립트 | 용도 |
|---------|------|
| `verify_data_status.py` | 전체 데이터 상태 확인 |
| `cleanup_duplicate_positions.py` | 중복 포지션 정리 |
| `cleanup_duplicate_cbs.py` | 중복 CB 정리 |
| `validate_kospi_kosdaq_data.py` | 시장 데이터 검증 |
| `create_admin_user.py` | 관리자 계정 생성 |
| `verify_officer_company_match.py` | 임원-회사 매칭 검증 |

## 사용 예시
```bash
cd backend
source .venv/bin/activate

# 데이터 상태 확인
DATABASE_URL="..." python scripts/maintenance/verify_data_status.py

# 중복 데이터 정리
DATABASE_URL="..." python scripts/maintenance/cleanup_duplicate_positions.py --dry-run
```

## 주의사항
- `cleanup_*` 스크립트는 `--dry-run` 옵션으로 먼저 테스트
- 프로덕션 DB 작업 전 반드시 백업 확인
