"""
Raymontology 온톨로지 모듈

팔란티어 기반 관계형 리스크 추적 시스템
"""

# Base Classes
from .base import (
    OntologyObject,
    OntologyLink,
    generate_object_id,
)

# Entities - Layer 0: Actors
from .entities import (
    Company,
    Officer,
    Fund,
)

# Entities - Layer 1: Financial
from .entities import (
    ConvertibleBond,
    Transaction,
)

# Entities - Layer 2: Risk
from .entities import (
    RiskLevel,
    InformationAsymmetry,
    PowerAsymmetry,
    RelationalRiskSignal,
)

# Relationships
from .relationships import (
    RelationshipType,
    EXPLOITATION_WEIGHTS,
    RISK_AMPLIFICATION_PATTERNS,
    RELATIONSHIP_DESCRIPTIONS,
    calculate_relationship_risk,
    detect_risk_pattern,
)

__all__ = [
    # Base
    "OntologyObject",
    "OntologyLink",
    "generate_object_id",

    # Layer 0: Actors
    "Company",
    "Officer",
    "Fund",

    # Layer 1: Financial
    "ConvertibleBond",
    "Transaction",

    # Layer 2: Risk
    "RiskLevel",
    "InformationAsymmetry",
    "PowerAsymmetry",
    "RelationalRiskSignal",

    # Relationships
    "RelationshipType",
    "EXPLOITATION_WEIGHTS",
    "RISK_AMPLIFICATION_PATTERNS",
    "RELATIONSHIP_DESCRIPTIONS",
    "calculate_relationship_risk",
    "detect_risk_pattern",
]

__version__ = "1.0.0"
