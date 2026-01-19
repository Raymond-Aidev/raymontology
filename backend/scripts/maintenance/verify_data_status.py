#!/usr/bin/env python3
"""
데이터 상태 검증 스크립트

모든 테이블의 현재 상태를 확인하고 보고합니다.
세션 시작 시 또는 작업 전후에 실행하여 데이터 상태를 검증합니다.

사용법:
    python3 scripts/verify_data_status.py
    python3 scripts/verify_data_status.py --coverage  # 기업별 데이터 커버리지 포함
    python3 scripts/verify_data_status.py --compare BEFORE_JSON  # 이전 상태와 비교

출력:
    - 모든 핵심 테이블의 레코드 수
    - 기업별 데이터 커버리지 (--coverage 옵션 시)
    - 상태 비교 결과 (--compare 옵션 시)
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 프로젝트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from scripts.utils.schema_validator import (
    TABLES,
    print_table_counts,
    print_count_comparison,
    compare_counts,
)


def get_db_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="raymontology_dev",
        user="postgres",
        password="dev_password",
    )


def get_all_table_counts(conn) -> dict:
    """모든 핵심 테이블의 레코드 수 조회"""
    counts = {}
    cursor = conn.cursor()

    for table in TABLES.values():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            result = cursor.fetchone()
            counts[table] = result[0] if result else 0
        except Exception as e:
            counts[table] = f"ERROR: {e}"

    cursor.close()
    return counts


def get_company_coverage(conn) -> dict:
    """기업별 데이터 커버리지 확인"""
    cursor = conn.cursor()
    coverage = {}

    # 전체 상장기업 수
    cursor.execute("""
        SELECT COUNT(*) FROM companies
        WHERE listing_status = 'Y' OR market IN ('KOSPI', 'KOSDAQ')
    """)
    coverage["total_listed_companies"] = cursor.fetchone()[0]

    # 임원 데이터 있는 기업 수
    cursor.execute("SELECT COUNT(DISTINCT company_id) FROM officer_positions")
    coverage["companies_with_officers"] = cursor.fetchone()[0]

    # CB 데이터 있는 기업 수
    cursor.execute("SELECT COUNT(DISTINCT company_id) FROM convertible_bonds")
    coverage["companies_with_cb"] = cursor.fetchone()[0]

    # 공시 데이터 있는 기업 수 (disclosures는 corp_code 사용)
    cursor.execute("SELECT COUNT(DISTINCT corp_code) FROM disclosures")
    coverage["companies_with_disclosures"] = cursor.fetchone()[0]

    # 임원 데이터 없는 상장기업 목록 (샘플)
    cursor.execute("""
        SELECT c.corp_code, c.name
        FROM companies c
        WHERE (c.listing_status = 'Y' OR c.market IN ('KOSPI', 'KOSDAQ'))
        AND c.id NOT IN (SELECT DISTINCT company_id FROM officer_positions)
        LIMIT 10
    """)
    coverage["sample_companies_without_officers"] = cursor.fetchall()

    cursor.close()
    return coverage


def get_duplicate_stats(conn) -> dict:
    """중복 레코드 통계"""
    cursor = conn.cursor()
    stats = {}

    # officer_positions 중복 확인
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(*) - COUNT(DISTINCT (officer_id, company_id, position, COALESCE(birth_date, ''))) as duplicates
        FROM officer_positions
    """)
    result = cursor.fetchone()
    stats["officer_positions"] = {
        "total": result[0],
        "duplicates": result[1],
        "unique": result[0] - result[1],
    }

    cursor.close()
    return stats


def save_status_to_file(counts: dict, filepath: str):
    """상태를 JSON 파일로 저장"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "counts": counts,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n상태 저장됨: {filepath}")


def load_status_from_file(filepath: str) -> dict:
    """JSON 파일에서 상태 로드"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("counts", {})


def main():
    parser = argparse.ArgumentParser(description="데이터 상태 검증")
    parser.add_argument("--coverage", action="store_true", help="기업별 데이터 커버리지 확인")
    parser.add_argument("--duplicates", action="store_true", help="중복 레코드 통계")
    parser.add_argument("--compare", type=str, help="이전 상태 JSON 파일과 비교")
    parser.add_argument("--save", type=str, help="현재 상태를 JSON 파일로 저장")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    # DB 연결
    conn = get_db_connection()

    try:
        # 현재 테이블 상태 조회
        counts = get_all_table_counts(conn)

        if args.json:
            # JSON 형식 출력
            output = {
                "timestamp": datetime.now().isoformat(),
                "counts": counts,
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return

        # 테이블 현황 출력
        print_table_counts(counts, f"데이터 상태 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

        # 이전 상태와 비교
        if args.compare:
            before_counts = load_status_from_file(args.compare)
            comparison = compare_counts(before_counts, counts)
            print_count_comparison(comparison, "변경 사항")

        # 기업별 커버리지
        if args.coverage:
            coverage = get_company_coverage(conn)
            print("\n" + "=" * 50)
            print(" 기업별 데이터 커버리지")
            print("=" * 50)
            print(f"  전체 상장기업: {coverage['total_listed_companies']:,}개")
            print(f"  임원 데이터 있음: {coverage['companies_with_officers']:,}개 "
                  f"({coverage['companies_with_officers']/coverage['total_listed_companies']*100:.1f}%)")
            print(f"  CB 데이터 있음: {coverage['companies_with_cb']:,}개 "
                  f"({coverage['companies_with_cb']/coverage['total_listed_companies']*100:.1f}%)")
            print(f"  공시 데이터 있음: {coverage['companies_with_disclosures']:,}개 "
                  f"({coverage['companies_with_disclosures']/coverage['total_listed_companies']*100:.1f}%)")

            if coverage["sample_companies_without_officers"]:
                print("\n  [임원 데이터 없는 기업 샘플]")
                for corp_code, name in coverage["sample_companies_without_officers"]:
                    print(f"    - {name} ({corp_code})")
            print("=" * 50)

        # 중복 통계
        if args.duplicates:
            stats = get_duplicate_stats(conn)
            print("\n" + "=" * 50)
            print(" 중복 레코드 통계")
            print("=" * 50)
            for table, data in stats.items():
                if isinstance(data, dict):
                    print(f"  {table}:")
                    print(f"    총 레코드: {data['total']:,}건")
                    print(f"    중복 레코드: {data['duplicates']:,}건 ({data['duplicates']/data['total']*100:.1f}%)")
                    print(f"    고유 레코드: {data['unique']:,}건")
            print("=" * 50)

        # 상태 저장
        if args.save:
            save_status_to_file(counts, args.save)

        # 검증 결과 요약
        print("\n" + "=" * 50)
        print(" 검증 결과")
        print("=" * 50)

        issues = []

        # 데이터 없는 테이블 확인
        empty_tables = [t for t, c in counts.items() if isinstance(c, int) and c == 0]
        if empty_tables:
            issues.append(f"데이터 없는 테이블: {empty_tables}")

        # 에러 발생 테이블 확인
        error_tables = [t for t, c in counts.items() if isinstance(c, str) and "ERROR" in c]
        if error_tables:
            issues.append(f"에러 발생 테이블: {error_tables}")

        if issues:
            print("  ⚠️ 주의사항:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✅ 모든 테이블 정상")

        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
