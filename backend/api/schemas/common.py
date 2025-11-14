"""
共用API Schema模型
"""

from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分頁響應模型"""

    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
