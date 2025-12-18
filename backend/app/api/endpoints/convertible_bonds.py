"""
Convertible Bonds API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.database import get_db
from app.models.convertible_bonds import ConvertibleBond
from app.models.companies import Company
from pydantic import BaseModel
from datetime import datetime, date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convertible-bonds", tags=["convertible-bonds"])


# Response Models
class ConvertibleBondResponse(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str]
    bond_name: str
    issue_date: Optional[date]
    maturity_date: Optional[date]
    issue_amount: Optional[int]
    conversion_price: Optional[int]
    conversion_ratio: Optional[float]
    interest_rate: Optional[float]
    underwriter: Optional[str]
    status: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConvertibleBondsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    bonds: List[ConvertibleBondResponse]


@router.get("/", response_model=ConvertibleBondsListResponse)
async def get_convertible_bonds(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of convertible bonds
    """
    try:
        # Build query
        query = select(ConvertibleBond, Company.name.label("company_name"))\
            .join(Company, ConvertibleBond.company_id == Company.id)

        # Apply filters
        if company_id:
            query = query.where(ConvertibleBond.company_id == company_id)

        # Count total
        count_query = select(func.count()).select_from(ConvertibleBond)
        if company_id:
            count_query = count_query.where(ConvertibleBond.company_id == company_id)

        result = await db.execute(count_query)
        total = result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Format response
        bonds = []
        for bond, company_name in rows:
            bonds.append(ConvertibleBondResponse(
                id=str(bond.id),
                company_id=str(bond.company_id),
                company_name=company_name,
                bond_name=bond.bond_name,
                issue_date=bond.issue_date,
                maturity_date=bond.maturity_date,
                issue_amount=bond.issue_amount,
                conversion_price=bond.conversion_price,
                conversion_ratio=bond.conversion_ratio,
                interest_rate=bond.interest_rate,
                underwriter=bond.underwriter,
                status=bond.status,
                created_at=bond.created_at,
                updated_at=bond.updated_at
            ))

        return ConvertibleBondsListResponse(
            total=total,
            page=page,
            page_size=page_size,
            bonds=bonds
        )

    except Exception as e:
        logger.error(f"Error getting convertible bonds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{bond_id}", response_model=ConvertibleBondResponse)
async def get_convertible_bond(
    bond_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get convertible bond by ID
    """
    try:
        query = select(ConvertibleBond, Company.name.label("company_name"))\
            .join(Company, ConvertibleBond.company_id == Company.id)\
            .where(ConvertibleBond.id == bond_id)

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Convertible bond not found")

        bond, company_name = row

        return ConvertibleBondResponse(
            id=str(bond.id),
            company_id=str(bond.company_id),
            company_name=company_name,
            bond_name=bond.bond_name,
            issue_date=bond.issue_date,
            maturity_date=bond.maturity_date,
            issue_amount=bond.issue_amount,
            conversion_price=bond.conversion_price,
            interest_rate=bond.interest_rate,
            created_at=bond.created_at,
            updated_at=bond.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting convertible bond {bond_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_id}", response_model=List[ConvertibleBondResponse])
async def get_company_bonds(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all convertible bonds for a specific company
    """
    try:
        query = select(ConvertibleBond, Company.name.label("company_name"))\
            .join(Company, ConvertibleBond.company_id == Company.id)\
            .where(ConvertibleBond.company_id == company_id)

        result = await db.execute(query)
        rows = result.all()

        bonds = []
        for bond, company_name in rows:
            bonds.append(ConvertibleBondResponse(
                id=str(bond.id),
                company_id=str(bond.company_id),
                company_name=company_name,
                bond_name=bond.bond_name,
                issue_date=bond.issue_date,
                maturity_date=bond.maturity_date,
                issue_amount=bond.issue_amount,
                conversion_price=bond.conversion_price,
                conversion_ratio=bond.conversion_ratio,
                interest_rate=bond.interest_rate,
                underwriter=bond.underwriter,
                status=bond.status,
                created_at=bond.created_at,
                updated_at=bond.updated_at
            ))

        return bonds

    except Exception as e:
        logger.error(f"Error getting bonds for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
