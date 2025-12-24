"""
Officers API Endpoints

임원 관련 API - officer_positions 테이블 기반
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from typing import List, Optional
import logging

from app.database import get_db
from app.models.officers import Officer
from app.models.officer_positions import OfficerPosition
from app.models.companies import Company
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/officers", tags=["officers"])


# Response Models
class OfficerResponse(BaseModel):
    id: str
    name: str
    name_en: Optional[str]
    position: Optional[str]
    current_company_id: Optional[str]
    company_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfficersListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    officers: List[OfficerResponse]


@router.get("/", response_model=OfficersListResponse)
async def get_officers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of officers

    company_id 지정 시 officer_positions 테이블에서 현재 재직 중인 임원 조회
    """
    try:
        if company_id:
            # 회사별 조회: officer_positions 기반
            query = (
                select(Officer, OfficerPosition.position.label("op_position"), Company.name.label("company_name"))
                .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
                .join(Company, OfficerPosition.company_id == Company.id)
                .where(OfficerPosition.company_id == company_id)
                .where(OfficerPosition.is_current == True)
            )

            if search:
                query = query.where(Officer.name.ilike(f"%{search}%"))

            # Count
            count_query = (
                select(func.count(distinct(Officer.id)))
                .select_from(Officer)
                .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
                .where(OfficerPosition.company_id == company_id)
                .where(OfficerPosition.is_current == True)
            )
            if search:
                count_query = count_query.where(Officer.name.ilike(f"%{search}%"))
        else:
            # 전체 조회: officers 테이블 기반 (기존 방식 유지)
            query = select(Officer, Officer.position.label("op_position"), Company.name.label("company_name"))\
                .outerjoin(Company, Officer.current_company_id == Company.id)

            if search:
                query = query.where(Officer.name.ilike(f"%{search}%"))

            count_query = select(func.count()).select_from(Officer)
            if search:
                count_query = count_query.where(Officer.name.ilike(f"%{search}%"))

        result = await db.execute(count_query)
        total = result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Format response
        officers = []
        for officer, op_position, company_name in rows:
            officers.append(OfficerResponse(
                id=str(officer.id),
                name=officer.name,
                name_en=officer.name_en,
                position=op_position or officer.position,  # officer_positions 우선
                current_company_id=company_id if company_id else (str(officer.current_company_id) if officer.current_company_id else None),
                company_name=company_name,
                created_at=officer.created_at,
                updated_at=officer.updated_at
            ))

        return OfficersListResponse(
            total=total,
            page=page,
            page_size=page_size,
            officers=officers
        )

    except Exception as e:
        logger.error(f"Error getting officers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{officer_id}", response_model=OfficerResponse)
async def get_officer(
    officer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get officer by ID

    현재 재직 중인 회사 정보를 officer_positions에서 조회
    """
    try:
        # 임원 기본 정보 조회
        officer_result = await db.execute(
            select(Officer).where(Officer.id == officer_id)
        )
        officer = officer_result.scalar_one_or_none()

        if not officer:
            raise HTTPException(status_code=404, detail="Officer not found")

        # 현재 재직 중인 회사 조회 (officer_positions 기반)
        current_position_query = (
            select(OfficerPosition.position, OfficerPosition.company_id, Company.name.label("company_name"))
            .join(Company, OfficerPosition.company_id == Company.id)
            .where(OfficerPosition.officer_id == officer_id)
            .where(OfficerPosition.is_current == True)
            .limit(1)  # 여러 회사 겸직 시 첫 번째만
        )
        current_result = await db.execute(current_position_query)
        current_row = current_result.first()

        if current_row:
            position, company_id, company_name = current_row
        else:
            position = officer.position
            company_id = officer.current_company_id
            company_name = None

        return OfficerResponse(
            id=str(officer.id),
            name=officer.name,
            name_en=officer.name_en,
            position=position or officer.position,
            current_company_id=str(company_id) if company_id else None,
            company_name=company_name,
            created_at=officer.created_at,
            updated_at=officer.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting officer {officer_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}", response_model=List[OfficerResponse])
async def get_company_officers(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all officers for a specific company

    officer_positions 테이블에서 is_current=true인 임원 조회
    """
    try:
        # officer_positions 기반 조회
        query = (
            select(Officer, OfficerPosition.position.label("op_position"), Company.name.label("company_name"))
            .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
            .join(Company, OfficerPosition.company_id == Company.id)
            .where(OfficerPosition.company_id == company_id)
            .where(OfficerPosition.is_current == True)
            .order_by(Officer.influence_score.desc().nulls_last(), Officer.name)
        )

        result = await db.execute(query)
        rows = result.all()

        officers = []
        for officer, op_position, company_name in rows:
            officers.append(OfficerResponse(
                id=str(officer.id),
                name=officer.name,
                name_en=officer.name_en,
                position=op_position or officer.position,
                current_company_id=company_id,
                company_name=company_name,
                created_at=officer.created_at,
                updated_at=officer.updated_at
            ))

        return officers

    except Exception as e:
        logger.error(f"Error getting officers for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
