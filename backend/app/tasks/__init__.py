"""
Background Tasks

Celery를 사용한 백그라운드 작업
"""
from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
