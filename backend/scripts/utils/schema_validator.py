"""
스키마 검증 유틸리티

모든 테이블 접근 시 이 모듈의 상수와 함수를 사용하여
테이블명 오류를 방지합니다.

사용 예:
    from scripts.utils.schema_validator import TABLES, validate_table_name, get_all_table_counts

    # 테이블명 검증
    table = validate_table_name("company")  # ValueError: Unknown table
    table = validate_table_name("companies")  # OK

    # 전체 테이블 COUNT
    counts = get_all_table_counts(connection)
"""

from typing import Dict, List, Optional
import asyncio

# =============================================================================
# 테이블명 상수 (하드코딩 방지)
# =============================================================================

TABLES = {
    # 핵심 테이블 (11개)
    "companies": "companies",
    "officers": "officers",
    "officer_positions": "officer_positions",
    "disclosures": "disclosures",
    "convertible_bonds": "convertible_bonds",
    "cb_subscribers": "cb_subscribers",
    "financial_statements": "financial_statements",
    "risk_signals": "risk_signals",
    "risk_scores": "risk_scores",
    "major_shareholders": "major_shareholders",
    "affiliates": "affiliates",
}

# 시스템 테이블 (직접 접근 금지)
SYSTEM_TABLES = {
    "alembic_version": "alembic_version",
    "users": "users",
    "crawl_jobs": "crawl_jobs",
    "disclosure_parsed_data": "disclosure_parsed_data",
    "ontology_links": "ontology_links",
    "ontology_objects": "ontology_objects",
    "script_execution_log": "script_execution_log",
}

# 자주 혼동되는 테이블명 매핑
COMMON_MISTAKES = {
    "company": "companies",
    "officer": "officers",
    "position": "officer_positions",
    "positions": "officer_positions",
    "cb": "convertible_bonds",
    "bond": "convertible_bonds",
    "bonds": "convertible_bonds",
    "subscriber": "cb_subscribers",
    "subscribers": "cb_subscribers",
    "disclosure": "disclosures",
    "shareholder": "major_shareholders",
    "shareholders": "major_shareholders",
    "affiliate": "affiliates",
    "financial": "financial_statements",
    "financials": "financial_statements",
    "risk": "risk_signals",
}


# =============================================================================
# 검증 함수
# =============================================================================

def validate_table_name(table_name: str) -> str:
    """
    테이블명이 올바른지 확인하고, 올바른 이름 반환.

    Args:
        table_name: 검증할 테이블명

    Returns:
        검증된 테이블명

    Raises:
        ValueError: 알 수 없는 테이블명일 경우
    """
    # 정확한 테이블명인 경우
    if table_name in TABLES.values():
        return table_name

    # 흔한 실수인 경우 올바른 이름 제안
    if table_name.lower() in COMMON_MISTAKES:
        correct_name = COMMON_MISTAKES[table_name.lower()]
        raise ValueError(
            f"테이블명 오류: '{table_name}'\n"
            f"올바른 이름: '{correct_name}'\n"
            f"SCHEMA_REGISTRY.md를 참조하세요."
        )

    # 유사한 이름 찾기
    suggestions = [t for t in TABLES.values() if table_name.lower() in t.lower()]

    if suggestions:
        raise ValueError(
            f"알 수 없는 테이블: '{table_name}'\n"
            f"유사한 테이블: {suggestions}\n"
            f"SCHEMA_REGISTRY.md를 참조하세요."
        )
    else:
        raise ValueError(
            f"알 수 없는 테이블: '{table_name}'\n"
            f"사용 가능한 테이블: {list(TABLES.values())}\n"
            f"SCHEMA_REGISTRY.md를 참조하세요."
        )


def suggest_correct_table_name(table_name: str) -> Optional[str]:
    """
    잘못된 테이블명에 대해 올바른 이름을 제안.

    Args:
        table_name: 확인할 테이블명

    Returns:
        올바른 테이블명 또는 None
    """
    if table_name in TABLES.values():
        return table_name

    if table_name.lower() in COMMON_MISTAKES:
        return COMMON_MISTAKES[table_name.lower()]

    return None


# =============================================================================
# DB 상태 조회 함수
# =============================================================================

