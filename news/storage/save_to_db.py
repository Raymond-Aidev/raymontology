"""
News 기사 DB 저장 스크립트

Claude WebFetch로 파싱한 결과를 PostgreSQL에 저장합니다.

사용법:
    # 단일 기사 저장 (Claude가 호출)
    from news.storage.save_to_db import save_article

    result = await save_article(
        url="https://www.drcr.co.kr/articles/647",
        title="롯데건설 분식회계 의혹",
        publisher="DRCR",
        publish_date="2026-01-10",
        summary="롯데건설 관련 복잡한 자금 흐름...",
        entities=[
            {"type": "company", "name": "롯데건설", "role": "주요 기업"},
            {"type": "person", "name": "홍길동", "role": "전 CFO"},
        ],
        relations=[
            {"source": "롯데건설", "target": "SPC A", "type": "spc_related", "detail": "자금 이체"},
        ],
        risks=[
            {"type": "governance", "description": "복잡한 SPC 구조", "severity": "high"},
        ]
    )

⚠️ 안전 설계:
- 기존 테이블 수정 없음
- news_* 테이블에만 INSERT
- 트랜잭션 롤백 지원
"""
import asyncio
import sys
from datetime import datetime, date
from typing import Optional
from uuid import UUID
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.news import (
    NewsArticle, NewsEntity, NewsRelation, NewsRisk,
    RISK_WEIGHTS
)


# Database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)

# Async engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def match_company(session: AsyncSession, name: str) -> tuple[Optional[UUID], Optional[str], float]:
    """
    기업명으로 companies 테이블 매칭

    Returns:
        (company_id, corp_code, confidence)
    """
    # 정확히 일치
    result = await session.execute(
        text("SELECT id, corp_code FROM companies WHERE name = :name LIMIT 1"),
        {"name": name}
    )
    row = result.fetchone()
    if row:
        return row[0], row[1], 1.0

    # 부분 일치 (trigram)
    result = await session.execute(
        text("""
            SELECT id, corp_code, similarity(name, :name) as sim
            FROM companies
            WHERE name % :name
            ORDER BY sim DESC
            LIMIT 1
        """),
        {"name": name}
    )
    row = result.fetchone()
    if row and row[2] > 0.5:
        return row[0], row[1], float(row[2])

    return None, None, 0.0


async def match_officer(session: AsyncSession, name: str) -> tuple[Optional[UUID], float]:
    """
    인물명으로 officers 테이블 매칭

    Returns:
        (officer_id, confidence)
    """
    # 정확히 일치
    result = await session.execute(
        text("SELECT id FROM officers WHERE name = :name LIMIT 1"),
        {"name": name}
    )
    row = result.fetchone()
    if row:
        return row[0], 1.0

    return None, 0.0


