"""
회사 종합 보고서 API 엔드포인트

회사명으로 검색하여 전체 데이터를 조회
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
import asyncpg
import logging

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["company-report"])

# asyncpg는 순수 postgresql:// 형식 필요 (SQLAlchemy의 +asyncpg 제거)
DB_URL = settings.database_url.replace('postgresql+asyncpg://', 'postgresql://').replace('+asyncpg', '')


# Response Models
class CompanyBasicInfo(BaseModel):
    id: str
    corp_code: str
    name: str
    ticker: Optional[str] = None  # 종목코드 (6자리)
    market: Optional[str] = None  # KOSPI, KOSDAQ, KONEX, ETF
    company_type: Optional[str] = None  # NORMAL, SPAC, REIT, ETF
    trading_status: Optional[str] = None  # NORMAL, SUSPENDED, TRADING_HALT


class RiskScoreInfo(BaseModel):
    analysis_year: int
    analysis_quarter: Optional[int]
    total_score: float
    risk_level: str
    investment_grade: str
    raymondsrisk_score: float
    human_risk_score: float
    cb_risk_score: float
    financial_health_score: float


class RiskSignalInfo(BaseModel):
    pattern_type: str
    severity: str
    risk_score: float
    title: str
    description: str


class CBInfo(BaseModel):
    issue_date: Optional[str]
    issue_amount_billion: float
    conversion_price: Optional[int]
    maturity_date: Optional[str]
    bond_name: Optional[str]  # "제N회..." 형태의 채권명


class CBSubscriberInfo(BaseModel):
    subscriber_name: str
    subscription_amount_billion: float
    issue_date: Optional[str]
    bond_name: Optional[str]  # "제N회..." 형태의 채권명


class OfficerInfo(BaseModel):
    name: str
    position: str
    term_start: Optional[str]
    term_end: Optional[str]
    is_current: bool = False  # 최신 보고서 기준 재직 여부


class FinancialInfo(BaseModel):
    fiscal_year: int
    quarter: Optional[str]
    total_assets_billion: Optional[float]
    total_liabilities_billion: Optional[float]
    total_equity_billion: Optional[float]
    revenue_billion: Optional[float]
    operating_profit_billion: Optional[float]
    net_income_billion: Optional[float]


class ShareholderInfo(BaseModel):
    shareholder_name: str
    share_ratio: Optional[float]
    is_largest: bool
    report_year: Optional[int]


class AffiliateInfo(BaseModel):
    affiliate_name: str
    relationship_type: str


class CompanyFullReport(BaseModel):
    """회사 종합 보고서"""
    basic_info: CompanyBasicInfo
    disclosure_count: int
    risk_score: Optional[RiskScoreInfo]
    risk_signals: List[RiskSignalInfo]
    convertible_bonds: List[CBInfo]
    cb_subscribers: List[CBSubscriberInfo]
    officers: List[OfficerInfo]
    financials: List[FinancialInfo]
    shareholders: List[ShareholderInfo]
    affiliates: List[AffiliateInfo]
    summary: Dict[str, Any]


class CompanySearchResult(BaseModel):
    """검색 결과"""
    id: str
    corp_code: str
    name: str
    cb_count: int
    risk_level: Optional[str]
    investment_grade: Optional[str]


@router.get("/search", response_model=List[CompanySearchResult])
async def search_companies_by_name(
    q: str = Query(..., min_length=1, description="회사명 검색어 (부분 일치)"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수")
):
    """
    회사명으로 검색

    - 부분 일치 지원
    - CB 발행 건수 및 리스크 등급 포함
    """
    try:
        conn = await asyncpg.connect(DB_URL)

        try:
            companies = await conn.fetch("""
                SELECT c.id, c.corp_code, c.name,
                       COALESCE(cb.cb_count, 0) as cb_count,
                       rs.risk_level, rs.investment_grade
                FROM companies c
                LEFT JOIN (
                    SELECT company_id, COUNT(*) as cb_count
                    FROM convertible_bonds
                    GROUP BY company_id
                ) cb ON c.id = cb.company_id
                LEFT JOIN risk_scores rs ON c.id = rs.company_id
                WHERE c.name ILIKE $1
                ORDER BY cb.cb_count DESC NULLS LAST, c.name
                LIMIT $2
            """, f"%{q}%", limit)

            return [
                CompanySearchResult(
                    id=str(row['id']),
                    corp_code=row['corp_code'] or '',
                    name=row['name'],
                    cb_count=row['cb_count'],
                    risk_level=row['risk_level'],
                    investment_grade=row['investment_grade']
                )
                for row in companies
            ]
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/name/{company_name}", response_model=CompanyFullReport)
async def get_company_full_report(
    company_name: str,
    exact_match: bool = Query(False, description="정확히 일치하는 회사명만 조회")
):
    """
    회사명으로 종합 보고서 조회

    - 기본정보, 리스크 점수, 리스크 신호
    - CB 발행 및 인수인 현황
    - 임원 현황
    - 재무제표
    - 주주 및 계열회사 정보

    **exact_match=false (기본)**: 부분 일치 시 가장 유사한 회사 선택
    **exact_match=true**: 정확히 일치하는 회사만 조회
    """
    try:
        conn = await asyncpg.connect(DB_URL)

        try:
            # 1. 회사 찾기
            if exact_match:
                company = await conn.fetchrow("""
                    SELECT id, corp_code, name, ticker, market, company_type, trading_status
                    FROM companies WHERE name = $1
                """, company_name)
            else:
                company = await conn.fetchrow("""
                    SELECT id, corp_code, name, ticker, market, company_type, trading_status
                    FROM companies
                    WHERE name ILIKE $1
                    ORDER BY
                        CASE WHEN name = $2 THEN 0 ELSE 1 END,
                        LENGTH(name)
                    LIMIT 1
                """, f"%{company_name}%", company_name)

            if not company:
                raise HTTPException(status_code=404, detail=f"회사를 찾을 수 없습니다: {company_name}")

            company_id = company['id']
            corp_code = company['corp_code']

            # 2. 공시 건수
            disclosure_count = await conn.fetchval("""
                SELECT COUNT(*) FROM disclosures WHERE corp_code = $1
            """, corp_code) or 0

            # 3. 리스크 점수
            risk_score_row = await conn.fetchrow("""
                SELECT analysis_year, analysis_quarter, total_score, risk_level,
                       investment_grade, raymondsrisk_score, human_risk_score,
                       cb_risk_score, financial_health_score
                FROM risk_scores
                WHERE company_id = $1
                ORDER BY analysis_year DESC, analysis_quarter DESC NULLS LAST
                LIMIT 1
            """, company_id)

            risk_score = None
            if risk_score_row:
                risk_score = RiskScoreInfo(
                    analysis_year=risk_score_row['analysis_year'],
                    analysis_quarter=risk_score_row['analysis_quarter'],
                    total_score=float(risk_score_row['total_score']),
                    risk_level=risk_score_row['risk_level'],
                    investment_grade=risk_score_row['investment_grade'],
                    raymondsrisk_score=float(risk_score_row['raymondsrisk_score']),
                    human_risk_score=float(risk_score_row['human_risk_score']),
                    cb_risk_score=float(risk_score_row['cb_risk_score']),
                    financial_health_score=float(risk_score_row['financial_health_score'])
                )

            # 4. 리스크 신호
            risk_signals_rows = await conn.fetch("""
                SELECT pattern_type, severity, risk_score, title, description
                FROM risk_signals
                WHERE target_company_id = $1
                ORDER BY risk_score DESC
            """, company_id)

            risk_signals = [
                RiskSignalInfo(
                    pattern_type=row['pattern_type'],
                    severity=row['severity'],
                    risk_score=float(row['risk_score']),
                    title=row['title'],
                    description=row['description']
                )
                for row in risk_signals_rows
            ]

            # 5. CB 발행
            cb_rows = await conn.fetch("""
                SELECT issue_date, issue_amount / 100000000.0 as issue_amount_billion,
                       conversion_price, maturity_date, bond_name
                FROM convertible_bonds
                WHERE company_id = $1
                ORDER BY issue_date DESC NULLS LAST
            """, company_id)

            convertible_bonds = [
                CBInfo(
                    issue_date=str(row['issue_date']) if row['issue_date'] else None,
                    issue_amount_billion=float(row['issue_amount_billion']) if row['issue_amount_billion'] else 0,
                    conversion_price=row['conversion_price'],
                    maturity_date=str(row['maturity_date']) if row['maturity_date'] else None,
                    bond_name=row['bond_name']
                )
                for row in cb_rows
            ]

            # 6. CB 인수인
            sub_rows = await conn.fetch("""
                SELECT cs.subscriber_name,
                       cs.subscription_amount / 100000000.0 as subscription_amount_billion,
                       cb.issue_date,
                       cb.bond_name
                FROM cb_subscribers cs
                JOIN convertible_bonds cb ON cs.cb_id = cb.id
                WHERE cb.company_id = $1
                ORDER BY cb.issue_date DESC NULLS LAST
            """, company_id)

            cb_subscribers = [
                CBSubscriberInfo(
                    subscriber_name=row['subscriber_name'],
                    subscription_amount_billion=float(row['subscription_amount_billion']) if row['subscription_amount_billion'] else 0,
                    issue_date=str(row['issue_date']) if row['issue_date'] else None,
                    bond_name=row['bond_name']
                )
                for row in sub_rows
            ]

            # 7. 임원 - 최신 보고서 기준 재직 여부 포함
            # 먼저 해당 회사의 가장 최신 보고서 날짜 조회
            latest_report = await conn.fetchrow("""
                SELECT MAX(source_report_date) as latest_date
                FROM officer_positions
                WHERE company_id = $1
            """, company_id)
            latest_report_date = latest_report['latest_date'] if latest_report else None

            officer_rows = await conn.fetch("""
                WITH latest_officers AS (
                    -- 최신 보고서의 임원 목록
                    SELECT DISTINCT o.name, op.position
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    WHERE op.company_id = $1
                    AND op.source_report_date = $2
                )
                SELECT DISTINCT ON (o.name, op.position)
                    o.name,
                    op.position,
                    op.term_start_date,
                    op.term_end_date,
                    CASE WHEN lo.name IS NOT NULL THEN true ELSE false END as is_current
                FROM officers o
                JOIN officer_positions op ON o.id = op.officer_id
                LEFT JOIN latest_officers lo ON o.name = lo.name AND op.position = lo.position
                WHERE op.company_id = $1
                ORDER BY o.name, op.position, op.source_report_date DESC NULLS LAST
            """, company_id, latest_report_date)

            officers = [
                OfficerInfo(
                    name=row['name'],
                    position=row['position'] or '',
                    term_start=str(row['term_start_date']) if row['term_start_date'] else None,
                    term_end=str(row['term_end_date']) if row['term_end_date'] else None,
                    is_current=row['is_current']
                )
                for row in officer_rows
            ]

            # 8. 재무제표
            fin_rows = await conn.fetch("""
                SELECT fiscal_year, quarter,
                       total_assets / 100000000.0 as total_assets_billion,
                       total_liabilities / 100000000.0 as total_liabilities_billion,
                       total_equity / 100000000.0 as total_equity_billion,
                       revenue / 100000000.0 as revenue_billion,
                       operating_profit / 100000000.0 as operating_profit_billion,
                       net_income / 100000000.0 as net_income_billion
                FROM financial_statements
                WHERE company_id = $1
                ORDER BY fiscal_year DESC, quarter DESC NULLS LAST
            """, company_id)

            financials = [
                FinancialInfo(
                    fiscal_year=row['fiscal_year'],
                    quarter=row['quarter'],
                    total_assets_billion=float(row['total_assets_billion']) if row['total_assets_billion'] else None,
                    total_liabilities_billion=float(row['total_liabilities_billion']) if row['total_liabilities_billion'] else None,
                    total_equity_billion=float(row['total_equity_billion']) if row['total_equity_billion'] else None,
                    revenue_billion=float(row['revenue_billion']) if row['revenue_billion'] else None,
                    operating_profit_billion=float(row['operating_profit_billion']) if row['operating_profit_billion'] else None,
                    net_income_billion=float(row['net_income_billion']) if row['net_income_billion'] else None
                )
                for row in fin_rows
            ]

            # 9. 주주 (중복 제거 + 숫자로만 된 이름 필터링 - 파싱 오류 데이터)
            # 동일 주주는 가장 최신 보고서 기준으로 1건만 표시
            sh_rows = await conn.fetch("""
                SELECT DISTINCT ON (shareholder_name_normalized)
                    shareholder_name,
                    share_ratio,
                    is_largest_shareholder,
                    report_year,
                    source_rcept_no
                FROM major_shareholders
                WHERE company_id = $1
                  AND shareholder_name !~ '^[0-9,\\.\\s]+$'
                ORDER BY shareholder_name_normalized, source_rcept_no DESC NULLS LAST
            """, company_id)

            shareholders = [
                ShareholderInfo(
                    shareholder_name=row['shareholder_name'],
                    share_ratio=float(row['share_ratio']) if row['share_ratio'] else None,
                    is_largest=row['is_largest_shareholder'] or False,
                    report_year=row['report_year']
                )
                for row in sh_rows
            ]

            # 지분율 높은 순으로 재정렬
            shareholders.sort(key=lambda x: x.share_ratio or 0, reverse=True)

            # 10. 계열회사
            aff_rows = await conn.fetch("""
                SELECT c2.name as affiliate_name, a.relationship_type
                FROM affiliates a
                JOIN companies c2 ON a.affiliate_company_id = c2.id
                WHERE a.parent_company_id = $1
            """, company_id)

            affiliates = [
                AffiliateInfo(
                    affiliate_name=row['affiliate_name'],
                    relationship_type=row['relationship_type'] or 'AFFILIATE'
                )
                for row in aff_rows
            ]

            # Summary 생성
            total_cb_amount = sum(cb.issue_amount_billion for cb in convertible_bonds)

            # 인수인별 합계
            subscriber_totals = {}
            for sub in cb_subscribers:
                name = sub.subscriber_name
                subscriber_totals[name] = subscriber_totals.get(name, 0) + sub.subscription_amount_billion

            top_subscribers = sorted(subscriber_totals.items(), key=lambda x: x[1], reverse=True)[:5]

            summary = {
                "cb_total_count": len(convertible_bonds),
                "cb_total_amount_billion": round(total_cb_amount, 1),
                "risk_signal_count": len(risk_signals),
                "high_risk_signals": len([s for s in risk_signals if s.severity == 'HIGH']),
                "officer_count": len(officers),
                "top_cb_subscribers": [{"name": name, "amount_billion": round(amt, 1)} for name, amt in top_subscribers],
                "has_financial_loss": any(f.net_income_billion and f.net_income_billion < 0 for f in financials)
            }

            return CompanyFullReport(
                basic_info=CompanyBasicInfo(
                    id=str(company_id),
                    corp_code=corp_code or '',
                    name=company['name'],
                    ticker=company.get('ticker'),
                    market=company.get('market'),
                    company_type=company.get('company_type'),
                    trading_status=company.get('trading_status')
                ),
                disclosure_count=disclosure_count,
                risk_score=risk_score,
                risk_signals=risk_signals,
                convertible_bonds=convertible_bonds,
                cb_subscribers=cb_subscribers,
                officers=officers,
                financials=financials,
                shareholders=shareholders,
                affiliates=affiliates,
                summary=summary
            )

        finally:
            await conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-risk", response_model=List[CompanySearchResult])
async def get_high_risk_companies(
    min_score: float = Query(50, ge=0, le=100, description="최소 리스크 점수"),
    limit: int = Query(50, ge=1, le=200, description="결과 개수")
):
    """
    고위험 회사 목록 조회

    - 리스크 점수 기준 정렬
    - 투자등급 포함
    """
    try:
        conn = await asyncpg.connect(DB_URL)

        try:
            companies = await conn.fetch("""
                SELECT c.id, c.corp_code, c.name,
                       COALESCE(cb.cb_count, 0) as cb_count,
                       rs.risk_level, rs.investment_grade, rs.total_score
                FROM companies c
                JOIN risk_scores rs ON c.id = rs.company_id
                LEFT JOIN (
                    SELECT company_id, COUNT(*) as cb_count
                    FROM convertible_bonds
                    GROUP BY company_id
                ) cb ON c.id = cb.company_id
                WHERE rs.total_score >= $1
                ORDER BY rs.total_score DESC
                LIMIT $2
            """, min_score, limit)

            return [
                CompanySearchResult(
                    id=str(row['id']),
                    corp_code=row['corp_code'] or '',
                    name=row['name'],
                    cb_count=row['cb_count'],
                    risk_level=row['risk_level'],
                    investment_grade=row['investment_grade']
                )
                for row in companies
            ]
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"High risk query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
