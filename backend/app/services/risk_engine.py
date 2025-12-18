"""
Risk Engine

Raymontology 핵심: 5가지 리스크 요소 분석
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, List, Optional, Tuple
import uuid
from datetime import datetime, timedelta

from app.models.companies import Company
from app.models.officers import Officer
from app.models.ontology_links import OntologyLink
from app.models.ontology_objects import OntologyObject


class RiskEngine:
    """
    리스크 분석 엔진

    5가지 리스크 요소:
    1. 정보 비대칭 (Information Asymmetry)
    2. 권력 집중 (Power Concentration)
    3. 거래 패턴 (Transaction Pattern)
    4. 펀드 리스크 (Fund Risk)
    5. 네트워크 리스크 (Network Risk)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # 가중치 (합계 = 1.0)
        self.weights = {
            "information_asymmetry": 0.25,
            "power_concentration": 0.25,
            "transaction_pattern": 0.20,
            "fund_risk": 0.15,
            "network_risk": 0.15,
        }

    async def calculate_risk_score(
        self,
        company_id: uuid.UUID
    ) -> Dict:
        """
        회사의 종합 리스크 점수 계산

        Args:
            company_id: 회사 UUID

        Returns:
            {
                "total_score": float,
                "components": {
                    "information_asymmetry": {...},
                    "power_concentration": {...},
                    "transaction_pattern": {...},
                    "fund_risk": {...},
                    "network_risk": {...}
                },
                "risk_level": str,
                "warnings": [...]
            }
        """
        # 회사 조회
        company = await self._get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # 5가지 요소 계산
        info_asymmetry = await self._calculate_information_asymmetry(company)
        power_concentration = await self._calculate_power_concentration(company)
        transaction_pattern = await self._calculate_transaction_pattern(company)
        fund_risk = await self._calculate_fund_risk(company)
        network_risk = await self._calculate_network_risk(company)

        # 종합 점수
        total_score = (
            info_asymmetry["score"] * self.weights["information_asymmetry"] +
            power_concentration["score"] * self.weights["power_concentration"] +
            transaction_pattern["score"] * self.weights["transaction_pattern"] +
            fund_risk["score"] * self.weights["fund_risk"] +
            network_risk["score"] * self.weights["network_risk"]
        )

        # 리스크 레벨
        risk_level = self._get_risk_level(total_score)

        # 경고 메시지
        warnings = self._generate_warnings(
            info_asymmetry,
            power_concentration,
            transaction_pattern,
            fund_risk,
            network_risk
        )

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "total_score": round(total_score, 3),
            "risk_level": risk_level,
            "components": {
                "information_asymmetry": info_asymmetry,
                "power_concentration": power_concentration,
                "transaction_pattern": transaction_pattern,
                "fund_risk": fund_risk,
                "network_risk": network_risk,
            },
            "warnings": warnings,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    # ========================================================================
    # 1. 정보 비대칭 (Information Asymmetry)
    # ========================================================================

    async def _calculate_information_asymmetry(self, company: Company) -> Dict:
        """
        정보 비대칭 점수

        측정 지표:
        - 내부자 거래 빈도
        - 공시 지연/누락
        - 임원 네트워크 복잡도
        - CB 발행 전후 주가 변동

        Returns:
            {"score": float, "factors": [...], "details": {...}}
        """
        factors = []
        score = 0.0

        # CB 발행 횟수 (많을수록 위험)
        cb_count = company.cb_issuance_count or 0
        if cb_count > 5:
            cb_score = min(cb_count / 10, 1.0)
            score += cb_score * 0.4
            factors.append({
                "name": "CB 발행 빈도",
                "value": cb_count,
                "score": cb_score,
                "weight": 0.4
            })

        # 온톨로지 링크에서 내부자 거래 패턴 조회
        insider_links = await self._count_links_by_type(
            company.ontology_object_id,
            ["INFORMATION_ADVANTAGE_OVER", "SUSPICIOUS_TRANSACTION_WITH"]
        )

        if insider_links > 0:
            insider_score = min(insider_links / 5, 1.0)
            score += insider_score * 0.6
            factors.append({
                "name": "의심 거래 패턴",
                "value": insider_links,
                "score": insider_score,
                "weight": 0.6
            })

        return {
            "score": min(score, 1.0),
            "factors": factors,
            "details": {
                "cb_issuance_count": cb_count,
                "suspicious_patterns": insider_links,
            }
        }

    # ========================================================================
    # 2. 권력 집중 (Power Concentration)
    # ========================================================================

    async def _calculate_power_concentration(self, company: Company) -> Dict:
        """
        권력 집중 점수

        측정 지표:
        - 소유 집중도
        - 계열사 거래 비율
        - 사외이사 독립성
        - 순환 출자 구조

        Returns:
            {"score": float, "factors": [...], "details": {...}}
        """
        factors = []
        score = 0.0

        # 소유 집중도 (직접 저장된 값 사용)
        ownership = company.ownership_concentration or 0.0
        if ownership > 0:
            score += ownership * 0.5
            factors.append({
                "name": "소유 집중도",
                "value": ownership,
                "score": ownership,
                "weight": 0.5
            })

        # 특수관계자 거래 비율
        affiliate_ratio = company.affiliate_transaction_ratio or 0.0
        if affiliate_ratio > 0:
            score += affiliate_ratio * 0.3
            factors.append({
                "name": "특수관계자 거래",
                "value": affiliate_ratio,
                "score": affiliate_ratio,
                "weight": 0.3
            })

        # 순환 구조 (온톨로지 링크)
        circular_links = await self._count_links_by_type(
            company.ontology_object_id,
            ["CROSS_SHAREHOLDING", "CIRCULAR_INVESTMENT"]
        )

        if circular_links > 0:
            circular_score = min(circular_links / 3, 1.0)
            score += circular_score * 0.2
            factors.append({
                "name": "순환 구조",
                "value": circular_links,
                "score": circular_score,
                "weight": 0.2
            })

        return {
            "score": min(score, 1.0),
            "factors": factors,
            "details": {
                "ownership_concentration": ownership,
                "affiliate_transaction_ratio": affiliate_ratio,
                "circular_structures": circular_links,
            }
        }

    # ========================================================================
    # 3. 거래 패턴 (Transaction Pattern)
    # ========================================================================

    async def _calculate_transaction_pattern(self, company: Company) -> Dict:
        """
        거래 패턴 점수

        측정 지표:
        - 비정상 거래량
        - 주가 조작 의심
        - 공매도 급증
        - 대량 양수도

        Returns:
            {"score": float, "factors": [...], "details": {...}}
        """
        factors = []
        score = 0.0

        # 의심스러운 거래 링크
        suspicious_txn = await self._count_links_by_type(
            company.ontology_object_id,
            ["SUSPICIOUS_TRANSACTION_WITH", "RELATED_PARTY_TRANSACTION"]
        )

        if suspicious_txn > 0:
            txn_score = min(suspicious_txn / 10, 1.0)
            score += txn_score
            factors.append({
                "name": "의심 거래",
                "value": suspicious_txn,
                "score": txn_score,
                "weight": 1.0
            })

        return {
            "score": min(score, 1.0),
            "factors": factors,
            "details": {
                "suspicious_transactions": suspicious_txn,
            }
        }

    # ========================================================================
    # 4. 펀드 리스크 (Fund Risk)
    # ========================================================================

    async def _calculate_fund_risk(self, company: Company) -> Dict:
        """
        펀드 리스크 점수

        측정 지표:
        - CB 보유 펀드 수
        - 특수관계 펀드 투자
        - 공동 투자 패턴
        - 펀드 간 담합 의심

        Returns:
            {"score": float, "factors": [...], "details": {...}}
        """
        factors = []
        score = 0.0

        # CB 소유 링크
        cb_links = await self._count_links_by_type(
            company.ontology_object_id,
            ["OWNS_CB_IN", "CONVERTED_CB_TO_SHARES"]
        )

        if cb_links > 0:
            cb_score = min(cb_links / 5, 1.0)
            score += cb_score * 0.6
            factors.append({
                "name": "CB 소유 펀드",
                "value": cb_links,
                "score": cb_score,
                "weight": 0.6
            })

        # 담합 의심 링크
        collusion_links = await self._count_links_by_type(
            company.ontology_object_id,
            ["COLLUSION_WITH", "CO_INVESTED_WITH"]
        )

        if collusion_links > 0:
            collusion_score = min(collusion_links / 3, 1.0)
            score += collusion_score * 0.4
            factors.append({
                "name": "담합 의심",
                "value": collusion_links,
                "score": collusion_score,
                "weight": 0.4
            })

        return {
            "score": min(score, 1.0),
            "factors": factors,
            "details": {
                "cb_holders": cb_links,
                "collusion_patterns": collusion_links,
            }
        }

    # ========================================================================
    # 5. 네트워크 리스크 (Network Risk)
    # ========================================================================

    async def _calculate_network_risk(self, company: Company) -> Dict:
        """
        네트워크 리스크 점수

        측정 지표:
        - 임원 겸직 수
        - 가족 관계망
        - 페이퍼컴퍼니 연결
        - 실질 지배자 은폐

        Returns:
            {"score": float, "factors": [...], "details": {...}}
        """
        factors = []
        score = 0.0

        # 가족/페이퍼컴퍼니 링크
        hidden_control = await self._count_links_by_type(
            company.ontology_object_id,
            ["FAMILY_RELATION", "SHELL_COMPANY_FOR", "SHADOW_DIRECTOR_OF", "PROXY_FOR"]
        )

        if hidden_control > 0:
            control_score = min(hidden_control / 3, 1.0)
            score += control_score * 0.7
            factors.append({
                "name": "은폐된 지배 구조",
                "value": hidden_control,
                "score": control_score,
                "weight": 0.7
            })

        # 임원 네트워크 복잡도
        officer_links = await self._count_officer_connections(company.id)
        if officer_links > 5:
            network_score = min(officer_links / 20, 1.0)
            score += network_score * 0.3
            factors.append({
                "name": "임원 네트워크",
                "value": officer_links,
                "score": network_score,
                "weight": 0.3
            })

        return {
            "score": min(score, 1.0),
            "factors": factors,
            "details": {
                "hidden_control_links": hidden_control,
                "officer_connections": officer_links,
            }
        }

    # ========================================================================
    # 헬퍼 함수
    # ========================================================================

    async def _get_company(self, company_id: uuid.UUID) -> Optional[Company]:
        """회사 조회"""
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def _count_links_by_type(
        self,
        object_id: Optional[str],
        link_types: List[str]
    ) -> int:
        """특정 타입의 링크 개수"""
        if not object_id:
            return 0

        result = await self.db.execute(
            select(func.count()).select_from(OntologyLink).where(
                OntologyLink.link_type.in_(link_types),
                (OntologyLink.source_object_id == object_id) |
                (OntologyLink.target_object_id == object_id)
            )
        )
        return result.scalar() or 0

    async def _count_officer_connections(self, company_id: uuid.UUID) -> int:
        """임원 연결 개수"""
        result = await self.db.execute(
            select(func.count()).select_from(Officer).where(
                Officer.current_company_id == company_id
            )
        )
        officer_count = result.scalar() or 0

        # 임원들의 평균 board_count
        result = await self.db.execute(
            select(func.avg(Officer.board_count)).where(
                Officer.current_company_id == company_id
            )
        )
        avg_boards = result.scalar() or 0

        return int(officer_count * avg_boards)

    def _get_risk_level(self, score: float) -> str:
        """리스크 레벨 판정"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_warnings(self, *components) -> List[str]:
        """경고 메시지 생성"""
        warnings = []

        for component in components:
            for factor in component.get("factors", []):
                if factor["score"] >= 0.7:
                    warnings.append(
                        f"⚠️ {factor['name']}: {factor['value']} (위험 수준)"
                    )

        return warnings
