"""
認證相關的 FastAPI 依賴
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.auth import get_user_id_from_token
from domain.models.user import User
from typing import Optional
import uuid

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid.UUID:
    """
    從 JWT token 取得當前用戶 ID

    Args:
        credentials: HTTP Bearer token

    Returns:
        用戶 UUID

    Raises:
        HTTPException: 如果 token 無效或缺失
    """
    token = credentials.credentials
    user_id = get_user_id_from_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    取得當前用戶物件

    Args:
        user_id: 用戶 UUID
        db: 資料庫 session

    Returns:
        User 物件

    Raises:
        HTTPException: 如果用戶不存在或未啟用
    """
    user = await db.run_sync(lambda session: User.get_by_id(session, user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用戶已停用")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    取得當前活躍用戶（已驗證且啟用）

    Args:
        current_user: 當前用戶

    Returns:
        User 物件
    """
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    取得當前用戶（可選）
    如果沒有提供 token 則返回 None，不會拋出異常

    Args:
        credentials: HTTP Bearer token (可選)
        db: 資料庫 session

    Returns:
        User 物件或 None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = get_user_id_from_token(token)

    if user_id is None:
        return None

    user = await db.run_sync(lambda session: User.get_by_id(session, user_id))

    if user is None or not user.is_active:
        return None

    return user
