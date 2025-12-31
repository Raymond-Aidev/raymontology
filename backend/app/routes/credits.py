"""
이용권(Credits) API 라우터

토스 인앱결제(IAP) 검증을 통한 이용권 구매 처리.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import logging

from app.database import get_db
from app.models.toss_users import TossUser, CreditTransaction, CreditProduct, ReportView
from app.config import settings

# mTLS 클라이언트 import (인앱결제 검증용)
_toss_client_available = False

try:
    from app.services.toss_api_client import get_toss_client, TossAPIClient
    _test_client = get_toss_client()
    _toss_client_available = True
except Exception as e:
    logging.warning(f"TossAPIClient 미사용 (IAP 검증 불가): {e}")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credits", tags=["credits"])

# ============================================================================
# Request/Response Models
# ============================================================================


class CreditBalanceResponse(BaseModel):
    """이용권 잔액 응답"""
    credits: int
    lastPurchaseAt: Optional[str] = None


class CreditProductResponse(BaseModel):
    """이용권 상품 정보"""
    id: str
    name: str
    credits: int
    price: int
    badge: Optional[str] = None


class CreditProductListResponse(BaseModel):
    """이용권 상품 목록"""
    products: List[CreditProductResponse]


class PurchaseRequest(BaseModel):
    """이용권 구매 요청 (토스 인앱결제)"""
    productId: str  # SKU ID (report_1, report_10, report_30)
    orderId: str    # 토스 인앱결제 주문 ID
    receiptData: Optional[str] = None  # 기존 호환성 유지


class VerifyPurchaseRequest(BaseModel):
    """토스 인앱결제 검증 요청"""
    orderId: str    # 토스에서 발급한 주문 ID
    sku: str        # 상품 SKU


class PurchaseResponse(BaseModel):
    """이용권 구매 응답"""
    success: bool
    credits: int  # 구매 후 잔액
    message: str


class TransactionResponse(BaseModel):
    """거래 내역"""
    id: str
    type: str
    amount: int
    balanceAfter: int
    description: Optional[str] = None
    createdAt: str


class TransactionHistoryResponse(BaseModel):
    """거래 내역 목록"""
    transactions: List[TransactionResponse]
    total: int


# ============================================================================
# Helper Functions
# ============================================================================


async def get_current_toss_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> TossUser:
    """현재 로그인한 토스 사용자 조회"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다"
        )

    access_token = authorization.replace("Bearer ", "")

    result = await db.execute(
        select(TossUser).where(TossUser.access_token == access_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )

    return user


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 이용권 잔액 조회
    """
    # 마지막 구매 시점 조회
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .where(CreditTransaction.transaction_type == "purchase")
        .order_by(desc(CreditTransaction.created_at))
        .limit(1)
    )
    last_purchase = result.scalar_one_or_none()

    return CreditBalanceResponse(
        credits=user.credits,
        lastPurchaseAt=last_purchase.created_at.isoformat() if last_purchase else None,
    )


@router.get("/products", response_model=CreditProductListResponse)
async def get_products(
    db: AsyncSession = Depends(get_db),
):
    """
    이용권 상품 목록 조회
    """
    result = await db.execute(
        select(CreditProduct)
        .where(CreditProduct.is_active == True)
        .order_by(CreditProduct.sort_order)
    )
    products = result.scalars().all()

    # 상품이 없으면 기본 상품 반환
    if not products:
        return CreditProductListResponse(
            products=[
                CreditProductResponse(
                    id="report_1",
                    name="리포트 1건",
                    credits=1,
                    price=500,
                    badge=None,
                ),
                CreditProductResponse(
                    id="report_10",
                    name="리포트 10건",
                    credits=10,
                    price=3000,
                    badge="추천",
                ),
                CreditProductResponse(
                    id="report_30",
                    name="리포트 30건",
                    credits=30,
                    price=7000,
                    badge="최저가",
                ),
            ]
        )

    return CreditProductListResponse(
        products=[
            CreditProductResponse(
                id=p.id,
                name=p.name,
                credits=p.credits,
                price=p.price,
                badge=p.badge,
            )
            for p in products
        ]
    )


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_credits(
    request: PurchaseRequest,
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    이용권 구매 (토스 인앱결제 검증)

    1. orderId로 토스 서버에서 결제 상태 검증
    2. 검증 성공 시 이용권 충전
    3. 거래 내역 기록
    """
    # 상품 정보 조회
    product_info = {
        "report_1": {"name": "리포트 1건", "credits": 1, "price": 500},
        "report_10": {"name": "리포트 10건", "credits": 10, "price": 3000},
        "report_30": {"name": "리포트 30건", "credits": 30, "price": 7000},
    }

    # DB에서 상품 조회
    result = await db.execute(
        select(CreditProduct).where(CreditProduct.id == request.productId)
    )
    product = result.scalar_one_or_none()

    if not product:
        if request.productId not in product_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 상품입니다"
            )
        product_data = product_info[request.productId]
    else:
        product_data = {
            "name": product.name,
            "credits": product.credits,
            "price": product.price,
        }

    # 중복 구매 체크 (같은 orderId로 이미 처리됨)
    existing_result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .where(CreditTransaction.order_id == request.orderId)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 처리된 주문입니다"
        )

    # ========== 토스 인앱결제 검증 ==========
    if _toss_client_available and not request.orderId.startswith("mock_"):
        try:
            client = get_toss_client()
            verified, message = await client.verify_purchase(
                user_key=user.toss_user_key,
                order_id=request.orderId,
                expected_sku=request.productId,
            )

            if not verified:
                logger.warning(f"IAP verification failed: user={user.toss_user_key}, order={request.orderId}, reason={message}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"결제 검증 실패: {message}"
                )

            logger.info(f"[Production] IAP verified: user={user.toss_user_key}, order={request.orderId}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"IAP verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="결제 검증 중 오류가 발생했습니다"
            )
    else:
        # 개발 환경: Mock 검증 (orderId가 mock_으로 시작하면 통과)
        if settings.debug:
            logger.info(f"[Sandbox] Skipping IAP verification for: {request.orderId}")
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="결제 검증 서비스를 사용할 수 없습니다"
            )

    # 이용권 충전
    credits_to_add = product_data["credits"]
    user.credits += credits_to_add
    new_balance = user.credits

    # 거래 내역 기록
    transaction = CreditTransaction(
        user_id=user.id,
        transaction_type="purchase",
        amount=credits_to_add,
        balance_after=new_balance,
        product_id=request.productId,
        order_id=request.orderId,
        payment_amount=product_data["price"],
        payment_method="toss_iap",
        receipt_data=request.receiptData,
        description=f"{product_data['name']} 구매",
    )
    db.add(transaction)

    await db.commit()

    logger.info(f"Credits purchased: user={user.toss_user_key}, product={request.productId}, order={request.orderId}, credits={credits_to_add}")

    return PurchaseResponse(
        success=True,
        credits=new_balance,
        message=f"{product_data['name']}이(가) 충전되었습니다",
    )


