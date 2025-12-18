"""
관리자 계정 생성 스크립트

Railway 배포 후 실행:
railway run python backend/scripts/create_admin.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.security import get_password_hash
from app.database import AsyncSessionLocal, init_db
from app.models.user import User


async def create_admin():
    """관리자 계정 생성"""
    print("🔧 데이터베이스 초기화 중...")
    await init_db()

    print("👤 관리자 계정 생성 시작...")

    async with AsyncSessionLocal() as session:
        # 기존 관리자 확인
        result = await session.execute(
            select(User).where(User.email == "admin@raymontology.com")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("⚠️  관리자 계정이 이미 존재합니다.")
            print(f"   Email: {existing_admin.email}")
            print(f"   Name: {existing_admin.full_name}")
            return

        # 관리자 생성
        admin_user = User(
            email="admin@raymontology.com",
            hashed_password=get_password_hash("Admin1234!"),
            full_name="Administrator",
            is_active=True,
        )

        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        print("✅ 관리자 계정 생성 완료!")
        print(f"   Email: admin@raymontology.com")
        print(f"   Password: Admin1234!")
        print(f"   ID: {admin_user.id}")
        print("\n⚠️  보안을 위해 비밀번호를 즉시 변경하세요!")


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n❌ 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
