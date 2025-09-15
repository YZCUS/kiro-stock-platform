"""
CRUD 操作基礎類別
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel as PydanticBaseModel
from models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD 操作基礎類別"""
    
    def __init__(self, model: Type[ModelType]):
        """
        初始化 CRUD 物件
        
        Args:
            model: SQLAlchemy 模型類別
        """
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """根據 ID 取得單一記錄"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        order_by: str = None
    ) -> List[ModelType]:
        """取得多筆記錄"""
        query = select(self.model).offset(skip).limit(limit)
        
        if order_by:
            if hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """建立新記錄"""
        obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """更新記錄"""
        obj_data = db_obj.to_dict()
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else obj_in
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """刪除記錄"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
    
    async def count(self, db: AsyncSession) -> int:
        """計算記錄總數"""
        result = await db.execute(select(func.count(self.model.id)))
        return result.scalar()
    
    async def exists(self, db: AsyncSession, id: Any) -> bool:
        """檢查記錄是否存在"""
        result = await db.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_by_field(
        self, 
        db: AsyncSession, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """根據指定欄位取得記錄"""
        if not hasattr(self.model, field_name):
            return None
        
        result = await db.execute(
            select(self.model).where(getattr(self.model, field_name) == field_value)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_by_field(
        self, 
        db: AsyncSession, 
        field_name: str, 
        field_value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """根據指定欄位取得多筆記錄"""
        if not hasattr(self.model, field_name):
            return []
        
        result = await db.execute(
            select(self.model)
            .where(getattr(self.model, field_name) == field_value)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def bulk_create(
        self, 
        db: AsyncSession, 
        *, 
        objs_in: List[CreateSchemaType]
    ) -> List[ModelType]:
        """批次建立記錄"""
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        
        for db_obj in db_objs:
            await db.refresh(db_obj)
        
        return db_objs
    
    async def bulk_update(
        self, 
        db: AsyncSession, 
        *, 
        updates: List[Dict[str, Any]]
    ) -> int:
        """批次更新記錄"""
        if not updates:
            return 0
        
        result = await db.execute(
            update(self.model),
            updates
        )
        await db.commit()
        return result.rowcount
    
    async def bulk_delete(
        self, 
        db: AsyncSession, 
        *, 
        ids: List[int]
    ) -> int:
        """批次刪除記錄"""
        if not ids:
            return 0
        
        result = await db.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        await db.commit()
        return result.rowcount