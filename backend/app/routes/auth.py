"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
import traceback
import secrets
import hashlib

from app.database import get_db
from app.models.users import User, PasswordResetToken, EmailVerificationToken
from app.schemas.auth import (
    UserRegister, UserLogin, Token, UserMe,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse
)
from app.core.security import (
    get_password_hash,
    verify_password,
    get_current_user,
    authenticate_user,
    create_user_token,
    validate_password_strength,
)
from app.services.email_service import email_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def send_verification_email_sync(to_email: str, token: str, username: str):
    """백그라운드에서 이메일 발송 (동기)"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(email_service.send_verification_email(to_email, token, username))
        loop.close()
    except Exception as e:
        logger.error(f"Background email error: {e}")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입 - 이메일 인증 요청

    Args:
        user_data: 회원가입 정보
        db: 데이터베이스 세션

    Returns:
        MessageResponse: 인증 이메일 발송 안내

    Raises:
        HTTPException: 409 (이메일 또는 사용자명 중복)
        HTTPException: 400 (비밀번호 강도 부족)
        HTTPException: 403 (회원가입 비활성화)
    """
    # 회원가입 비활성화 체크
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="현재 회원가입이 비활성화되어 있습니다. 관리자에게 문의하세요."
        )

    try:
        logger.info(f"Register attempt for email: {user_data.email}")

        # 비밀번호 강도 검증
        is_valid, error_message = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # 이메일 중복 체크 (이미 가입된 사용자)
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 이메일입니다."
            )

        # 사용자명 중복 체크
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        existing_username = result.scalar_one_or_none()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 닉네임입니다."
            )

        # 기존 인증 대기 토큰 삭제 (같은 이메일)
        await db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.email == user_data.email)
        )
        existing_tokens = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.email == user_data.email,
                EmailVerificationToken.verified_at.is_(None)
            )
        )
        for token in existing_tokens.scalars():
            await db.delete(token)

        # 이메일 인증 토큰 생성
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        hashed_pw = get_password_hash(user_data.password)

        verification_token = EmailVerificationToken(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=24)  # 24시간 유효
        )

        db.add(verification_token)
        await db.commit()

        # 인증 이메일 발송 (백그라운드)
        background_tasks.add_task(
            send_verification_email_sync,
            user_data.email,
            raw_token,
            user_data.username
        )

        logger.info(f"Verification email queued for: {user_data.email}")

        return MessageResponse(message="인증 이메일이 발송되었습니다. 이메일을 확인해주세요.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 처리 중 오류가 발생했습니다."
        )


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    이메일 인증 완료

    Args:
        token: 인증 토큰
        db: 데이터베이스 세션

    Returns:
        MessageResponse: 인증 완료 메시지

    Raises:
        HTTPException: 400 (유효하지 않거나 만료된 토큰)
    """
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # 토큰 조회
        result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.verified_at.is_(None),
                EmailVerificationToken.expires_at > datetime.utcnow()
            )
        )
        verification = result.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않거나 만료된 인증 링크입니다."
            )

        # 이메일/닉네임 중복 재확인
        result = await db.execute(
            select(User).where(User.email == verification.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 이메일입니다."
            )

        result = await db.execute(
            select(User).where(User.username == verification.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 닉네임입니다."
            )

        # 사용자 생성
        new_user = User(
            email=verification.email,
            username=verification.username,
            hashed_password=verification.hashed_password,
            full_name=verification.full_name,
        )

        db.add(new_user)

        # 토큰 사용 처리
        verification.verified_at = datetime.utcnow()

        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User verified and created: {new_user.email}")

        return MessageResponse(message="이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 인증 처리 중 오류가 발생했습니다."
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


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    비밀번호 재설정 요청

    Args:
        request: 이메일 주소
        db: 데이터베이스 세션

    Returns:
        MessageResponse: 성공 메시지
    """
    try:
        # 사용자 조회 (존재 여부와 관계없이 동일한 응답 반환 - 보안)
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if user and user.is_active:
            # 기존 미사용 토큰 만료 처리
            existing_tokens = await db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > datetime.utcnow()
                )
            )
            for token in existing_tokens.scalars():
                token.used_at = datetime.utcnow()

            # 새 토큰 생성
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes)
            )
            db.add(reset_token)
            await db.commit()

            # 이메일 발송
            await email_service.send_password_reset_email(user.email, raw_token)
            logger.info(f"Password reset email sent to: {user.email}")

        # 보안: 사용자 존재 여부와 관계없이 동일한 메시지 반환
        return MessageResponse(
            message="이메일이 등록되어 있다면 비밀번호 재설정 링크가 발송되었습니다."
        )

    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 요청 처리 중 오류가 발생했습니다."
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    비밀번호 재설정

    Args:
        request: 토큰 및 새 비밀번호
        db: 데이터베이스 세션

    Returns:
        MessageResponse: 성공 메시지

    Raises:
        HTTPException: 400 (유효하지 않은 토큰 또는 만료)
    """
    try:
        # 토큰 해시
        token_hash = hashlib.sha256(request.token.encode()).hexdigest()

        # 토큰 조회
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않거나 만료된 토큰입니다."
            )

        # 비밀번호 강도 검증
        is_valid, error_message = validate_password_strength(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # 사용자 조회
        result = await db.execute(
            select(User).where(User.id == reset_token.user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 사용자입니다."
            )

        # 비밀번호 업데이트
        user.hashed_password = get_password_hash(request.new_password)

        # 토큰 사용 처리
        reset_token.used_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Password reset successful for: {user.email}")

        return MessageResponse(message="비밀번호가 성공적으로 변경되었습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 처리 중 오류가 발생했습니다."
        )
