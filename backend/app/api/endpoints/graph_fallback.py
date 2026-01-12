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
        # 1. 중심 회사 조회 (investment_grade 포함)
        if is_corp_code:
            company_query = text("""
                SELECT c.id::text, c.name, c.corp_code, c.ticker, c.market, c.sector,
                       rs.investment_grade
                FROM companies c
                LEFT JOIN risk_scores rs ON c.id = rs.company_id
                WHERE c.corp_code = :company_id
            """)
        else:
            company_query = text("""
                SELECT c.id::text, c.name, c.corp_code, c.ticker, c.market, c.sector,
                       rs.investment_grade
                FROM companies c
                LEFT JOIN risk_scores rs ON c.id = rs.company_id
                WHERE c.id::text = :company_id
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
                "sector": company.sector,
                "investment_grade": company.investment_grade
            }
        ))
        seen_node_ids.add(center_id)
        
        # 2. 현재 임원 조회 (적자기업 경력 수 포함)
        officers_query = text("""
            SELECT DISTINCT o.id::text, o.name, o.birth_date, op.position, op.is_current
            FROM officers o
            JOIN officer_positions op ON o.id = op.officer_id
            WHERE op.company_id::text = :company_id AND op.is_current = true
            LIMIT 50
        """)
        result = await db.execute(officers_query, {"company_id": center_id})
        officers = result.fetchall()

        # 적자기업 ID 목록 조회 (최근 2년 적자 회사)
        deficit_query = text("""
            SELECT DISTINCT company_id::text
            FROM financial_statements
            WHERE net_income < 0
            AND fiscal_year >= EXTRACT(YEAR FROM CURRENT_DATE) - 2
        """)
        deficit_result = await db.execute(deficit_query)
        deficit_company_ids = {row[0] for row in deficit_result.fetchall()}

        for officer in officers:
            if officer.id not in seen_node_ids:
                # 해당 임원의 적자기업 경력 수 계산 (동명이인 방지: 이름 + 출생년월 비교)
                # 주의: 현재 조회 중인 회사(center_id)는 제외 - 과거 경력만 카운트
                deficit_career_query = text("""
                    SELECT COUNT(DISTINCT op2.company_id)
                    FROM officer_positions op2
                    JOIN officers o2 ON op2.officer_id = o2.id
                    WHERE o2.name = :name
                    AND (o2.birth_date = :birth_date OR (o2.birth_date IS NULL AND :birth_date IS NULL))
                    AND op2.company_id::text = ANY(:deficit_ids)
                    AND op2.company_id::text != :current_company_id
                """)
                deficit_result = await db.execute(deficit_career_query, {
                    "name": officer.name,
                    "birth_date": officer.birth_date,
                    "deficit_ids": list(deficit_company_ids),
                    "current_company_id": center_id
                })
                deficit_career_count = deficit_result.scalar() or 0

                # 상장사 경력 수 계산 (동명이인 방지: 이름 + 출생년월 비교)
                career_query = text("""
                    SELECT COUNT(DISTINCT op2.company_id)
                    FROM officer_positions op2
                    JOIN officers o2 ON op2.officer_id = o2.id
                    WHERE o2.name = :name
                    AND (o2.birth_date = :birth_date OR (o2.birth_date IS NULL AND :birth_date IS NULL))
                """)
                career_result = await db.execute(career_query, {
                    "name": officer.name,
                    "birth_date": officer.birth_date
                })
                listed_career_count = career_result.scalar() or 0

                nodes.append(GraphNode(
                    id=officer.id,
                    type="Officer",
                    properties={
                        "name": officer.name,
                        "birth_date": officer.birth_date,
                        "position": officer.position,
                        "listed_career_count": listed_career_count,
                        "deficit_career_count": deficit_career_count
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
                       s.is_related_party, s.subscription_amount, s.cb_id::text,
                       cb.bond_name, cb.issue_date::text as issue_date
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
                            "is_related_party": sub.is_related_party,
                            "current_investment": {
                                "cb_id": sub.cb_id,
                                "bond_name": sub.bond_name,
                                "issue_date": sub.issue_date,
                                "amount": sub.subscription_amount
                            }
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
        
        # 5. depth >= 3: 임원 타사 경력 (동명이인 방지: 이름 + 출생년월 비교)
        if depth >= 3:
            # 현재 임원들의 (이름, 출생년월) 쌍으로 동일인 식별
            officer_identities = {(o.name, o.birth_date) for o in officers}
            officer_names = [o.name for o in officers]
            if officer_names:
                careers_query = text("""
                    SELECT DISTINCT c.id::text as company_id, c.name as company_name,
                           o.id::text as officer_id, o.name as officer_name,
                           o.birth_date, op.position
                    FROM officer_positions op
                    JOIN officers o ON op.officer_id = o.id
                    JOIN companies c ON op.company_id = c.id
                    WHERE o.name = ANY(:names)
                      AND c.id::text != :center_id
                    LIMIT 50
                """)
                result = await db.execute(careers_query, {
                    "names": officer_names,
                    "center_id": center_id
                })
                careers = result.fetchall()

                for career in careers:
                    # 동명이인 필터링: (이름, 출생년월) 쌍이 일치하는 경우만 포함
                    if (career.officer_name, career.birth_date) not in officer_identities:
                        continue  # 동명이인이면 스킵

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
    """임원 경력 조회 (PostgreSQL 폴백)

    v2.4 개선:
    - career_raw_text: 사업보고서 '주요경력' 원문 텍스트 추가
    - 패턴 파싱 실패해도 원문은 항상 표시 가능
    """
    try:
        # 임원 정보 조회 (career_history JSON + career_raw_text 원문 포함)
        officer_query = text("""
            SELECT id::text, name, birth_date, position, career_history, career_raw_text
            FROM officers WHERE id::text = :officer_id
        """)
        result = await db.execute(officer_query, {"officer_id": officer_id})
        officer = result.fetchone()

        if not officer:
            raise HTTPException(status_code=404, detail="Officer not found")

        # 경력 조회 (officer_positions 테이블) - 중복 제거: 동일 회사는 최신 레코드만 반환
        # v2.5: 동일 회사 내 직책이 다르더라도 가장 최근 보고서 기준 1개만 표시
        career_query = text("""
            SELECT DISTINCT ON (c.id)
                   c.id::text as company_id, c.name as company_name,
                   op.position, op.term_start_date::text, op.term_end_date::text, op.is_current,
                   op.source_report_date::text
            FROM officer_positions op
            JOIN companies c ON op.company_id = c.id
            WHERE op.officer_id::text = :officer_id
            ORDER BY c.id, op.source_report_date DESC NULLS LAST, op.is_current DESC
        """)
        result = await db.execute(career_query, {"officer_id": officer_id})
        careers = result.fetchall()

        # 현재 재직 중인 경력을 상단에 배치
        career_history = []
        current_careers = []
        past_careers = []
        for c in careers:
            career_item = {
                "company_id": c.company_id,
                "company_name": c.company_name,
                "position": c.position,
                "start_date": c.term_start_date,
                "end_date": c.term_end_date,
                "is_current": c.is_current,
                "is_listed": True,
                "source": "db",
                "source_report_date": c.source_report_date  # v2.5: 보고서 기준일 추가
            }
            if c.is_current:
                current_careers.append(career_item)
            else:
                past_careers.append(career_item)
        career_history = current_careers + past_careers

        # officers.career_history JSON에서 사업보고서 주요경력 정보 추출
        # 출처: 사업보고서 > "임원 및 직원 등의 현황" > "주요경력" 필드
        parsed_careers = []
        if officer.career_history:
            import json
            try:
                raw_careers = officer.career_history if isinstance(officer.career_history, list) else json.loads(officer.career_history)
                for item in raw_careers:
                    if isinstance(item, dict):
                        career_text = item.get("text", "")  # 변수명 변경: text → career_text (SQLAlchemy text() 충돌 방지)
                        status = item.get("status", "unknown")
                        # 주요경력 텍스트에서 회사명과 직책 분리 시도
                        # 예: "(주)이아이디 재무이사" -> company_name: "(주)이아이디", position: "재무이사"
                        parts = career_text.rsplit(" ", 1) if career_text else ["", ""]
                        company_name = parts[0] if len(parts) > 1 else career_text
                        position = parts[1] if len(parts) > 1 else ""

                        parsed_careers.append({
                            "company_name": company_name,
                            "company_id": None,  # 비상장사는 ID 없음
                            "position": position,
                            "start_date": None,
                            "end_date": None,
                            "is_current": status == "current",
                            "is_listed": False,  # 비상장사 경력
                            "source": "disclosure",  # 사업보고서 출처
                            "raw_text": career_text  # 원본 텍스트 보존
                        })
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning(f"Failed to parse career_history: {e}")

        # 상장사 DB 경력 (상단) + 사업보고서 주요경력 (하단) 통합
        # 규칙: 상장사 임원 DB를 먼저 표시하고, 사업보고서 주요경력은 아래에 표시
        all_careers = career_history + parsed_careers

        return {
            "officer": {
                "id": officer.id,
                "type": "Officer",
                "properties": {
                    "name": officer.name,
                    "birth_date": officer.birth_date,
                    "position": officer.position
                }
            },
            "career_history": all_careers,  # 통합된 경력 목록 (db + disclosure)
            "career_raw_text": officer.career_raw_text  # 사업보고서 주요경력 원문 (v2.4)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in officer career fallback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Response Models for Subscriber Investments
class CBInfo(BaseModel):
    id: str
    bond_name: Optional[str] = None
    issue_date: Optional[str] = None
    total_amount: Optional[int] = None


class InvestmentHistoryItem(BaseModel):
    company_id: str
    company_name: str
    total_amount: Optional[int] = None
    investment_count: int = 0
    first_investment: Optional[str] = None
    latest_investment: Optional[str] = None
    cbs: List[CBInfo] = []


class SubscriberInvestmentFallbackResponse(BaseModel):
    subscriber: GraphNode
    investment_history: List[InvestmentHistoryItem]


@router.get("/subscriber/{subscriber_id}/investments", response_model=SubscriberInvestmentFallbackResponse)
async def get_subscriber_investments_fallback(
    subscriber_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    CB 인수자 투자 이력 조회 (PostgreSQL 폴백)

    - 투자한 회사 목록
    - 각 회사별 CB 목록
    """
    try:
        # 1. 인수자 정보 조회
        subscriber_query = text("""
            SELECT id::text, subscriber_name, subscriber_type, is_related_party
            FROM cb_subscribers
            WHERE id::text = :subscriber_id
            LIMIT 1
        """)
        result = await db.execute(subscriber_query, {"subscriber_id": subscriber_id})
        subscriber = result.fetchone()

        if not subscriber:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        # 2. 인수자의 투자 이력 조회 (같은 이름의 인수자 모두 포함)
        investments_query = text("""
            SELECT
                c.id::text as company_id,
                c.name as company_name,
                cb.id::text as cb_id,
                cb.bond_name,
                cb.issue_date::text,
                s.subscription_amount as amount
            FROM cb_subscribers s
            JOIN convertible_bonds cb ON s.cb_id = cb.id
            JOIN companies c ON cb.company_id = c.id
            WHERE s.subscriber_name = (
                SELECT subscriber_name FROM cb_subscribers WHERE id::text = :subscriber_id
            )
            ORDER BY cb.issue_date DESC
        """)
        result = await db.execute(investments_query, {"subscriber_id": subscriber_id})
        investments = result.fetchall()

        # 3. 회사별로 그룹화
        company_investments: Dict[str, Dict[str, Any]] = {}
        for inv in investments:
            company_id = inv.company_id
            if company_id not in company_investments:
                company_investments[company_id] = {
                    "company_id": company_id,
                    "company_name": inv.company_name,
                    "total_amount": 0,
                    "investment_count": 0,
                    "first_investment": None,
                    "latest_investment": None,
                    "cbs": []
                }

            comp = company_investments[company_id]
            comp["investment_count"] += 1
            if inv.amount:
                comp["total_amount"] += inv.amount

            # 날짜 추적
            if inv.issue_date:
                if comp["first_investment"] is None or inv.issue_date < comp["first_investment"]:
                    comp["first_investment"] = inv.issue_date
                if comp["latest_investment"] is None or inv.issue_date > comp["latest_investment"]:
                    comp["latest_investment"] = inv.issue_date

            # CB 정보 추가
            comp["cbs"].append(CBInfo(
                id=inv.cb_id,
                bond_name=inv.bond_name,
                issue_date=inv.issue_date,
                total_amount=inv.amount
            ))

        # 4. 최신 투자순 정렬
        investment_history = sorted(
            [InvestmentHistoryItem(**comp) for comp in company_investments.values()],
            key=lambda x: x.latest_investment or "",
            reverse=True
        )

        return SubscriberInvestmentFallbackResponse(
            subscriber=GraphNode(
                id=subscriber.id,
                type="Subscriber",
                properties={
                    "name": subscriber.subscriber_name,
                    "type": subscriber.subscriber_type,
                    "is_related_party": subscriber.is_related_party
                }
            ),
            investment_history=investment_history
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in subscriber investments fallback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
