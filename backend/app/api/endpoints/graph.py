"""
그래프 네트워크 API 엔드포인트

인터랙티브 그래프 시각화를 위한 API
- 회사 중심 네트워크
- 임원 경력 이력
- CB 인수자 투자 이력
- 노드 중심 전환
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import UUID

from neo4j.time import DateTime as Neo4jDateTime, Date as Neo4jDate, Time as Neo4jTime, Duration as Neo4jDuration
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, time, timedelta

from app.config import settings
from app.database import AsyncSessionLocal
import app.database as db_module  # 동적으로 neo4j_driver 접근
import logging

logger = logging.getLogger(__name__)


def serialize_neo4j_value(value: Any) -> Any:
    """Neo4j 타입을 JSON 직렬화 가능한 Python 타입으로 변환"""
    if value is None:
        return None
    elif isinstance(value, Neo4jDateTime):
        return value.to_native().isoformat()
    elif isinstance(value, Neo4jDate):
        return value.to_native().isoformat()
    elif isinstance(value, Neo4jTime):
        return value.to_native().isoformat()
    elif isinstance(value, Neo4jDuration):
        return str(value)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, time):
        return value.isoformat()
    elif isinstance(value, timedelta):
        return str(value)
    elif isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [serialize_neo4j_value(item) for item in value]
    else:
        return value


def serialize_node_properties(node: Any) -> Dict[str, Any]:
    """Neo4j 노드의 properties를 JSON 직렬화 가능한 딕셔너리로 변환"""
    return {k: serialize_neo4j_value(v) for k, v in dict(node.items()).items()}

router = APIRouter(prefix="/graph", tags=["graph"])


# Response Models
class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    type: str  # Company, Officer, ConvertibleBond, Subscriber
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    """그래프 관계"""
    id: str
    type: str  # WORKS_AT, WORKED_AT, ISSUED, SUBSCRIBED, etc.
    source: str
    target: str
    properties: Dict[str, Any]


class GraphResponse(BaseModel):
    """그래프 응답"""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    center: Optional[Dict[str, str]] = None


class CareerHistory(BaseModel):
    """임원 경력 이력"""
    company_id: Optional[str] = None  # 비상장사는 ID 없음
    company_name: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    is_listed: bool = True  # companies 테이블에 있으면 상장회사
    source: str = "db"  # "db": 상장사 임원 DB, "disclosure": 공시 파싱 경력


class OfficerCareerResponse(BaseModel):
    """임원 경력 응답"""
    officer: GraphNode
    career_history: List[CareerHistory]
    career_raw_text: Optional[str] = None  # 사업보고서 주요경력 원문 (v2.5)


class InvestmentHistory(BaseModel):
    """투자 이력"""
    company_id: str
    company_name: str
    total_amount: Optional[int] = None
    investment_count: int = 0
    first_investment: Optional[str] = None
    latest_investment: Optional[str] = None
    cbs: List[Dict[str, Any]] = []


class SubscriberInvestmentResponse(BaseModel):
    """인수자 투자 이력 응답"""
    subscriber: GraphNode
    investment_history: List[InvestmentHistory]


class RecenterRequest(BaseModel):
    """노드 중심 전환 요청"""
    node_type: str = Field(..., description="Company|Officer|ConvertibleBond|Subscriber")
    node_id: str
    depth: int = Field(1, ge=1, le=3)
    limit: int = Field(100, ge=10, le=500)


# Dependencies
def is_neo4j_available() -> bool:
    """Neo4j 드라이버 사용 가능 여부 확인"""
    return db_module.neo4j_driver is not None


async def get_neo4j_driver():
    """공유 Neo4j driver 제공 (app.database에서 초기화된 드라이버 사용)"""
    # 동적으로 neo4j_driver 참조 (init_db 이후 업데이트된 값 사용)
    driver = db_module.neo4j_driver
    if driver is None:
        raise HTTPException(status_code=503, detail="Neo4j not available")
    yield driver
    # 드라이버 종료는 app shutdown에서 처리 (database.close_db)


async def get_neo4j_driver_optional():
    """Neo4j driver 제공 (없으면 None 반환, 에러 없음)"""
    driver = db_module.neo4j_driver
    yield driver


async def get_db():
    """Database session 제공"""
    async with AsyncSessionLocal() as session:
        yield session


# Helper Functions

async def _get_officer_career_from_postgres(officer_id: str, db: AsyncSession):
    """PostgreSQL에서 임원 경력 조회 (Neo4j fallback)"""
    from sqlalchemy import text

    # 임원 정보 조회 (career_raw_text 포함)
    officer_query = text("""
        SELECT id::text, name, birth_date, position, career_history, career_raw_text
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
        career_history.append(CareerHistory(
            company_id=c.company_id,
            company_name=c.company_name,
            position=c.position,
            start_date=c.term_start_date,
            end_date=c.term_end_date,
            is_current=c.is_current if c.is_current is not None else False,
            is_listed=True,
            source="db"
        ))

    # officers.career_history JSON에서 추가 경력 정보 추출
    if officer.career_history:
        import json
        try:
            raw_careers = officer.career_history if isinstance(officer.career_history, list) else json.loads(officer.career_history)
            for item in raw_careers:
                if isinstance(item, dict) and item.get("text"):
                    career_history.append(CareerHistory(
                        company_id=None,
                        company_name=item.get("text", "")[:50],
                        position=item.get("text", ""),
                        start_date=None,
                        end_date=None,
                        is_current=item.get("status") == "current",
                        is_listed=False,
                        source="disclosure"
                    ))
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse career_history for officer {officer.id}: {e}")

    return OfficerCareerResponse(
        officer=GraphNode(
            id=officer.id,
            type="Officer",
            properties={
                "name": officer.name,
                "birth_date": officer.birth_date,
                "position": officer.position
            }
        ),
        career_history=career_history,
        career_raw_text=officer.career_raw_text  # 사업보고서 주요경력 원문 (v2.5)
    )


def serialize_neo4j_node(record: Dict) -> GraphNode:
    """Neo4j 노드를 GraphNode로 변환"""
    node = record
    return GraphNode(
        id=node.get("id", str(node.element_id)),
        type=list(node.labels)[0] if node.labels else "Unknown",
        properties=serialize_node_properties(node)
    )


def serialize_neo4j_relationship(rel: Any) -> GraphRelationship:
    """Neo4j 관계를 GraphRelationship으로 변환"""
    # start_node와 end_node에서 'id' 속성 추출 (UUID)
    # element_id가 아닌 실제 데이터 id 사용
    source_id = rel.start_node.get("id", str(rel.start_node.element_id))
    target_id = rel.end_node.get("id", str(rel.end_node.element_id))

    return GraphRelationship(
        id=str(rel.element_id),
        type=rel.type,
        source=source_id,
        target=target_id,
        properties=serialize_node_properties(rel)
    )


