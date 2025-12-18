"""
데이터베이스 마이그레이션 스크립트

Railway 배포 후 실행:
railway run python backend/scripts/db_migrate.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base
from app.models import User, Company, Disclosure, RiskScore  # 모든 모델 임포트


async def create_tables():
    """데이터베이스 테이블 생성"""
    print("🔧 데이터베이스 마이그레이션 시작...")

    async with engine.begin() as conn:
        # 모든 테이블 생성
        await conn.run_sync(Base.metadata.create_all)

    print("✅ 데이터베이스 테이블 생성 완료!")
    print("\n생성된 테이블:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")


async def drop_tables():
    """데이터베이스 테이블 삭제 (주의!)"""
    print("⚠️  모든 테이블을 삭제합니다. 계속하시겠습니까? (yes/no)")
    response = input("> ")

    if response.lower() != "yes":
        print("❌ 취소되었습니다.")
        return

    print("🗑️  테이블 삭제 중...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("✅ 모든 테이블이 삭제되었습니다.")


async def reset_database():
    """데이터베이스 리셋 (삭제 + 생성)"""
    await drop_tables()
    await create_tables()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="데이터베이스 마이그레이션")
    parser.add_argument(
        "action",
        choices=["create", "drop", "reset"],
        help="create: 테이블 생성, drop: 테이블 삭제, reset: 리셋",
    )

    args = parser.parse_args()

    try:
        if args.action == "create":
            asyncio.run(create_tables())
        elif args.action == "drop":
            asyncio.run(drop_tables())
        elif args.action == "reset":
            asyncio.run(reset_database())
    except KeyboardInterrupt:
        print("\n❌ 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