async def save_article(
    url: str,
    title: str,
    publisher: Optional[str] = None,
    publish_date: Optional[str] = None,
    author: Optional[str] = None,
    summary: Optional[str] = None,
    raw_content: Optional[str] = None,
    entities: list[dict] = None,
    relations: list[dict] = None,
    risks: list[dict] = None,
    dry_run: bool = False
) -> dict:
    """
    파싱된 기사를 DB에 저장

    Args:
        url: 기사 URL (unique key)
        title: 기사 제목
        publisher: 매체명
        publish_date: 게시일 (YYYY-MM-DD)
        author: 작성자
        summary: 요약
        raw_content: 원문 텍스트
        entities: 엔티티 목록 [{"type", "name", "role"}, ...]
        relations: 관계 목록 [{"source", "target", "type", "detail", "period"}, ...]
        risks: 위험 목록 [{"type", "description", "severity"}, ...]
        dry_run: True면 롤백

    Returns:
        {"success": bool, "article_id": str, "stats": {...}}
    """
    entities = entities or []
    relations = relations or []
    risks = risks or []

    async with async_session() as session:
        try:
            # 1. 기사 저장
            pub_date = None
            if publish_date:
                if isinstance(publish_date, str):
                    pub_date = datetime.strptime(publish_date, "%Y-%m-%d").date()
                elif isinstance(publish_date, date):
                    pub_date = publish_date

            # 중복 체크
            existing = await session.execute(
                select(NewsArticle).where(NewsArticle.url == url)
            )
            if existing.scalar_one_or_none():
                return {
                    "success": False,
                    "error": f"Article already exists: {url}",
                    "article_id": None
                }

            article = NewsArticle(
                url=url,
                title=title,
                publisher=publisher,
                publish_date=pub_date,
                author=author,
                summary=summary,
                raw_content=raw_content,
                status='active',
                parse_version='v4'
            )
            session.add(article)
            await session.flush()  # article.id 확보

            # 2. 엔티티 저장 (이름으로 매핑)
            entity_map = {}  # name -> NewsEntity
            for ent in entities:
                company_id, corp_code, company_conf = None, None, 0.0
                officer_id, officer_conf = None, 0.0

                if ent.get('type') == 'company':
                    company_id, corp_code, company_conf = await match_company(session, ent['name'])
                elif ent.get('type') == 'person':
                    officer_id, officer_conf = await match_officer(session, ent['name'])

                confidence = max(company_conf, officer_conf) if company_id or officer_id else None

                entity = NewsEntity(
                    article_id=article.id,
                    entity_type=ent.get('type', 'unknown'),
                    entity_name=ent['name'],
                    entity_role=ent.get('role'),
                    matched_company_id=company_id,
                    matched_officer_id=officer_id,
                    matched_corp_code=corp_code,
                    match_confidence=confidence
                )
                session.add(entity)
                await session.flush()
                entity_map[ent['name']] = entity

            # 3. 관계 저장
            relations_saved = 0
            for rel in relations:
                source_entity = entity_map.get(rel['source'])
                target_entity = entity_map.get(rel['target'])

                if not source_entity or not target_entity:
                    continue  # 엔티티가 없으면 스킵

                relation_type = rel.get('type', 'related')
                risk_weight = RISK_WEIGHTS.get(relation_type, 1.0)

                relation = NewsRelation(
                    article_id=article.id,
                    source_entity_id=source_entity.id,
                    target_entity_id=target_entity.id,
                    relation_type=relation_type,
                    relation_detail=rel.get('detail'),
                    relation_period=rel.get('period'),
                    risk_weight=risk_weight
                )
                session.add(relation)
                relations_saved += 1

            # 4. 위험 요소 저장
            for risk in risks:
                news_risk = NewsRisk(
                    article_id=article.id,
                    risk_type=risk.get('type', 'unknown'),
                    description=risk['description'],
                    severity=risk.get('severity', 'medium')
                )
                session.add(news_risk)

            if dry_run:
                await session.rollback()
                return {
                    "success": True,
                    "dry_run": True,
                    "article_id": str(article.id),
                    "stats": {
                        "entities": len(entities),
                        "relations": relations_saved,
                        "risks": len(risks)
                    }
                }

            await session.commit()

            return {
                "success": True,
                "article_id": str(article.id),
                "stats": {
                    "entities": len(entities),
                    "relations": relations_saved,
                    "risks": len(risks),
                    "matched_companies": sum(1 for e in entity_map.values() if e.matched_company_id),
                    "matched_officers": sum(1 for e in entity_map.values() if e.matched_officer_id)
                }
            }

        except Exception as e:
            await session.rollback()
            return {
                "success": False,
                "error": str(e),
                "article_id": None
            }


async def get_article_stats() -> dict:
    """
    현재 저장된 기사 통계 조회
    """
    async with async_session() as session:
        articles = await session.execute(text("SELECT COUNT(*) FROM news_articles"))
        entities = await session.execute(text("SELECT COUNT(*) FROM news_entities"))
        relations = await session.execute(text("SELECT COUNT(*) FROM news_relations"))
        risks = await session.execute(text("SELECT COUNT(*) FROM news_risks"))

        return {
            "articles": articles.scalar(),
            "entities": entities.scalar(),
            "relations": relations.scalar(),
            "risks": risks.scalar()
        }


# CLI 실행
if __name__ == "__main__":
    async def main():
        # 테스트: 통계 조회
        stats = await get_article_stats()
        print("=== News DB Stats ===")
        print(f"Articles: {stats['articles']}")
        print(f"Entities: {stats['entities']}")
        print(f"Relations: {stats['relations']}")
        print(f"Risks: {stats['risks']}")

    asyncio.run(main())
