#!/usr/bin/env python3
"""
DB 마이그레이션: officers 테이블에 career_raw_text 컬럼 추가

목적: 사업보고서 '주요경력' 원문을 그대로 저장하여 UI에 표시
기존 career_history (JSONB)는 前/現 패턴 파싱 결과 유지

사용법:
    cd backend
    source .venv/bin/activate
    DATABASE_URL="..." python scripts/migrations/add_career_raw_text.py

롤백:
    DATABASE_URL="..." python scripts/migrations/add_career_raw_text.py --rollback
"""

import asyncio
import asyncpg
import argparse
import os
import sys
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL 환경 변수가 설정되지 않았습니다")
    sys.exit(1)

# asyncpg용 URL 변환
if DATABASE_URL.startswith('postgresql+asyncpg://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')


async def migrate():
    """career_raw_text 컬럼 추가"""
    print(f"[{datetime.now()}] 마이그레이션 시작: career_raw_text 컬럼 추가")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 컬럼 존재 여부 확인
        check_query = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'officers' AND column_name = 'career_raw_text'
        """
        existing = await conn.fetchval(check_query)

        if existing:
            print("  career_raw_text 컬럼이 이미 존재합니다. 스킵.")
            return

        # 컬럼 추가
        await conn.execute("""
            ALTER TABLE officers
            ADD COLUMN career_raw_text TEXT
        """)
        print("  ✅ career_raw_text 컬럼 추가 완료")

        # 컬럼 설명 추가
        await conn.execute("""
            COMMENT ON COLUMN officers.career_raw_text IS
            '사업보고서 임원현황 표의 주요경력 원문 텍스트. 불릿(□)을 줄바꿈으로 변환하여 저장.'
        """)
        print("  ✅ 컬럼 코멘트 추가 완료")

    finally:
        await conn.close()

    print(f"[{datetime.now()}] 마이그레이션 완료")


async def rollback():
    """career_raw_text 컬럼 제거"""
    print(f"[{datetime.now()}] 롤백 시작: career_raw_text 컬럼 제거")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 컬럼 존재 여부 확인
        check_query = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'officers' AND column_name = 'career_raw_text'
        """
        existing = await conn.fetchval(check_query)

        if not existing:
            print("  career_raw_text 컬럼이 존재하지 않습니다. 스킵.")
            return

        # 컬럼 제거
        await conn.execute("""
            ALTER TABLE officers DROP COLUMN career_raw_text
        """)
        print("  ✅ career_raw_text 컬럼 제거 완료")

    finally:
        await conn.close()

    print(f"[{datetime.now()}] 롤백 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="career_raw_text 컬럼 마이그레이션")
    parser.add_argument("--rollback", action="store_true", help="롤백 실행")
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
