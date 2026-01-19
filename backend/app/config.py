"""
Raymontology 환경 설정
Railway 환경 변수 기반
"""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """
    애플리케이션 설정

    Railway 자동 주입:
    - DATABASE_URL
    - REDIS_URL
    - PORT
    """

    # Database (Railway 자동 주입, 없으면 기본값 사용)
    database_url: str = "postgresql://localhost/raymontology"
    redis_url: Optional[str] = None
    port: int = 8000

    # Neo4j (optional - only needed for graph visualization)
    neo4j_uri: Optional[str] = None
    neo4j_user: str = "neo4j"
    neo4j_password: Optional[str] = None

    # External APIs (optional - only needed for crawling new data)
    dart_api_key: Optional[str] = None
    dart_data_dir: Path = Path("./data/dart")

    # Cloudflare R2 (PDF 저장소) - 선택사항
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_endpoint_url: Optional[str] = None

    # Security - 프로덕션에서는 반드시 SECRET_KEY 환경변수 설정 필요
    # 개발 환경에서만 기본값 사용 (프로덕션에서는 검증됨)
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Email (Gmail SMTP)
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from_address: str = "noreply@konnect-ai.net"
    email_from_name: str = "RaymondsRisk"
    password_reset_expire_minutes: int = 60

    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "https://api.konnect-ai.net/api/auth/google/callback"

    # Kakao OAuth
    kakao_client_id: Optional[str] = None
    kakao_client_secret: Optional[str] = None
    kakao_redirect_uri: str = "https://api.konnect-ai.net/api/auth/kakao/callback"

    # Environment
    environment: str = "development"
    debug: bool = False
    frontend_url: str = "http://localhost:5173"

    # Registration Control (회원가입 비활성화 - 관리자만 계정 생성 가능)
    registration_enabled: bool = False

    # CORS - 프로덕션에서는 False로 설정하여 허용된 origin만 접근 허용
    # 환경변수 CORS_ALLOW_ALL=false로 오버라이드 가능
    cors_allow_all: bool = True  # TODO: 프로덕션 배포 전 False로 변경

    # Payment Gateway (PG) - 결제 대행사
    pg_provider: str = "mock"  # 'tosspayments', 'portone', 'mock'
    toss_payments_client_key: Optional[str] = None
    toss_payments_secret_key: Optional[str] = None

    # Monitoring & Observability
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    sentry_traces_sample_rate: float = 0.1
    slack_webhook_url: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_production_settings(self) -> None:
        """프로덕션 환경 필수 설정 검증"""
        if self.is_production:
            # 시크릿 키 검증
            if self.secret_key.startswith("dev-"):
                raise ValueError(
                    "프로덕션 환경에서는 SECRET_KEY 환경변수를 설정해야 합니다. "
                    "기본 개발용 키는 사용할 수 없습니다."
                )
            # CORS 검증 (경고만)
            if self.cors_allow_all:
                import logging
                logging.warning(
                    "⚠️ 프로덕션에서 CORS_ALLOW_ALL=true 설정됨. "
                    "보안을 위해 False로 변경을 권장합니다."
                )

    @property
    def allowed_origins(self) -> list[str]:
        """CORS allowed origins"""
        if self.cors_allow_all:
            return ["*"]
        if self.is_production:
            return [self.frontend_url]
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
            self.frontend_url
        ]


settings = Settings()

# 프로덕션 설정 검증 (앱 시작 시 실행)
settings.validate_production_settings()
