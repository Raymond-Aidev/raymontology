"""
PostgreSQL 기반 Graph API (Neo4j 폴백)

Neo4j가 없을 때 PostgreSQL 데이터만으로 관계도를 제공합니다.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph-fallback", tags=["graph-fallback"])


# Response Models (graph.py와 동일)
class GraphNode(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any]


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    center: Optional[Dict[str, str]] = None


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/company/{company_id}", response_model=GraphResponse)
async def get_company_network_fallback(
    company_id: str,
    depth: int = Query(1, ge=1, le=3),
    limit: int = Query(100, ge=10, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    PostgreSQL 기반 회사 관계 네트워크 (Neo4j 폴백)
    
    - depth 1: 임원 + CB
    - depth 2: 1단계 + CB 인수자
    - depth 3: 2단계 + 임원 타사 경력
    """
    nodes = []
    relationships = []
    seen_node_ids = set()
    rel_counter = 0
    
    # company_id가 corp_code인지 UUID인지 확인
    is_corp_code = len(company_id) == 8 and company_id.isdigit()
    
    try:
        # 1. 중심 회사 조회
        if is_corp_code:
            company_query = text("""
                SELECT id::text, name, corp_code, ticker, market, sector
                FROM companies WHERE corp_code = :company_id
            """)
        else:
            company_query = text("""
                SELECT id::text, name, corp_code, ticker, market, sector
                FROM companies WHERE id::text = :company_id
            """)
        
        result = await db.execute(company_query, {"company_id": company_id})
        company = result.fetchone()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        center_id = company.id
        nodes.append(GraphNode(
            id=center_id,
            type="Company",
            properties={
                "name": company.name,
                "corp_code": company.corp_code,
                "ticker": company.ticker,
                "market": company.market,
                "sector": company.sector
            }
        ))
        seen_node_ids.add(center_id)
        
        # 2. 현재 임원 조회
        officers_query = text("""
            SELECT DISTINCT o.id::text, o.name, o.birth_date, op.position, op.is_current
            FROM officers o
            JOIN officer_positions op ON o.id = op.officer_id
            WHERE op.company_id::text = :company_id AND op.is_current = true
            LIMIT 50
        """)
        result = await db.execute(officers_query, {"company_id": center_id})
        officers = result.fetchall()
        
        for officer in officers:
            if officer.id not in seen_node_ids:
                nodes.append(GraphNode(
                    id=officer.id,
                    type="Officer",
                    properties={
                        "name": officer.name,
                        "birth_date": officer.birth_date,
                        "position": officer.position
                    }
                ))
                seen_node_ids.add(officer.id)
                
                rel_counter += 1
                relationships.append(GraphRelationship(
                    id=f"rel_{rel_counter}",
                    type="WORKS_AT",
                    source=officer.id,
                    target=center_id,
                    properties={"position": officer.position, "is_current": True}
                ))
        
        # 3. 전환사채(CB) 조회
        cb_query = text("""
            SELECT id::text, bond_name, issue_date::text, issue_amount, bond_type
            FROM convertible_bonds
            WHERE company_id::text = :company_id
            ORDER BY issue_date DESC
            LIMIT 20
        """)
        result = await db.execute(cb_query, {"company_id": center_id})
        cbs = result.fetchall()

        for cb in cbs:
            if cb.id not in seen_node_ids:
                nodes.append(GraphNode(
                    id=cb.id,
                    type="ConvertibleBond",
                    properties={
                        "bond_name": cb.bond_name,
                        "issue_date": cb.issue_date,
                        "issue_amount": cb.issue_amount,
                        "bond_type": cb.bond_type
                    }
                ))
                seen_node_ids.add(cb.id)
                
                rel_counter += 1
                relationships.append(GraphRelationship(
                    id=f"rel_{rel_counter}",
                    type="ISSUED",
                    source=center_id,
                    target=cb.id,
                    properties={}
                ))
        
        # 4. depth >= 2: CB 인수자 조회
        if depth >= 2:
            subscribers_query = text("""
                SELECT DISTINCT s.id::text, s.subscriber_name, s.subscriber_type, 
                       s.is_related_party, s.subscription_amount, s.cb_id::text
                FROM cb_subscribers s
                JOIN convertible_bonds cb ON s.cb_id = cb.id
                WHERE cb.company_id::text = :company_id
                LIMIT 50
            """)
            result = await db.execute(subscribers_query, {"company_id": center_id})
            subscribers = result.fetchall()
            
            for sub in subscribers:
                if sub.id not in seen_node_ids:
                    nodes.append(GraphNode(
                        id=sub.id,
                        type="Subscriber",
                        properties={
                            "name": sub.subscriber_name,
                            "type": sub.subscriber_type,
                            "is_related_party": sub.is_related_party
                        }
                    ))
                    seen_node_ids.add(sub.id)
                
                rel_counter += 1
                relationships.append(GraphRelationship(
                    id=f"rel_{rel_counter}",
                    type="SUBSCRIBED",
                    source=sub.id,
                    target=sub.cb_id,
                    properties={"amount": sub.subscription_amount}
                ))
        
        # 5. depth >= 3: 임원 타사 경력
        if depth >= 3:
            # 현재 임원들의 이름으로 타 회사 경력 조회
            officer_names = [o.name for o in officers]
            if officer_names:
                careers_query = text("""
                    SELECT DISTINCT c.id::text as company_id, c.name as company_name, 
                           o.id::text as officer_id, o.name as officer_name, op.position
                    FROM officer_positions op
                    JOIN officers o ON op.officer_id = o.id
                    JOIN companies c ON op.company_id = c.id
                    WHERE o.name = ANY(:names) 
                      AND c.id::text != :center_id
                    LIMIT 30
                """)
                result = await db.execute(careers_query, {
                    "names": officer_names,
                    "center_id": center_id
                })
                careers = result.fetchall()
                
                for career in careers:
                    if career.company_id not in seen_node_ids:
                        nodes.append(GraphNode(
                            id=career.company_id,
                            type="Company",
                            properties={
                                "name": career.company_name,
                                "relation_type": "officer_career"
                            }
                        ))
                        seen_node_ids.add(career.company_id)
                    
                    rel_counter += 1
                    relationships.append(GraphRelationship(
                        id=f"rel_{rel_counter}",
                        type="WORKED_AT",
                        source=career.officer_id,
                        target=career.company_id,
                        properties={"position": career.position}
                    ))
        
        # 6. 대주주 조회
        shareholders_query = text("""
            SELECT id::text, shareholder_name, share_ratio, share_count, shareholder_type
            FROM major_shareholders
            WHERE company_id::text = :company_id
            ORDER BY share_ratio DESC NULLS LAST
            LIMIT 10
        """)
        result = await db.execute(shareholders_query, {"company_id": center_id})
        shareholders = result.fetchall()
        
        for sh in shareholders:
            if sh.id not in seen_node_ids:
                nodes.append(GraphNode(
                    id=sh.id,
                    type="Shareholder",
                    properties={
                        "name": sh.shareholder_name,
                        "share_ratio": float(sh.share_ratio) if sh.share_ratio else 0,
                        "share_count": sh.share_count,
                        "type": sh.shareholder_type
                    }
                ))
                seen_node_ids.add(sh.id)
                
                rel_counter += 1
                relationships.append(GraphRelationship(
                    id=f"rel_{rel_counter}",
                    type="SHAREHOLDER_OF",
                    source=sh.id,
                    target=center_id,
                    properties={"share_ratio": float(sh.share_ratio) if sh.share_ratio else 0}
                ))
        
        return GraphResponse(
            nodes=nodes,
            relationships=relationships,
            center={"type": "Company", "id": company_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in graph fallback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/officer/{officer_id}/career")
async def get_officer_career_fallback(
    officer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """임원 경력 조회 (PostgreSQL 폴백)"""
    try:
        # 임원 정보 조회 (career_history JSON 포함)
        officer_query = text("""
            SELECT id::text, name, birth_date, position, career_history
            FROM officers WHERE id::text = :officer_id
        """)
        result = await db.execute(officer_query, {"officer_id": officer_id})
        officer = result.fetchone()

        if not officer:
            raise HTTPException(status_code=404, detail="Officer not found")

        # 경력 조회 (officer_positions 테이블)
        career_query = text("""
            SELECT c.id::text as company_id, c.name as company_name,
                   op.position, op.term_start_date::text, op.term_end_date::text, op.is_current
            FROM officer_positions op
            JOIN companies c ON op.company_id = c.id
            WHERE op.officer_id::text = :officer_id
            ORDER BY op.is_current DESC, op.term_start_date DESC
        """)
        result = await db.execute(career_query, {"officer_id": officer_id})
        careers = result.fetchall()

        career_history = []
        for c in careers:
            career_history.append({
                "company_id": c.company_id,
                "company_name": c.company_name,
                "position": c.position,
                "start_date": c.term_start_date,
                "end_date": c.term_end_date,
                "is_current": c.is_current,
                "is_listed": True,
                "source": "db"
            })

        # officers.career_history JSON에서 추가 경력 정보 추출
        parsed_careers = []
        if officer.career_history:
            import json
            try:
                raw_careers = officer.career_history if isinstance(officer.career_history, list) else json.loads(officer.career_history)
                for item in raw_careers:
                    if isinstance(item, dict):
                        parsed_careers.append({
                            "text": item.get("text", ""),
                            "status": item.get("status", "unknown"),
                            "source": "parsed"
                        })
            except:
                pass

        return {
            "officer": {
                "id": officer.id,
                "type": "Officer",
                "properties": {
                    "name": officer.name,
                    "birth_date": officer.birth_date,
                    "position": officer.position,
                    "career_history": parsed_careers
                }
            },
            "career_history": career_history,
            "parsed_careers": parsed_careers
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in officer career fallback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
