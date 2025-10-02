"""
認證工具 - JWT Token 生成與驗證
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.settings import settings
import uuid


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT access token

    Args:
        data: 要編碼到 token 的數據（通常包含 user_id）
        expires_delta: token 過期時間，如果沒有提供則使用設定的預設值

    Returns:
        編碼後的 JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.security.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解碼並驗證 JWT token

    Args:
        token: JWT token 字串

    Returns:
        解碼後的 payload，如果驗證失敗則返回 None
    """
    try:
        payload = jwt.decode(token, settings.security.secret_key, algorithms=[settings.security.algorithm])
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[uuid.UUID]:
    """
    從 token 中取得 user_id

    Args:
        token: JWT token 字串

    Returns:
        user_id (UUID)，如果驗證失敗則返回 None
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        return uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        return None
