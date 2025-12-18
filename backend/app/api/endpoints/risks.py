"""
위험 신호 탐지 API 엔드포인트

회사 위험도 분석 및 8가지 위험 패턴 조회
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Company
from app.services.risk_detection import RiskDetectionEngine
from app.config import settings
from neo4j import AsyncGraphDatabase
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risks", tags=["risks"])


# Response Models
class RiskSignal(BaseModel):
    """개별 위험 신호"""
    pattern_type: str  # circular_investment, excessive_cb, etc.
    risk_level: str  # low, medium, high, critical
    severity_score: float  # 0-100
    title: str
    description: str
    details: Dict[str, Any]
    detected_at: str


class CompanyRiskResponse(BaseModel):
    """회사 종합 위험도 응답"""
    company_id: str
    company_name: str
    overall_risk_level: str  # low, medium, high, critical
    risk_score: float  # 0-100
    total_signals: int
    signals_by_level: Dict[str, int]
    signals: List[RiskSignal]
    analyzed_at: str


class RiskPatternDetailResponse(BaseModel):
    """특정 위험 패턴 상세"""
    pattern_type: str
    pattern_name: str
    risk_level: str
    severity_score: float
    description: str
    findings: Dict[str, Any]
    recommendations: List[str]


class RiskComparisonResponse(BaseModel):
    """위험도 비교 분석"""
    companies: List[Dict[str, Any]]
    industry_average: Optional[float]
    comparison_summary: str


# Dependencies
async def get_db():
    """Database session 제공"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_neo4j_driver():
    """Neo4j driver 제공"""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        yield driver
    finally:
        await driver.close()


# Helper Functions
def format_risk_signal(pattern_type: str, pattern_data: Dict[str, Any]) -> RiskSignal:
    """위험 패턴 데이터를 RiskSignal 형식으로 변환"""

    # 패턴별 제목 및 설명
    pattern_info = {
        "circular_investment": {
            "title": "순환 투자 패턴 발견",
            "description": "회사 간 CB 투자가 순환 구조를 형성하고 있습니다"
        },
        "excessive_cb": {
            "title": "과도한 CB 발행",
            "description": "단기간 내 과도한 CB 발행이 감지되었습니다"
        },
        "officer_concentration": {
            "title": "임원 집중도 높음",
            "description": "소수의 임원이 다수 회사를 겸직하고 있습니다"
        },
        "financial_distress_cb": {
            "title": "재무 악화 중 CB 발행",
            "description": "재무 건전성이 낮은 상태에서 CB를 발행하고 있습니다"
        },
        "related_party_transactions": {
            "title": "특수관계자 거래",
            "description": "계열사 또는 임원 관련 회사와의 CB 거래가 발견되었습니다"
        },
        "officer_movement": {
            "title": "임원 이동 패턴",
            "description": "임원의 잦은 회사 이동이 감지되었습니다"
        },
        "cb_investor_concentration": {
            "title": "CB 투자자 집중",
            "description": "소수 투자자가 CB 투자를 독점하고 있습니다"
        },
        "affiliate_chain_risk": {
            "title": "계열사 연쇄 부실 위험",
            "description": "계열사 간 부실이 연쇄적으로 전파될 위험이 있습니다"
        }
    }

    info = pattern_info.get(pattern_type, {
        "title": f"{pattern_type} 패턴",
        "description": "위험 패턴이 감지되었습니다"
    })

    # 위험도 및 점수 추출
    risk_level = pattern_data.get("risk_level", "low")

    # 위험도를 점수로 변환
    severity_map = {"low": 25, "medium": 50, "high": 75, "critical": 100}
    severity_score = severity_map.get(risk_level, 0)

    # 패턴별 상세 정보 추출
    details = {k: v for k, v in pattern_data.items() if k != "risk_level"}

    return RiskSignal(
        pattern_type=pattern_type,
        risk_level=risk_level,
        severity_score=severity_score,
        title=info["title"],
        description=info["description"],
        details=details,
        detected_at=datetime.utcnow().isoformat()
    )


