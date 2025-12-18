"""
Raymontology 온톨로지 기본 클래스
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid


def generate_object_id(prefix: str = "OBJ") -> str:
    """전역 고유 ID 생성"""
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"


class OntologyObject(BaseModel):
    """
    모든 엔티티의 부모 클래스

    Raymontology = Raymond + Ontology
    팔란티어 핵심: Object-Link-Property 트리플
    """
    model_config = ConfigDict(from_attributes=True)

    object_id: str = Field(default_factory=lambda: generate_object_id())
    object_type: str

    # 시간 버전 관리
    valid_from: datetime = Field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None
    version: int = Field(default=1, ge=1)

    # 계보 추적
    source_documents: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    # 속성
    properties: Dict[str, Any] = Field(default_factory=dict)

    # 메타데이터
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class OntologyLink(BaseModel):
    """관계도 1급 시민"""
    model_config = ConfigDict(from_attributes=True)

    link_id: str = Field(default_factory=lambda: generate_object_id("LINK"))
    link_type: str

    source_object_id: str
    target_object_id: str

    properties: Dict[str, Any] = Field(default_factory=dict)

    valid_from: datetime = Field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None

    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
