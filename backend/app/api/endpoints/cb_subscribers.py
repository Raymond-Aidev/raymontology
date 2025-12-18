"""
CB Subscribers API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.database import get_db
from app.models.cb_subscribers import CBSubscriber
from app.models.convertible_bonds import ConvertibleBond
from app.models.companies import Company
from pydantic import BaseModel
from datetime import datetime, date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cb-subscribers", tags=["cb-subscribers"])


# Response Models
class CBSubscriberResponse(BaseModel):
    id: str
    cb_id: str
    bond_name: Optional[str]
    company_name: Optional[str]
    subscriber_name: str
    subscriber_type: Optional[str]
    subscription_amount: Optional[float]
    subscription_quantity: Optional[float]
    is_related_party: bool
    relationship: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CBSubscribersListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    subscribers: List[CBSubscriberResponse]


@router.get("/", response_model=CBSubscribersListResponse)
async def get_cb_subscribers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    cb_id: Optional[str] = Query(None, description="Filter by CB ID"),
    is_related_party: Optional[bool] = Query(None, description="Filter by related party status"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of CB subscribers
    """
    try:
        # Build query
        query = select(
            CBSubscriber,
            ConvertibleBond.bond_name.label("bond_name"),
            Company.name.label("company_name")
        ).join(
            ConvertibleBond, CBSubscriber.cb_id == ConvertibleBond.id
        ).join(
            Company, ConvertibleBond.company_id == Company.id
        )

        # Apply filters
        if cb_id:
            query = query.where(CBSubscriber.cb_id == cb_id)
        if is_related_party is not None:
            # is_related_party is varchar in DB, check for 'Y' or 'N'
            if is_related_party:
                query = query.where(CBSubscriber.is_related_party == 'Y')
            else:
                query = query.where(CBSubscriber.is_related_party != 'Y')

        # Count total
        count_query = select(func.count()).select_from(CBSubscriber)
        if cb_id:
            count_query = count_query.where(CBSubscriber.cb_id == cb_id)
        if is_related_party is not None:
            if is_related_party:
                count_query = count_query.where(CBSubscriber.is_related_party == 'Y')
            else:
                count_query = count_query.where(CBSubscriber.is_related_party != 'Y')

        result = await db.execute(count_query)
        total = result.scalar_one()

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Format response
        subscribers = []
        for subscriber, bond_name, company_name in rows:
            subscribers.append(CBSubscriberResponse(
                id=str(subscriber.id),
                cb_id=str(subscriber.cb_id),
                bond_name=bond_name,
                company_name=company_name,
                subscriber_name=subscriber.subscriber_name,
                subscriber_type=subscriber.subscriber_type,
                subscription_amount=subscriber.subscription_amount,
                subscription_quantity=subscriber.subscription_quantity,
                is_related_party=subscriber.is_related_party == 'Y',
                relationship=subscriber.relationship_to_company,
                created_at=subscriber.created_at
            ))

        return CBSubscribersListResponse(
            total=total,
            page=page,
            page_size=page_size,
            subscribers=subscribers
        )

    except Exception as e:
        logger.error(f"Error getting CB subscribers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscriber_id}", response_model=CBSubscriberResponse)
async def get_cb_subscriber(
    subscriber_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get CB subscriber by ID
    """
    try:
        query = select(
            CBSubscriber,
            ConvertibleBond.bond_name.label("bond_name"),
            Company.name.label("company_name")
        ).join(
            ConvertibleBond, CBSubscriber.cb_id == ConvertibleBond.id
        ).join(
            Company, ConvertibleBond.company_id == Company.id
        ).where(CBSubscriber.id == subscriber_id)

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="CB subscriber not found")

        subscriber, bond_name, company_name = row

        return CBSubscriberResponse(
            id=str(subscriber.id),
            cb_id=str(subscriber.cb_id),
            bond_name=bond_name,
            company_name=company_name,
            subscriber_name=subscriber.subscriber_name,
            subscriber_type=subscriber.subscriber_type,
            subscription_amount=subscriber.subscription_amount,
            subscription_quantity=subscriber.subscription_quantity,
            is_related_party=subscriber.is_related_party == 'Y',
            relationship=subscriber.relationship_to_company,
            created_at=subscriber.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CB subscriber {subscriber_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bond/{cb_id}", response_model=List[CBSubscriberResponse])
async def get_bond_subscribers(
    cb_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all subscribers for a specific convertible bond
    """
    try:
        query = select(
            CBSubscriber,
            ConvertibleBond.bond_name.label("bond_name"),
            Company.name.label("company_name")
        ).join(
            ConvertibleBond, CBSubscriber.cb_id == ConvertibleBond.id
        ).join(
            Company, ConvertibleBond.company_id == Company.id
        ).where(CBSubscriber.cb_id == cb_id)

        result = await db.execute(query)
        rows = result.all()

        subscribers = []
        for subscriber, bond_name, company_name in rows:
            subscribers.append(CBSubscriberResponse(
                id=str(subscriber.id),
                cb_id=str(subscriber.cb_id),
                bond_name=bond_name,
                company_name=company_name,
                subscriber_name=subscriber.subscriber_name,
                subscriber_type=subscriber.subscriber_type,
                subscription_amount=subscriber.subscription_amount,
                subscription_quantity=subscriber.subscription_quantity,
                is_related_party=subscriber.is_related_party == 'Y',
                relationship=subscriber.relationship_to_company,
                created_at=subscriber.created_at
            ))

        return subscribers

    except Exception as e:
        logger.error(f"Error getting subscribers for bond {cb_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
