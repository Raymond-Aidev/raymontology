"""
위험 패턴 탐지 엔진

그래프 관계와 재무지표를 결합하여 8가지 위험 신호 탐지:
1. 순환 투자 (Circular Investment)
2. 과도한 CB 발행 (Excessive CB Issuance)
3. 임원 집중도 (Officer Concentration)
4. 재무 악화 + CB 발행 (Financial Distress + CB)
5. 특수관계자 거래 (Related Party Transaction)
6. 임원 이동 패턴 (Officer Movement Pattern)
7. CB 투자자 집중 (CB Investor Concentration)
8. 계열사 연쇄 부실 (Affiliate Chain Risk)
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from neo4j import AsyncGraphDatabase, AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json
import re

from app.services.financial_metrics import FinancialMetricsCalculator
import logging

logger = logging.getLogger(__name__)


class RiskDetectionEngine:
    """위험 패턴 탐지 엔진"""

    def __init__(self, neo4j_driver: AsyncDriver):
        self.driver = neo4j_driver
        self.metrics_calculator = FinancialMetricsCalculator()

    async def detect_circular_investment(
        self,
        company_id: str,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        1. 순환 투자 패턴 탐지

        A사 → B사 → C사 → A사 형태의 순환 투자 구조

        Returns:
            [{
                "cycle": ["회사A", "회사B", "회사C", "회사A"],
                "total_amount": 5000000000,
                "companies": [...],
                "risk_level": "high"
            }]
        """
        cypher = """
        MATCH path = (start:Company {id: $company_id})-[:INVESTED_IN*1..%d]->(start)
        WHERE ALL(r in relationships(path) WHERE r.investment_count > 0)
        WITH path,
             [n in nodes(path) | n.name] as company_names,
             [n in nodes(path) | n.id] as company_ids,
             reduce(total = 0, r in relationships(path) | total + r.total_amount) as total_amount
        RETURN company_names as cycle,
               company_ids,
               total_amount,
               length(path) as cycle_length
        ORDER BY total_amount DESC
        LIMIT 10
        """ % max_depth

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            records = await result.data()

            cycles = []
            for record in records:
                risk_level = "high" if record["total_amount"] > 1_000_000_000 else "medium"

                cycles.append({
                    "cycle": record["cycle"],
                    "company_ids": record["company_ids"],
                    "total_amount": record["total_amount"],
                    "cycle_length": record["cycle_length"],
                    "risk_level": risk_level
                })

            return cycles

    async def detect_excessive_cb_issuance(
        self,
        company_id: str,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        2. 과도한 CB 발행 패턴

        최근 N개월 내 CB 발행 빈도 및 총액 분석

        Returns:
            {
                "cb_count": 5,
                "total_amount": 10000000000,
                "avg_interval_days": 45,
                "risk_level": "high",
                "details": [...]
            }
        """
        cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

        cypher = """
        MATCH (c:Company {id: $company_id})-[:ISSUED]->(cb:ConvertibleBond)
        WHERE cb.issue_date >= date($cutoff_date)
        WITH c, cb
        ORDER BY cb.issue_date
        WITH c,
             COUNT(cb) as cb_count,
             SUM(COALESCE(cb.total_amount, 0)) as total_amount,
             COLLECT({
                 bond_name: cb.bond_name,
                 issue_date: cb.issue_date,
                 amount: cb.total_amount
             }) as details
        RETURN cb_count,
               total_amount,
               details
        """

        async with self.driver.session() as session:
            result = await session.run(
                cypher,
                company_id=company_id,
                cutoff_date=cutoff_date
            )
            record = await result.single()

            if not record or record["cb_count"] == 0:
                return {
                    "cb_count": 0,
                    "total_amount": 0,
                    "avg_interval_days": None,
                    "risk_level": "low",
                    "details": []
                }

            cb_count = record["cb_count"]
            total_amount = record["total_amount"]
            details = record["details"]

            # 평균 발행 간격 계산
            avg_interval = months * 30 / cb_count if cb_count > 0 else None

            # 위험도 평가
            if cb_count >= 4 or total_amount > 5_000_000_000:
                risk_level = "high"
            elif cb_count >= 2 or total_amount > 1_000_000_000:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "cb_count": cb_count,
                "total_amount": total_amount,
                "avg_interval_days": avg_interval,
                "risk_level": risk_level,
                "details": details
            }

    async def detect_officer_concentration(
        self,
        company_id: str
    ) -> Dict[str, Any]:
        """
        3. 임원 집중도 패턴

        한 임원이 다수 회사의 임원을 겸직하는 패턴

        Returns:
            {
                "high_concentration_officers": [
                    {
                        "officer_name": "홍길동",
                        "position_count": 5,
                        "influence_score": 0.85,
                        "companies": [...]
                    }
                ],
                "risk_level": "medium"
            }
        """
        cypher = """
        MATCH (c:Company {id: $company_id})<-[w:WORKS_AT]-(o:Officer)
        WHERE w.is_current = true
        MATCH (o)-[w2:WORKS_AT {is_current: true}]->(other:Company)
        WITH o, c, COUNT(DISTINCT other) as position_count, COLLECT(DISTINCT other.name) as companies
        WHERE position_count >= 3
        RETURN o.name as officer_name,
               o.influence_score as influence_score,
               position_count,
               companies
        ORDER BY position_count DESC, influence_score DESC
        LIMIT 10
        """

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            records = await result.data()

            officers = []
            for record in records:
                officers.append({
                    "officer_name": record["officer_name"],
                    "position_count": record["position_count"],
                    "influence_score": record.get("influence_score", 0),
                    "companies": record["companies"]
                })

            # 위험도 평가
            if officers and max(o["position_count"] for o in officers) >= 5:
                risk_level = "high"
            elif officers:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "high_concentration_officers": officers,
                "risk_level": risk_level
            }

    async def detect_financial_distress_with_cb(
        self,
        db: AsyncSession,
        company_id: str
    ) -> Dict[str, Any]:
        """
        4. 재무 악화 + CB 발행 패턴

        재무 건전성이 낮은 회사의 CB 발행

        Returns:
            {
                "health_score": 35.5,
                "recent_cb_count": 2,
                "metrics": {...},
                "warnings": [...],
                "risk_level": "high"
            }
        """
        # 재무 건전성 분석
        health_analysis = await self.metrics_calculator.analyze_company_health(db, company_id)

        # 최근 CB 발행 조회
        cb_data = await self.detect_excessive_cb_issuance(company_id, months=6)

        # 위험도 평가
        health_score = health_analysis["health_score"]
        cb_count = cb_data["cb_count"]

        if health_score < 50 and cb_count >= 2:
            risk_level = "high"
        elif health_score < 60 and cb_count >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "health_score": health_score,
            "recent_cb_count": cb_count,
            "cb_total_amount": cb_data["total_amount"],
            "metrics": health_analysis["metrics"],
            "warnings": health_analysis["warnings"],
            "strengths": health_analysis["strengths"],
            "risk_level": risk_level
        }

    async def detect_related_party_transactions(
        self,
        company_id: str
    ) -> Dict[str, Any]:
        """
        5. 특수관계자 거래 패턴

        계열사 또는 임원 겸직 회사 간 CB 투자 패턴

        Returns:
            {
                "affiliate_investments": [...],
                "officer_linked_investments": [...],
                "risk_level": "medium"
            }
        """
        cypher = """
        MATCH (c:Company {id: $company_id})

        // 1. 계열사 간 CB 투자
        OPTIONAL MATCH (c)-[:AFFILIATE_OF]-(affiliate:Company)
        OPTIONAL MATCH (affiliate)-[inv:INVESTED_IN]->(c)
        WITH c, COLLECT(DISTINCT {
            company: affiliate.name,
            company_id: affiliate.id,
            investment_count: inv.investment_count,
            total_amount: inv.total_amount
        }) as affiliate_investments

        // 2. 임원 겸직 회사 간 CB 투자
        OPTIONAL MATCH (c)<-[:WORKS_AT {is_current: true}]-(o:Officer)-[:WORKS_AT {is_current: true}]->(other:Company)
        OPTIONAL MATCH (other)-[inv2:INVESTED_IN]->(c)
        WHERE other.id <> c.id
        WITH c, affiliate_investments, COLLECT(DISTINCT {
            company: other.name,
            company_id: other.id,
            officer: o.name,
            investment_count: inv2.investment_count,
            total_amount: inv2.total_amount
        }) as officer_linked_investments

        RETURN affiliate_investments,
               officer_linked_investments
        """

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            record = await result.single()

            if not record:
                return {
                    "affiliate_investments": [],
                    "officer_linked_investments": [],
                    "risk_level": "low"
                }

            affiliate_investments = [inv for inv in record["affiliate_investments"] if inv.get("investment_count")]
            officer_linked = [inv for inv in record["officer_linked_investments"] if inv.get("investment_count")]

            # 위험도 평가
            total_related_count = len(affiliate_investments) + len(officer_linked)
            if total_related_count >= 3:
                risk_level = "high"
            elif total_related_count >= 1:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "affiliate_investments": affiliate_investments,
                "officer_linked_investments": officer_linked,
                "total_related_count": total_related_count,
                "risk_level": risk_level
            }

    def _extract_company_name_from_career(self, career_text: str) -> Optional[str]:
        """
        career_history text에서 회사명 추출

        예: "(주)이아이디 재무이사" -> "이아이디"
        """
        if not career_text:
            return None

        # (주), (유), 주식회사 등 제거하고 회사명 추출
        patterns = [
            r'\(주\)([^\s]+)',      # (주)회사명
            r'\(유\)([^\s]+)',      # (유)회사명
            r'주식회사\s*([^\s]+)', # 주식회사 회사명
            r'^([^\s]+)\s+',        # 첫 단어 (회사명으로 추정)
        ]

        for pattern in patterns:
            match = re.search(pattern, career_text)
            if match:
                return match.group(1).strip()

        return None

    async def detect_officer_movement_pattern(
        self,
        company_id: str,
        db: Optional[AsyncSession] = None,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        6. 임원 이동 패턴

        부실 회사 출신 임원의 유입 패턴

        Args:
            company_id: 대상 회사 ID
            db: SQLAlchemy 세션 (고위험 회사 조회용)
            months: 분석 기간 (개월)

        Returns:
            {
                "high_risk_officers": [
                    {
                        "officer": "홍길동",
                        "previous_companies": ["부실회사A", "부실회사B"],
                        "high_risk_companies": ["부실회사A"],
                        "career_count": 8
                    }
                ],
                "risk_level": "medium"
            }
        """
        cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

        cypher = """
        MATCH (c:Company {id: $company_id})<-[w:WORKS_AT {is_current: true}]-(o:Officer)

        // 임원의 이전 경력 조회 (career_history JSON)
        WITH c, o, o.career_history as career_history
        WHERE career_history IS NOT NULL

        // career_count가 높은 임원 필터링
        WITH c, o, career_history, o.career_count as career_count
        WHERE career_count >= 4

        RETURN o.name as officer,
               o.career_count as career_count,
               o.influence_score as influence_score,
               career_history
        ORDER BY career_count DESC
        LIMIT 10
        """

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            records = await result.data()

            # 고위험 회사 목록 조회 (db가 제공된 경우)
            high_risk_company_names = set()
            if db:
                try:
                    from app.models.risk_scores import RiskScore
                    from app.models.companies import Company

                    # 리스크 점수가 60 이상인 회사 조회
                    stmt = (
                        select(Company.name)
                        .join(RiskScore, Company.id == RiskScore.company_id)
                        .where(RiskScore.total_score >= 60)
                    )
                    result_db = await db.execute(stmt)
                    high_risk_company_names = {row[0] for row in result_db.fetchall()}
                    logger.debug(f"Found {len(high_risk_company_names)} high-risk companies")
                except Exception as e:
                    logger.warning(f"Failed to fetch high-risk companies: {e}")

            high_risk_officers = []
            total_high_risk_careers = 0

            for record in records:
                career_history = record.get("career_history")
                previous_companies = []
                high_risk_companies = []

                # career_history JSON 파싱
                if career_history:
                    try:
                        careers = career_history if isinstance(career_history, list) else json.loads(career_history)
                        for career in careers:
                            if isinstance(career, dict) and career.get("text"):
                                company_name = self._extract_company_name_from_career(career["text"])
                                if company_name:
                                    previous_companies.append(company_name)
                                    # 고위험 회사 경력 확인
                                    if company_name in high_risk_company_names:
                                        high_risk_companies.append(company_name)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse career_history: {e}")

                if high_risk_companies:
                    total_high_risk_careers += len(high_risk_companies)

                high_risk_officers.append({
                    "officer": record["officer"],
                    "career_count": record["career_count"],
                    "influence_score": record.get("influence_score", 0),
                    "previous_companies": previous_companies[:5],  # 최대 5개
                    "high_risk_companies": high_risk_companies
                })

            # 위험도 평가 (고위험 회사 경력 기반)
            if total_high_risk_careers >= 3:
                risk_level = "high"
            elif total_high_risk_careers >= 1 or (high_risk_officers and max(o["career_count"] for o in high_risk_officers) >= 6):
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "high_risk_officers": high_risk_officers,
                "total_high_risk_careers": total_high_risk_careers,
                "risk_level": risk_level
            }

    async def detect_cb_investor_concentration(
        self,
        company_id: str
    ) -> Dict[str, Any]:
        """
        7. CB 투자자 집중 패턴

        소수 투자자의 과도한 CB 인수

        Returns:
            {
                "top_investors": [
                    {
                        "investor": "투자사A",
                        "investment_count": 12,
                        "total_amount": 3000000000,
                        "concentration_ratio": 0.35
                    }
                ],
                "risk_level": "high"
            }
        """
        cypher = """
        MATCH (c:Company {id: $company_id})<-[:ISSUED]-(cb:ConvertibleBond)<-[sub:SUBSCRIBED]-(s:Subscriber)
        WITH c,
             COUNT(DISTINCT cb) as total_cb_count,
             SUM(COALESCE(sub.subscription_amount, 0)) as total_cb_amount

        MATCH (c)<-[:ISSUED]-(cb:ConvertibleBond)<-[sub:SUBSCRIBED]-(s:Subscriber)
        WITH c, total_cb_count, total_cb_amount, s,
             COUNT(DISTINCT cb) as investor_cb_count,
             SUM(COALESCE(sub.subscription_amount, 0)) as investor_amount
        WITH c, total_cb_count, total_cb_amount, s, investor_cb_count, investor_amount,
             CASE
                 WHEN total_cb_count > 0 THEN toFloat(investor_cb_count) / total_cb_count
                 ELSE 0
             END as concentration_ratio
        WHERE concentration_ratio > 0.2

        RETURN s.name as investor,
               investor_cb_count as investment_count,
               investor_amount as total_amount,
               concentration_ratio
        ORDER BY concentration_ratio DESC
        LIMIT 10
        """

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            records = await result.data()

            top_investors = []
            for record in records:
                top_investors.append({
                    "investor": record["investor"],
                    "investment_count": record["investment_count"],
                    "total_amount": record["total_amount"],
                    "concentration_ratio": round(record["concentration_ratio"], 3)
                })

            # 위험도 평가
            if top_investors and max(inv["concentration_ratio"] for inv in top_investors) > 0.4:
                risk_level = "high"
            elif top_investors:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "top_investors": top_investors,
                "total_investors": len(top_investors),
                "risk_level": risk_level
            }

    async def detect_affiliate_chain_risk(
        self,
        company_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        8. 계열사 연쇄 부실 패턴

        계열사 중 재무 악화 회사의 비율

        Args:
            company_id: 대상 회사 ID
            db: SQLAlchemy 세션 (재무 건전성 조회용)

        Returns:
            {
                "total_affiliates": 5,
                "distressed_affiliates": 2,
                "distressed_companies": ["회사A", "회사B"],
                "distress_ratio": 0.4,
                "risk_level": "high"
            }
        """
        cypher = """
        MATCH (c:Company {id: $company_id})-[:AFFILIATE_OF]-(affiliate:Company)
        RETURN COLLECT(DISTINCT affiliate.id) as affiliate_ids
        """

        async with self.driver.session() as session:
            result = await session.run(cypher, company_id=company_id)
            record = await result.single()

            if not record or not record["affiliate_ids"]:
                return {
                    "total_affiliates": 0,
                    "distressed_affiliates": 0,
                    "distress_ratio": 0.0,
                    "risk_level": "low"
                }

            affiliate_ids = record["affiliate_ids"]
            total_affiliates = len(affiliate_ids)

            # 계열사 재무 건전성 조회
            distressed_count = 0
            distressed_companies = []

            if db:
                try:
                    from app.models.financial_statements import FinancialStatement
                    from app.models.companies import Company
                    import uuid

                    # UUID 변환
                    affiliate_uuids = []
                    for aid in affiliate_ids:
                        try:
                            affiliate_uuids.append(uuid.UUID(aid) if isinstance(aid, str) else aid)
                        except (ValueError, TypeError):
                            continue

                    if affiliate_uuids:
                        # 각 계열사의 최신 재무제표 조회
                        stmt = (
                            select(
                                Company.id,
                                Company.name,
                                FinancialStatement.total_equity,
                                FinancialStatement.total_liabilities,
                                FinancialStatement.operating_income,
                                FinancialStatement.net_income
                            )
                            .join(FinancialStatement, Company.id == FinancialStatement.company_id)
                            .where(Company.id.in_(affiliate_uuids))
                            .order_by(Company.id, FinancialStatement.fiscal_year.desc())
                            .distinct(Company.id)
                        )
                        result_db = await db.execute(stmt)
                        financials = result_db.fetchall()

                        for row in financials:
                            company_name = row[1]
                            total_equity = float(row[2]) if row[2] else 0
                            total_liabilities = float(row[3]) if row[3] else 0
                            operating_income = float(row[4]) if row[4] else 0
                            net_income = float(row[5]) if row[5] else 0

                            # 재무 건전성 평가 기준
                            # 1. 부채비율 200% 초과
                            # 2. 영업이익 적자
                            # 3. 당기순이익 적자
                            is_distressed = False

                            if total_equity > 0:
                                debt_ratio = total_liabilities / total_equity
                                if debt_ratio > 2.0:
                                    is_distressed = True

                            if operating_income < 0 or net_income < 0:
                                is_distressed = True

                            if is_distressed:
                                distressed_count += 1
                                distressed_companies.append(company_name)

                except Exception as e:
                    logger.warning(f"Failed to fetch affiliate financials: {e}")
                    return {
                        "total_affiliates": total_affiliates,
                        "affiliate_ids": affiliate_ids,
                        "distressed_affiliates": None,
                        "distress_ratio": None,
                        "risk_level": "unknown",
                        "note": f"Error: {str(e)}"
                    }

            # 부실 비율 계산
            distress_ratio = distressed_count / total_affiliates if total_affiliates > 0 else 0.0

            # 위험도 평가
            if distress_ratio >= 0.5:
                risk_level = "critical"
            elif distress_ratio >= 0.3:
                risk_level = "high"
            elif distress_ratio >= 0.1:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "total_affiliates": total_affiliates,
                "distressed_affiliates": distressed_count,
                "distressed_companies": distressed_companies[:5],  # 최대 5개
                "distress_ratio": round(distress_ratio, 3),
                "risk_level": risk_level
            }

    async def analyze_company_risk(
        self,
        db: AsyncSession,
        company_id: str
    ) -> Dict[str, Any]:
        """
        특정 회사의 종합 위험도 분석

        8가지 위험 패턴을 모두 검사하고 종합 평가

        Returns:
            {
                "company_id": "...",
                "overall_risk_level": "high",
                "risk_score": 75,
                "patterns": {
                    "circular_investment": {...},
                    "excessive_cb": {...},
                    ...
                }
            }
        """
        patterns = {}

        # 1. 순환 투자
        patterns["circular_investment"] = await self.detect_circular_investment(company_id)

        # 2. 과도한 CB 발행
        patterns["excessive_cb"] = await self.detect_excessive_cb_issuance(company_id)

        # 3. 임원 집중도
        patterns["officer_concentration"] = await self.detect_officer_concentration(company_id)

        # 4. 재무 악화 + CB
        patterns["financial_distress_cb"] = await self.detect_financial_distress_with_cb(db, company_id)

        # 5. 특수관계자 거래
        patterns["related_party_transactions"] = await self.detect_related_party_transactions(company_id)

        # 6. 임원 이동 패턴
        patterns["officer_movement"] = await self.detect_officer_movement_pattern(company_id, db=db)

        # 7. CB 투자자 집중
        patterns["cb_investor_concentration"] = await self.detect_cb_investor_concentration(company_id)

        # 8. 계열사 연쇄 부실
        patterns["affiliate_chain_risk"] = await self.detect_affiliate_chain_risk(company_id, db=db)

        # 종합 위험도 계산
        risk_scores = {
            "high": 3,
            "medium": 2,
            "low": 1,
            "unknown": 0
        }

        total_score = 0
        valid_patterns = 0

        for pattern_name, pattern_data in patterns.items():
            if isinstance(pattern_data, dict) and "risk_level" in pattern_data:
                score = risk_scores.get(pattern_data["risk_level"], 0)
                total_score += score
                valid_patterns += 1
            elif isinstance(pattern_data, list) and pattern_data:
                # 리스트인 경우 (순환 투자)
                total_score += 3  # high
                valid_patterns += 1

        # 평균 점수 (0-100 스케일)
        avg_score = (total_score / (valid_patterns * 3)) * 100 if valid_patterns > 0 else 0

        # 종합 위험도
        if avg_score >= 60:
            overall_risk = "high"
        elif avg_score >= 40:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        return {
            "company_id": company_id,
            "overall_risk_level": overall_risk,
            "risk_score": round(avg_score, 1),
            "patterns": patterns,
            "analyzed_at": datetime.utcnow().isoformat()
        }
