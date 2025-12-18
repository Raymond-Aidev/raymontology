"""
Authentication Tests
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base, get_db
from app.models.users import User
from app.auth import hash_password

# Test Database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test Engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def test_db():
    """테스트용 데이터베이스"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(test_db):
    """테스트용 HTTP 클라이언트"""

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db: AsyncSession):
    """테스트용 사용자"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
    )

    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user


# ============================================================================
# 회원가입 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """회원가입 성공"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "full_name": "New User"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """중복 이메일로 회원가입 실패"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",  # 이미 존재
            "username": "anotheruser",
            "password": "password123"
        }
    )

    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user: User):
    """중복 사용자명으로 회원가입 실패"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "another@example.com",
            "username": "testuser",  # 이미 존재
            "password": "password123"
        }
    )

    assert response.status_code == 409
    assert "Username already taken" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """잘못된 이메일 형식"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "notanemail",
            "username": "user123",
            "password": "password123"
        }
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# 로그인 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """로그인 성공"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    """잘못된 비밀번호로 로그인 실패"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """존재하지 않는 사용자로 로그인 실패"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 401


# ============================================================================
# /me 엔드포인트 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, test_user: User):
    """현재 사용자 정보 조회 성공"""
    # 로그인
    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    access_token = login_response.json()["access_token"]

    # /me 호출
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_without_token(client: AsyncClient):
    """토큰 없이 /me 호출 실패"""
    response = await client.get("/api/auth/me")

    assert response.status_code == 403  # Forbidden (no token)


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    """잘못된 토큰으로 /me 호출 실패"""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401
