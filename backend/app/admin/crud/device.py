"""设备CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from backend.app.admin.model import Device
from backend.app.common.exception.errors import NotFoundException


class CRUDDevice:
    """设备CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[Device]:
        """根据ID获取设备"""
        result = await db.execute(select(Device).where(Device.device_id == id))
        return result.scalar_one_or_none()
    
    async def get_by_sn(self, db: AsyncSession, sn: str) -> Optional[Device]:
        """根据设备序列号获取设备"""
        result = await db.execute(
            select(Device).where(Device.sn == sn)
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
    ) -> List[Device]:
        """获取设备列表"""
        query = select(Device)
        
        conditions = []
        if status:
            conditions.append(Device.status == status)
        if channel_id:
            conditions.append(Device.channel_id == channel_id)
        if sn:
            conditions.append(Device.sn.contains(sn))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Device.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> Device:
        """创建设备"""
        db_obj = Device(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        id: int, 
        obj_in: dict
    ) -> Device:
        """更新设备"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("设备不存在")
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除设备"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("设备不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        """统计指定状态的设备数量"""
        result = await db.execute(
            select(Device).where(Device.status == status)
        )
        return len(result.scalars().all())
    
    async def count_by_channel(self, db: AsyncSession, channel_id: int) -> int:
        """统计指定渠道的设备数量"""
        result = await db.execute(
            select(Device).where(Device.channel_id == channel_id)
        )
        return len(result.scalars().all())
    
    async def update_last_seen(self, db: AsyncSession, sn: str) -> None:
        """更新设备最后在线时间"""
        device = await self.get_by_sn(db, sn)
        if device:
            device.last_seen = datetime.now()
            await db.flush()


# 创建实例
device_crud = CRUDDevice()
