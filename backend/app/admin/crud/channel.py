"""渠道CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from backend.app.admin.model import Channel
from backend.app.common.exception.errors import NotFoundException


class CRUDChannel:
    """渠道CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[Channel]:
        """根据ID获取渠道"""
        result = await db.execute(select(Channel).where(Channel.channel_id == id))
        return result.scalar_one_or_none()
    
    async def get_by_code(self, db: AsyncSession, channel_code: str) -> Optional[Channel]:
        """根据渠道代码获取渠道"""
        result = await db.execute(
            select(Channel).where(Channel.channel_code == channel_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_api_key(self, db: AsyncSession, api_key: str) -> Optional[Channel]:
        """根据API密钥获取渠道"""
        result = await db.execute(
            select(Channel).where(Channel.api_key == api_key)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Channel]:
        """获取渠道列表"""
        query = select(Channel)
        
        conditions = []
        if status:
            conditions.append(Channel.status == status)
        if search:
            conditions.append(
                or_(
                    Channel.channel_code.contains(search),
                    Channel.name.contains(search)
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Channel.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> Channel:
        """创建渠道"""
        db_obj = Channel(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        id: int, 
        obj_in: dict
    ) -> Channel:
        """更新渠道"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("渠道不存在")
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除渠道"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("渠道不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_active(self, db: AsyncSession) -> int:
        """统计活跃渠道数量"""
        result = await db.execute(
            select(Channel).where(Channel.status == "active")
        )
        return len(result.scalars().all())


# 创建实例
channel_crud = CRUDChannel()
