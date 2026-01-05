#!/usr/bin/env python3
"""
meta.json 스키마 통일 마이그레이션 스크립트

목표: 모든 meta.json 파일을 schema_version 2.0으로 업데이트

현재 스키마 (v1.0):
{
    "corp_code": "00317681",
    "corp_name": "메타바이오메드",
    "stock_code": "059210",
    "corp_cls": "K",
    "report_nm": "사업보고서 (2023.12)",
    "rcept_no": "20240409002052",
    "flr_nm": "제출자명",
    "rcept_dt": "20240409",
    "rm": ""
}

목표 스키마 (v2.0):
{
    "rcept_no": "20240409002052",
    "corp_code": "00317681",
    "corp_name": "회사명",
    "stock_code": "012720",
    "report_type": "annual_2023",
    "report_nm": "사업보고서 (2023.12)",
    "rcept_dt": "20240409",
    "flr_nm": "제출자명",
    "file_size": 54885,
    "xml_count": 1,
    "downloaded_at": "2025-11-16T13:09:23.792942",
    "schema_version": "2.0"
}

사용법:
    python scripts/maintenance/migrate_meta_schema.py --dry-run  # 테스트
    python scripts/maintenance/migrate_meta_schema.py            # 실행
    python scripts/maintenance/migrate_meta_schema.py --stats    # 통계만
"""

import argparse
import json
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'dart'
SCHEMA_VERSION = "2.0"


def detect_report_type(report_nm: str, rcept_dt: str) -> str:
    """보고서 유형 감지

    Args:
        report_nm: 보고서명 (예: "사업보고서 (2023.12)")
        rcept_dt: 접수일 (예: "20240409")

    Returns:
        report_type (예: "annual_2023", "q1_2024", "cb_disclosure")
    """
    # 사업보고서
    if '사업보고서' in report_nm:
        # (2023.12) 패턴에서 연도 추출
        match = re.search(r'\((\d{4})\.\d{1,2}\)', report_nm)
        if match:
            return f"annual_{match.group(1)}"
        # 연도 추출 실패시 접수일 기준
        year = int(rcept_dt[:4]) - 1  # 사업보고서는 전년도 기준
        return f"annual_{year}"

    # 분기보고서
    if '분기보고서' in report_nm:
        match = re.search(r'\((\d{4})\.\d{1,2}\)', report_nm)
        year = match.group(1) if match else rcept_dt[:4]
        if '1분기' in report_nm or '03.' in report_nm:
            return f"q1_{year}"
        elif '3분기' in report_nm or '09.' in report_nm:
            return f"q3_{year}"
        return f"q1_{year}"  # 기본값

    # 반기보고서
    if '반기보고서' in report_nm:
        match = re.search(r'\((\d{4})\.\d{1,2}\)', report_nm)
        year = match.group(1) if match else rcept_dt[:4]
        return f"q2_{year}"

    # CB 관련
    if '전환사채' in report_nm or 'CB' in report_nm or '신주인수권' in report_nm:
        return "cb_disclosure"

    # 감사보고서
    if '감사보고서' in report_nm:
        match = re.search(r'\((\d{4})\.\d{1,2}\)', report_nm)
        year = match.group(1) if match else str(int(rcept_dt[:4]) - 1)
        return f"audit_{year}"

    # 기타
    return "other"


def get_zip_info(meta_path: Path) -> Tuple[Optional[int], Optional[int]]:
    """ZIP 파일 정보 조회

    Returns:
        (file_size, xml_count)
    """
    zip_path = meta_path.with_name(meta_path.name.replace('_meta.json', '.zip'))

    if not zip_path.exists():
        return None, None

    try:
        file_size = zip_path.stat().st_size

        with zipfile.ZipFile(zip_path, 'r') as zf:
            xml_count = sum(1 for n in zf.namelist() if n.endswith('.xml'))

        return file_size, xml_count
    except Exception as e:
        logger.debug(f"ZIP info error: {zip_path}: {e}")
        return None, None


