"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import traceback

from app.database import get_db
from app.models.users import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserMe
from app.core.security import (
    get_password_hash,
    verify_password,
    get_current_user,
    authenticate_user,
    create_user_token,
    validate_password_strength,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입

    Args:
        user_data: 회원가입 정보
        db: 데이터베이스 세션

    Returns:
        Token: 액세스 토큰

    Raises:
        HTTPException: 409 (이메일 또는 사용자명 중복)
        HTTPException: 400 (비밀번호 강도 부족)
    """
    try:
        logger.info(f"Register attempt for email: {user_data.email}")

        # 비밀번호 강도 검증
        is_valid, error_message = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # 이메일 중복 체크
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # 사용자명 중복 체크
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        existing_username = result.scalar_one_or_none()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )

        # 사용자 생성
        hashed_pw = get_password_hash(user_data.password)

        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User registered successfully: {new_user.email}")

        # 토큰 생성 (create_user_token 헬퍼 사용)
        return create_user_token(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    로그인

    Args:
        user_data: 로그인 정보
        db: 데이터베이스 세션

    Returns:
        Token: 액세스 토큰

    Raises:
        HTTPException: 401 (인증 실패)
    """
    # authenticate_user 헬퍼 사용
    user = await authenticate_user(db, user_data.email, user_data.password)

    # 인증 실패
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 비활성 사용자 체크
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # 마지막 로그인 시간 업데이트
    user.last_login = datetime.utcnow()
    await db.commit()

    # 토큰 생성 (create_user_token 헬퍼 사용)
    return create_user_token(user)


@router.get("/me", response_model=UserMe)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    현재 사용자 정보 조회

    Args:
        current_user: 현재 인증된 사용자

    Returns:
        UserMe: 사용자 정보
    """
    return current_user
