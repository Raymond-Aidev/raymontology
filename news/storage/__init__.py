"""
News Storage Module

DB 저장 관련 기능을 제공합니다.
"""
from news.storage.save_to_db import save_article, get_article_stats

__all__ = ["save_article", "get_article_stats"]
