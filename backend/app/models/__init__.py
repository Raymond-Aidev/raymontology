"""
SQLAlchemy Models

모든 모델을 여기서 import
"""

from app.database import Base

# Import all models
from app.models.companies import Company
from app.models.officers import Officer
from app.models.officer_positions import OfficerPosition
from app.models.ontology_objects import OntologyObject
from app.models.ontology_links import OntologyLink
from app.models.risk_signals import RiskSignal, RiskSeverity, RiskStatus
from app.models.disclosures import Disclosure, DisclosureParsedData, CrawlJob
from app.models.affiliates import Affiliate
from app.models.convertible_bonds import ConvertibleBond
from app.models.cb_subscribers import CBSubscriber
from app.models.financial_statements import FinancialStatement
from app.models.financial_details import FinancialDetails
from app.models.financial_ratios import FinancialRatios
from app.models.raymonds_index import RaymondsIndex
from app.models.users import User
from app.models.major_shareholders import MajorShareholder
from app.models.risk_scores import RiskScore
from app.models.toss_users import TossUser, CreditTransaction, ReportView, CreditProduct
from app.models.stock_prices import StockPrice
from app.models.service_application import ServiceApplication, ApplicationStatus, PlanType, ENTERPRISE_PLANS
from app.models.news import (
    NewsArticle, NewsEntity, NewsRelation, NewsRisk, NewsCompanyComplexity,
    RISK_WEIGHTS, COMPLEXITY_GRADES
)
from app.models.daily_stock_price import DailyStockPrice
from app.models.stock_info import StockInfo
from app.models.financial_snapshot import FinancialSnapshot
# EGM (임시주주총회) 관련 모델
from app.models.egm_disclosures import (
    EGMDisclosure, EGMType, DisputeType, ParseStatus,
    EGM_REPORT_TYPES, DISPUTE_STRONG_KEYWORDS, DISPUTE_MEDIUM_KEYWORDS
)
from app.models.dispute_officers import DisputeOfficer, AppointmentContext

__all__ = [
    "Base",
    "Company",
    "Officer",
    "OfficerPosition",
    "OntologyObject",
    "OntologyLink",
    "RiskSignal",
    "RiskSeverity",
    "RiskStatus",
    "Disclosure",
    "DisclosureParsedData",
    "CrawlJob",
    "Affiliate",
    "ConvertibleBond",
    "CBSubscriber",
    "FinancialStatement",
    "FinancialDetails",
    "FinancialRatios",
    "RaymondsIndex",
    "User",
    "MajorShareholder",
    "RiskScore",
    "TossUser",
    "CreditTransaction",
    "ReportView",
    "CreditProduct",
    "StockPrice",
    "ServiceApplication",
    "ApplicationStatus",
    "PlanType",
    "ENTERPRISE_PLANS",
    # News models
    "NewsArticle",
    "NewsEntity",
    "NewsRelation",
    "NewsRisk",
    "NewsCompanyComplexity",
    "RISK_WEIGHTS",
    "COMPLEXITY_GRADES",
    # M&A Target models
    "DailyStockPrice",
    "StockInfo",
    "FinancialSnapshot",
    # EGM (임시주주총회) 관련 모델
    "EGMDisclosure",
    "EGMType",
    "DisputeType",
    "ParseStatus",
    "EGM_REPORT_TYPES",
    "DISPUTE_STRONG_KEYWORDS",
    "DISPUTE_MEDIUM_KEYWORDS",
    "DisputeOfficer",
    "AppointmentContext",
]
