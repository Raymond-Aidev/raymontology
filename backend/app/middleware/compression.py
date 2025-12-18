"""
Gzip 압축 미들웨어

Railway 환경 최적화: 최소 1KB 이상 응답만 압축
"""
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware


def setup_compression(app: FastAPI):
    """
    Gzip 압축 설정

    Railway 대역폭 절약을 위해 1KB 이상 응답만 압축

    Args:
        app: FastAPI 애플리케이션

    Usage:
        from app.middleware.compression import setup_compression

        app = FastAPI()
        setup_compression(app)
    """
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000  # 1KB (1000 bytes)
    )
