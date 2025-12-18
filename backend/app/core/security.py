"""
Security & Authentication

JWT 토큰 기반 인증 시스템
"""
from datetime import datetime, timedelta
from typing import Optional, Any
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.users import User

# ============================================================================
# Password Hashing
# ============================================================================


def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱 (Bcrypt)

    Args:
        password: 평문 비밀번호

    Returns:
        str: 해싱된 비밀번호

    Example:
        >>> hashed = get_password_hash("mypassword123")
        >>> print(hashed)
        $2b$12$...
    """
    # bcrypt 4.x uses direct API
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해싱된 비밀번호

    Returns:
        bool: 일치 여부

    Example:
        >>> hashed = get_password_hash("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# ============================================================================
# JWT Token Management
# ============================================================================

# HTTPBearer 스키마 (Authorization: Bearer <token>)
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (예: {"sub": "user@example.com"})
        expires_delta: 만료 시간 (기본: 30분)

    Returns:
        str: JWT 토큰

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()

    # 만료 시간 설정
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    # JWT 토큰 생성
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    JWT 토큰 디코딩 및 검증

    Args:
        token: JWT 토큰

    Returns:
        Optional[dict]: 토큰 페이로드 또는 None

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_access_token(token)
        >>> print(payload["sub"])
        user@example.com
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


# ============================================================================
# User Authentication Dependencies
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 가져오기 (FastAPI 의존성)

    Args:
        credentials: HTTP Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        User: 현재 사용자

    Raises:
        HTTPException: 인증 실패 시

    Usage:
        @app.get("/me")
        async def read_users_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 토큰 추출
    token = credentials.credentials

    # 토큰 디코딩
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 사용자 이메일 추출
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # 데이터베이스에서 사용자 조회
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # 비활성 사용자 체크
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    활성 사용자만 허용 (추가 검증)

    Args:
        current_user: 현재 사용자

    Returns:
        User: 활성 사용자

    Raises:
        HTTPException: 비활성 사용자인 경우
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# ============================================================================
# Authentication Helper Functions
# ============================================================================

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """
    사용자 인증 (이메일 + 비밀번호)

    Args:
        db: 데이터베이스 세션
        email: 이메일
        password: 평문 비밀번호

    Returns:
        Optional[User]: 인증 성공 시 User, 실패 시 None

    Example:
        user = await authenticate_user(db, "user@example.com", "password123")
        if user:
            token = create_access_token({"sub": user.email})
    """
    # 이메일로 사용자 조회
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    # 비밀번호 검증
    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_user_token(user: User) -> dict:
    """
    사용자 토큰 생성 (로그인 응답용)

    Args:
        user: 사용자 객체

    Returns:
        dict: {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 1800
        }
    """
    access_token = create_access_token(
        data={"sub": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60  # 초 단위
    }


# ============================================================================
# Password Validation
# ============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    비밀번호 강도 검증

    Args:
        password: 검증할 비밀번호

    Returns:
        tuple[bool, str]: (유효 여부, 에러 메시지)

    Rules:
        - 최소 8자 이상
        - 최소 1개의 대문자
        - 최소 1개의 소문자
        - 최소 1개의 숫자
        - 최소 1개의 특수문자
    """
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."

    if not any(c.isupper() for c in password):
        return False, "비밀번호에 최소 1개의 대문자가 포함되어야 합니다."

    if not any(c.islower() for c in password):
        return False, "비밀번호에 최소 1개의 소문자가 포함되어야 합니다."

    if not any(c.isdigit() for c in password):
        return False, "비밀번호에 최소 1개의 숫자가 포함되어야 합니다."

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "비밀번호에 최소 1개의 특수문자가 포함되어야 합니다."

    return True, ""


# ============================================================================
# Optional: Superuser Check
# ============================================================================

async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    관리자 권한 체크

    Args:
        current_user: 현재 사용자

    Returns:
        User: 관리자 사용자

    Raises:
        HTTPException: 관리자가 아닌 경우

    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            admin: User = Depends(get_current_superuser)
        ):
            # 관리자만 접근 가능
    """
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user
