"""
검증 래퍼 유틸리티

모든 파싱 스크립트에 적용하여 자동으로:
1. 작업 전 테이블 COUNT 기록
2. 스크립트 실행
3. 작업 후 테이블 COUNT 기록
4. 증감분 계산 및 로그 저장
5. 결과 출력

사용 예:
    from scripts.utils.validation_wrapper import with_validation, ValidationContext

    # 데코레이터 방식
    @with_validation(script_name="parse_officers")
    async def main():
        # 파싱 로직
        pass

    # 컨텍스트 매니저 방식
    async with ValidationContext("parse_cb") as ctx:
        # 파싱 로직
        ctx.add_note("대호에이엘 CB 17건 파싱")
"""

import os
import sys
import json
import time
import functools
from datetime import datetime
from typing import Callable, Optional, Any

# 프로젝트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
            counts[table] = -1

    cursor.close()
    return counts


def log_execution(
    conn,
    script_name: str,
    counts_before: dict,
    counts_after: dict,
    status: str,
    error_message: Optional[str] = None,
    execution_time: Optional[float] = None,
    notes: Optional[str] = None,
):
    """script_execution_log 테이블에 실행 기록 저장"""
    cursor = conn.cursor()

    # 증감분 계산
    records_added = 0
    records_deleted = 0
    for table in TABLES.values():
        before = counts_before.get(table, 0)
        after = counts_after.get(table, 0)
        if isinstance(before, int) and isinstance(after, int):
            diff = after - before
            if diff > 0:
                records_added += diff
            else:
                records_deleted += abs(diff)

    cursor.execute(
        """
        INSERT INTO script_execution_log
        (script_name, table_counts_before, table_counts_after, records_added, records_deleted, status, error_message, execution_time_seconds, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            script_name,
            json.dumps(counts_before),
            json.dumps(counts_after),
            records_added,
            records_deleted,
            status,
            error_message,
            execution_time,
            notes,
        ),
    )

    log_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    return log_id


class ValidationContext:
    """
    검증 컨텍스트 매니저

    사용 예:
        async with ValidationContext("parse_officers") as ctx:
            # 파싱 로직
            ctx.add_note("처리 완료")
    """

    def __init__(self, script_name: str):
        self.script_name = script_name
        self.conn = None
        self.counts_before = {}
        self.counts_after = {}
        self.start_time = None
        self.notes = []
        self.status = "success"
        self.error_message = None

    def add_note(self, note: str):
        """메모 추가"""
        self.notes.append(note)

    def __enter__(self):
        """동기 컨텍스트 매니저 시작"""
        self.conn = get_db_connection()
        self.counts_before = get_all_table_counts(self.conn)
        self.start_time = time.time()

        print("\n" + "=" * 60)
        print(f" 작업 시작: {self.script_name}")
        print(f" 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print_table_counts(self.counts_before, "작업 전 상태")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """동기 컨텍스트 매니저 종료"""
        execution_time = time.time() - self.start_time if self.start_time else 0

        if exc_type is not None:
            self.status = "failed"
            self.error_message = str(exc_val)

        self.counts_after = get_all_table_counts(self.conn)

        # 비교 출력
        comparison = compare_counts(self.counts_before, self.counts_after)
        print_count_comparison(comparison, "작업 결과")

        # 로그 저장
        notes_str = "\n".join(self.notes) if self.notes else None
        log_id = log_execution(
            self.conn,
            self.script_name,
            self.counts_before,
            self.counts_after,
            self.status,
            self.error_message,
            execution_time,
            notes_str,
        )

        print(f"\n [실행 기록 저장됨: ID={log_id}]")
        print(f" [소요 시간: {execution_time:.2f}초]")
        print(f" [상태: {self.status}]")

        if self.error_message:
            print(f" [에러: {self.error_message}]")

        print("=" * 60 + "\n")

        self.conn.close()

        return False  # 예외를 다시 발생시킴

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 시작"""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        return self.__exit__(exc_type, exc_val, exc_tb)


def with_validation(script_name: str):
    """
    검증 데코레이터

    사용 예:
        @with_validation("parse_officers")
        def main():
            # 파싱 로직
            pass

        @with_validation("parse_cb")
        async def main():
            # 비동기 파싱 로직
            pass
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with ValidationContext(script_name) as ctx:
                result = func(*args, **kwargs)
                return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with ValidationContext(script_name) as ctx:
                result = await func(*args, **kwargs)
                return result

        # 비동기 함수인지 확인
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def validate_before_after(script_name: str, func: Callable, *args, **kwargs) -> Any:
    """
    단순 함수를 검증과 함께 실행

    사용 예:
        def parse_data():
            # 파싱 로직
            return result

        result = validate_before_after("parse_data", parse_data)
    """
    with ValidationContext(script_name) as ctx:
        result = func(*args, **kwargs)
        return result


# =============================================================================
# 테스트
# =============================================================================

if __name__ == "__main__":
    print("=== 검증 래퍼 테스트 ===\n")

    # 1. 컨텍스트 매니저 테스트
    print("1. 컨텍스트 매니저 테스트:")
    with ValidationContext("test_script") as ctx:
        ctx.add_note("테스트 메모 1")
        ctx.add_note("테스트 메모 2")
        print("   (테스트 작업 수행 중...)")
        time.sleep(0.5)

    # 2. 데코레이터 테스트
    print("\n2. 데코레이터 테스트:")

    @with_validation("test_decorated")
    def test_function():
        print("   (데코레이터로 감싼 함수 실행 중...)")
        time.sleep(0.3)
        return "done"

    result = test_function()
    print(f"   결과: {result}")

    print("\n=== 테스트 완료 ===")