def get_all_table_counts_sync(conn) -> Dict[str, int]:
    """
    모든 핵심 테이블의 레코드 수 조회 (동기 버전).

    Args:
        conn: psycopg2 또는 SQLAlchemy connection

    Returns:
        {테이블명: 레코드수} 딕셔너리
    """
    counts = {}
    cursor = conn.cursor() if hasattr(conn, 'cursor') else conn

    for table in TABLES.values():
        try:
            if hasattr(conn, 'cursor'):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                result = cursor.fetchone()
            else:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = result[0] if result else 0
        except Exception as e:
            counts[table] = f"ERROR: {e}"

    return counts


async def get_all_table_counts_async(conn) -> Dict[str, int]:
    """
    모든 핵심 테이블의 레코드 수 조회 (비동기 버전).

    Args:
        conn: asyncpg 또는 async SQLAlchemy connection

    Returns:
        {테이블명: 레코드수} 딕셔너리
    """
    counts = {}

    for table in TABLES.values():
        try:
            result = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            counts[table] = result or 0
        except Exception as e:
            counts[table] = f"ERROR: {e}"

    return counts


def get_table_counts_query() -> str:
    """
    모든 테이블 COUNT를 조회하는 SQL 쿼리 반환.

    Returns:
        UNION ALL로 연결된 COUNT 쿼리
    """
    queries = [
        f"SELECT '{table}' as tbl, COUNT(*) as cnt FROM {table}"
        for table in TABLES.values()
    ]
    return " UNION ALL ".join(queries) + " ORDER BY tbl"


def print_table_counts(counts: Dict[str, int], title: str = "테이블 현황") -> None:
    """
    테이블 COUNT를 보기 좋게 출력.

    Args:
        counts: {테이블명: 레코드수} 딕셔너리
        title: 출력 제목
    """
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

    total = 0
    for table in sorted(counts.keys()):
        count = counts[table]
        if isinstance(count, int):
            print(f"  {table:25s}: {count:>10,} 건")
            total += count
        else:
            print(f"  {table:25s}: {count}")

    print(f"{'='*50}")
    print(f"  {'합계':25s}: {total:>10,} 건")
    print(f"{'='*50}\n")


def compare_counts(before: Dict[str, int], after: Dict[str, int]) -> Dict[str, dict]:
    """
    작업 전후 COUNT 비교.

    Args:
        before: 작업 전 COUNT
        after: 작업 후 COUNT

    Returns:
        {테이블명: {before, after, diff}} 딕셔너리
    """
    result = {}

    for table in TABLES.values():
        b = before.get(table, 0)
        a = after.get(table, 0)

        if isinstance(b, int) and isinstance(a, int):
            diff = a - b
            result[table] = {
                "before": b,
                "after": a,
                "diff": diff,
                "changed": diff != 0
            }
        else:
            result[table] = {
                "before": b,
                "after": a,
                "diff": "N/A",
                "changed": False
            }

    return result


def print_count_comparison(comparison: Dict[str, dict], title: str = "작업 결과") -> None:
    """
    작업 전후 비교 결과 출력.

    Args:
        comparison: compare_counts() 결과
        title: 출력 제목
    """
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

    changed_tables = []
    unchanged_tables = []

    for table in sorted(comparison.keys()):
        data = comparison[table]
        if data.get("changed"):
            changed_tables.append((table, data))
        else:
            unchanged_tables.append((table, data))

    if changed_tables:
        print("\n [변경된 테이블]")
        for table, data in changed_tables:
            diff = data["diff"]
            sign = "+" if diff > 0 else ""
            print(f"  {table:25s}: {data['before']:>10,} → {data['after']:>10,} ({sign}{diff:,})")

    if unchanged_tables:
        print("\n [변경 없음]")
        for table, data in unchanged_tables:
            print(f"  {table:25s}: {data['before']:>10,} 건")

    print(f"{'='*60}\n")


# =============================================================================
# 테스트 (직접 실행 시)
# =============================================================================

if __name__ == "__main__":
    print("=== 스키마 검증 테스트 ===\n")

    # 올바른 테이블명 테스트
    print("1. 올바른 테이블명:")
    for table in ["companies", "officers", "convertible_bonds"]:
        result = validate_table_name(table)
        print(f"   {table} → OK")

    # 잘못된 테이블명 테스트
    print("\n2. 잘못된 테이블명:")
    for wrong_name in ["company", "cb", "position"]:
        try:
            validate_table_name(wrong_name)
        except ValueError as e:
            print(f"   {wrong_name} → {COMMON_MISTAKES.get(wrong_name, 'Unknown')}")

    # COUNT 쿼리 생성
    print("\n3. COUNT 쿼리:")
    print(get_table_counts_query()[:200] + "...")