# Endpoints
@router.get("/companies/{company_id}", response_model=CompanyRiskResponse)
async def get_company_risks(
    company_id: str,
    include_patterns: Optional[str] = Query(None, description="포함할 패턴 (쉼표 구분)"),
    min_severity: Optional[str] = Query(None, description="최소 위험도 (low/medium/high/critical)"),
    db: AsyncSession = Depends(get_db),
    neo4j_driver = Depends(get_neo4j_driver)
):
    """
    회사 종합 위험도 분석

    - 8가지 위험 패턴 종합 검사
    - 위험도 등급 및 점수
    - 탐지된 위험 신호 목록
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 위험도 분석
        engine = RiskDetectionEngine(neo4j_driver)
        analysis = await engine.analyze_company_risk(db, company_id)

        # 패턴 필터링
        patterns = analysis["patterns"]
        if include_patterns:
            pattern_list = [p.strip() for p in include_patterns.split(",")]
            patterns = {k: v for k, v in patterns.items() if k in pattern_list}

        # 위험 신호 생성
        signals = []
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_levels.get(min_severity, 0) if min_severity else 0

        for pattern_type, pattern_data in patterns.items():
            if not pattern_data:
                continue

            # 빈 패턴 데이터 스킵 (리스트/딕셔너리가 비어있는 경우)
            if isinstance(pattern_data, list) and len(pattern_data) == 0:
                continue
            if isinstance(pattern_data, dict) and len(pattern_data) == 0:
                continue

            signal = format_risk_signal(pattern_type, pattern_data)

            # 최소 위험도 필터
            if severity_levels.get(signal.risk_level, 0) >= min_level:
                signals.append(signal)

        # 위험도별 집계
        signals_by_level = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for signal in signals:
            signals_by_level[signal.risk_level] += 1

        return CompanyRiskResponse(
            company_id=company_id,
            company_name=company.name,
            overall_risk_level=analysis["overall_risk_level"],
            risk_score=analysis["risk_score"],
            total_signals=len(signals),
            signals_by_level=signals_by_level,
            signals=signals,
            analyzed_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing company risks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/patterns/{pattern_type}", response_model=RiskPatternDetailResponse)
async def get_risk_pattern_detail(
    company_id: str,
    pattern_type: str,
    db: AsyncSession = Depends(get_db),
    neo4j_driver = Depends(get_neo4j_driver)
):
    """
    특정 위험 패턴 상세 조회

    - 순환 투자 (circular_investment)
    - 과도한 CB 발행 (excessive_cb)
    - 임원 집중도 (officer_concentration)
    - 재무 악화 + CB (financial_distress_cb)
    - 특수관계자 거래 (related_party_transactions)
    - 임원 이동 패턴 (officer_movement)
    - CB 투자자 집중 (cb_investor_concentration)
    - 계열사 연쇄 부실 (affiliate_chain_risk)
    """
    try:
        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # 위험 탐지 엔진
        engine = RiskDetectionEngine(neo4j_driver)

        # 패턴별 상세 조회
        pattern_methods = {
            "circular_investment": engine.detect_circular_investment,
            "excessive_cb": engine.detect_excessive_cb_issuance,
            "officer_concentration": engine.detect_officer_concentration,
            "financial_distress_cb": lambda cid: engine.detect_financial_distress_with_cb(db, cid),
            "related_party_transactions": engine.detect_related_party_transactions,
            "officer_movement": engine.detect_officer_movement_pattern,
            "cb_investor_concentration": engine.detect_cb_investor_concentration,
            "affiliate_chain_risk": engine.detect_affiliate_chain_risk
        }

        if pattern_type not in pattern_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pattern type. Must be one of: {', '.join(pattern_methods.keys())}"
            )

        # 패턴 탐지
        findings = await pattern_methods[pattern_type](company_id)

        # 패턴 정보
        pattern_names = {
            "circular_investment": "순환 투자 패턴",
            "excessive_cb": "과도한 CB 발행",
            "officer_concentration": "임원 집중도",
            "financial_distress_cb": "재무 악화 중 CB 발행",
            "related_party_transactions": "특수관계자 거래",
            "officer_movement": "임원 이동 패턴",
            "cb_investor_concentration": "CB 투자자 집중",
            "affiliate_chain_risk": "계열사 연쇄 부실 위험"
        }

        pattern_descriptions = {
            "circular_investment": "회사 간 CB 투자가 순환 구조를 형성하여 자금이 실제로 유입되지 않고 순환하는 패턴",
            "excessive_cb": "단기간 내 과도한 CB 발행으로 자금 압박이 예상되는 패턴",
            "officer_concentration": "소수 임원이 다수 회사를 겸직하여 의사결정 독점이 우려되는 패턴",
            "financial_distress_cb": "재무 건전성이 악화된 상태에서 CB를 발행하여 부실 위험이 높은 패턴",
            "related_party_transactions": "계열사 또는 임원 관련 회사와의 CB 거래로 이익 충돌이 우려되는 패턴",
            "officer_movement": "임원의 잦은 회사 이동으로 불안정한 경영이 예상되는 패턴",
            "cb_investor_concentration": "소수 투자자가 CB 투자를 독점하여 경영권 위협이 우려되는 패턴",
            "affiliate_chain_risk": "계열사 간 상호 연결로 부실이 연쇄적으로 전파될 위험이 있는 패턴"
        }

        # 권장사항
        recommendations_map = {
            "circular_investment": [
                "순환 투자 구조의 실질적 자금 흐름 검증 필요",
                "각 회사의 독립적 재무 건전성 확인",
                "순환 고리 내 회사들의 동시 부실 가능성 모니터링"
            ],
            "excessive_cb": [
                "향후 CB 상환 일정 및 자금 계획 확인",
                "CB 발행 사유 및 자금 사용처 검토",
                "추가 CB 발행 가능성 및 희석 위험 평가"
            ],
            "officer_concentration": [
                "겸직 임원의 실질적 업무 수행 능력 검토",
                "이사회 독립성 및 견제 기능 확인",
                "특수관계자 거래 내역 정밀 검토"
            ],
            "financial_distress_cb": [
                "재무 건전성 개선 계획 확인",
                "CB 자금의 사용처 및 효과 모니터링",
                "추가 부실 징후 면밀히 관찰"
            ],
            "related_party_transactions": [
                "거래 조건의 공정성 검토",
                "이사회 승인 절차 확인",
                "이익 충돌 가능성 평가"
            ],
            "officer_movement": [
                "임원 이동 사유 확인",
                "경영 안정성 평가",
                "핵심 임원 유지 정책 검토"
            ],
            "cb_investor_concentration": [
                "주요 투자자의 의도 및 배경 조사",
                "경영권 방어 수단 확인",
                "투자자 다변화 전략 검토"
            ],
            "affiliate_chain_risk": [
                "각 계열사의 독립적 생존 가능성 평가",
                "계열사 간 상호 의존도 분석",
                "그룹 전체의 종합 재무 건전성 검토"
            ]
        }

        risk_level = findings.get("risk_level", "low")
        severity_map = {"low": 25, "medium": 50, "high": 75, "critical": 100}

        return RiskPatternDetailResponse(
            pattern_type=pattern_type,
            pattern_name=pattern_names[pattern_type],
            risk_level=risk_level,
            severity_score=severity_map.get(risk_level, 0),
            description=pattern_descriptions[pattern_type],
            findings=findings,
            recommendations=recommendations_map[pattern_type]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pattern detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies/compare", response_model=RiskComparisonResponse)
async def compare_company_risks(
    company_ids: List[str],
    db: AsyncSession = Depends(get_db),
    neo4j_driver = Depends(get_neo4j_driver)
):
    """
    여러 회사의 위험도 비교 분석

    - 최대 10개 회사 동시 비교
    - 위험도 순위
    - 업종 평균 대비 분석 (향후 구현)
    """
    try:
        if len(company_ids) > 10:
            raise HTTPException(
                status_code=400,
                detail="최대 10개 회사까지 비교 가능합니다"
            )

        if len(company_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="최소 2개 회사를 선택해야 합니다"
            )

        # 회사 존재 확인
        result = await db.execute(
            select(Company).where(Company.id.in_(company_ids))
        )
        companies = result.scalars().all()

        if len(companies) != len(company_ids):
            raise HTTPException(
                status_code=404,
                detail="일부 회사를 찾을 수 없습니다"
            )

        # 각 회사별 위험도 분석
        engine = RiskDetectionEngine(neo4j_driver)
        comparison_data = []

        for company in companies:
            try:
                analysis = await engine.analyze_company_risk(db, str(company.id))
                comparison_data.append({
                    "company_id": str(company.id),
                    "company_name": company.name,
                    "risk_score": analysis["risk_score"],
                    "risk_level": analysis["overall_risk_level"],
                    "pattern_count": len([
                        p for p in analysis["patterns"].values()
                        if p and (
                            (isinstance(p, list) and len(p) > 0) or
                            (isinstance(p, dict) and len(p) > 0)
                        )
                    ])
                })
            except Exception as e:
                logger.warning(f"분석 실패 - {company.name}: {e}")
                comparison_data.append({
                    "company_id": str(company.id),
                    "company_name": company.name,
                    "risk_score": 0,
                    "risk_level": "unknown",
                    "pattern_count": 0,
                    "error": str(e)
                })

        # 위험도 순으로 정렬
        comparison_data.sort(key=lambda x: x["risk_score"], reverse=True)

        # 평균 계산
        valid_scores = [c["risk_score"] for c in comparison_data if c["risk_score"] > 0]
        industry_average = sum(valid_scores) / len(valid_scores) if valid_scores else None

        # 요약
        highest = comparison_data[0]
        lowest = comparison_data[-1]
        summary = f"가장 높은 위험도: {highest['company_name']} ({highest['risk_score']:.1f}점), " \
                  f"가장 낮은 위험도: {lowest['company_name']} ({lowest['risk_score']:.1f}점)"

        return RiskComparisonResponse(
            companies=comparison_data,
            industry_average=industry_average,
            comparison_summary=summary
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing risks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns", response_model=List[Dict[str, str]])
async def list_risk_patterns():
    """
    사용 가능한 위험 패턴 목록 조회

    - 8가지 위험 패턴 정보
    """
    patterns = [
        {
            "type": "circular_investment",
            "name": "순환 투자 패턴",
            "description": "회사 간 CB 투자가 순환 구조를 형성"
        },
        {
            "type": "excessive_cb",
            "name": "과도한 CB 발행",
            "description": "단기간 내 과도한 CB 발행"
        },
        {
            "type": "officer_concentration",
            "name": "임원 집중도",
            "description": "소수 임원이 다수 회사 겸직"
        },
        {
            "type": "financial_distress_cb",
            "name": "재무 악화 중 CB 발행",
            "description": "재무 건전성이 낮은 상태에서 CB 발행"
        },
        {
            "type": "related_party_transactions",
            "name": "특수관계자 거래",
            "description": "계열사 또는 임원 관련 회사와의 CB 거래"
        },
        {
            "type": "officer_movement",
            "name": "임원 이동 패턴",
            "description": "임원의 잦은 회사 이동"
        },
        {
            "type": "cb_investor_concentration",
            "name": "CB 투자자 집중",
            "description": "소수 투자자가 CB 투자 독점"
        },
        {
            "type": "affiliate_chain_risk",
            "name": "계열사 연쇄 부실 위험",
            "description": "계열사 간 부실 연쇄 전파 가능성"
        }
    ]

    return patterns
