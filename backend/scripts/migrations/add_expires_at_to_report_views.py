"""
DB 마이그레이션: report_views 테이블에 expires_at 컬럼 추가

실행 방법:
    DATABASE_URL="postgresql://..." python scripts/migrations/add_expires_at_to_report_views.py

롤백 방법:
    DATABASE_URL="postgresql://..." python scripts/migrations/add_expires_at_to_report_views.py --rollback
"""
import asyncio
import sys
import os
from datetime import timedelta

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def migrate(db_url: str):
    """expires_at 컬럼 추가 및 기존 데이터 업데이트"""
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 컬럼 존재 여부 확인
        check_column = await session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'report_views' AND column_name = 'expires_at'
        """))
        column_exists = check_column.fetchone() is not None

        if column_exists:
            print("✓ expires_at 컬럼이 이미 존재합니다.")
        else:
            # 2. 컬럼 추가
            print("expires_at 컬럼 추가 중...")
            await session.execute(text("""
                ALTER TABLE report_views
                ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE
            """))
            print("✓ expires_at 컬럼 추가 완료")

        # 3. 기존 데이터에 expires_at 설정 (first_viewed_at + 30일)
        print("기존 데이터에 expires_at 설정 중...")
        result = await session.execute(text("""
            UPDATE report_views
            SET expires_at = first_viewed_at + INTERVAL '30 days'
            WHERE expires_at IS NULL
        """))
        print(f"✓ {result.rowcount}건 업데이트 완료")

        # 4. 인덱스 추가 (없으면)
        check_index = await session.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'report_views' AND indexname = 'ix_report_views_expires_at'
        """))
        if check_index.fetchone() is None:
            print("expires_at 인덱스 생성 중...")
            await session.execute(text("""
                CREATE INDEX ix_report_views_expires_at ON report_views (expires_at)
            """))
            print("✓ 인덱스 생성 완료")
        else:
            print("✓ 인덱스가 이미 존재합니다.")

        await session.commit()

    await engine.dispose()
    print("\n✅ 마이그레이션 완료!")


async def rollback(db_url: str):
    """expires_at 컬럼 제거 (롤백)"""
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 인덱스 제거
        print("인덱스 제거 중...")
        await session.execute(text("""
            DROP INDEX IF EXISTS ix_report_views_expires_at
        """))
        print("✓ 인덱스 제거 완료")

        # 컬럼 제거
        print("expires_at 컬럼 제거 중...")
        await session.execute(text("""
            ALTER TABLE report_views
            DROP COLUMN IF EXISTS expires_at
        """))
        print("✓ 컬럼 제거 완료")

        await session.commit()

    await engine.dispose()
    print("\n✅ 롤백 완료!")


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL 환경변수가 필요합니다.")
        sys.exit(1)

    # asyncpg 드라이버 사용
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "--rollback" in sys.argv:
        print("=== 롤백 모드 ===\n")
        asyncio.run(rollback(db_url))
    else:
        print("=== 마이그레이션 모드 ===\n")
        asyncio.run(migrate(db_url))
