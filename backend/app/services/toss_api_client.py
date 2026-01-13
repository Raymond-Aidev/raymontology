"""
Toss Apps-in-Toss API Client (mTLS)

토스 앱인토스 서버와 mTLS 기반 통신을 위한 클라이언트.
토스 로그인, 인앱결제 검증 등에 사용.

참조: https://developers-apps-in-toss.toss.im/development/integration-process.md

환경변수 설정 방법:
  방법 1 (권장 - Railway): 인증서 내용을 환경변수에 저장
    - TOSS_MTLS_CERT_CONTENT: 인증서 내용 (PEM 형식)
    - TOSS_MTLS_KEY_CONTENT: 키 내용 (PEM 형식)

  방법 2 (로컬): 파일 경로 지정
    - TOSS_MTLS_CERT_PATH: 인증서 파일 경로
    - TOSS_MTLS_KEY_PATH: 키 파일 경로

복호화 키 설정 (사용자 정보 복호화):
    - TOSS_DECRYPT_KEY: AES-256 복호화 키 (Base64 인코딩)
    - TOSS_DECRYPT_AAD: AAD (Additional Authenticated Data)
"""

import os
import logging
import tempfile
import base64
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import httpx

# AES-256 GCM 복호화를 위한 cryptography 라이브러리
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _crypto_available = True
except ImportError:
    _crypto_available = False
    AESGCM = None

logger = logging.getLogger(__name__)

# 임시 파일 경로 (환경변수 내용을 파일로 저장할 때 사용)
_temp_cert_path: Optional[str] = None
_temp_key_path: Optional[str] = None


def _setup_cert_files_from_env() -> tuple[Optional[str], Optional[str]]:
    """
    환경변수에서 인증서 내용을 읽어 임시 파일로 저장

    Returns:
        tuple[Optional[str], Optional[str]]: (cert_path, key_path) 또는 (None, None)
    """
    global _temp_cert_path, _temp_key_path

    # 이미 설정된 경우 재사용
    if _temp_cert_path and _temp_key_path:
        if os.path.exists(_temp_cert_path) and os.path.exists(_temp_key_path):
            return _temp_cert_path, _temp_key_path

    cert_content = os.getenv("TOSS_MTLS_CERT_CONTENT")
    key_content = os.getenv("TOSS_MTLS_KEY_CONTENT")

    if not cert_content or not key_content:
        return None, None

    try:
        # 임시 디렉토리에 인증서 파일 생성
        temp_dir = tempfile.gettempdir()

        _temp_cert_path = os.path.join(temp_dir, "toss_mtls_cert.crt")
        _temp_key_path = os.path.join(temp_dir, "toss_mtls_key.key")

        # 인증서 내용 저장 (Railway에서 줄바꿈이 \n 문자열로 저장될 수 있음)
        cert_content_fixed = cert_content.replace("\\n", "\n")
        key_content_fixed = key_content.replace("\\n", "\n")

        with open(_temp_cert_path, "w") as f:
            f.write(cert_content_fixed)

        with open(_temp_key_path, "w") as f:
            f.write(key_content_fixed)

        # 키 파일 권한 제한 (보안)
        os.chmod(_temp_key_path, 0o600)

        logger.info(f"환경변수에서 mTLS 인증서 파일 생성 완료: {_temp_cert_path}")
        return _temp_cert_path, _temp_key_path

    except Exception as e:
        logger.error(f"환경변수에서 인증서 파일 생성 실패: {e}")
        return None, None


class TossAPIError(Exception):
    """토스 API 오류"""
    def __init__(self, error_code: str, reason: str, status_code: int = 400):
        self.error_code = error_code
        self.reason = reason
        self.status_code = status_code
        super().__init__(f"[{error_code}] {reason}")


# ============================================================================
# 사용자 정보 복호화 (AES-256 GCM)
# ============================================================================

