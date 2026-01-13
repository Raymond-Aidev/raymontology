"""
기업별 관계 복잡도 계산기

뉴스에서 추출된 관계 데이터를 기반으로 기업별 복잡도 스코어와 등급을 산출합니다.

복잡도 = Σ(관계 수 × 위험 가중치) + 고위험 요소 × 10

등급 기준:
    A: 0-20점 (단순)
    B: 20-40점 (보통)
    C: 40-60점 (복잡)
    D: 60-80점 (매우 복잡)
    E: 80-90점 (위험)
    F: 90-100점 (고위험)
"""
import asyncio
import sys
import os
from decimal import Decimal
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.models.news import (
    NewsArticle, NewsEntity, NewsRelation, NewsRisk, NewsCompanyComplexity,
    RISK_WEIGHTS, COMPLEXITY_GRADES
)


DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def calculate_grade(score: float) -> str:
    """
    점수를 등급으로 변환
    """
    for grade, (low, high) in COMPLEXITY_GRADES.items():
        if low <= score < high:
            return grade
    return 'F'


async def calculate_company_complexity(company_id: str, corp_code: str) -> dict:
    """
    특정 기업의 복잡도 계산

    Args:
        company_id: companies.id (UUID string)
        corp_code: companies.corp_code

    Returns:
        {"score": float, "grade": str, "stats": {...}}
    """
    async with async_session() as session:
        # 1. 해당 기업과 관련된 엔티티 조회
        entities_result = await session.execute(
            select(NewsEntity)
            .where(NewsEntity.matched_company_id == company_id)
        )
        entities = entities_result.scalars().all()

        if not entities:
            return {
                "score": 0,
                "grade": "A",
                "stats": {
                    "entity_count": 0,
                    "relation_count": 0,
                    "high_risk_count": 0,
                    "article_count": 0
                }
            }

        entity_ids = [e.id for e in entities]
        article_ids = set(e.article_id for e in entities)

        # 2. 관계 조회 (source 또는 target)
        relations_result = await session.execute(
            select(NewsRelation)
            .where(
                (NewsRelation.source_entity_id.in_(entity_ids)) |
                (NewsRelation.target_entity_id.in_(entity_ids))
            )
        )
        relations = relations_result.scalars().all()

        # 3. 관련 기사의 위험 요소 조회
        risks_result = await session.execute(
            select(NewsRisk)
            .where(NewsRisk.article_id.in_(article_ids))
        )
        risks = risks_result.scalars().all()

        # 4. 복잡도 점수 계산
        # 기본: 관계 수 × 위험 가중치
        relation_score = sum(float(r.risk_weight) for r in relations)

        # 고위험 요소 가산
        high_risk_count = sum(1 for r in risks if r.severity in ('high', 'critical'))
        risk_score = high_risk_count * 10

        # 엔티티 다양성 가산
        unique_entity_types = set(e.entity_type for e in entities)
        diversity_score = len(unique_entity_types) * 2

        # 최종 점수 (0-100 정규화)
        raw_score = relation_score + risk_score + diversity_score
        normalized_score = min(100, raw_score)

        return {
            "score": normalized_score,
            "grade": calculate_grade(normalized_score),
            "stats": {
                "entity_count": len(entities),
                "relation_count": len(relations),
                "high_risk_count": high_risk_count,
                "article_count": len(article_ids)
            }
        }


async def update_company_complexity(
    company_id: str,
    corp_code: str,
    dry_run: bool = False
) -> dict:
    """
    기업 복잡도 계산 후 DB 업데이트 (upsert)
    """
    result = await calculate_company_complexity(company_id, corp_code)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            **result
        }

    async with async_session() as session:
        try:
            # Upsert
            stmt = insert(NewsCompanyComplexity).values(
                company_id=company_id,
                corp_code=corp_code,
                complexity_score=Decimal(str(result["score"])),
                complexity_grade=result["grade"],
                entity_count=result["stats"]["entity_count"],
                relation_count=result["stats"]["relation_count"],
                high_risk_count=result["stats"]["high_risk_count"],
                article_count=result["stats"]["article_count"]
            )

            stmt = stmt.on_conflict_do_update(
                constraint='uq_news_company_complexity_company_id',
                set_={
                    'complexity_score': Decimal(str(result["score"])),
                    'complexity_grade': result["grade"],
                    'entity_count': result["stats"]["entity_count"],
                    'relation_count': result["stats"]["relation_count"],
                    'high_risk_count': result["stats"]["high_risk_count"],
                    'article_count': result["stats"]["article_count"],
                    'calculated_at': func.now()
                }
            )

            await session.execute(stmt)
            await session.commit()

            return {
                "success": True,
                **result
            }

        except Exception as e:
            await session.rollback()
            return {
                "success": False,
                "error": str(e)
            }


async def recalculate_all_companies() -> dict:
    """
    모든 관련 기업의 복잡도 재계산

    Returns:
        {"total": int, "updated": int, "errors": int}
    """
    async with async_session() as session:
        # news_entities에서 매칭된 기업 목록 조회
        result = await session.execute(
            text("""
                SELECT DISTINCT ne.matched_company_id, ne.matched_corp_code
                FROM news_entities ne
                WHERE ne.matched_company_id IS NOT NULL
            """)
        )
        companies = result.fetchall()

    total = len(companies)
    updated = 0
    errors = 0

    for company_id, corp_code in companies:
        result = await update_company_complexity(str(company_id), corp_code)
        if result.get("success"):
            updated += 1
        else:
            errors += 1
            print(f"Error updating {corp_code}: {result.get('error')}")

    return {
        "total": total,
        "updated": updated,
        "errors": errors
    }


async def get_complexity_ranking(limit: int = 20) -> list[dict]:
    """
    복잡도 랭킹 조회
    """
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    ncc.corp_code,
                    c.name as company_name,
                    ncc.complexity_score,
                    ncc.complexity_grade,
                    ncc.entity_count,
                    ncc.relation_count,
                    ncc.high_risk_count,
                    ncc.article_count
                FROM news_company_complexity ncc
                LEFT JOIN companies c ON ncc.company_id = c.id
                ORDER BY ncc.complexity_score DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        rows = result.fetchall()

        return [
            {
                "corp_code": row[0],
                "company_name": row[1],
                "complexity_score": float(row[2]),
                "complexity_grade": row[3],
                "entity_count": row[4],
                "relation_count": row[5],
                "high_risk_count": row[6],
                "article_count": row[7]
            }
            for row in rows
        ]


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="News Complexity Calculator")
    parser.add_argument("--recalculate", action="store_true", help="Recalculate all companies")
    parser.add_argument("--ranking", type=int, default=0, help="Show top N companies")
    args = parser.parse_args()

    async def main():
        if args.recalculate:
            print("=== Recalculating All Companies ===")
            result = await recalculate_all_companies()
            print(f"Total: {result['total']}")
            print(f"Updated: {result['updated']}")
            print(f"Errors: {result['errors']}")

        if args.ranking > 0:
            print(f"\n=== Top {args.ranking} Complexity Ranking ===")
            ranking = await get_complexity_ranking(args.ranking)
            for i, item in enumerate(ranking, 1):
                print(f"{i}. [{item['complexity_grade']}] {item['company_name']} "
                      f"(Score: {item['complexity_score']:.1f}, "
                      f"Relations: {item['relation_count']}, "
                      f"High Risk: {item['high_risk_count']})")

    asyncio.run(main())
