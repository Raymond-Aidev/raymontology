"""
OAuth 소셜 로그인 라우터
Google, Kakao OAuth 2.0 지원
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import httpx
import secrets
import uuid

from app.database import get_db
from app.models.users import User
from app.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["OAuth"])


# =============================================================================
# Google OAuth
# =============================================================================

@router.get("/google")
async def google_login():
    """
    Google OAuth 로그인 시작
    사용자를 Google 로그인 페이지로 리다이렉트
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth가 설정되지 않았습니다"
        )

    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{google_auth_url}?{query_string}")


@router.get("/google/callback")
async def google_callback(
    code: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth 콜백
    인증 코드를 받아 토큰 교환 후 사용자 생성/로그인
    """
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=google_auth_failed"
        )

    if not code:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=no_code"
        )

    try:
        # 1. 코드를 토큰으로 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

        if token_response.status_code != 200:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=token_exchange_failed"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # 2. 사용자 정보 가져오기
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        if user_response.status_code != 200:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=user_info_failed"
            )

        google_user = user_response.json()
        email = google_user.get("email")
        google_id = google_user.get("id")
        name = google_user.get("name", "")
        picture = google_user.get("picture")

        if not email:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=no_email"
            )

        # 3. 사용자 찾기 또는 생성
        user = await _find_or_create_oauth_user(
            db=db,
            email=email,
            oauth_provider="google",
            oauth_provider_id=google_id,
            full_name=name,
            profile_image=picture
        )

        # 4. JWT 토큰 생성
        jwt_token = create_access_token(data={"sub": str(user.id)})

        # 5. 프론트엔드로 리다이렉트 (토큰 포함)
        return RedirectResponse(
            url=f"{settings.frontend_url}/oauth/callback?token={jwt_token}"
        )

    except Exception as e:
        print(f"Google OAuth error: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_error"
        )


# =============================================================================
# Kakao OAuth
# =============================================================================

@router.get("/kakao")
async def kakao_login():
    """
    Kakao OAuth 로그인 시작
    사용자를 Kakao 로그인 페이지로 리다이렉트
    """
    if not settings.kakao_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kakao OAuth가 설정되지 않았습니다"
        )

    kakao_auth_url = "https://kauth.kakao.com/oauth/authorize"
    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
        "scope": "profile_nickname,profile_image,account_email"
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{kakao_auth_url}?{query_string}")


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Kakao OAuth 콜백
    인증 코드를 받아 토큰 교환 후 사용자 생성/로그인
    """
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=kakao_auth_failed"
        )

    if not code:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=no_code"
        )

    try:
        # 1. 코드를 토큰으로 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.kakao_client_id,
                    "client_secret": settings.kakao_client_secret,
                    "redirect_uri": settings.kakao_redirect_uri,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

        if token_response.status_code != 200:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=token_exchange_failed"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # 2. 사용자 정보 가져오기
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        if user_response.status_code != 200:
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=user_info_failed"
            )

        kakao_user = user_response.json()
        kakao_id = str(kakao_user.get("id"))
        kakao_account = kakao_user.get("kakao_account", {})
        profile = kakao_account.get("profile", {})

        email = kakao_account.get("email")
        nickname = profile.get("nickname", "")
        profile_image = profile.get("profile_image_url")

        if not email:
            # 카카오에서 이메일을 제공하지 않는 경우 가상 이메일 생성
            email = f"kakao_{kakao_id}@konnect-ai.net"

        # 3. 사용자 찾기 또는 생성
        user = await _find_or_create_oauth_user(
            db=db,
            email=email,
            oauth_provider="kakao",
            oauth_provider_id=kakao_id,
            full_name=nickname,
            profile_image=profile_image
        )

        # 4. JWT 토큰 생성
        jwt_token = create_access_token(data={"sub": str(user.id)})

        # 5. 프론트엔드로 리다이렉트 (토큰 포함)
        return RedirectResponse(
            url=f"{settings.frontend_url}/oauth/callback?token={jwt_token}"
        )

    except Exception as e:
        print(f"Kakao OAuth error: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_error"
        )


# =============================================================================
# Helper Functions
# =============================================================================

async def _find_or_create_oauth_user(
    db: AsyncSession,
    email: str,
    oauth_provider: str,
    oauth_provider_id: str,
    full_name: str = None,
    profile_image: str = None
) -> User:
    """
    OAuth 사용자 찾기 또는 생성

    1. oauth_provider_id로 찾기
    2. email로 찾기 (기존 이메일 계정과 연결)
    3. 새 사용자 생성
    """
    # 1. OAuth provider ID로 찾기
    stmt = select(User).where(
        User.oauth_provider == oauth_provider,
        User.oauth_provider_id == oauth_provider_id
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.utcnow()
        if profile_image and not user.profile_image:
            user.profile_image = profile_image
        await db.commit()
        return user

    # 2. 이메일로 찾기 (기존 계정과 연결)
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # 기존 계정에 OAuth 정보 추가
        user.oauth_provider = oauth_provider
        user.oauth_provider_id = oauth_provider_id
        if profile_image and not user.profile_image:
            user.profile_image = profile_image
        user.last_login = datetime.utcnow()
        await db.commit()
        return user

    # 3. 새 사용자 생성
    # username 생성 (이메일의 @ 앞부분 + 랜덤 suffix)
    email_prefix = email.split("@")[0]
    random_suffix = secrets.token_hex(3)
    username = f"{email_prefix}_{random_suffix}"

    user = User(
        id=uuid.uuid4(),
        email=email,
        username=username,
        hashed_password=None,  # OAuth 사용자는 비밀번호 없음
        full_name=full_name,
        profile_image=profile_image,
        oauth_provider=oauth_provider,
        oauth_provider_id=oauth_provider_id,
        is_active=True,
        is_superuser=False,
        last_login=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