def decrypt_toss_user_info(encrypted_text: str) -> Optional[str]:
    """
    토스 API에서 받은 암호화된 사용자 정보를 복호화합니다.

    암호화 알고리즘:
    - AES-256 GCM
    - IV (NONCE): 12바이트, 암호문 앞에 포함
    - AAD: 토스에서 제공하는 값 (환경변수 TOSS_DECRYPT_AAD)

    환경변수:
    - TOSS_DECRYPT_KEY: Base64 인코딩된 256비트 AES 키
    - TOSS_DECRYPT_AAD: AAD 값 (보통 "TOSS")

    Args:
        encrypted_text: Base64 인코딩된 암호문

    Returns:
        복호화된 평문, 실패 시 None
    """
    if not encrypted_text:
        return None

    if not _crypto_available:
        logger.warning("cryptography 라이브러리가 설치되지 않아 복호화할 수 없습니다.")
        return None

    # 환경변수에서 복호화 키 로드
    decrypt_key_b64 = os.getenv("TOSS_DECRYPT_KEY")
    decrypt_aad = os.getenv("TOSS_DECRYPT_AAD", "TOSS")  # 기본값 "TOSS"

    if not decrypt_key_b64:
        logger.debug("TOSS_DECRYPT_KEY 환경변수가 설정되지 않아 복호화를 건너뜁니다.")
        return None

    try:
        IV_LENGTH = 12

        # Base64 디코딩
        decoded = base64.b64decode(encrypted_text)
        key = base64.b64decode(decrypt_key_b64)

        # IV 추출 (처음 12바이트)
        iv = decoded[:IV_LENGTH]
        ciphertext = decoded[IV_LENGTH:]

        # AES-256 GCM 복호화
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, decrypt_aad.encode())

        return plaintext.decode("utf-8")

    except Exception as e:
        logger.warning(f"사용자 정보 복호화 실패: {e}")
        return None


def decrypt_user_info_fields(user_info: "TossUserInfo") -> dict:
    """
    TossUserInfo의 모든 암호화된 필드를 복호화합니다.

    Returns:
        복호화된 필드 딕셔너리:
        {
            "name": "홍길동" or None,
            "phone": "01012345678" or None,
            "email": "user@example.com" or None,
            "birthday": "19900101" or None,
            "gender": "MALE" or "FEMALE" or None,
        }
    """
    return {
        "name": decrypt_toss_user_info(user_info.encrypted_name),
        "phone": decrypt_toss_user_info(user_info.encrypted_phone),
        "email": decrypt_toss_user_info(user_info.encrypted_email),
        "birthday": decrypt_toss_user_info(user_info.encrypted_birthday),
        "gender": decrypt_toss_user_info(user_info.encrypted_gender),
    }


def _parse_response(response: httpx.Response) -> dict:
    """
    토스 API 응답 파싱 (방어적 코딩)

    API 공통 응답 형식:
    - 성공: {"resultType": "SUCCESS", "success": {...}}
    - 실패: {"resultType": "FAIL", "error": {"errorCode": "...", "reason": "..."}}
    - 또는 직접 데이터 반환 (일부 API)
    """
    data = response.json()

    # resultType 래핑 형식 처리
    if isinstance(data, dict) and "resultType" in data:
        if data["resultType"] == "FAIL":
            error = data.get("error", {})
            raise TossAPIError(
                error_code=error.get("errorCode", "UNKNOWN_ERROR"),
                reason=error.get("reason", "알 수 없는 오류가 발생했습니다."),
                status_code=response.status_code,
            )
        # SUCCESS인 경우 success 하위 데이터 반환
        return data.get("success", data)

    # 직접 데이터 반환 형식
    return data


