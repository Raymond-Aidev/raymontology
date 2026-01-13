"""
News 관계 분석 API 엔드포인트

뉴스 기반 기업 관계 복잡도 조회 API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text
from typing import Optional, List
from uuid import UUID
import logging

from app.database import get_db
from app.models.news import (
    NewsArticle, NewsEntity, NewsRelation, NewsRisk, NewsCompanyComplexity,
    RISK_WEIGHTS, COMPLEXITY_GRADES
)
from app.models.companies import Company

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["News Analysis"])


# ============================================================================
# Response Formatters
# ============================================================================

def format_article_response(article: NewsArticle) -> dict:
    """기사 응답 포맷"""
    return {
        "id": str(article.id),
        "url": article.url,
        "title": article.title,
        "publisher": article.publisher,
        "publish_date": article.publish_date.isoformat() if article.publish_date else None,
        "author": article.author,
        "summary": article.summary,
        "status": article.status,
        "created_at": article.created_at.isoformat() if article.created_at else None,
    }


def format_entity_response(entity: NewsEntity) -> dict:
    """엔티티 응답 포맷"""
    return {
        "id": str(entity.id),
        "entity_type": entity.entity_type,
        "entity_name": entity.entity_name,
        "entity_role": entity.entity_role,
        "matched_company_id": str(entity.matched_company_id) if entity.matched_company_id else None,
        "matched_corp_code": entity.matched_corp_code,
        "match_confidence": float(entity.match_confidence) if entity.match_confidence else None,
    }


def format_relation_response(relation: NewsRelation) -> dict:
    """관계 응답 포맷"""
    return {
        "id": str(relation.id),
        "relation_type": relation.relation_type,
        "relation_detail": relation.relation_detail,
        "relation_period": relation.relation_period,
        "risk_weight": float(relation.risk_weight) if relation.risk_weight else 1.0,
        "source_entity_id": str(relation.source_entity_id),
        "target_entity_id": str(relation.target_entity_id),
    }


def format_complexity_response(complexity: NewsCompanyComplexity, company: Optional[Company] = None) -> dict:
    """복잡도 응답 포맷"""
    response = {
        "company_id": str(complexity.company_id),
        "corp_code": complexity.corp_code,
        "complexity_score": float(complexity.complexity_score),
        "complexity_grade": complexity.complexity_grade,
        "entity_count": complexity.entity_count,
        "relation_count": complexity.relation_count,
        "high_risk_count": complexity.high_risk_count,
        "article_count": complexity.article_count,
        "calculated_at": complexity.calculated_at.isoformat() if complexity.calculated_at else None,
    }
    if company:
        response["company_name"] = company.name
        response["company_ticker"] = company.ticker
        response["company_market"] = company.market
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/statistics")
async def get_news_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    News 분석 시스템 전체 통계
    """
    try:
        articles = await db.execute(select(func.count(NewsArticle.id)))
        entities = await db.execute(select(func.count(NewsEntity.id)))
        relations = await db.execute(select(func.count(NewsRelation.id)))
        risks = await db.execute(select(func.count(NewsRisk.id)))
        companies = await db.execute(select(func.count(NewsCompanyComplexity.id)))

        # 등급별 분포
        grade_query = (
            select(
                NewsCompanyComplexity.complexity_grade,
                func.count(NewsCompanyComplexity.id).label('count')
            )
            .group_by(NewsCompanyComplexity.complexity_grade)
        )
        grade_result = await db.execute(grade_query)
        grade_distribution = {row[0]: row[1] for row in grade_result.all()}

        return {
            "articles": articles.scalar() or 0,
            "entities": entities.scalar() or 0,
            "relations": relations.scalar() or 0,
            "risks": risks.scalar() or 0,
            "companies_analyzed": companies.scalar() or 0,
            "grade_distribution": grade_distribution,
            "risk_weights": RISK_WEIGHTS,
            "grade_thresholds": COMPLEXITY_GRADES
        }

    except Exception as e:
        logger.error(f"Error fetching news statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles")
