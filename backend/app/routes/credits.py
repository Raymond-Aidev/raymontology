"""
이용권(Credits) API 라우터

토스 인앱결제(IAP) 검증을 통한 이용권 구매 처리.

ACID 원칙 준수:
- Atomicity: 단일 트랜잭션으로 이용권 충전/차감 + 거래내역 기록
- Consistency: 잔액 마이너스 방지, 무제한 이용권 특수 처리
- Isolation: SELECT FOR UPDATE로 Race Condition 방지
- Durability: PostgreSQL WAL 기반 지속성 보장
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import logging

# ============================================================================
# 상수 정의
# ============================================================================

# 조회 기록 보관 기간 (일)
REPORT_VIEW_RETENTION_DAYS = 30

# 무제한 이용권 상수 (P3: 매직넘버 상수화)
UNLIMITED_CREDITS = -1

from app.database import get_db
from app.models.toss_users import TossUser, CreditTransaction, CreditProduct, ReportView
from app.config import settings

# mTLS 클라이언트 import (인앱결제 검증용)
_toss_client_available = False
TossAPIError = None  # 방어적 초기화

try:
    from app.services.toss_api_client import get_toss_client, TossAPIClient, TossAPIError
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

    # 상품이 없으면 기본 상품 반환 (2026-01-07 가격 개편)
    if not products:
        return CreditProductListResponse(
            products=[
                CreditProductResponse(
                    id="report_10",
                    name="리포트 10건",
                    credits=10,
                    price=1000,
                    badge=None,
                ),
                CreditProductResponse(
                    id="report_30",
                    name="리포트 30건",
                    credits=30,
                    price=2000,
                    badge="추천",
                ),
                CreditProductResponse(
                    id="report_unlimited",
                    name="무제한 이용권",
                    credits=UNLIMITED_CREDITS,
                    price=10000,
                    badge="BEST",
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

    ACID 준수:
    - P1: SELECT FOR UPDATE로 사용자 행 잠금 (Race Condition 방지)
    - P1: 중복 구매 체크도 잠금 상태에서 수행
    - P3: UNLIMITED_CREDITS 상수 사용
    """
    # 상품 정보 조회 (2026-01-07 가격 개편)
    # - 10건 1,000원, 30건 2,000원, 무제한 10,000원
    product_info = {
        "report_10": {"name": "리포트 10건", "credits": 10, "price": 1000},
        "report_30": {"name": "리포트 30건", "credits": 30, "price": 2000},
        "report_unlimited": {"name": "무제한 이용권", "credits": UNLIMITED_CREDITS, "price": 10000},
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

    # ========== P1: SELECT FOR UPDATE로 사용자 행 잠금 ==========
    # Race Condition 방지: 동시 구매 요청 시 중복 처리 방지
    locked_user_result = await db.execute(
        select(TossUser)
        .where(TossUser.id == user.id)
        .with_for_update()  # 행 잠금
    )
    locked_user = locked_user_result.scalar_one()

    # 중복 구매 체크 (잠금 상태에서 수행 - Race Condition 방지)
    existing_result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == locked_user.id)
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
                user_key=locked_user.toss_user_key,
                order_id=request.orderId,
                expected_sku=request.productId,
            )

            if not verified:
                logger.warning(f"IAP verification failed: user={locked_user.toss_user_key}, order={request.orderId}, reason={message}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"결제 검증 실패: {message}"
                )

            logger.info(f"[Production] IAP verified: user={locked_user.toss_user_key}, order={request.orderId}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"IAP verification error: {e}")
            # TossAPIError인 경우 상세 에러 정보 반환
            if TossAPIError and isinstance(e, TossAPIError):
                raise HTTPException(
                    status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
                    detail=f"결제 검증 오류: [{e.error_code}] {e.reason}"
                )
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

    # ========== P3: UNLIMITED_CREDITS 상수 사용 ==========
    # 이용권 충전
    credits_to_add = product_data["credits"]
    if credits_to_add == UNLIMITED_CREDITS:
        # 무제한 이용권: credits를 UNLIMITED_CREDITS로 설정
        locked_user.credits = UNLIMITED_CREDITS
        new_balance = UNLIMITED_CREDITS
    else:
        locked_user.credits += credits_to_add
        new_balance = locked_user.credits

    # 거래 내역 기록
    transaction = CreditTransaction(
        user_id=locked_user.id,
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

    # 단일 트랜잭션으로 커밋 (Atomicity 보장)
    await db.commit()

    logger.info(f"Credits purchased: user={locked_user.toss_user_key}, product={request.productId}, order={request.orderId}, credits={credits_to_add}")

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

    ACID 준수:
    - P1: SELECT FOR UPDATE로 Race Condition 방지
    - P2: 조기 커밋 제거, 단일 트랜잭션으로 처리
    - P3: UNLIMITED_CREDITS 상수 사용
    """
    now = datetime.utcnow()

    # ========== P1: SELECT FOR UPDATE로 사용자 행 잠금 ==========
    # Race Condition 방지: 동시 요청 시 이중 차감 방지
    locked_user_result = await db.execute(
        select(TossUser)
        .where(TossUser.id == user.id)
        .with_for_update()  # 행 잠금
    )
    locked_user = locked_user_result.scalar_one()

    # 이미 조회한 기업인지 확인
    result = await db.execute(
        select(ReportView)
        .where(ReportView.user_id == locked_user.id)
        .where(ReportView.company_id == company_id)
    )
    existing_view = result.scalar_one_or_none()

    if existing_view:
        # 만료 여부 확인 (expires_at이 NULL이면 무제한 - 레거시)
        is_expired = existing_view.expires_at and existing_view.expires_at < now

        if not is_expired:
            # ========== P2: 재조회도 단일 트랜잭션으로 처리 ==========
            # 조기 커밋 제거: view_count 업데이트를 최종 커밋에 포함
            existing_view.last_viewed_at = now
            existing_view.view_count += 1
            # 커밋은 아래에서 한 번만 수행
            await db.commit()

            return {
                "success": True,
                "credits": locked_user.credits,
                "deducted": False,
                "message": "이미 조회한 기업입니다",
                "expiresAt": existing_view.expires_at.isoformat() if existing_view.expires_at else None,
            }
        else:
            # 만료됨 - 새로 차감 필요, 기존 기록 삭제
            await db.delete(existing_view)
            await db.flush()
            # 아래 로직에서 새로 차감 및 기록 생성

    # ========== P3: UNLIMITED_CREDITS 상수 사용 ==========
    # 이용권 확인
    if locked_user.credits == 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="이용권이 부족합니다"
        )

    # 이용권 차감 (무제한이면 차감 안 함)
    if locked_user.credits == UNLIMITED_CREDITS:
        # 무제한 이용권: 차감 없음
        new_balance = UNLIMITED_CREDITS
    else:
        locked_user.credits -= 1
        new_balance = locked_user.credits

    # 거래 내역 기록
    is_unlimited = (new_balance == UNLIMITED_CREDITS)
    transaction = CreditTransaction(
        user_id=locked_user.id,
        transaction_type="use",
        amount=0 if is_unlimited else -1,
        balance_after=new_balance,
        company_id=company_id,
        company_name=company_name,
        description=f"{company_name or company_id} 리포트 조회" + (" (무제한)" if is_unlimited else ""),
    )
    db.add(transaction)

    # 조회 기록 저장 (30일 보관)
    expires_at = datetime.utcnow() + timedelta(days=REPORT_VIEW_RETENTION_DAYS)
    report_view = ReportView(
        user_id=locked_user.id,
        company_id=company_id,
        company_name=company_name,
        expires_at=expires_at,
    )
    db.add(report_view)

    # 단일 트랜잭션으로 커밋 (Atomicity 보장)
    await db.commit()

    logger.info(f"Credit used: user={locked_user.toss_user_key}, company={company_id}, remaining={new_balance}")

    return {
        "success": True,
        "credits": new_balance,
        "deducted": True,
        "message": "리포트 조회 권한이 확인되었습니다",
    }


@router.get("/viewed-companies")
async def get_viewed_companies(
    limit: int = 50,
    include_expired: bool = False,
    user: TossUser = Depends(get_current_toss_user),
    db: AsyncSession = Depends(get_db),
):
    """
    조회한 기업 목록 (재조회 가능)

    - 30일 보관 기간 적용
    - include_expired=True 시 만료된 기업도 포함
    """
    now = datetime.utcnow()

    query = select(ReportView).where(ReportView.user_id == user.id)

    if not include_expired:
        # 만료되지 않은 기록만 (expires_at이 NULL이거나 미래)
        query = query.where(
            or_(
                ReportView.expires_at.is_(None),  # 레거시 데이터 (무제한)
                ReportView.expires_at > now
            )
        )

    result = await db.execute(
        query
        .order_by(desc(ReportView.last_viewed_at))
        .limit(limit)
    )
    views = result.scalars().all()

    # 응답 데이터 구성 (예외 방지를 위해 개별 처리)
    companies_data = []
    for v in views:
        try:
            # expires_at이 timezone-aware인 경우 처리
            expires_at_dt = v.expires_at
            if expires_at_dt:
                # timezone-aware datetime을 naive로 변환 (UTC 기준)
                if hasattr(expires_at_dt, 'tzinfo') and expires_at_dt.tzinfo is not None:
                    expires_at_dt = expires_at_dt.replace(tzinfo=None)
                is_expired = expires_at_dt < now
                days_remaining = max(0, (expires_at_dt - now).days)
            else:
                is_expired = False
                days_remaining = None

            companies_data.append({
                "companyId": v.company_id,
                "companyName": v.company_name,
                "firstViewedAt": v.first_viewed_at.isoformat() if v.first_viewed_at else None,
                "lastViewedAt": v.last_viewed_at.isoformat() if v.last_viewed_at else None,
                "viewCount": v.view_count or 1,
                "expiresAt": v.expires_at.isoformat() if v.expires_at else None,
                "isExpired": is_expired,
                "daysRemaining": days_remaining,
            })
        except Exception as e:
            logger.error(f"Error processing view {v.id}: {e}")
            # 에러 발생 시에도 기본 데이터 포함
            companies_data.append({
                "companyId": v.company_id,
                "companyName": v.company_name,
                "firstViewedAt": None,
                "lastViewedAt": None,
                "viewCount": 1,
                "expiresAt": None,
                "isExpired": False,
                "daysRemaining": None,
            })

    return {
        "companies": companies_data,
        "total": len(companies_data),
        "retentionDays": REPORT_VIEW_RETENTION_DAYS,
    }
