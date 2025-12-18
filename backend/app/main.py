"""
Raymontology FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
import traceback

from app.config import settings
from app.database import init_db, close_db

# Import new API endpoints
from app.api.endpoints import (
    graph,
    financials,
    risks,
    companies as companies_api,
    officers,
    convertible_bonds,
    cb_subscribers,
    company_report
)
from app.routes import auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Raymontology API",
    description="관계형 리스크 온톨로지 시스템 - 회사 관계 네트워크 분석",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - settings.allowed_origins 사용 (보안 강화)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # config.py에서 환경별 origin 관리
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 서버 로그에만 상세 정보 기록 (클라이언트에는 노출 안 함)
    logger.error(f"Global exception: {str(exc)}")
    logger.error(traceback.format_exc())
    # 프로덕션에서는 내부 오류 상세 숨김
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


# API Routers
app.include_router(auth.router)
app.include_router(graph.router, prefix="/api")
app.include_router(financials.router, prefix="/api")
app.include_router(risks.router, prefix="/api")
app.include_router(companies_api.router, prefix="/api")
app.include_router(officers.router, prefix="/api")
app.include_router(convertible_bonds.router, prefix="/api")
app.include_router(cb_subscribers.router, prefix="/api")
app.include_router(company_report.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "service": "Raymontology API",
        "description": "관계형 리스크 온톨로지 시스템 - 회사 관계 네트워크 분석",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": {
            "report": "/api/report (회사 종합보고서)",
            "graph": "/api/graph",
            "financials": "/api/financials",
            "risks": "/api/risks",
            "companies": "/api/companies",
            "officers": "/api/officers",
            "convertible_bonds": "/api/convertible-bonds",
            "cb_subscribers": "/api/cb-subscribers",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "version": "2.0.0"
    }

# Startup Event
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작"""
    logger.info("Raymontology API starting...")
    logger.info(f"Environment: {settings.environment}")

    # 데이터베이스 초기화 (필수)
    try:
        await init_db()
        logger.info("Database connections initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error(traceback.format_exc())
        # DB 없이도 앱은 시작 (health check 응답 가능)

    # 배치 스케줄러 시작 (선택사항 - 실패해도 앱 계속 실행)
    # 현재 Railway 배포에서는 비활성화
    # if settings.environment == "production":
    #     try:
    #         from app.scheduler import start_scheduler
    #         start_scheduler()
    #         logger.info("Batch scheduler started")
    #     except Exception as e:
    #         logger.warning(f"Scheduler failed to start: {e}")

    logger.info("Raymontology API started successfully")

# Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료"""
    logger.info("Raymontology API shutting down...")

    try:
        # 데이터베이스 연결 종료
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
