"""
認證相關的 Pydantic schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


class UserRegister(BaseModel):
    """用戶註冊請求"""

    email: EmailStr = Field(..., description="電子郵件")
    username: str = Field(..., min_length=3, max_length=50, description="用戶名稱")
    password: str = Field(..., min_length=6, max_length=100, description="密碼")

    @validator("username")
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用戶名稱只能包含字母、數字、底線和連字號")
        return v


class UserLogin(BaseModel):
    """用戶登入請求"""

    username: str = Field(..., description="用戶名稱或電子郵件")
    password: str = Field(..., description="密碼")


class UserResponse(BaseModel):
    """用戶資訊回應"""

    id: str = Field(..., description="用戶ID")
    email: str = Field(..., description="電子郵件")
    username: str = Field(..., description="用戶名稱")
    is_active: bool = Field(..., description="是否啟用")
    created_at: Optional[datetime] = Field(None, description="建立時間")

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token 回應"""

    access_token: str = Field(..., description="存取令牌")
    token_type: str = Field(default="bearer", description="令牌類型")
    user: UserResponse = Field(..., description="用戶資訊")


class PasswordChange(BaseModel):
    """修改密碼請求"""

    old_password: str = Field(..., description="舊密碼")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密碼")
