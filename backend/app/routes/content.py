"""
Content Routes - 페이지 콘텐츠 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
import uuid
import os
import aiofiles
from datetime import datetime

from app.database import get_db
from app.models.content import PageContent, DEFAULT_ABOUT_CONTENT, IMAGE_SIZE_RECOMMENDATIONS
from app.models.users import User
from app.core.security import get_current_user

router = APIRouter(prefix="/api/content", tags=["content"])


# ============================================================================
# 공개 API (인증 불필요)
# ============================================================================

@router.get("/{page}")
async def get_page_content(
    page: str,
    db: AsyncSession = Depends(get_db)
):
    """
    페이지 콘텐츠 조회 (공개)
    DB에 저장된 값이 없으면 기본값 반환
    """
    # DB에서 해당 페이지의 모든 콘텐츠 조회
    result = await db.execute(
        select(PageContent).where(PageContent.page == page)
    )
    db_contents = result.scalars().all()

    # 기본값 로드
    if page == "about":
        content = _deep_copy_dict(DEFAULT_ABOUT_CONTENT)
    else:
        content = {}

    # DB 값으로 오버라이드
    for item in db_contents:
        if item.section not in content:
            content[item.section] = {}
        content[item.section][item.field] = item.value

    return {
        "page": page,
        "content": content,
        "image_sizes": IMAGE_SIZE_RECOMMENDATIONS
    }


# ============================================================================
# 관리자 API (인증 필요)
# ============================================================================

@router.put("/{page}/{section}/{field}")
async def update_content(
    page: str,
    section: str,
    field: str,
    body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    콘텐츠 업데이트 (관리자 전용)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )

    value = body.get("value", "")

    # 기존 레코드 조회
    result = await db.execute(
        select(PageContent).where(
            PageContent.page == page,
            PageContent.section == section,
            PageContent.field == field
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = value
        existing.updated_at = datetime.utcnow()
    else:
        new_content = PageContent(
            page=page,
            section=section,
            field=field,
            value=value
        )
        db.add(new_content)

    await db.commit()

    return {
        "success": True,
        "page": page,
        "section": section,
        "field": field,
        "value": value
    }


@router.post("/{page}/{section}/image")
async def upload_image(
    page: str,
    section: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    이미지 업로드 (관리자 전용)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )

    # 파일 유효성 검사
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 업로드 가능합니다."
        )

    # 파일 크기 제한 (5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 크기는 5MB 이하여야 합니다."
        )

    # 파일명 생성
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{page}_{section}_{uuid.uuid4().hex[:8]}.{ext}"

    # 저장 경로
    upload_dir = "uploads/content"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)

    # 파일 저장
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 이미지 URL
    image_url = f"/uploads/content/{filename}"

    # DB에 저장
    result = await db.execute(
        select(PageContent).where(
            PageContent.page == page,
            PageContent.section == section,
            PageContent.field == "image"
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # 기존 이미지 파일 삭제 (선택적)
        if existing.value and existing.value.startswith("/uploads/"):
            old_path = existing.value.lstrip("/")
            if os.path.exists(old_path):
                os.remove(old_path)
        existing.value = image_url
        existing.updated_at = datetime.utcnow()
    else:
        new_content = PageContent(
            page=page,
            section=section,
            field="image",
            value=image_url
        )
        db.add(new_content)

    await db.commit()

    # 권장 사이즈 정보
    size_key = f"{section}.image"
    recommended_size = IMAGE_SIZE_RECOMMENDATIONS.get(size_key)

    return {
        "success": True,
        "image_url": image_url,
        "filename": filename,
        "recommended_size": recommended_size
    }


@router.delete("/{page}/{section}/image")
async def delete_image(
    page: str,
    section: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    이미지 삭제 (관리자 전용)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )

    result = await db.execute(
        select(PageContent).where(
            PageContent.page == page,
            PageContent.section == section,
            PageContent.field == "image"
        )
    )
    existing = result.scalar_one_or_none()

    if existing and existing.value:
        # 파일 삭제
        if existing.value.startswith("/uploads/"):
            file_path = existing.value.lstrip("/")
            if os.path.exists(file_path):
                os.remove(file_path)

        # DB 레코드 삭제
        await db.delete(existing)
        await db.commit()

    return {"success": True}


@router.get("/admin/sections")
async def get_editable_sections(
    current_user: User = Depends(get_current_user)
):
    """
    편집 가능한 섹션 목록 반환 (관리자 전용)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )

    sections = []

    # About 페이지 섹션
    for section_id, fields in DEFAULT_ABOUT_CONTENT.items():
        section_info = {
            "page": "about",
            "section": section_id,
            "fields": []
        }
        for field_name, default_value in fields.items():
            field_info = {
                "field": field_name,
                "type": "image" if field_name == "image" else "text",
                "default": default_value if field_name != "image" else "",
            }
            # 이미지 필드에 권장 사이즈 추가
            if field_name == "image":
                size_key = f"{section_id}.image"
                if size_key in IMAGE_SIZE_RECOMMENDATIONS:
                    field_info["recommended_size"] = IMAGE_SIZE_RECOMMENDATIONS[size_key]
            section_info["fields"].append(field_info)
        sections.append(section_info)

    return {"sections": sections}


def _deep_copy_dict(d: dict) -> dict:
    """딕셔너리 깊은 복사"""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy_dict(v)
        else:
            result[k] = v
    return result