# Endpoints
@router.get("/company/{company_id}", response_model=GraphResponse)
async def get_company_network(
    company_id: str,
    depth: int = Query(1, ge=1, le=3, description="탐색 깊이: 1=임원+CB회차, 2=+인수자, 3=+타사경력/투자"),
    limit: int = Query(100, ge=10, le=500, description="노드 제한"),
    report_years: Optional[str] = Query(None, description="사업보고서 연도 필터 (쉼표 구분, 예: 2023,2024,2025)"),
    driver=Depends(get_neo4j_driver),
    db: AsyncSession = Depends(get_db)
):
    """
    회사 중심 네트워크 조회

    탐색 깊이 정의:
    - depth 1: 임원 노드 + CB 회차 노드만 (인수자 없음)
    - depth 2: 1단계 + CB 인수대상자(Subscriber) 노드
    - depth 3: 2단계 + 임원의 타 상장사 경력 회사 + Subscriber의 타 상장사 CB 투자 회사

    report_years 파라미터:
    - 사업보고서 공시 연도 필터링 (source_report_date 기준)
    - 예: "2025" → 2025년 사업보고서에 나온 임원만
    - 예: "2023,2024,2025" → 최근 3년 사업보고서에 나온 임원
    """
    # company_id가 corp_code 형식(8자리 숫자)인지 UUID 형식인지 확인
    is_corp_code = len(company_id) == 8 and company_id.isdigit()

    # report_years 파싱 및 임원 ID 필터링
    filtered_officer_ids: Optional[set] = None
    if report_years:
        try:
            years = [int(y.strip()) for y in report_years.split(',')]
            # PostgreSQL에서 해당 연도 사업보고서의 임원 ID 조회
            from sqlalchemy import text
            query = text("""
                SELECT DISTINCT op.officer_id::text
                FROM officer_positions op
                JOIN companies c ON op.company_id = c.id
                WHERE (c.corp_code = :corp_code OR c.id::text = :company_id)
                  AND EXTRACT(YEAR FROM op.source_report_date) = ANY(:years)
            """)
            result = await db.execute(query, {
                "corp_code": company_id if is_corp_code else "",
                "company_id": company_id if not is_corp_code else "",
                "years": years
            })
            filtered_officer_ids = {row[0] for row in result.fetchall()}
            logger.info(f"report_years={years} 필터: {len(filtered_officer_ids)}명 임원 ID")
        except Exception as e:
            logger.warning(f"report_years 필터 처리 실패: {e}")

    # depth에 따라 다른 Cypher 쿼리 구성
    if is_corp_code:
        company_match = "MATCH (c:Company {corp_code: $company_id})"
    else:
        company_match = "MATCH (c:Company {id: $company_id})"

    # 1단계: 임원 + CB 회차만 (인수자 없음)
    if depth == 1:
        cypher = f"""
    {company_match}

    // 1단계: 임원 + CB 회차만
    OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
    WHERE r1.is_current = true

    OPTIONAL MATCH (c)-[r2:AFFILIATE_OF]-(aff:Company)

    OPTIONAL MATCH (c)-[r3:ISSUED]->(cb:ConvertibleBond)

    // 대주주
    OPTIONAL MATCH (c)<-[r_sh:SHAREHOLDER_OF]-(sh:Shareholder)

    WITH c,
         collect(DISTINCT o) as officers,
         collect(DISTINCT r1) as officer_rels,
         collect(DISTINCT aff) as affiliates,
         collect(DISTINCT r2) as affiliate_rels,
         collect(DISTINCT cb)[..20] as cbs,
         collect(DISTINCT r3)[..20] as cb_rels,
         collect(DISTINCT sh)[..20] as shareholders,
         collect(DISTINCT r_sh)[..20] as shareholder_rels

    RETURN c, officers, officer_rels, affiliates, affiliate_rels,
           cbs, cb_rels, shareholders, shareholder_rels,
           [] as subscribers, [] as subscriber_rels,
           [] as officer_career_companies, [] as officer_career_rels,
           [] as subscriber_investment_companies, [] as subscriber_investment_rels
    LIMIT $limit
    """

    # 2단계: 1단계 + 인수자
    elif depth == 2:
        cypher = f"""
    {company_match}

    // 1단계: 임원 + CB 회차
    OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
    WHERE r1.is_current = true

    OPTIONAL MATCH (c)-[r2:AFFILIATE_OF]-(aff:Company)

    OPTIONAL MATCH (c)-[r3:ISSUED]->(cb:ConvertibleBond)

    // 대주주
    OPTIONAL MATCH (c)<-[r_sh:SHAREHOLDER_OF]-(sh:Shareholder)

    // 2단계: CB 인수자
    OPTIONAL MATCH (cb)<-[r4:SUBSCRIBED]-(s:Subscriber)

    WITH c,
         collect(DISTINCT o) as officers,
         collect(DISTINCT r1) as officer_rels,
         collect(DISTINCT aff) as affiliates,
         collect(DISTINCT r2) as affiliate_rels,
         collect(DISTINCT cb)[..20] as cbs,
         collect(DISTINCT r3)[..20] as cb_rels,
         collect(DISTINCT sh)[..20] as shareholders,
         collect(DISTINCT r_sh)[..20] as shareholder_rels,
         collect(DISTINCT s)[..50] as subscribers,
         collect(DISTINCT r4)[..50] as subscriber_rels

    RETURN c, officers, officer_rels, affiliates, affiliate_rels,
           cbs, cb_rels, shareholders, shareholder_rels, subscribers, subscriber_rels,
           [] as officer_career_companies, [] as officer_career_rels,
           [] as subscriber_investment_companies, [] as subscriber_investment_rels
    LIMIT $limit
    """

    # 3단계: 2단계 + 임원 타사 경력 + 인수자 타사 투자
    else:  # depth == 3
        cypher = f"""
    {company_match}

    // 1단계: 임원 + CB 회차
    OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
    WHERE r1.is_current = true

    OPTIONAL MATCH (c)-[r2:AFFILIATE_OF]-(aff:Company)

    OPTIONAL MATCH (c)-[r3:ISSUED]->(cb:ConvertibleBond)

    // 대주주
    OPTIONAL MATCH (c)<-[r_sh:SHAREHOLDER_OF]-(sh:Shareholder)

    // 2단계: CB 인수자
    OPTIONAL MATCH (cb)<-[r4:SUBSCRIBED]-(s:Subscriber)

    WITH c, o, r1, aff, r2, cb, r3, sh, r_sh, s, r4

    // 3단계: 임원의 타 상장사 경력 (현재 회사 제외)
    // 동일인 식별: 이름 + 생년월일
    OPTIONAL MATCH (same_officer:Officer)-[r_career:WORKS_AT|WORKED_AT]->(career_company:Company)
    WHERE o IS NOT NULL
      AND same_officer.name = o.name
      AND career_company.id <> c.id
      AND (
        (same_officer.birth_date IS NOT NULL AND o.birth_date IS NOT NULL
         AND substring(replace(replace(replace(same_officer.birth_date, '년', ''), '월', ''), '.', ''), 0, 6)
            = substring(replace(replace(replace(o.birth_date, '년', ''), '월', ''), '.', ''), 0, 6))
        OR (same_officer.birth_date IS NULL AND o.birth_date IS NULL)
      )

    // 3단계: 인수자의 타 상장사 CB 투자 (현재 회사 제외)
    // CB 노드와 발행 회사 모두 수집
    OPTIONAL MATCH (s)-[r_invest:SUBSCRIBED]->(other_cb:ConvertibleBond)<-[r_other_issued:ISSUED]-(invest_company:Company)
    WHERE s IS NOT NULL AND invest_company.id <> c.id

    WITH c,
         collect(DISTINCT o) as officers,
         collect(DISTINCT r1) as officer_rels,
         collect(DISTINCT aff) as affiliates,
         collect(DISTINCT r2) as affiliate_rels,
         collect(DISTINCT cb)[..20] as cbs,
         collect(DISTINCT r3)[..20] as cb_rels,
         collect(DISTINCT sh)[..20] as shareholders,
         collect(DISTINCT r_sh)[..20] as shareholder_rels,
         collect(DISTINCT s)[..50] as subscribers,
         collect(DISTINCT r4)[..50] as subscriber_rels,
         collect(DISTINCT career_company)[..30] as officer_career_companies,
         collect(DISTINCT r_career)[..30] as officer_career_rels,
         collect(DISTINCT invest_company)[..30] as subscriber_investment_companies,
         collect(DISTINCT other_cb)[..50] as subscriber_investment_cbs,
         collect(DISTINCT r_invest)[..50] as subscriber_investment_rels,
         collect(DISTINCT r_other_issued)[..50] as subscriber_investment_issued_rels

    RETURN c, officers, officer_rels, affiliates, affiliate_rels,
           cbs, cb_rels, shareholders, shareholder_rels, subscribers, subscriber_rels,
           officer_career_companies, officer_career_rels,
           subscriber_investment_companies, subscriber_investment_cbs,
           subscriber_investment_rels, subscriber_investment_issued_rels
    LIMIT $limit
    """

    # 임원 상장사 경력 수 조회용 보조 쿼리
    officer_career_count_cypher = """
    MATCH (o:Officer {id: $officer_id})
    MATCH (same_person:Officer)-[:WORKS_AT|WORKED_AT]->(company:Company)
    WHERE same_person.name = o.name
      AND (
        (same_person.birth_date IS NOT NULL AND o.birth_date IS NOT NULL
         AND substring(replace(replace(replace(same_person.birth_date, '년', ''), '월', ''), '.', ''), 0, 6)
            = substring(replace(replace(replace(o.birth_date, '년', ''), '월', ''), '.', ''), 0, 6))
        OR (same_person.birth_date IS NULL AND o.birth_date IS NULL)
      )
    RETURN count(DISTINCT company) as career_count
    """

    try:
        async with driver.session() as session:
            result = await session.run(cypher, company_id=company_id, limit=limit)
            record = await result.single()

            if not record:
                raise HTTPException(status_code=404, detail="Company not found")

            nodes = []
            relationships = []

            # Center company
            company_node = record["c"]
            nodes.append(GraphNode(
                id=company_node["id"],
                type="Company",
                properties=serialize_node_properties(company_node)
            ))

            # Officers - 상장사 경력 수 포함 (report_years 필터 적용)
            filtered_officer_node_ids = set()  # 필터링된 임원 노드 ID 저장
            for officer in record["officers"]:
                if officer:
                    officer_id = officer["id"]

                    # report_years 필터가 있으면 해당 연도 임원만 포함
                    if filtered_officer_ids is not None and officer_id not in filtered_officer_ids:
                        continue  # 이 임원은 해당 연도에 공시되지 않았음

                    filtered_officer_node_ids.add(officer_id)

                    # 상장사 경력 수 조회
                    career_count = 0
                    try:
                        career_result = await session.run(
                            officer_career_count_cypher,
                            officer_id=officer_id
                        )
                        career_record = await career_result.single()
                        if career_record:
                            career_count = career_record["career_count"]
                    except Exception as e:
                        logger.warning(f"Failed to get officer career count: {e}")

                    officer_props = serialize_node_properties(officer)
                    officer_props["listed_career_count"] = career_count

                    nodes.append(GraphNode(
                        id=officer_id,
                        type="Officer",
                        properties=officer_props
                    ))

            # Officer relationships (필터링된 임원만)
            for rel in record["officer_rels"]:
                if rel:
                    rel_data = serialize_neo4j_relationship(rel)
                    # source 또는 target이 필터링된 임원인 경우만 포함
                    if filtered_officer_ids is None or rel_data.source in filtered_officer_node_ids:
                        relationships.append(rel_data)

            # Affiliates
            for affiliate in record["affiliates"]:
                if affiliate:
                    nodes.append(GraphNode(
                        id=affiliate["id"],
                        type="Company",
                        properties=serialize_node_properties(affiliate)
                    ))

            for rel in record["affiliate_rels"]:
                if rel:
                    relationships.append(serialize_neo4j_relationship(rel))

            # CBs
            for cb in record["cbs"]:
                if cb:
                    nodes.append(GraphNode(
                        id=cb["id"],
                        type="ConvertibleBond",
                        properties=serialize_node_properties(cb)
                    ))

            for rel in record["cb_rels"]:
                if rel:
                    relationships.append(serialize_neo4j_relationship(rel))

            # Shareholders
            for shareholder in record.get("shareholders", []):
                if shareholder:
                    nodes.append(GraphNode(
                        id=shareholder["id"],
                        type="Shareholder",
                        properties=serialize_node_properties(shareholder)
                    ))

            for rel in record.get("shareholder_rels", []):
                if rel:
                    relationships.append(serialize_neo4j_relationship(rel))

            # Subscribers (depth >= 2)
            # 중복 인수자 노드 방지
            seen_subscriber_ids = set()
            for subscriber in record["subscribers"]:
                if subscriber and subscriber["id"] not in seen_subscriber_ids:
                    nodes.append(GraphNode(
                        id=subscriber["id"],
                        type="Subscriber",
                        properties=serialize_node_properties(subscriber)
                    ))
                    seen_subscriber_ids.add(subscriber["id"])

            # 인수자-CB 관계 중복 방지 (같은 인수자가 같은 CB에 여러 관계를 가진 경우)
            seen_sub_rel_pairs = set()
            for rel in record["subscriber_rels"]:
                if rel:
                    serialized = serialize_neo4j_relationship(rel)
                    # source(subscriber) + target(CB) 쌍으로 중복 체크
                    rel_pair = (serialized.source, serialized.target)
                    if rel_pair not in seen_sub_rel_pairs:
                        relationships.append(serialized)
                        seen_sub_rel_pairs.add(rel_pair)

            # 3단계: 임원 타 상장사 경력 회사 (depth == 3)
            seen_node_ids = {n.id for n in nodes}  # 중복 방지
            for career_company in record.get("officer_career_companies", []):
                if career_company and career_company["id"] not in seen_node_ids:
                    nodes.append(GraphNode(
                        id=career_company["id"],
                        type="Company",
                        properties={
                            **serialize_node_properties(career_company),
                            "relation_type": "officer_career"  # 임원 경력 회사 표시
                        }
                    ))
                    seen_node_ids.add(career_company["id"])

            for rel in record.get("officer_career_rels", []):
                if rel:
                    relationships.append(serialize_neo4j_relationship(rel))

            # 3단계: 인수자 타 상장사 CB 투자 - CB 노드 추가 (depth == 3)
            seen_rel_ids = {r.id for r in relationships}  # 관계 중복 방지
            for invest_cb in record.get("subscriber_investment_cbs", []):
                if invest_cb and invest_cb["id"] not in seen_node_ids:
                    nodes.append(GraphNode(
                        id=invest_cb["id"],
                        type="ConvertibleBond",
                        properties={
                            **serialize_node_properties(invest_cb),
                            "relation_type": "subscriber_investment"  # 인수자 투자 CB 표시
                        }
                    ))
                    seen_node_ids.add(invest_cb["id"])

            # 3단계: 인수자 타 상장사 CB 투자 - 회사 노드 추가 (depth == 3)
            for invest_company in record.get("subscriber_investment_companies", []):
                if invest_company and invest_company["id"] not in seen_node_ids:
                    nodes.append(GraphNode(
                        id=invest_company["id"],
                        type="Company",
                        properties={
                            **serialize_node_properties(invest_company),
                            "relation_type": "subscriber_investment"  # 인수자 투자 회사 표시
                        }
                    ))
                    seen_node_ids.add(invest_company["id"])

            # 3단계: SUBSCRIBED 관계 (Subscriber -> CB)
            for rel in record.get("subscriber_investment_rels", []):
                if rel:
                    serialized = serialize_neo4j_relationship(rel)
                    if serialized.id not in seen_rel_ids:
                        relationships.append(serialized)
                        seen_rel_ids.add(serialized.id)

            # 3단계: ISSUED 관계 (Company -> CB)
            for rel in record.get("subscriber_investment_issued_rels", []):
                if rel:
                    serialized = serialize_neo4j_relationship(rel)
                    if serialized.id not in seen_rel_ids:
                        relationships.append(serialized)
                        seen_rel_ids.add(serialized.id)

            return GraphResponse(
                nodes=nodes,
                relationships=relationships,
                center={"type": "Company", "id": company_id}
            )

    except Exception as e:
        logger.error(f"Error fetching company network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/officer/{officer_id}/career", response_model=OfficerCareerResponse)
