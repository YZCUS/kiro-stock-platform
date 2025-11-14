"""
認證相關的 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth import create_access_token
from core.auth_dependencies import get_current_active_user, get_current_user_id
from api.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    PasswordChange,
)
from domain.models.user import User
from datetime import timedelta
from app.settings import settings
import uuid

router = APIRouter(prefix="/auth", tags=["認證"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    用戶註冊

    Args:
        user_data: 註冊資訊
        db: 資料庫 session

    Returns:
        TokenResponse: 包含 access token 和用戶資訊

    Raises:
        HTTPException: 如果電子郵件或用戶名稱已存在
    """
    # 檢查電子郵件是否已存在
    existing_user = await db.run_sync(
        lambda session: User.get_by_email(session, user_data.email)
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="電子郵件已被註冊"
        )

    # 檢查用戶名稱是否已存在
    existing_username = await db.run_sync(
        lambda session: User.get_by_username(session, user_data.username)
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用戶名稱已被使用"
        )

    # 建立新用戶
    user = await db.run_sync(
        lambda session: User.create_user(
            session,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
        )
    )
    await db.commit()
    await db.refresh(user)

    # 生成 access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.security.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    用戶登入

    Args:
        credentials: 登入憑證（用戶名稱或電子郵件 + 密碼）
        db: 資料庫 session

    Returns:
        TokenResponse: 包含 access token 和用戶資訊

    Raises:
        HTTPException: 如果用戶名稱/電子郵件或密碼錯誤
    """
    # 嘗試用 username 或 email 查找用戶
    user = await db.run_sync(
        lambda session: User.get_by_username(session, credentials.username)
    )

    if user is None:
        user = await db.run_sync(
            lambda session: User.get_by_email(session, credentials.username)
        )

    # 驗證用戶和密碼
    if user is None or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶名稱/電子郵件或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用戶已停用")

    # 生成 access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.security.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    取得當前用戶資訊

    Args:
        current_user: 當前用戶

    Returns:
        UserResponse: 用戶資訊
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    修改密碼

    Args:
        password_data: 密碼修改資訊
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        成功訊息

    Raises:
        HTTPException: 如果舊密碼錯誤
    """
    # 驗證舊密碼
    if not current_user.check_password(password_data.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="舊密碼錯誤"
        )

    # 更新密碼
    current_user.hashed_password = User.get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "密碼已成功修改"}