async def list_articles(
    status: Optional[str] = Query(None, description="상태 필터 (active, archived, deleted)"),
    publisher: Optional[str] = Query(None, description="매체 필터"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    기사 목록 조회
    """
    try:
        query = select(NewsArticle).order_by(desc(NewsArticle.created_at))

        if status:
            query = query.where(NewsArticle.status == status)
        if publisher:
            query = query.where(NewsArticle.publisher.ilike(f"%{publisher}%"))

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        articles = result.scalars().all()

        # 전체 개수
        count_query = select(func.count(NewsArticle.id))
        if status:
            count_query = count_query.where(NewsArticle.status == status)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "articles": [format_article_response(a) for a in articles]
        }

    except Exception as e:
        logger.error(f"Error listing articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/{article_id}")
async def get_article_detail(
    article_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    기사 상세 조회 (엔티티, 관계, 위험 포함)
    """
    try:
        # 기사
        article_result = await db.execute(
            select(NewsArticle).where(NewsArticle.id == article_id)
        )
        article = article_result.scalar_one_or_none()

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # 엔티티
        entities_result = await db.execute(
            select(NewsEntity).where(NewsEntity.article_id == article_id)
        )
        entities = entities_result.scalars().all()

        # 관계
        relations_result = await db.execute(
            select(NewsRelation).where(NewsRelation.article_id == article_id)
        )
        relations = relations_result.scalars().all()

        # 위험
        risks_result = await db.execute(
            select(NewsRisk).where(NewsRisk.article_id == article_id)
        )
        risks = risks_result.scalars().all()

        response = format_article_response(article)
        response["entities"] = [format_entity_response(e) for e in entities]
        response["relations"] = [format_relation_response(r) for r in relations]
        response["risks"] = [
            {
                "id": str(r.id),
                "risk_type": r.risk_type,
                "description": r.description,
                "severity": r.severity
            }
            for r in risks
        ]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/complexity/ranking")
async def get_complexity_ranking(
    grade: Optional[str] = Query(None, description="등급 필터 (A,B,C,D,E,F)"),
    min_score: Optional[float] = Query(None, description="최소 점수"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    기업 복잡도 랭킹 조회
    """
    try:
        query = (
            select(NewsCompanyComplexity, Company)
            .outerjoin(Company, NewsCompanyComplexity.company_id == Company.id)
            .order_by(desc(NewsCompanyComplexity.complexity_score))
        )

        if grade:
            grades = [g.strip() for g in grade.split(',')]
            query = query.where(NewsCompanyComplexity.complexity_grade.in_(grades))

        if min_score is not None:
            query = query.where(NewsCompanyComplexity.complexity_score >= min_score)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        rankings = []
        for i, (complexity, company) in enumerate(rows, start=offset + 1):
            item = format_complexity_response(complexity, company)
            item["rank"] = i
            rankings.append(item)

        # 전체 개수
        count_query = select(func.count(NewsCompanyComplexity.id))
        if grade:
            count_query = count_query.where(NewsCompanyComplexity.complexity_grade.in_(grades))
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "rankings": rankings
        }

    except Exception as e:
        logger.error(f"Error fetching complexity ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/complexity/company/{company_id}")
async def get_company_complexity(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업의 복잡도 조회
    """
    try:
        query = (
            select(NewsCompanyComplexity, Company)
            .outerjoin(Company, NewsCompanyComplexity.company_id == Company.id)
            .where(NewsCompanyComplexity.company_id == company_id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            # 복잡도 데이터가 없으면 기본값 반환
            return {
                "company_id": str(company_id),
                "complexity_score": 0,
                "complexity_grade": "A",
                "entity_count": 0,
                "relation_count": 0,
                "high_risk_count": 0,
                "article_count": 0,
                "message": "No news data analyzed for this company"
            }

        complexity, company = row
        return format_complexity_response(complexity, company)

    except Exception as e:
        logger.error(f"Error fetching complexity for {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}/articles")
async def get_company_articles(
    company_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업이 언급된 기사 목록
    """
    try:
        # 해당 기업과 매칭된 엔티티의 기사 조회
        query = (
            select(NewsArticle)
            .join(NewsEntity, NewsArticle.id == NewsEntity.article_id)
            .where(NewsEntity.matched_company_id == company_id)
            .distinct()
            .order_by(desc(NewsArticle.publish_date))
            .limit(limit)
        )

        result = await db.execute(query)
        articles = result.scalars().all()

        return {
            "company_id": str(company_id),
            "total": len(articles),
            "articles": [format_article_response(a) for a in articles]
        }

    except Exception as e:
        logger.error(f"Error fetching articles for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}/relations")
async def get_company_relations(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 기업의 관계 네트워크 조회

    기사에서 추출된 모든 관계를 반환합니다.
    """
    try:
        # 해당 기업과 매칭된 엔티티 조회
        entity_query = (
            select(NewsEntity)
            .where(NewsEntity.matched_company_id == company_id)
        )
        entity_result = await db.execute(entity_query)
        entities = entity_result.scalars().all()

        if not entities:
            return {
                "company_id": str(company_id),
                "entities": [],
                "relations": [],
                "message": "No news data for this company"
            }

        entity_ids = [e.id for e in entities]

        # 관계 조회 (source 또는 target)
        relations_query = (
            select(NewsRelation, NewsEntity)
            .join(NewsEntity, NewsRelation.target_entity_id == NewsEntity.id)
            .where(NewsRelation.source_entity_id.in_(entity_ids))
        )
        relations_result = await db.execute(relations_query)
        outgoing = relations_result.all()

        relations_query2 = (
            select(NewsRelation, NewsEntity)
            .join(NewsEntity, NewsRelation.source_entity_id == NewsEntity.id)
            .where(NewsRelation.target_entity_id.in_(entity_ids))
        )
        relations_result2 = await db.execute(relations_query2)
        incoming = relations_result2.all()

        # 관련 엔티티 수집
        related_entities = {}
        relations_list = []

        for relation, target_entity in outgoing:
            rel_data = format_relation_response(relation)
            rel_data["target_entity"] = format_entity_response(target_entity)
            rel_data["direction"] = "outgoing"
            relations_list.append(rel_data)
            related_entities[str(target_entity.id)] = format_entity_response(target_entity)

        for relation, source_entity in incoming:
            rel_data = format_relation_response(relation)
            rel_data["source_entity"] = format_entity_response(source_entity)
            rel_data["direction"] = "incoming"
            relations_list.append(rel_data)
            related_entities[str(source_entity.id)] = format_entity_response(source_entity)

        return {
            "company_id": str(company_id),
            "entity_count": len(entities),
            "relation_count": len(relations_list),
            "entities": list(related_entities.values()),
            "relations": relations_list
        }

    except Exception as e:
        logger.error(f"Error fetching relations for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
