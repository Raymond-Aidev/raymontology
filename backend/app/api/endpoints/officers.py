"""
Officers API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.database import get_db
from app.models.officers import Officer
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
    """
    try:
        # Build query
        query = select(Officer, Company.name.label("company_name"))\
            .outerjoin(Company, Officer.current_company_id == Company.id)

        # Apply filters
        if search:
            query = query.where(Officer.name.ilike(f"%{search}%"))

        if company_id:
            query = query.where(Officer.current_company_id == company_id)

        # Count total
        count_query = select(func.count()).select_from(Officer)
        if search:
            count_query = count_query.where(Officer.name.ilike(f"%{search}%"))
        if company_id:
            count_query = count_query.where(Officer.current_company_id == company_id)

        result = await db.execute(count_query)
        total = result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Format response
        officers = []
        for officer, company_name in rows:
            officers.append(OfficerResponse(
                id=str(officer.id),
                name=officer.name,
                name_en=officer.name_en,
                position=officer.position,
                current_company_id=str(officer.current_company_id) if officer.current_company_id else None,
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
    """
    try:
        query = select(Officer, Company.name.label("company_name"))\
            .outerjoin(Company, Officer.current_company_id == Company.id)\
            .where(Officer.id == officer_id)

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Officer not found")

        officer, company_name = row

        return OfficerResponse(
            id=str(officer.id),
            name=officer.name,
            name_en=officer.name_en,
            position=officer.position,
            current_company_id=str(officer.current_company_id) if officer.current_company_id else None,
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
    """
    try:
        query = select(Officer, Company.name.label("company_name"))\
            .join(Company, Officer.current_company_id == Company.id)\
            .where(Officer.current_company_id == company_id)

        result = await db.execute(query)
        rows = result.all()

        officers = []
        for officer, company_name in rows:
            officers.append(OfficerResponse(
                id=str(officer.id),
                name=officer.name,
                name_en=officer.name_en,
                position=officer.position,
                current_company_id=str(officer.current_company_id),
                company_name=company_name,
                created_at=officer.created_at,
                updated_at=officer.updated_at
            ))

        return officers

    except Exception as e:
        logger.error(f"Error getting officers for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
