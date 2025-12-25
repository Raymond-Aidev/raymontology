"""
Authentication Schemas
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


# ============================================================================
# Request Schemas
# ============================================================================

class UserRegister(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str


# ============================================================================
# Response Schemas
# ============================================================================

class Token(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초 단위 (예: 1800 = 30분)


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime]


class UserMe(BaseModel):
    """현재 사용자 정보"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime


# ============================================================================
# Password Reset Schemas
# ============================================================================

class ForgotPasswordRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """비밀번호 재설정"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class MessageResponse(BaseModel):
    """일반 메시지 응답"""
    message: str
