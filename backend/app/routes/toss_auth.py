"""
토스 로그인 API 라우터 (앱인토스용)

mTLS 기반 토스 API 연동으로 실제 토스 로그인 처리.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import logging
import os
import base64

from app.database import get_db
from app.models.toss_users import TossUser
from app.config import settings

# mTLS 클라이언트 import (환경변수 없으면 None)
_toss_client_available = False
_toss_client_init_error = None
TossAPIError = None  # 방어적 초기화

try:
    from app.services.toss_api_client import get_toss_client, TossAPIClient, TossAPIError
    # 실제 클라이언트 인스턴스 생성 시도 (인증서 확인)
    _test_client = get_toss_client()
    _toss_client_available = True
    logging.info("TossAPIClient 초기화 성공 (mTLS 인증서 확인됨)")
except (ValueError, FileNotFoundError) as e:
    _toss_client_init_error = str(e)
    logging.warning(f"TossAPIClient 초기화 실패 (mTLS 미설정): {e}")
except Exception as e:
    _toss_client_init_error = str(e)
    logging.warning(f"TossAPIClient 초기화 실패 (예외): {e}")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/toss", tags=["toss-auth"])

# ============================================================================
# 토스 콜백 Basic Auth 설정
# ============================================================================

# 콘솔에 등록한 Basic Auth 값 (username:password 형식)
TOSS_CALLBACK_CREDENTIALS = os.getenv(
    "TOSS_CALLBACK_CREDENTIALS",
    "raymondsrisk:Toss20260114Callback!"
)


def verify_toss_callback_auth(authorization: Optional[str] = Header(None)) -> bool:
    """
    토스 콜백 Basic Auth 검증

    토스 서버가 콜백 호출 시 Authorization 헤더에 Base64 인코딩된 credentials를 보냄.
    콘솔에 설정한 값과 일치하는지 검증.
    """
    if not authorization:
        logger.warning("Toss callback: Missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    if not authorization.startswith("Basic "):
        logger.warning(f"Toss callback: Invalid auth scheme: {authorization[:20]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Basic authentication required"
        )

    try:
        # Base64 디코딩
        encoded_credentials = authorization.replace("Basic ", "")
        decoded_bytes = base64.b64decode(encoded_credentials)
        decoded_credentials = decoded_bytes.decode("utf-8")

        # 검증
        if decoded_credentials != TOSS_CALLBACK_CREDENTIALS:
            logger.warning(f"Toss callback: Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        return True

    except Exception as e:
        logger.error(f"Toss callback auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# ============================================================================
# Request/Response Models
# ============================================================================


class TokenRequest(BaseModel):
    """인가 코드로 토큰 발급 요청"""
    authorizationCode: str
    referrer: str  # 'sandbox' or 'DEFAULT'


class TokenResponse(BaseModel):
    """토큰 발급 응답"""
    accessToken: str
    refreshToken: str
    expiresIn: int  # 초 단위


class RefreshRequest(BaseModel):
    """토큰 갱신 요청"""
    refreshToken: str


class UserInfoResponse(BaseModel):
    """사용자 정보 응답"""
    userKey: str
    name: Optional[str] = None
    credits: int


class LogoutRequest(BaseModel):
    """로그아웃 요청"""
    pass  # Bearer 토큰으로 인증


# ============================================================================
# 헬퍼 함수
# ============================================================================


def _get_toss_client() -> "TossAPIClient":
    """mTLS 클라이언트 인스턴스 반환 (없으면 예외)"""
    if not _toss_client_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"토스 API 클라이언트가 초기화되지 않았습니다: {_toss_client_init_error}"
        )
    return get_toss_client()


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/token", response_model=TokenResponse)
async def exchange_code_for_token(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    인가 코드로 토큰 발급

    1. 앱인토스 API에 인가 코드 전송 (mTLS)
    2. accessToken, refreshToken 수신
    3. 사용자 정보 조회 및 저장
    """
    # 모의 응답 사용 조건:
    # - mTLS 클라이언트가 없는 경우에만 mock 사용
    # - 샌드박스 환경에서도 실제 토스 API 호출 필요 (인가코드 검증)
    use_mock = not _toss_client_available  # mTLS 인증서 미설정 시에만 mock

    if use_mock:
        # 모의 토큰 생성
        mock_token = f"mock_access_{request.authorizationCode[:8]}"
        mock_refresh = f"mock_refresh_{request.authorizationCode[:8]}"
        mock_user_key = f"mock_user_{request.authorizationCode[:8]}"

        # 사용자 조회 또는 생성
        result = await db.execute(
            select(TossUser).where(TossUser.toss_user_key == mock_user_key)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = TossUser(
                toss_user_key=mock_user_key,
                name="테스트 사용자",
                credits=10,  # 신규 가입 보너스
                access_token=mock_token,
                refresh_token=mock_refresh,
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
        else:
            user.access_token = mock_token
            user.refresh_token = mock_refresh
            user.token_expires_at = datetime.utcnow() + timedelta(hours=1)
            user.last_login_at = datetime.utcnow()

        await db.commit()
        logger.info(f"[Mock] Token issued for: {mock_user_key} (mTLS not available)")

        return TokenResponse(
            accessToken=mock_token,
            refreshToken=mock_refresh,
            expiresIn=3600,
        )

    # ========== 프로덕션: mTLS 기반 실제 토스 API 호출 ==========
    try:
        client = _get_toss_client()

        # 1. 인가 코드로 토큰 발급
        token_response = await client.generate_token(
            authorization_code=request.authorizationCode,
            referrer=request.referrer,
        )

        access_token = token_response.access_token
        refresh_token = token_response.refresh_token
        expires_in = token_response.expires_in

        # 2. 사용자 정보 조회
        user_info = await client.get_user_info(access_token)
        # user_key는 정수로 올 수 있으므로 문자열로 변환
        user_key = str(user_info.user_key)

        # 3. DB에 사용자 조회 또는 생성
        result = await db.execute(
            select(TossUser).where(TossUser.toss_user_key == user_key)
        )
        user = result.scalar_one_or_none()

        if not user:
            # 신규 사용자: 5건 무료 크레딧 지급
            user = TossUser(
                toss_user_key=user_key,
                name=user_info.encrypted_name,  # 암호화된 상태로 저장
                credits=5,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
            logger.info(f"[Production] New Toss user created: {user_key}")
        else:
            # 기존 사용자: 토큰 업데이트
            user.access_token = access_token
            user.refresh_token = refresh_token
            user.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            user.last_login_at = datetime.utcnow()
            logger.info(f"[Production] Toss user logged in: {user_key}")

        await db.commit()

        return TokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=expires_in,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 발급 실패: {e}")
        # TossAPIError인 경우 상세 에러 정보 반환
        if TossAPIError and isinstance(e, TossAPIError):
            raise HTTPException(
                status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
                detail=f"토스 API 오류: [{e.error_code}] {e.reason}"
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"토스 API 통신 오류: {str(e)}"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 로그인한 사용자 정보 조회
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다"
        )

    access_token = authorization.replace("Bearer ", "")

    # DB에서 토큰으로 사용자 조회
    result = await db.execute(
        select(TossUser).where(TossUser.access_token == access_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    return UserInfoResponse(
        userKey=user.toss_user_key,
        name=user.name,
        credits=user.credits,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    리프레시 토큰으로 액세스 토큰 갱신
    """
    # DB에서 리프레시 토큰으로 사용자 조회
    result = await db.execute(
        select(TossUser).where(TossUser.refresh_token == request.refreshToken)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다"
        )

    # Mock 토큰 갱신: mock 토큰인 경우에만 모의 갱신
    use_mock_refresh = request.refreshToken.startswith("mock_")

    if use_mock_refresh:
        new_access_token = f"mock_access_refreshed_{user.toss_user_key[:8]}"
        new_refresh_token = f"mock_refresh_refreshed_{user.toss_user_key[:8]}"

        user.access_token = new_access_token
        user.refresh_token = new_refresh_token
        user.token_expires_at = datetime.utcnow() + timedelta(hours=1)

        await db.commit()
        logger.info(f"[Mock] Token refreshed for: {user.toss_user_key}")

        return TokenResponse(
            accessToken=new_access_token,
            refreshToken=new_refresh_token,
            expiresIn=3600,
        )

    # ========== 프로덕션: mTLS 기반 토큰 갱신 ==========
    try:
        client = _get_toss_client()

        token_response = await client.refresh_token(request.refreshToken)

        # DB 업데이트
        user.access_token = token_response.access_token
        user.refresh_token = token_response.refresh_token
        user.token_expires_at = datetime.utcnow() + timedelta(seconds=token_response.expires_in)

        await db.commit()
        logger.info(f"[Production] Token refreshed for: {user.toss_user_key}")

        return TokenResponse(
            accessToken=token_response.access_token,
            refreshToken=token_response.refresh_token,
            expiresIn=token_response.expires_in,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 갱신 실패: {e}")
        # TossAPIError인 경우 상세 에러 정보 반환
        if TossAPIError and isinstance(e, TossAPIError):
            raise HTTPException(
                status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
                detail=f"토스 API 오류: [{e.error_code}] {e.reason}"
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"토스 API 통신 오류: {str(e)}"
        )


@router.post("/logout")
async def logout(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    로그아웃 (토큰 무효화)
    - 토스 서버에 연결 해제 요청
    - DB에서 토큰 삭제
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다"
        )

    access_token = authorization.replace("Bearer ", "")

    # DB에서 토큰으로 사용자 조회
    result = await db.execute(
        select(TossUser).where(TossUser.access_token == access_token)
    )
    user = result.scalar_one_or_none()

    if user:
        user_key = user.toss_user_key

        # 프로덕션: 토스 서버에 연결 해제 요청
        if _toss_client_available and not access_token.startswith("mock_"):
            try:
                client = get_toss_client()
                await client.disconnect(access_token=access_token)
                logger.info(f"[Production] Toss disconnect successful: {user_key}")
            except Exception as e:
                # 토스 API 실패해도 로컬 로그아웃은 진행
                logger.warning(f"Toss disconnect failed (continuing): {e}")

        # DB에서 토큰 무효화
        user.access_token = None
        user.refresh_token = None
        user.token_expires_at = None
        await db.commit()
        logger.info(f"User logged out: {user_key}")

    return {"message": "로그아웃 되었습니다"}


@router.get("/status")
async def get_toss_api_status():
    """
    토스 API 연동 상태 확인 (디버깅용)
    """
    return {
        "mTLS_available": _toss_client_available,
        "mTLS_error": _toss_client_init_error if not _toss_client_available else None,
        "debug_mode": settings.debug,
        "environment": "sandbox" if settings.debug else "production",
    }


# ============================================================================
# 로그인 끊기 콜백 (토스앱에서 연결 해제 시 호출)
# ============================================================================


class DisconnectCallbackRequest(BaseModel):
    """토스 로그인 끊기 콜백 요청"""
    userKey: int  # 토스 사용자 고유 키 (number 타입)
    referrer: str  # UNLINK, WITHDRAWAL_TERMS, WITHDRAWAL_TOSS


class DisconnectCallbackResponse(BaseModel):
    """콜백 응답"""
    status: str = "ok"
    message: str = ""


@router.post("/callback/disconnect", response_model=DisconnectCallbackResponse)
async def toss_disconnect_callback(
    request: DisconnectCallbackRequest,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_toss_callback_auth),
):
    """
    토스 로그인 끊기 콜백 (POST 방식)

    사용자가 토스앱에서 연결을 해제할 때 토스 서버가 호출합니다.
    - 콘솔에서 콜백 URL 및 Basic Auth 헤더 설정 필요
    - Basic Auth: raymondsrisk:Toss20260114Callback!

    referrer 값:
    - UNLINK: 사용자가 토스앱에서 직접 연결 끊음
    - WITHDRAWAL_TERMS: 사용자가 로그인 약관 동의 철회
    - WITHDRAWAL_TOSS: 사용자가 토스 회원 탈퇴

    Note:
    - 서비스에서 직접 로그인 끊기 API를 호출한 경우에는 콜백이 호출되지 않음
    """
    user_key = str(request.userKey)
    referrer = request.referrer

    logger.info(f"Toss disconnect callback received: userKey={user_key}, referrer={referrer}")

    # 사용자 조회
    result = await db.execute(
        select(TossUser).where(TossUser.toss_user_key == user_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Disconnect callback: user not found: {user_key}")
        return DisconnectCallbackResponse(
            status="ok",
            message="User not found (already disconnected or never connected)"
        )

    # 토큰 무효화
    user.access_token = None
    user.refresh_token = None
    user.token_expires_at = None

    # referrer에 따른 추가 처리
    if referrer == "WITHDRAWAL_TOSS":
        # 토스 회원 탈퇴: 계정 비활성화
        user.is_active = False
        logger.info(f"User deactivated due to Toss withdrawal: {user_key}")

    await db.commit()

    logger.info(f"Disconnect callback processed: userKey={user_key}, referrer={referrer}")

    return DisconnectCallbackResponse(
        status="ok",
        message=f"User {user_key} disconnected successfully"
    )


@router.get("/callback/disconnect", response_model=DisconnectCallbackResponse)
async def toss_disconnect_callback_get(
    userKey: int,
    referrer: str,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_toss_callback_auth),
):
    """
    토스 로그인 끊기 콜백 (GET 방식)

    토스 서버가 GET 방식으로 호출할 때 사용.
    - Basic Auth: raymondsrisk:Toss20260114Callback!
    """
    user_key = str(userKey)

    logger.info(f"Toss disconnect callback (GET) received: userKey={user_key}, referrer={referrer}")

    # 사용자 조회
    result = await db.execute(
        select(TossUser).where(TossUser.toss_user_key == user_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Disconnect callback (GET): user not found: {user_key}")
        return DisconnectCallbackResponse(
            status="ok",
            message="User not found (already disconnected or never connected)"
        )

    # 토큰 무효화
    user.access_token = None
    user.refresh_token = None
    user.token_expires_at = None

    # referrer에 따른 추가 처리
    if referrer == "WITHDRAWAL_TOSS":
        user.is_active = False
        logger.info(f"User deactivated due to Toss withdrawal: {user_key}")

    await db.commit()

    logger.info(f"Disconnect callback (GET) processed: userKey={user_key}, referrer={referrer}")

    return DisconnectCallbackResponse(
        status="ok",
        message=f"User {user_key} disconnected successfully"
    )
