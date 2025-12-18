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

    # Database (Railway 자동 주입)
    database_url: str
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

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Environment
    environment: str = "development"
    debug: bool = False
    frontend_url: str = "http://localhost:5173"

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

    @property
    def allowed_origins(self) -> list[str]:
        """CORS allowed origins"""
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