@router.get("/history", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    limit: int = 20,
    offset: int = 0,
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    이용권 거래 내역 조회
    """
    # 총 개수 조회
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(CreditTransaction.id))
        .where(CreditTransaction.user_id == user.id)
    )
    total = count_result.scalar_one()

    # 거래 내역 조회
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()

    return TransactionHistoryResponse(
        transactions=[
            TransactionResponse(
                id=str(t.id),
                type=t.transaction_type,
                amount=t.amount,
                balanceAfter=t.balance_after,
                description=t.description,
                createdAt=t.created_at.isoformat(),
            )
            for t in transactions
        ],
        total=total,
    )


@router.post("/use")
async def use_credit_for_report(
    company_id: str,
    company_name: str = None,
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    리포트 조회를 위한 이용권 차감

    - 이미 조회한 기업이면 차감하지 않음
    - 이용권이 없으면 에러 반환
    """
    # 이미 조회한 기업인지 확인
    result = await db.execute(
        select(ReportView)
        .where(ReportView.user_id == user.id)
        .where(ReportView.company_id == company_id)
    )
    existing_view = result.scalar_one_or_none()

    if existing_view:
        # 재조회 - 차감 없음
        existing_view.last_viewed_at = datetime.utcnow()
        existing_view.view_count += 1
        await db.commit()

        return {
            "success": True,
            "credits": user.credits,
            "deducted": False,
            "message": "이미 조회한 기업입니다",
        }

    # 이용권 확인
    if user.credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="이용권이 부족합니다"
        )

    # 이용권 차감
    user.credits -= 1
    new_balance = user.credits

    # 거래 내역 기록
    transaction = CreditTransaction(
        user_id=user.id,
        transaction_type="use",
        amount=-1,
        balance_after=new_balance,
        company_id=company_id,
        company_name=company_name,
        description=f"{company_name or company_id} 리포트 조회",
    )
    db.add(transaction)

    # 조회 기록 저장
    report_view = ReportView(
        user_id=user.id,
        company_id=company_id,
        company_name=company_name,
    )
    db.add(report_view)

    await db.commit()

    logger.info(f"Credit used: user={user.toss_user_key}, company={company_id}, remaining={new_balance}")

    return {
        "success": True,
        "credits": new_balance,
        "deducted": True,
        "message": "리포트 조회 권한이 확인되었습니다",
    }


@router.get("/viewed-companies")
async def get_viewed_companies(
    limit: int = 50,
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조회한 기업 목록 (재조회 가능)
    """
    result = await db.execute(
        select(ReportView)
        .where(ReportView.user_id == user.id)
        .order_by(desc(ReportView.last_viewed_at))
        .limit(limit)
    )
    views = result.scalars().all()

    return {
        "companies": [
            {
                "companyId": v.company_id,
                "companyName": v.company_name,
                "firstViewedAt": v.first_viewed_at.isoformat(),
                "lastViewedAt": v.last_viewed_at.isoformat(),
                "viewCount": v.view_count,
            }
            for v in views
        ],
        "total": len(views),
    }
