"""
Admin Routes - 관리자 전용 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid as uuid_module

from app.database import get_db
from app.models.users import User
from app.models.site_settings import SiteSetting
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# Schemas
# ============================================================================

class SiteSettingUpdate(BaseModel):
    """사이트 설정 업데이트 요청"""
    key: str
    value: str


class SiteSettingResponse(BaseModel):
    """사이트 설정 응답"""
    key: str
    value: str
    updated_at: datetime


class UserListItem(BaseModel):
    """사용자 목록 항목"""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    oauth_provider: Optional[str]
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    last_login: Optional[datetime]


class SubscriptionUpdateRequest(BaseModel):
    """이용권 업데이트 요청"""
    tier: Literal['free', 'light', 'max']  # 2종 플랜: Light 3,000원/월, Max 30,000원/월
    duration_days: Optional[int] = None  # None이면 무기한
    memo: Optional[str] = None  # 부여 사유


class UserListResponse(BaseModel):
    """사용자 목록 응답"""
    users: List[UserListItem]
    total: int


class StatsResponse(BaseModel):
    """통계 응답"""
    total_users: int
    active_users: int
    oauth_users: int
    superusers: int


# ============================================================================
# Helper: Admin Check
# ============================================================================

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 권한 확인"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


# ============================================================================
# Site Settings Endpoints
# ============================================================================

@router.get("/settings/{key}", response_model=SiteSettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """사이트 설정 조회 (관리자 전용)"""
    result = await db.execute(
        select(SiteSetting).where(SiteSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        # 기본값 반환
        return SiteSettingResponse(
            key=key,
            value="",
            updated_at=datetime.utcnow()
        )

    return SiteSettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at
    )


@router.put("/settings", response_model=SiteSettingResponse)
async def update_setting(
    data: SiteSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사이트 설정 업데이트 (관리자 전용)"""
    try:
        result = await db.execute(
            select(SiteSetting).where(SiteSetting.key == data.key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            # 기존 설정 업데이트
            setting.value = data.value
            setting.updated_by = current_user.id
        else:
            # 새 설정 생성
            setting = SiteSetting(
                key=data.key,
                value=data.value,
                updated_by=current_user.id
            )
            db.add(setting)

        await db.commit()
        await db.refresh(setting)

        logger.info(f"Setting '{data.key}' updated by {current_user.email}")

        return SiteSettingResponse(
            key=setting.key,
            value=setting.value,
            updated_at=setting.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to update setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="설정 업데이트에 실패했습니다."
        )


# ============================================================================
# Public Settings Endpoint (for terms/privacy pages)
# ============================================================================

@router.get("/public/settings/{key}")
async def get_public_setting(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """공개 사이트 설정 조회 (이용약관, 개인정보처리방침)"""
    if key not in ["terms", "privacy"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설정을 찾을 수 없습니다."
        )

    result = await db.execute(
        select(SiteSetting).where(SiteSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        # 기본 내용 반환
        default_content = {
            "terms": "# 이용약관\n\n이용약관 내용이 아직 등록되지 않았습니다.",
            "privacy": "# 개인정보 처리방침\n\n개인정보 처리방침 내용이 아직 등록되지 않았습니다."
        }
        return {"key": key, "value": default_content.get(key, "")}

    return {"key": setting.key, "value": setting.value}


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """사용자 목록 조회 (관리자 전용)"""
    # 전체 수 조회
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    # 사용자 목록 조회
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return UserListResponse(
        users=[
            UserListItem(
                id=str(user.id),
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                oauth_provider=user.oauth_provider,
                subscription_tier=user.subscription_tier or 'free',
                subscription_expires_at=user.subscription_expires_at,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ],
        total=total
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """통계 조회 (관리자 전용)"""
    # 전체 사용자 수
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar()

    # 활성 사용자 수
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_result.scalar()

    # OAuth 사용자 수
    oauth_result = await db.execute(
        select(func.count(User.id)).where(User.oauth_provider.isnot(None))
    )
    oauth_users = oauth_result.scalar()

    # 관리자 수
    superuser_result = await db.execute(
        select(func.count(User.id)).where(User.is_superuser == True)
    )
    superusers = superuser_result.scalar()

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        oauth_users=oauth_users,
        superusers=superusers
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사용자 활성/비활성 토글 (관리자 전용)"""
    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 사용자 ID 형식입니다."
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 자기 자신은 비활성화 불가
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 비활성화할 수 없습니다."
        )

    user.is_active = not user.is_active
    await db.commit()

    return {"message": f"사용자 상태가 {'활성화' if user.is_active else '비활성화'}되었습니다."}


@router.patch("/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: str,
    data: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사용자 이용권 업데이트 (관리자 전용)"""
    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 사용자 ID 형식입니다."
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 이용권 업데이트
    old_tier = user.subscription_tier
    user.subscription_tier = data.tier

    if data.tier == 'free':
        # 무료로 변경 시 만료일 제거
        user.subscription_expires_at = None
    elif data.duration_days is None:
        # 무기한
        user.subscription_expires_at = None
    else:
        # 기간 설정
        user.subscription_expires_at = datetime.utcnow() + timedelta(days=data.duration_days)

    await db.commit()

    tier_names = {
        'free': '무료',
        'light': '라이트',
        'max': '맥스'
    }

    expires_msg = "무기한" if user.subscription_expires_at is None else f"{data.duration_days}일"
    memo_msg = f" (사유: {data.memo})" if data.memo else ""

    logger.info(f"Subscription updated for {user.email}: {old_tier} -> {data.tier} ({expires_msg}) by {current_user.email}{memo_msg}")

    return {
        "message": f"이용권이 {tier_names.get(data.tier, data.tier)} ({expires_msg})으로 설정되었습니다.",
        "subscription_tier": user.subscription_tier,
        "subscription_expires_at": user.subscription_expires_at
    }


# ============================================================================
# Data Quality Monitoring Schemas
# ============================================================================

class DataQualityIssue(BaseModel):
    """데이터 품질 이슈 항목"""
    issue_type: str
    description: str
    record_count: int
    company_count: int
    severity: Literal['critical', 'warning', 'info']
    sample_data: Optional[List[Dict[str, Any]]] = None


class TableQualityStats(BaseModel):
    """테이블별 데이터 품질 통계"""
    table_name: str
    total_records: int
    issues: List[DataQualityIssue]
    quality_score: float  # 0-100
    last_checked: datetime


class DataQualityResponse(BaseModel):
    """데이터 품질 모니터링 전체 응답"""
    overall_score: float
    tables: List[TableQualityStats]
    summary: Dict[str, int]  # critical, warning, info counts


class DataCleanupRequest(BaseModel):
    """데이터 정제 요청"""
    table_name: str
    issue_type: str
    dry_run: bool = True  # 기본값: 시뮬레이션만


class DataCleanupResponse(BaseModel):
    """데이터 정제 응답"""
    table_name: str
    issue_type: str
    affected_records: int
    dry_run: bool
    message: str


# ============================================================================
# Data Quality Monitoring Endpoints
# ============================================================================

@router.get("/data-quality", response_model=DataQualityResponse)
async def get_data_quality_report(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    데이터 품질 모니터링 보고서 조회 (관리자 전용)

    주요 체크 항목:
    1. major_shareholders: 숫자로 시작하는 주주명, 재무항목명, 비정상 주식수
    2. officers: 이름 형식 오류, 직위 누락
    3. convertible_bonds: 금액 이상치, 날짜 오류
    """
    tables_stats = []
    summary = {"critical": 0, "warning": 0, "info": 0}

    # ========== 1. major_shareholders 품질 검사 ==========
    shareholder_issues = []

    # 1.1 전체 레코드 수
    total_result = await db.execute(text("SELECT COUNT(*) FROM major_shareholders"))
    shareholder_total = total_result.scalar()

    # 1.2 숫자로 시작하는 주주명
    numeric_name_result = await db.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT company_id)
        FROM major_shareholders
        WHERE shareholder_name ~ '^[0-9]'
    """))
    row = numeric_name_result.fetchone()
    numeric_count, numeric_companies = row[0], row[1]

    if numeric_count > 0:
        # 샘플 데이터 조회
        sample_result = await db.execute(text("""
            SELECT id, shareholder_name, share_count, company_id
            FROM major_shareholders
            WHERE shareholder_name ~ '^[0-9]'
            LIMIT 5
        """))
        samples = [dict(row._mapping) for row in sample_result.fetchall()]

        shareholder_issues.append(DataQualityIssue(
            issue_type="numeric_shareholder_name",
            description="주주명이 숫자로 시작 (파싱 오류 추정)",
            record_count=numeric_count,
            company_count=numeric_companies,
            severity="critical" if numeric_count > 100 else "warning",
            sample_data=samples
        ))
        summary["critical" if numeric_count > 100 else "warning"] += 1

    # 1.3 재무항목 이름이 주주명인 경우
    financial_terms = [
        '선급금', '장기대여금', '유동성사채', '단기차입금', '신탁 체결',
        '채권형', '금융자산', '이자비용', '감가상각비', '매출원가',
        '판관비', '자본금', '자본잉여금', '이익잉여금', '미수금',
        '미지급금', '예수금', '가수금', '선수금', '퇴직급여'
    ]
    terms_str = "', '".join(financial_terms)
    financial_name_result = await db.execute(text(f"""
        SELECT COUNT(*), COUNT(DISTINCT company_id)
        FROM major_shareholders
        WHERE shareholder_name IN ('{terms_str}')
    """))
    row = financial_name_result.fetchone()
    financial_count, financial_companies = row[0], row[1]

    if financial_count > 0:
        shareholder_issues.append(DataQualityIssue(
            issue_type="financial_item_name",
            description="주주명이 재무항목명 (파싱 오류)",
            record_count=financial_count,
            company_count=financial_companies,
            severity="critical",
            sample_data=None
        ))
        summary["critical"] += 1

    # 1.4 비정상적으로 큰 주식수 (100억주 초과)
    abnormal_share_result = await db.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT company_id)
        FROM major_shareholders
        WHERE share_count > 10000000000
    """))
    row = abnormal_share_result.fetchone()
    abnormal_count, abnormal_companies = row[0], row[1]

    if abnormal_count > 0:
        shareholder_issues.append(DataQualityIssue(
            issue_type="abnormal_share_count",
            description="주식수 100억주 초과 (이상치)",
            record_count=abnormal_count,
            company_count=abnormal_companies,
            severity="warning",
            sample_data=None
        ))
        summary["warning"] += 1

    # 1.5 NULL share_ratio
    null_ratio_result = await db.execute(text("""
        SELECT COUNT(*) FROM major_shareholders WHERE share_ratio IS NULL
    """))
    null_ratio_count = null_ratio_result.scalar()

    if null_ratio_count > 0:
        shareholder_issues.append(DataQualityIssue(
            issue_type="null_share_ratio",
            description="지분율 NULL",
            record_count=null_ratio_count,
            company_count=0,  # 집계하지 않음
            severity="info",
            sample_data=None
        ))
        summary["info"] += 1

    # 품질 점수 계산 (문제 레코드 비율 기반)
    problem_count = numeric_count + financial_count + abnormal_count
    quality_score = max(0, 100 - (problem_count / max(shareholder_total, 1)) * 100)

    tables_stats.append(TableQualityStats(
        table_name="major_shareholders",
        total_records=shareholder_total,
        issues=shareholder_issues,
        quality_score=round(quality_score, 1),
        last_checked=datetime.utcnow()
    ))

    # ========== 2. officers 품질 검사 ==========
    officer_issues = []

    total_result = await db.execute(text("SELECT COUNT(*) FROM officers"))
    officer_total = total_result.scalar()

    # 2.1 이름이 없는 임원
    null_name_result = await db.execute(text("""
        SELECT COUNT(*) FROM officers
        WHERE name IS NULL OR TRIM(name) = ''
    """))
    null_name_count = null_name_result.scalar()

    if null_name_count > 0:
        officer_issues.append(DataQualityIssue(
            issue_type="null_officer_name",
            description="임원 이름 NULL 또는 빈 문자열",
            record_count=null_name_count,
            company_count=0,
            severity="warning",
            sample_data=None
        ))
        summary["warning"] += 1

    # 2.2 직위가 없는 임원 (officer_positions 기준)
    no_position_result = await db.execute(text("""
        SELECT COUNT(*) FROM officers o
        WHERE NOT EXISTS (
            SELECT 1 FROM officer_positions op WHERE op.officer_id = o.id
        )
    """))
    no_position_count = no_position_result.scalar()

    if no_position_count > 0:
        officer_issues.append(DataQualityIssue(
            issue_type="no_position",
            description="직위 정보 없는 임원",
            record_count=no_position_count,
            company_count=0,
            severity="info",
            sample_data=None
        ))
        summary["info"] += 1

    officer_quality = max(0, 100 - (null_name_count / max(officer_total, 1)) * 100)

    tables_stats.append(TableQualityStats(
        table_name="officers",
        total_records=officer_total,
        issues=officer_issues,
        quality_score=round(officer_quality, 1),
        last_checked=datetime.utcnow()
    ))

    # ========== 3. convertible_bonds 품질 검사 ==========
    cb_issues = []

    total_result = await db.execute(text("SELECT COUNT(*) FROM convertible_bonds"))
    cb_total = total_result.scalar()

    # 3.1 발행금액 0 또는 NULL
    zero_amount_result = await db.execute(text("""
        SELECT COUNT(*) FROM convertible_bonds
        WHERE issue_amount IS NULL OR issue_amount <= 0
    """))
    zero_amount_count = zero_amount_result.scalar()

    if zero_amount_count > 0:
        cb_issues.append(DataQualityIssue(
            issue_type="zero_issue_amount",
            description="발행금액 0 또는 NULL",
            record_count=zero_amount_count,
            company_count=0,
            severity="warning",
            sample_data=None
        ))
        summary["warning"] += 1

    cb_quality = max(0, 100 - (zero_amount_count / max(cb_total, 1)) * 100)

    tables_stats.append(TableQualityStats(
        table_name="convertible_bonds",
        total_records=cb_total,
        issues=cb_issues,
        quality_score=round(cb_quality, 1),
        last_checked=datetime.utcnow()
    ))

    # 전체 품질 점수 (가중 평균)
    total_records = sum(t.total_records for t in tables_stats)
    if total_records > 0:
        overall_score = sum(
            t.quality_score * t.total_records for t in tables_stats
        ) / total_records
    else:
        overall_score = 100.0

    return DataQualityResponse(
        overall_score=round(overall_score, 1),
        tables=tables_stats,
        summary=summary
    )


@router.post("/data-quality/cleanup", response_model=DataCleanupResponse)
async def cleanup_data_quality_issue(
    request: DataCleanupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    데이터 품질 이슈 정제 (관리자 전용)

    dry_run=True: 삭제될 레코드 수만 반환 (실제 삭제 안 함)
    dry_run=False: 실제로 레코드 삭제
    """
    affected = 0

    if request.table_name == "major_shareholders":
        if request.issue_type == "numeric_shareholder_name":
            if request.dry_run:
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM major_shareholders
                    WHERE shareholder_name ~ '^[0-9]'
                """))
                affected = result.scalar()
            else:
                result = await db.execute(text("""
                    DELETE FROM major_shareholders
                    WHERE shareholder_name ~ '^[0-9]'
                """))
                affected = result.rowcount
                await db.commit()
                logger.info(f"Cleaned up {affected} numeric shareholder names by {current_user.email}")

        elif request.issue_type == "financial_item_name":
            financial_terms = [
                '선급금', '장기대여금', '유동성사채', '단기차입금', '신탁 체결',
                '채권형', '금융자산', '이자비용', '감가상각비', '매출원가',
                '판관비', '자본금', '자본잉여금', '이익잉여금', '미수금',
                '미지급금', '예수금', '가수금', '선수금', '퇴직급여'
            ]
            terms_str = "', '".join(financial_terms)

            if request.dry_run:
                result = await db.execute(text(f"""
                    SELECT COUNT(*) FROM major_shareholders
                    WHERE shareholder_name IN ('{terms_str}')
                """))
                affected = result.scalar()
            else:
                result = await db.execute(text(f"""
                    DELETE FROM major_shareholders
                    WHERE shareholder_name IN ('{terms_str}')
                """))
                affected = result.rowcount
                await db.commit()
                logger.info(f"Cleaned up {affected} financial item names by {current_user.email}")

        elif request.issue_type == "abnormal_share_count":
            if request.dry_run:
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM major_shareholders
                    WHERE share_count > 10000000000
                """))
                affected = result.scalar()
            else:
                result = await db.execute(text("""
                    DELETE FROM major_shareholders
                    WHERE share_count > 10000000000
                """))
                affected = result.rowcount
                await db.commit()
                logger.info(f"Cleaned up {affected} abnormal share counts by {current_user.email}")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown issue type: {request.issue_type}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cleanup not supported for table: {request.table_name}"
        )

    return DataCleanupResponse(
        table_name=request.table_name,
        issue_type=request.issue_type,
        affected_records=affected,
        dry_run=request.dry_run,
        message=f"{'시뮬레이션: ' if request.dry_run else ''}{affected}개 레코드 {'삭제 예정' if request.dry_run else '삭제 완료'}"
    )


# ============================================================================
# Database Tables Overview (SCHEMA_REGISTRY 기반)
# ============================================================================

class TableStats(BaseModel):
    """테이블 통계"""
    name: str
    display_name: str
    record_count: int
    description: str
    category: str  # core, financial, risk, user, system


class DatabaseOverviewResponse(BaseModel):
    """데이터베이스 전체 현황"""
    total_tables: int
    total_records: int
    tables: List[TableStats]
    last_updated: datetime


@router.get("/database-overview", response_model=DatabaseOverviewResponse)
async def get_database_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    데이터베이스 전체 테이블 현황 조회 (관리자 전용)
    SCHEMA_REGISTRY 기반으로 모든 데이터 테이블의 레코드 수 반환
    """
    # 테이블 정의 (SCHEMA_REGISTRY 기반)
    table_definitions = [
        # Core Tables
        {"name": "companies", "display_name": "기업", "description": "KOSPI/KOSDAQ 상장 기업", "category": "core"},
        {"name": "officers", "display_name": "임원", "description": "기업 임원 정보", "category": "core"},
        {"name": "officer_positions", "display_name": "임원 직위", "description": "임원-기업 연결 테이블", "category": "core"},
        {"name": "disclosures", "display_name": "공시", "description": "DART 공시 문서", "category": "core"},
        {"name": "major_shareholders", "display_name": "대주주", "description": "최대주주 및 특수관계인", "category": "core"},
        {"name": "affiliates", "display_name": "계열사", "description": "계열회사 관계", "category": "core"},

        # Financial Tables
        {"name": "financial_statements", "display_name": "재무제표", "description": "손익계산서/재무상태표 요약", "category": "financial"},
        {"name": "financial_details", "display_name": "상세 재무", "description": "RaymondsIndex 계산용 상세 재무", "category": "financial"},
        {"name": "convertible_bonds", "display_name": "전환사채", "description": "CB/BW 발행 정보", "category": "financial"},
        {"name": "cb_subscribers", "display_name": "CB 인수자", "description": "전환사채 인수자 정보", "category": "financial"},
        {"name": "stock_prices", "display_name": "주가", "description": "일별 주가 데이터", "category": "financial"},

        # Risk & Index Tables
        {"name": "risk_signals", "display_name": "위험신호", "description": "기업별 위험 신호", "category": "risk"},
        {"name": "risk_scores", "display_name": "위험점수", "description": "기업별 종합 위험 점수", "category": "risk"},
        {"name": "raymonds_index", "display_name": "RaymondsIndex", "description": "자본 배분 효율성 지수", "category": "risk"},

        # User Tables
        {"name": "users", "display_name": "사용자", "description": "회원 계정", "category": "user"},
        {"name": "user_query_usage", "display_name": "조회 이력", "description": "사용자 조회 제한 추적", "category": "user"},

        # System Tables
        {"name": "page_contents", "display_name": "페이지 콘텐츠", "description": "CMS 페이지 내용", "category": "system"},
        {"name": "site_settings", "display_name": "사이트 설정", "description": "전역 설정 값", "category": "system"},
    ]

    tables = []
    total_records = 0

    for tbl in table_definitions:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {tbl['name']}"))
            count = result.scalar() or 0
        except Exception:
            count = 0

        total_records += count
        tables.append(TableStats(
            name=tbl["name"],
            display_name=tbl["display_name"],
            record_count=count,
            description=tbl["description"],
            category=tbl["category"]
        ))

    return DatabaseOverviewResponse(
        total_tables=len(tables),
        total_records=total_records,
        tables=tables,
        last_updated=datetime.utcnow()
    )


@router.get("/data-quality/shareholder-issues")
async def get_shareholder_issues_detail(
    issue_type: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    대주주 데이터 이슈 상세 목록 조회 (관리자 전용)

    issue_type:
    - numeric_shareholder_name: 숫자로 시작하는 주주명
    - financial_item_name: 재무항목명
    - abnormal_share_count: 비정상 주식수
    """
    if issue_type == "numeric_shareholder_name":
        query = text("""
            SELECT
                ms.id,
                ms.shareholder_name,
                ms.share_count,
                ms.share_ratio,
                c.name as company_name,
                c.id as company_id
            FROM major_shareholders ms
            JOIN companies c ON ms.company_id = c.id
            WHERE ms.shareholder_name ~ '^[0-9]'
            ORDER BY ms.id
            LIMIT :limit OFFSET :offset
        """)
        count_query = text("""
            SELECT COUNT(*) FROM major_shareholders
            WHERE shareholder_name ~ '^[0-9]'
        """)
    elif issue_type == "financial_item_name":
        financial_terms = [
            '선급금', '장기대여금', '유동성사채', '단기차입금', '신탁 체결',
            '채권형', '금융자산', '이자비용', '감가상각비', '매출원가'
        ]
        terms_str = "', '".join(financial_terms)
        query = text(f"""
            SELECT
                ms.id,
                ms.shareholder_name,
                ms.share_count,
                ms.share_ratio,
                c.name as company_name,
                c.id as company_id
            FROM major_shareholders ms
            JOIN companies c ON ms.company_id = c.id
            WHERE ms.shareholder_name IN ('{terms_str}')
            ORDER BY ms.id
            LIMIT :limit OFFSET :offset
        """)
        count_query = text(f"""
            SELECT COUNT(*) FROM major_shareholders
            WHERE shareholder_name IN ('{terms_str}')
        """)
    elif issue_type == "abnormal_share_count":
        query = text("""
            SELECT
                ms.id,
                ms.shareholder_name,
                ms.share_count,
                ms.share_ratio,
                c.name as company_name,
                c.id as company_id
            FROM major_shareholders ms
            JOIN companies c ON ms.company_id = c.id
            WHERE ms.share_count > 10000000000
            ORDER BY ms.share_count DESC
            LIMIT :limit OFFSET :offset
        """)
        count_query = text("""
            SELECT COUNT(*) FROM major_shareholders
            WHERE share_count > 10000000000
        """)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown issue type: {issue_type}"
        )

    result = await db.execute(query, {"limit": limit, "offset": offset})
    items = [dict(row._mapping) for row in result.fetchall()]

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "issue_type": issue_type,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }
