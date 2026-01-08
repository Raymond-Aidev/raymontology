#!/usr/bin/env python3
"""
누락된 기업 사업보고서 다운로드 스크립트
대상: 우선순위 높음 (대기업 5개) + 중간 (신규 상장사 2개)
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# DART API 설정
DART_API_KEY = os.environ.get('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
BASE_URL = "https://opendart.fss.or.kr/api"

# 다운로드 대상 기업
TARGET_CORPS = {
    # 우선순위 높음: 대기업 (2024, 2025년 누락)
    "00113410": "CJ대한통운",
    "00155319": "POSCO홀딩스",
    "00360595": "현대글로비스",
    "00164742": "현대자동차",
    "00164779": "SK하이닉스",
    # 우선순위 중간: 신규 상장사 (2024년 누락)
    "01810477": "노타",
    "01872459": "본시스템즈",
}

# 대상 연도
TARGET_YEARS = [2024, 2025]

# 저장 경로
DATA_DIR = Path(__file__).parent.parent / "data" / "dart" / "batch_missing"


def get_disclosure_list(corp_code: str, year: int) -> list:
    """특정 기업의 사업보고서 목록 조회"""
    url = f"{BASE_URL}/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": f"{year}0101",
        "end_de": f"{year}1231",
        "pblntf_ty": "A",  # 정기공시
        "page_count": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "000":
            return data.get("list", [])
        else:
            print(f"  API 오류: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"  요청 실패: {e}")
        return []


def download_document(rcept_no: str, save_path: Path) -> bool:
    """문서 ZIP 다운로드"""
    url = f"{BASE_URL}/document.xml"
    params = {
        "crtfc_key": DART_API_KEY,
        "rcept_no": rcept_no,
    }

    try:
        response = requests.get(url, params=params, timeout=60, stream=True)
        content_type = response.headers.get('Content-Type', '')

        # ZIP 파일 유형: application/zip, application/x-msdownload 등
        valid_types = ['application/zip', 'application/x-msdownload', 'application/octet-stream']
        is_valid = response.status_code == 200 and any(t in content_type for t in valid_types)

        if is_valid:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"    다운로드 실패: status={response.status_code}, type={content_type}")
            return False
    except Exception as e:
        print(f"    다운로드 오류: {e}")
        return False


def save_meta(disclosure: dict, save_path: Path):
    """메타 정보 저장"""
    import json
    meta_path = save_path.with_suffix('.zip_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(disclosure, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("누락 기업 사업보고서 다운로드")
    print(f"대상: {len(TARGET_CORPS)}개 기업, 연도: {TARGET_YEARS}")
    print("=" * 60)
    print()

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    for corp_code, corp_name in TARGET_CORPS.items():
        print(f"\n[{corp_name}] ({corp_code})")

        for year in TARGET_YEARS:
            print(f"  {year}년 공시 조회 중...")

            # 이미 다운로드된 파일 확인
            corp_dir = DATA_DIR / corp_code / str(year)
            if corp_dir.exists() and list(corp_dir.glob("*.zip")):
                print(f"    → 이미 다운로드됨, 스킵")
                total_skipped += 1
                continue

            disclosures = get_disclosure_list(corp_code, year)

            # 사업보고서 필터링
            annual_reports = [d for d in disclosures if "사업보고서" in d.get("report_nm", "")]

            if not annual_reports:
                print(f"    → 사업보고서 없음")
                continue

            print(f"    사업보고서 {len(annual_reports)}건 발견")

            for disclosure in annual_reports:
                rcept_no = disclosure["rcept_no"]
                report_nm = disclosure["report_nm"]

                # 저장 경로
                # 실제 제출 연도 추출 (rcept_dt 기준)
                rcept_dt = disclosure.get("rcept_dt", "")
                actual_year = rcept_dt[:4] if rcept_dt else str(year)
                save_dir = DATA_DIR / corp_code / actual_year
                save_path = save_dir / f"{rcept_no}.zip"

                if save_path.exists():
                    print(f"    [{rcept_no}] 이미 존재, 스킵")
                    total_skipped += 1
                    continue

                print(f"    [{rcept_no}] {report_nm} 다운로드 중...")

                if download_document(rcept_no, save_path):
                    save_meta(disclosure, save_path)
                    file_size = save_path.stat().st_size / 1024
                    print(f"    → 완료 ({file_size:.1f} KB)")
                    total_downloaded += 1
                else:
                    total_failed += 1

                # API 호출 간격
                time.sleep(0.5)

    print()
    print("=" * 60)
    print(f"완료: 다운로드 {total_downloaded}건, 스킵 {total_skipped}건, 실패 {total_failed}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