async def get_officer_career(
    officer_id: str,
    driver=Depends(get_neo4j_driver_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    임원 경력 이력 조회

    - 현재 및 과거 경력
    - 시간순 정렬
    - 동일인 식별: 이름 + 생년월일 (YYYYMM) 기준
    - 두 가지 소스:
      1. "db": 상장사 임원 DB (Neo4j WORKS_AT/WORKED_AT)
      2. "disclosure": 공시 파싱 경력 (PostgreSQL career_history JSONB)
    - Neo4j 없으면 PostgreSQL fallback 사용
    """
    # Neo4j 없으면 PostgreSQL fallback 사용
    if driver is None:
        return await _get_officer_career_from_postgres(officer_id, db)
    # v2.5: 동일 회사는 1개 레코드만 반환 (Cypher 레벨에서 중복 제거)
    cypher = """
    // 먼저 해당 임원의 이름과 생년월일을 가져옴
    MATCH (target:Officer {id: $officer_id})

    // 같은 이름 + 같은 생년월일을 가진 모든 임원의 근무이력을 조회 (동일인물)
    // 생년월일 비교: 숫자만 추출하여 앞 6자리 비교 (YYYYMM)
    MATCH (o:Officer)-[r:WORKS_AT|WORKED_AT]->(c:Company)
    WHERE o.name = target.name
      AND (
        // 생년월일이 둘 다 있는 경우: 앞 6자리(YYYYMM) 비교
        (o.birth_date IS NOT NULL AND target.birth_date IS NOT NULL
         AND substring(replace(replace(replace(o.birth_date, '년', ''), '월', ''), '.', ''), 0, 6)
            = substring(replace(replace(replace(target.birth_date, '년', ''), '월', ''), '.', ''), 0, 6))
        // 생년월일이 둘 다 없는 경우도 동일인으로 간주 (fallback)
        OR (o.birth_date IS NULL AND target.birth_date IS NULL)
      )

    // v2.5: 회사별로 그룹화하여 최신 레코드만 선택
    WITH target, c, r
    ORDER BY r.is_current DESC, r.start_date DESC
    WITH target, c, collect(r)[0] as best_rel

    RETURN target as o,
           collect({
               company_id: c.id,
               company_name: c.name,
               position: best_rel.position,
               start_date: best_rel.start_date,
               end_date: best_rel.end_date,
               is_current: COALESCE(best_rel.is_current, false)
           }) as career_history
    """

    try:
        async with driver.session() as session:
            result = await session.run(cypher, officer_id=officer_id)
            record = await result.single()

            if not record:
                raise HTTPException(status_code=404, detail="Officer not found")

            officer_node = record["o"]
            career_data = record["career_history"]

            # 1. Neo4j에서 가져온 상장사 경력 (source="db")
            # v2.5: 동일 회사는 1개만 표시 (company_id 기준 중복 제거)
            seen_companies = set()  # 회사명 기준 중복 체크 (disclosure 데이터와 비교용)
            seen_company_ids = set()  # 회사 ID 기준 중복 체크 (동일 회사 1개만)
            all_careers = []

            for career in career_data:
                if career.get("company_id"):
                    company_id = career["company_id"]
                    company_name_raw = career.get("company_name", "").strip()
                    # 회사명 정규화 (중복 체크용)
                    company_name_normalized = company_name_raw.replace("(주)", "").replace("주식회사", "").replace("㈜", "").strip()

                    # v2.5: 동일 회사는 첫 번째 레코드만 사용 (is_current=True 우선 정렬되어 있음)
                    if company_id in seen_company_ids:
                        continue  # 이미 추가된 회사는 스킵

                    seen_company_ids.add(company_id)
                    seen_companies.add(company_name_raw)  # 원본 회사명 추가
                    seen_companies.add(company_name_normalized)  # 정규화된 회사명도 추가

                    # Neo4j Date 객체를 문자열로 변환
                    start_date = serialize_neo4j_value(career.get("start_date"))
                    end_date = serialize_neo4j_value(career.get("end_date"))
                    all_careers.append(CareerHistory(
                        company_id=company_id,
                        company_name=career["company_name"],
                        position=career["position"],
                        start_date=start_date,
                        end_date=end_date,
                        is_current=career.get("is_current", False),
                        is_listed=True,
                        source="db"
                    ))

            # 2. PostgreSQL에서 파싱된 경력 조회 (source="disclosure")
            # Neo4j ID와 PostgreSQL ID가 다를 수 있으므로 이름+생년월일로 조회
            career_raw_text = None  # 사업보고서 주요경력 원문 초기화 (v2.5)
            try:
                from sqlalchemy import text
                import re

                officer_name = officer_node.get("name")
                officer_birth = officer_node.get("birth_date")

                # 생년월일 정규화 (Neo4j: "1978년 11월" or "1973.11" -> "197811" or "197311")
                normalized_birth = None
                if officer_birth:
                    # 숫자만 추출
                    digits = re.sub(r'[^\d]', '', officer_birth)
                    if len(digits) >= 6:
                        normalized_birth = digits[:6]

                logger.info(f"PostgreSQL career_history 조회: name={officer_name}, birth={officer_birth}, normalized={normalized_birth}")

                # 이름 + 생년월일로 조회 (동일인 식별)
                # career_history가 있는 row만
                if normalized_birth:
                    # 생년월일이 있는 경우: 이름 + 생년월일 앞 6자리 비교
                    pg_result = await db.execute(
                        text("""
                            SELECT career_history, career_raw_text FROM officers
                            WHERE name = :name
                            AND birth_date IS NOT NULL
                            AND REPLACE(REPLACE(REPLACE(birth_date, '년', ''), '월', ''), '.', '') LIKE :birth_prefix || '%'
                            LIMIT 1
                        """),
                        {"name": officer_name, "birth_prefix": normalized_birth}
                    )
                else:
                    # 생년월일이 없는 경우: 이름만으로 조회 (fallback)
                    pg_result = await db.execute(
                        text("""
                            SELECT career_history, career_raw_text FROM officers
                            WHERE name = :name
                            LIMIT 1
                        """),
                        {"name": officer_name}
                    )
                row = pg_result.fetchone()
                logger.info(f"PostgreSQL career_history 결과: row={row is not None}, data={row[0] if row else None}")

                # career_raw_text 추출 (v2.5)
                career_raw_text = row[1] if row and len(row) > 1 else None

                if row and row[0]:
                    career_history_json = row[0]
                    if isinstance(career_history_json, list):
                        for item in career_history_json:
                            if isinstance(item, dict) and item.get("text"):
                                career_text = item["text"].strip()
                                is_current = item.get("status") == "current"

                                # 회사명과 직책 분리 (예: "(주)이아이디 대표이사")
                                # 간단한 분리: 마지막 공백 기준 또는 전체를 회사명으로
                                parts = career_text.rsplit(" ", 1)
                                if len(parts) == 2:
                                    company_name = parts[0].strip()
                                    position = parts[1].strip()
                                else:
                                    company_name = career_text
                                    position = "임원"

                                # 이미 DB에서 가져온 회사는 건너뜀 (중복 방지)
                                # 회사명 정규화: (주), 주식회사 등 제거 후 비교
                                normalized_name = company_name.replace("(주)", "").replace("주식회사", "").replace("㈜", "").strip()
                                if company_name not in seen_companies and normalized_name not in seen_companies:
                                    seen_companies.add(company_name)
                                    all_careers.append(CareerHistory(
                                        company_id=None,  # 비상장사는 ID 없음
                                        company_name=company_name,
                                        position=position,
                                        start_date=None,
                                        end_date=None,
                                        is_current=is_current,
                                        is_listed=False,  # 공시 파싱 = 비상장사 가능성
                                        source="disclosure"
                                    ))
            except Exception as pg_error:
                logger.warning(f"PostgreSQL career_history 조회 실패: {pg_error}")
                career_raw_text = None  # 에러 시 None

            # 정렬: is_current=True 우선, source="db" 우선, start_date 최신순
            all_careers.sort(
                key=lambda x: (
                    0 if x.is_current else 1,  # 현재 재직 우선
                    0 if x.source == "db" else 1,  # DB 소스 우선
                    x.start_date or "0000"  # 날짜 있는 것 우선
                ),
                reverse=False
            )

            return OfficerCareerResponse(
                officer=GraphNode(
                    id=officer_node["id"],
                    type="Officer",
                    properties=serialize_node_properties(officer_node)
                ),
                career_history=all_careers,
                career_raw_text=career_raw_text  # 사업보고서 주요경력 원문 (v2.5)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching officer career: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/officer/{officer_id}/career-network", response_model=GraphResponse)
async def get_officer_career_network(
    officer_id: str,
    limit: int = Query(100, ge=10, le=200),
    driver=Depends(get_neo4j_driver)
):
    """
    임원 경력 네트워크 확장

    - 경력 회사들과 그 회사의 임원/계열사/CB 표시
    - 동일인 식별: 이름 + 생년월일 (YYYYMM) 기준
    """
    cypher = """
    // 대상 임원 조회
    MATCH (target:Officer {id: $officer_id})

    // 같은 이름 + 생년월일을 가진 동일인의 경력 회사들
    MATCH (o:Officer)-[r:WORKED_AT|WORKS_AT]->(c:Company)
    WHERE o.name = target.name
      AND (
        (o.birth_date IS NOT NULL AND target.birth_date IS NOT NULL
         AND substring(replace(replace(replace(o.birth_date, '년', ''), '월', ''), '.', ''), 0, 6)
            = substring(replace(replace(replace(target.birth_date, '년', ''), '월', ''), '.', ''), 0, 6))
        OR (o.birth_date IS NULL AND target.birth_date IS NULL)
      )

    // 각 회사의 다른 임원들
    OPTIONAL MATCH (c)<-[:WORKS_AT {is_current: true}]-(other_officer:Officer)
    WHERE other_officer.id <> target.id

    // 각 회사의 계열사
    OPTIONAL MATCH (c)-[:AFFILIATE_OF]-(aff:Company)

    // 각 회사의 CB
    OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)

    RETURN target as o, r, c,
           collect(DISTINCT other_officer)[..10] as other_officers,
           collect(DISTINCT aff)[..5] as affiliates,
           collect(DISTINCT cb)[..5] as cbs
    LIMIT $limit
    """

    try:
        async with driver.session() as session:
            result = await session.run(cypher, officer_id=officer_id, limit=limit)

            nodes = []
            relationships = []
            seen_nodes = set()
            seen_rels = set()
            has_records = False

            async for record in result:
                has_records = True

                # Officer
                officer = record["o"]
                if officer["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=officer["id"],
                        type="Officer",
                        properties=serialize_node_properties(officer)
                    ))
                    seen_nodes.add(officer["id"])

                # Company
                company = record["c"]
                if company["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=company["id"],
                        type="Company",
                        properties=serialize_node_properties(company)
                    ))
                    seen_nodes.add(company["id"])

                # Career relationship (WORKS_AT or WORKED_AT)
                rel = record["r"]
                if rel:
                    serialized = serialize_neo4j_relationship(rel)
                    if serialized.id not in seen_rels:
                        relationships.append(serialized)
                        seen_rels.add(serialized.id)

                # Other officers
                for other in record["other_officers"]:
                    if other and other["id"] not in seen_nodes:
                        nodes.append(GraphNode(
                            id=other["id"],
                            type="Officer",
                            properties=serialize_node_properties(other)
                        ))
                        seen_nodes.add(other["id"])

                # Affiliates
                for aff in record["affiliates"]:
                    if aff and aff["id"] not in seen_nodes:
                        nodes.append(GraphNode(
                            id=aff["id"],
                            type="Company",
                            properties=serialize_node_properties(aff)
                        ))
                        seen_nodes.add(aff["id"])

                # CBs
                for cb in record["cbs"]:
                    if cb and cb["id"] not in seen_nodes:
                        nodes.append(GraphNode(
                            id=cb["id"],
                            type="ConvertibleBond",
                            properties=serialize_node_properties(cb)
                        ))
                        seen_nodes.add(cb["id"])

            if not has_records:
                raise HTTPException(status_code=404, detail="Officer not found")

            return GraphResponse(
                nodes=nodes,
                relationships=relationships,
                center={"type": "Officer", "id": officer_id}
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching officer career network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriber/{subscriber_id}/investments", response_model=SubscriberInvestmentResponse)
async def get_subscriber_investments(
    subscriber_id: str,
    driver=Depends(get_neo4j_driver)
):
    """
    CB 인수자 투자 이력 조회

    - 투자한 회사 목록
    - 각 회사별 CB 목록
    """
    cypher = """
    MATCH (s:Subscriber {id: $subscriber_id})

    // 투자 이력 - SUBSCRIBED 관계로 회사 연결
    OPTIONAL MATCH (s)-[sub:SUBSCRIBED]->(cb:ConvertibleBond)<-[:ISSUED]-(c:Company)

    WITH s, c,
         collect(DISTINCT {
             id: cb.id,
             bond_name: cb.bond_name,
             issue_date: cb.issue_date,
             total_amount: cb.issue_amount
         }) as cbs,
         sum(COALESCE(cb.issue_amount, 0)) as total_amount,
         count(DISTINCT cb) as investment_count,
         min(cb.issue_date) as first_investment,
         max(cb.issue_date) as latest_investment
    WHERE c IS NOT NULL

    RETURN s,
           collect({
               company_id: c.id,
               company_name: c.name,
               total_amount: total_amount,
               investment_count: investment_count,
               first_investment: first_investment,
               latest_investment: latest_investment,
               cbs: cbs
           }) as investments
    """

    try:
        async with driver.session() as session:
            result = await session.run(cypher, subscriber_id=subscriber_id)
            record = await result.single()

            if not record:
                raise HTTPException(status_code=404, detail="Subscriber not found")

            subscriber_node = record["s"]
            investments = record["investments"]

            # 투자 이력 변환
            investment_history = []
            for inv in investments:
                if inv.get("company_id"):
                    # None 값 처리 - Neo4j Date 타입 직렬화 필요
                    # CB 데이터도 Neo4j Date 직렬화 적용
                    cbs_serialized = []
                    for cb in inv.get("cbs", []):
                        if cb.get("id"):
                            cbs_serialized.append({
                                "id": cb.get("id"),
                                "bond_name": cb.get("bond_name"),
                                "issue_date": serialize_neo4j_value(cb.get("issue_date")),
                                "total_amount": cb.get("total_amount"),
                            })

                    inv_data = {
                        "company_id": inv["company_id"],
                        "company_name": inv["company_name"],
                        "total_amount": int(inv["total_amount"]) if inv.get("total_amount") else None,
                        "investment_count": int(inv["investment_count"]) if inv.get("investment_count") else 0,
                        "first_investment": serialize_neo4j_value(inv.get("first_investment")),
                        "latest_investment": serialize_neo4j_value(inv.get("latest_investment")),
                        "cbs": cbs_serialized
                    }
                    investment_history.append(InvestmentHistory(**inv_data))

            # 최신 투자순 정렬
            investment_history.sort(
                key=lambda x: x.latest_investment or "",
                reverse=True
            )

            return SubscriberInvestmentResponse(
                subscriber=GraphNode(
                    id=subscriber_node["id"],
                    type="Subscriber",
                    properties=serialize_node_properties(subscriber_node)
                ),
                investment_history=investment_history
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscriber investments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriber/{subscriber_id}/investment-network", response_model=GraphResponse)
async def get_subscriber_investment_network(
    subscriber_id: str,
    limit: int = Query(200, ge=10, le=500),
    driver=Depends(get_neo4j_driver)
):
    """
    인수자 투자 네트워크 확장

    - 투자한 회사들의 CB 네트워크
    """
    cypher = """
    MATCH (s:Subscriber {id: $subscriber_id})

    // 투자한 회사들
    MATCH (s)-[r_inv:INVESTED_IN]->(c:Company)

    // 각 회사의 CB들
    MATCH (c)-[r_issued:ISSUED]->(cb:ConvertibleBond)

    // 인수자의 CB 인수 관계
    OPTIONAL MATCH (s)-[r_sub:SUBSCRIBED]->(cb)

    // CB의 다른 인수자들
    OPTIONAL MATCH (cb)<-[r_other_sub:SUBSCRIBED]-(other_subscriber:Subscriber)
    WHERE other_subscriber.id <> s.id

    RETURN s, c, cb, r_inv, r_issued, r_sub,
           collect(DISTINCT other_subscriber)[..10] as other_subscribers,
           collect(DISTINCT r_other_sub)[..10] as other_subscriber_rels
    LIMIT $limit
    """

    try:
        async with driver.session() as session:
            result = await session.run(cypher, subscriber_id=subscriber_id, limit=limit)

            nodes = []
            relationships = []
            seen_nodes = set()
            seen_rels = set()
            has_records = False

            async for record in result:
                has_records = True

                # Subscriber
                subscriber = record["s"]
                if subscriber["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=subscriber["id"],
                        type="Subscriber",
                        properties=serialize_node_properties(subscriber)
                    ))
                    seen_nodes.add(subscriber["id"])

                # Company
                company = record["c"]
                if company and company["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=company["id"],
                        type="Company",
                        properties=serialize_node_properties(company)
                    ))
                    seen_nodes.add(company["id"])

                # CB
                cb = record["cb"]
                if cb and cb["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=cb["id"],
                        type="ConvertibleBond",
                        properties=serialize_node_properties(cb)
                    ))
                    seen_nodes.add(cb["id"])

                # INVESTED_IN relationship
                r_inv = record.get("r_inv")
                if r_inv:
                    rel = serialize_neo4j_relationship(r_inv)
                    if rel.id not in seen_rels:
                        relationships.append(rel)
                        seen_rels.add(rel.id)

                # ISSUED relationship
                r_issued = record.get("r_issued")
                if r_issued:
                    rel = serialize_neo4j_relationship(r_issued)
                    if rel.id not in seen_rels:
                        relationships.append(rel)
                        seen_rels.add(rel.id)

                # SUBSCRIBED relationship (main subscriber)
                r_sub = record.get("r_sub")
                if r_sub:
                    rel = serialize_neo4j_relationship(r_sub)
                    if rel.id not in seen_rels:
                        relationships.append(rel)
                        seen_rels.add(rel.id)

                # Other subscribers
                for other in record.get("other_subscribers", []):
                    if other and other["id"] not in seen_nodes:
                        nodes.append(GraphNode(
                            id=other["id"],
                            type="Subscriber",
                            properties=serialize_node_properties(other)
                        ))
                        seen_nodes.add(other["id"])

                # Other subscriber relationships
                for rel in record.get("other_subscriber_rels", []):
                    if rel:
                        serialized = serialize_neo4j_relationship(rel)
                        if serialized.id not in seen_rels:
                            relationships.append(serialized)
                            seen_rels.add(serialized.id)

            if not has_records:
                raise HTTPException(status_code=404, detail="Subscriber not found")

            return GraphResponse(
                nodes=nodes,
                relationships=relationships,
                center={"type": "Subscriber", "id": subscriber_id}
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscriber investment network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 대주주(Shareholder) 상세 API
# ============================================================================

class ShareholderDetailResponse(BaseModel):
    """대주주 상세 정보"""
    id: str
    name: str
    type: str  # INDIVIDUAL, INSTITUTION, OFFICER, OTHER
    shares: int
    percentage: float
    acquisition_date: Optional[str] = None
    acquisition_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None


class ShareholderHistoryItem(BaseModel):
    """대주주 변동 이력"""
    date: str
    percentage: float
    change: float  # 양수: 증가, 음수: 감소
    shares_changed: int
    reason: Optional[str] = None


class ShareholderCompanyItem(BaseModel):
    """대주주 관련 회사"""
    company_id: str
    company_name: str
    percentage: float
    shares: int


@router.get("/shareholder/{shareholder_id}/detail", response_model=ShareholderDetailResponse)
async def get_shareholder_detail(
    shareholder_id: str,
    driver=Depends(get_neo4j_driver),
    db: AsyncSession = Depends(get_db)
):
    """
    대주주 상세 정보 조회

    - Neo4j Shareholder 노드 정보 + PostgreSQL major_shareholders 상세 데이터
    """
    from sqlalchemy import text

    try:
        # 1. Neo4j에서 기본 정보 조회
        cypher = """
        MATCH (s:Shareholder {id: $shareholder_id})
        RETURN s
        """

        async with driver.session() as session:
            result = await session.run(cypher, shareholder_id=shareholder_id)
            record = await result.single()

            if not record:
                raise HTTPException(status_code=404, detail="Shareholder not found")

            shareholder = record["s"]

            # Neo4j 속성 추출
            shareholder_name = shareholder.get("name", "")
            shareholder_type = shareholder.get("type", "OTHER")
            share_count = shareholder.get("share_count", 0)
            share_ratio = shareholder.get("share_ratio", 0.0)
            report_date = shareholder.get("report_date", "")

            # 2. PostgreSQL에서 추가 정보 조회 (동일 이름 기준 최신 데이터)
            pg_result = await db.execute(
                text("""
                    SELECT share_count, share_ratio, report_date, change_reason,
                           previous_share_ratio, shareholder_type
                    FROM major_shareholders
                    WHERE shareholder_name = :name
                    ORDER BY report_date DESC
                    LIMIT 1
                """),
                {"name": shareholder_name}
            )
            pg_row = pg_result.fetchone()

            if pg_row:
                share_count = int(pg_row.share_count) if pg_row.share_count else share_count
                share_ratio = float(pg_row.share_ratio) if pg_row.share_ratio else share_ratio
                if pg_row.report_date:
                    report_date = pg_row.report_date.isoformat() if hasattr(pg_row.report_date, 'isoformat') else str(pg_row.report_date)

            # 타입 매핑 (프론트엔드 호환)
            type_mapping = {
                "INDIVIDUAL": "individual",
                "INSTITUTION": "institution",
                "OFFICER": "individual",
                "OTHER": "corporation"
            }
            mapped_type = type_mapping.get(shareholder_type, "individual")

            return ShareholderDetailResponse(
                id=shareholder_id,
                name=shareholder_name,
                type=mapped_type,
                shares=int(share_count) if share_count else 0,
                percentage=float(share_ratio) if share_ratio else 0.0,
                acquisition_date=report_date if report_date else None,
                acquisition_price=None,  # 취득가 정보 없음
                current_value=None,      # 현재가 정보 없음
                profit_loss=None         # 손익 정보 없음
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching shareholder detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shareholder/{shareholder_id}/history", response_model=List[ShareholderHistoryItem])
async def get_shareholder_history(
    shareholder_id: str,
    driver=Depends(get_neo4j_driver),
    db: AsyncSession = Depends(get_db)
):
    """
    대주주 지분 변동 이력 조회

    - PostgreSQL major_shareholders 테이블에서 동일 이름 기준 이력 조회
    """
    from sqlalchemy import text

    try:
        # 1. Neo4j에서 shareholder 이름 조회
        cypher = """
        MATCH (s:Shareholder {id: $shareholder_id})
        RETURN s.name as name
        """

        async with driver.session() as session:
            result = await session.run(cypher, shareholder_id=shareholder_id)
            record = await result.single()

            if not record:
                raise HTTPException(status_code=404, detail="Shareholder not found")

            shareholder_name = record["name"]

        # 2. PostgreSQL에서 이력 조회
        pg_result = await db.execute(
            text("""
                SELECT share_count, share_ratio, report_date, change_reason, previous_share_ratio
                FROM major_shareholders
                WHERE shareholder_name = :name
                ORDER BY report_date DESC
                LIMIT 20
            """),
            {"name": shareholder_name}
        )
        rows = pg_result.fetchall()

        history = []
        prev_share_count = None

        for row in rows:
            share_count = int(row.share_count) if row.share_count else 0
            share_ratio = float(row.share_ratio) if row.share_ratio else 0.0
            report_date = row.report_date.isoformat() if row.report_date and hasattr(row.report_date, 'isoformat') else str(row.report_date) if row.report_date else ""

            # 지분 변동 계산
            change = 0.0
            shares_changed = 0

            if row.previous_share_ratio is not None:
                change = share_ratio - float(row.previous_share_ratio)

            # 주식 수 변동 계산 (이전 레코드 기준)
            if prev_share_count is not None:
                shares_changed = share_count - prev_share_count

            prev_share_count = share_count

            history.append(ShareholderHistoryItem(
                date=report_date,
                percentage=share_ratio,
                change=round(change, 2),
                shares_changed=shares_changed,
                reason=row.change_reason
            ))

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching shareholder history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shareholder/{shareholder_id}/companies", response_model=List[ShareholderCompanyItem])
async def get_shareholder_companies(
    shareholder_id: str,
    driver=Depends(get_neo4j_driver),
    db: AsyncSession = Depends(get_db)
):
    """
    대주주가 지분을 보유한 회사 목록 조회

    - Neo4j SHAREHOLDER_OF 관계 기반 + PostgreSQL major_shareholders 데이터
    """
    from sqlalchemy import text

    try:
        # 1. Neo4j에서 관계 조회
        cypher = """
        MATCH (s:Shareholder {id: $shareholder_id})-[r:SHAREHOLDER_OF]->(c:Company)
        RETURN c.id as company_id, c.name as company_name,
               r.share_ratio as percentage, r.share_count as shares
        ORDER BY r.share_ratio DESC
        """

        companies = []

        async with driver.session() as session:
            result = await session.run(cypher, shareholder_id=shareholder_id)
            records = await result.data()

            for record in records:
                companies.append(ShareholderCompanyItem(
                    company_id=record["company_id"],
                    company_name=record["company_name"],
                    percentage=float(record["percentage"]) if record.get("percentage") else 0.0,
                    shares=int(record["shares"]) if record.get("shares") else 0
                ))

        # Neo4j에서 관계가 없으면 PostgreSQL에서 조회 시도
        if not companies:
            # Neo4j에서 이름 가져오기
            name_cypher = """
            MATCH (s:Shareholder {id: $shareholder_id})
            RETURN s.name as name
            """
            async with driver.session() as session:
                name_result = await session.run(name_cypher, shareholder_id=shareholder_id)
                name_record = await name_result.single()

                if not name_record:
                    return []

                shareholder_name = name_record["name"]

            # PostgreSQL에서 조회
            pg_result = await db.execute(
                text("""
                    SELECT DISTINCT ON (c.id) c.id as company_id, c.name as company_name,
                           ms.share_ratio, ms.share_count
                    FROM major_shareholders ms
                    JOIN companies c ON ms.company_id = c.id
                    WHERE ms.shareholder_name = :name
                    ORDER BY c.id, ms.report_date DESC
                """),
                {"name": shareholder_name}
            )
            rows = pg_result.fetchall()

            for row in rows:
                companies.append(ShareholderCompanyItem(
                    company_id=str(row.company_id),
                    company_name=row.company_name,
                    percentage=float(row.share_ratio) if row.share_ratio else 0.0,
                    shares=int(row.share_count) if row.share_count else 0
                ))

        # 지분율 높은 순 정렬
        companies.sort(key=lambda x: x.percentage, reverse=True)

        return companies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching shareholder companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recenter", response_model=GraphResponse)
async def recenter_graph(
    request: RecenterRequest,
    driver=Depends(get_neo4j_driver)
):
    """
    노드 중심 전환 (범용)

    - 특정 노드를 중심으로 그래프 재구성
    - 모든 노드 타입 지원
    """
    node_label_map = {
        "Company": "Company",
        "Officer": "Officer",
        "ConvertibleBond": "ConvertibleBond",
        "Subscriber": "Subscriber"
    }

    if request.node_type not in node_label_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node_type. Must be one of: {list(node_label_map.keys())}"
        )

    label = node_label_map[request.node_type]

    cypher = f"""
    MATCH (center:{label} {{id: $node_id}})

    // 직접 연결된 모든 노드와 관계
    MATCH (center)-[r]-(connected)

    RETURN center, r, connected
    LIMIT $limit
    """

    try:
        async with driver.session() as session:
            result = await session.run(
                cypher,
                node_id=request.node_id,
                limit=request.limit
            )

            nodes = []
            relationships = []
            seen_nodes = set()
            seen_rels = set()
            has_records = False

            async for record in result:
                has_records = True

                # Center node
                center = record["center"]
                if center["id"] not in seen_nodes:
                    nodes.append(GraphNode(
                        id=center["id"],
                        type=request.node_type,
                        properties=serialize_node_properties(center)
                    ))
                    seen_nodes.add(center["id"])

                # Connected node
                connected = record["connected"]
                if connected["id"] not in seen_nodes:
                    # labels 속성 사용 (Record 객체에서는 사용 가능)
                    node_type = list(connected.labels)[0] if hasattr(connected, 'labels') and connected.labels else "Unknown"
                    nodes.append(GraphNode(
                        id=connected["id"],
                        type=node_type,
                        properties=serialize_node_properties(connected)
                    ))
                    seen_nodes.add(connected["id"])

                # Relationship
                rel = record["r"]
                if rel:
                    serialized = serialize_neo4j_relationship(rel)
                    if serialized.id not in seen_rels:
                        relationships.append(serialized)
                        seen_rels.add(serialized.id)

            if not has_records:
                raise HTTPException(status_code=404, detail=f"{request.node_type} not found")

            return GraphResponse(
                nodes=nodes,
                relationships=relationships,
                center={"type": request.node_type, "id": request.node_id}
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recentering graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