def migrate_meta_file(meta_path: Path, dry_run: bool = False) -> Dict:
    """단일 meta.json 파일 마이그레이션

    Returns:
        {'status': 'migrated'|'skipped'|'error', 'reason': str}
    """
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 이미 v2.0인 경우 스킵
        if data.get('schema_version') == SCHEMA_VERSION:
            return {'status': 'skipped', 'reason': 'already_v2'}

        # 새 스키마로 변환
        new_data = {
            'rcept_no': data.get('rcept_no', ''),
            'corp_code': data.get('corp_code', ''),
            'corp_name': data.get('corp_name', ''),
            'stock_code': data.get('stock_code', ''),
            'report_type': detect_report_type(
                data.get('report_nm', ''),
                data.get('rcept_dt', '')
            ),
            'report_nm': data.get('report_nm', ''),
            'rcept_dt': data.get('rcept_dt', ''),
            'flr_nm': data.get('flr_nm', ''),
        }

        # ZIP 파일 정보 추가
        file_size, xml_count = get_zip_info(meta_path)
        if file_size is not None:
            new_data['file_size'] = file_size
        if xml_count is not None:
            new_data['xml_count'] = xml_count

        # 메타데이터 추가
        new_data['downloaded_at'] = data.get('downloaded_at', datetime.now().isoformat())
        new_data['schema_version'] = SCHEMA_VERSION

        # 기존 필드 중 유지할 것들
        if 'target_year' in data:
            new_data['target_year'] = data['target_year']

        if not dry_run:
            # 백업 생성
            backup_path = meta_path.with_suffix('.json.bak')
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            # 새 스키마로 저장
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

        return {'status': 'migrated', 'reason': 'success'}

    except Exception as e:
        return {'status': 'error', 'reason': str(e)}


def run_migration(dry_run: bool = False, sample: int = None):
    """메인 마이그레이션 프로세스"""
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}meta.json 스키마 마이그레이션 시작")

    stats = {
        'total': 0,
        'migrated': 0,
        'skipped': 0,
        'errors': 0,
    }

    meta_files = list(DART_DATA_DIR.rglob('*_meta.json'))

    if sample:
        meta_files = meta_files[:sample]
        logger.info(f"샘플 모드: {sample}개만 처리")

    logger.info(f"총 meta.json 파일: {len(meta_files):,}개")

    for i, meta_path in enumerate(meta_files):
        if (i + 1) % 10000 == 0:
            logger.info(f"진행: {i+1:,}/{len(meta_files):,} ({(i+1)/len(meta_files)*100:.1f}%)")

        result = migrate_meta_file(meta_path, dry_run=dry_run)
        stats['total'] += 1
        stats[result['status']] = stats.get(result['status'], 0) + 1

        if result['status'] == 'error':
            logger.warning(f"오류: {meta_path}: {result['reason']}")

    logger.info("\n=== 마이그레이션 결과 ===")
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}총 파일: {stats['total']:,}")
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}마이그레이션: {stats['migrated']:,}")
    logger.info(f"스킵 (이미 v2.0): {stats['skipped']:,}")
    logger.info(f"오류: {stats['errors']:,}")

    return stats


def show_stats():
    """현재 스키마 통계"""
    from collections import Counter

    schema_counter = Counter()
    total = 0

    for meta_path in DART_DATA_DIR.rglob('*_meta.json'):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            version = data.get('schema_version', 'v1.0')
            schema_counter[version] += 1
            total += 1
        except:
            schema_counter['error'] += 1

    print(f"\n=== meta.json 스키마 통계 ===")
    print(f"총 파일: {total:,}")
    for version, count in schema_counter.most_common():
        pct = count / total * 100 if total > 0 else 0
        print(f"  {version}: {count:,} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='meta.json 스키마 마이그레이션')
    parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 시뮬레이션')
    parser.add_argument('--sample', type=int, help='샘플 개수 (테스트용)')
    parser.add_argument('--stats', action='store_true', help='통계만 표시')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    run_migration(dry_run=args.dry_run, sample=args.sample)


if __name__ == '__main__':
    main()
