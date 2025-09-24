"""激活记录CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from backend.app.admin.model import Activation
from backend.app.common.exception.errors import NotFoundException


class CRUDActivation:
    """激活记录CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[Activation]:
        """根据ID获取激活记录"""
        result = await db.execute(select(Activation).where(Activation.activation_id == id))
        return result.scalar_one_or_none()
    
    async def get_by_code(self, db: AsyncSession, activation_code: str) -> Optional[Activation]:
        """根据激活码获取激活记录"""
        result = await db.execute(
            select(Activation).where(Activation.activation_code == activation_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_sn(self, db: AsyncSession, sn: str) -> List[Activation]:
        """根据设备序列号获取激活记录列表"""
        result = await db.execute(
            select(Activation).where(Activation.sn == sn).order_by(Activation.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_latest_by_sn(self, db: AsyncSession, sn: str) -> Optional[Activation]:
        """获取设备最新的激活记录"""
        result = await db.execute(
            select(Activation)
            .where(Activation.sn == sn)
            .order_by(Activation.activated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        channel_id: Optional[int] = None,
        sn: Optional[str] = None
    ) -> List[Activation]:
        """获取激活记录列表"""
        query = select(Activation)
        
        conditions = []
        if status:
            conditions.append(Activation.status == status)
        if channel_id:
            conditions.append(Activation.channel_id == channel_id)
        if sn:
            conditions.append(Activation.sn.contains(sn))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Activation.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> Activation:
        """创建激活记录"""
        db_obj = Activation(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        id: int, 
        obj_in: dict
    ) -> Activation:
        """更新激活记录"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("激活记录不存在")
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除激活记录"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("激活记录不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        """统计指定状态的激活记录数量"""
        result = await db.execute(
            select(Activation).where(Activation.status == status)
        )
        return len(result.scalars().all())
    
    async def count_by_channel(self, db: AsyncSession, channel_id: int) -> int:
        """统计指定渠道的激活记录数量"""
        result = await db.execute(
            select(Activation).where(Activation.channel_id == channel_id)
        )
        return len(result.scalars().all())
    
    async def get_expired_activations(self, db: AsyncSession) -> List[Activation]:
        """获取已过期的激活记录"""
        current_time = datetime.now()
        result = await db.execute(
            select(Activation)
            .where(
                and_(
                    Activation.expires_at < current_time,
                    Activation.status == "active"
                )
            )
        )
        return result.scalars().all()


# 创建实例
activation_crud = CRUDActivation()