@dataclass
class TossTokenResponse:
    """토스 토큰 발급 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1시간


@dataclass
class TossUserInfo:
    """토스 사용자 정보 (복호화 전)"""
    user_key: str
    scope: str
    # 아래 필드들은 AES-256 GCM 암호화됨
    encrypted_name: Optional[str] = None
    encrypted_phone: Optional[str] = None
    encrypted_email: Optional[str] = None
    encrypted_birthday: Optional[str] = None
    encrypted_gender: Optional[str] = None


@dataclass
class TossOrderStatus:
    """인앱결제 주문 상태"""
    order_id: str
    status: str  # PURCHASED, PAYMENT_COMPLETED, FAILED, REFUNDED, etc.
    sku: str
    purchased_at: Optional[datetime] = None


class TossAPIClient:
    """
    토스 앱인토스 API 클라이언트 (mTLS)

    사용법:
        client = TossAPIClient(
            cert_path="/path/to/cert.crt",
            key_path="/path/to/key.key"
        )
        token = await client.generate_token(auth_code, referrer)
        user = await client.get_user_info(token.access_token)
    """

    BASE_URL = "https://apps-in-toss-api.toss.im"

    def __init__(
        self,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
    ):
        """
        Args:
            cert_path: mTLS 인증서 경로 (기본: 환경변수에서 자동 설정)
            key_path: mTLS 키 경로 (기본: 환경변수에서 자동 설정)

        환경변수 우선순위:
            1. TOSS_MTLS_CERT_CONTENT / TOSS_MTLS_KEY_CONTENT (내용 직접 저장)
            2. TOSS_MTLS_CERT_PATH / TOSS_MTLS_KEY_PATH (파일 경로)
        """
        # 방법 1: 직접 전달된 경로 사용
        if cert_path and key_path:
            self.cert_path = cert_path
            self.key_path = key_path
        else:
            # 방법 2: 환경변수 내용에서 임시 파일 생성 (Railway 권장)
            env_cert_path, env_key_path = _setup_cert_files_from_env()

            if env_cert_path and env_key_path:
                self.cert_path = env_cert_path
                self.key_path = env_key_path
                logger.info("환경변수 내용에서 mTLS 인증서 로드")
            else:
                # 방법 3: 환경변수 경로 사용 (로컬 개발)
                self.cert_path = os.getenv("TOSS_MTLS_CERT_PATH")
                self.key_path = os.getenv("TOSS_MTLS_KEY_PATH")

        if not self.cert_path or not self.key_path:
            raise ValueError(
                "mTLS 인증서가 설정되지 않았습니다. 다음 중 하나를 설정하세요:\n"
                "  - TOSS_MTLS_CERT_CONTENT, TOSS_MTLS_KEY_CONTENT (인증서 내용)\n"
                "  - TOSS_MTLS_CERT_PATH, TOSS_MTLS_KEY_PATH (파일 경로)"
            )

        if not os.path.exists(self.cert_path):
            raise FileNotFoundError(f"인증서 파일을 찾을 수 없습니다: {self.cert_path}")
        if not os.path.exists(self.key_path):
            raise FileNotFoundError(f"키 파일을 찾을 수 없습니다: {self.key_path}")

        logger.info(f"TossAPIClient 초기화 완료: cert={self.cert_path}")

    def _get_client(self) -> httpx.AsyncClient:
        """mTLS가 설정된 HTTP 클라이언트 생성"""
        return httpx.AsyncClient(
            cert=(self.cert_path, self.key_path),
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
            }
        )

    async def generate_token(
        self,
        authorization_code: str,
        referrer: str,
    ) -> TossTokenResponse:
        """
        인가 코드로 액세스 토큰 발급

        Args:
            authorization_code: appLogin()에서 받은 인가 코드 (유효기간 10분)
            referrer: appLogin()에서 받은 referrer

        Returns:
            TossTokenResponse: access_token (1시간), refresh_token (14일)
        """
        url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/generate-token"

        async with self._get_client() as client:
            response = await client.post(
                url,
                json={
                    "authorizationCode": authorization_code,
                    "referrer": referrer,
                }
            )

            if response.status_code != 200:
                logger.error(f"토큰 발급 실패: {response.status_code} - {response.text}")
                response.raise_for_status()

            data = _parse_response(response)
            logger.info("토스 토큰 발급 성공")

            return TossTokenResponse(
                access_token=data["accessToken"],
                refresh_token=data["refreshToken"],
                token_type=data.get("tokenType", "Bearer"),
                expires_in=data.get("expiresIn", 3600),
            )

    async def refresh_token(self, refresh_token: str) -> TossTokenResponse:
        """
        리프레시 토큰으로 새 액세스 토큰 발급

        Args:
            refresh_token: 기존 refresh_token (유효기간 14일)

        Returns:
            TossTokenResponse: 새로운 access_token
        """
        url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/refresh-token"

        async with self._get_client() as client:
            response = await client.post(
                url,
                json={"refreshToken": refresh_token}
            )

            if response.status_code != 200:
                logger.error(f"토큰 갱신 실패: {response.status_code} - {response.text}")
                response.raise_for_status()

            data = _parse_response(response)
            logger.info("토스 토큰 갱신 성공")

            return TossTokenResponse(
                access_token=data["accessToken"],
                refresh_token=data.get("refreshToken", refresh_token),
                token_type=data.get("tokenType", "Bearer"),
                expires_in=data.get("expiresIn", 3600),
            )

    async def get_user_info(self, access_token: str) -> TossUserInfo:
        """
        사용자 정보 조회

        Args:
            access_token: 액세스 토큰

        Returns:
            TossUserInfo: 사용자 정보 (개인정보는 암호화됨)

        Note:
            name, phone, email 등 개인정보는 AES-256 GCM 암호화되어 반환됨.
            복호화 키는 토스에서 이메일로 별도 제공.
        """
        url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/login-me"

        async with self._get_client() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"사용자 정보 조회 실패: {response.status_code} - {response.text}")
                response.raise_for_status()

            data = _parse_response(response)
            logger.info(f"토스 사용자 정보 조회 성공: userKey={data.get('userKey')}")

            return TossUserInfo(
                user_key=data["userKey"],
                scope=data.get("scope", ""),
                encrypted_name=data.get("name"),
                encrypted_phone=data.get("phone"),
                encrypted_email=data.get("email"),
                encrypted_birthday=data.get("birthday"),
                encrypted_gender=data.get("gender"),
            )

    async def disconnect(
        self,
        access_token: Optional[str] = None,
        user_key: Optional[str] = None,
    ) -> bool:
        """
        로그인 연결 해제 (로그아웃)

        공식 API 문서 참조:
        - accessToken: /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token
        - userKey: /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key

        Args:
            access_token: 액세스 토큰 (방법 1)
            user_key: 사용자 키 (방법 2) - int 또는 str

        Returns:
            bool: 성공 여부
        """
        if access_token:
            url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token"
            async with self._get_client() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
        elif user_key:
            url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key"
            # userKey는 number 타입으로 전송 (가이드 참조)
            user_key_int = int(user_key) if isinstance(user_key, str) else user_key
            async with self._get_client() as client:
                response = await client.post(
                    url,
                    json={"userKey": user_key_int}
                )
        else:
            raise ValueError("access_token 또는 user_key 중 하나는 필수입니다.")

        success = response.status_code == 200
        if success:
            logger.info("토스 로그인 연결 해제 성공")
        else:
            logger.error(f"토스 로그인 연결 해제 실패: {response.status_code} - {response.text}")

        return success

    # ===== 인앱결제 관련 =====

    async def get_order_status(
        self,
        user_key: str,
        order_id: str,
    ) -> TossOrderStatus:
        """
        인앱결제 주문 상태 조회

        Args:
            user_key: 토스 사용자 키
            order_id: 주문 ID

        Returns:
            TossOrderStatus: 주문 상태 정보
        """
        url = f"{self.BASE_URL}/api-partner/v1/apps-in-toss/order/get-order-status"

        async with self._get_client() as client:
            # POST 메서드로 요청, orderId는 body에 포함 (토스 API 스펙)
            response = await client.post(
                url,
                json={"orderId": order_id},
                headers={"x-toss-user-key": user_key}
            )

            if response.status_code != 200:
                logger.error(f"주문 상태 조회 실패: {response.status_code} - {response.text}")
                response.raise_for_status()

            data = _parse_response(response)
            logger.info(f"주문 상태 조회 성공: orderId={order_id}, status={data.get('status')}")

            return TossOrderStatus(
                order_id=data["orderId"],
                status=data["status"],
                sku=data.get("sku", ""),
                purchased_at=datetime.fromisoformat(data["purchasedAt"]) if data.get("purchasedAt") else None,
            )

    async def verify_purchase(
        self,
        user_key: str,
        order_id: str,
        expected_sku: str,
    ) -> tuple[bool, str]:
        """
        인앱결제 구매 검증

        Args:
            user_key: 토스 사용자 키
            order_id: 주문 ID
            expected_sku: 예상 상품 SKU

        Returns:
            tuple[bool, str]: (검증 성공 여부, 상태 메시지)
        """
        try:
            order = await self.get_order_status(user_key, order_id)

            if order.status not in ("PURCHASED", "PAYMENT_COMPLETED"):
                return False, f"유효하지 않은 주문 상태: {order.status}"

            if order.sku != expected_sku:
                return False, f"SKU 불일치: expected={expected_sku}, actual={order.sku}"

            return True, "결제 검증 성공"

        except Exception as e:
            logger.error(f"결제 검증 실패: {e}")
            return False, f"결제 검증 실패: {str(e)}"


# 싱글톤 인스턴스 (lazy initialization)
_client_instance: Optional[TossAPIClient] = None


def get_toss_client() -> TossAPIClient:
    """
    TossAPIClient 싱글톤 인스턴스 반환

    환경변수 TOSS_MTLS_CERT_PATH, TOSS_MTLS_KEY_PATH가 설정되어 있어야 함.
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = TossAPIClient()

    return _client_instance
