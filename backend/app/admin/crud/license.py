"""许可证CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.app.admin.model import License
from backend.app.common.exception.errors import NotFoundException


class CRUDLicense:
    """许可证CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[License]:
        """根据ID获取许可证"""
        result = await db.execute(select(License).where(License.license_id == id))
        return result.scalar_one_or_none()
    
    async def get_by_sn(self, db: AsyncSession, sn: str) -> List[License]:
        """根据设备序列号获取许可证列表"""
        result = await db.execute(
            select(License).where(License.sn == sn).order_by(License.issued_at.desc())
        )
        return result.scalars().all()
    
    async def get_active_by_sn(self, db: AsyncSession, sn: str) -> Optional[License]:
        """获取设备当前有效的许可证"""
        current_time = datetime.now()
        result = await db.execute(
            select(License)
            .where(
                and_(
                    License.sn == sn,
                    License.revoked_at.is_(None),
                    or_(
                        License.expires_at.is_(None),
                        License.expires_at > current_time
                    )
                )
            )
            .order_by(License.issued_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        sn: Optional[str] = None,
        activation_id: Optional[int] = None,
        is_revoked: Optional[bool] = None
    ) -> List[License]:
        """获取许可证列表"""
        query = select(License)
        
        conditions = []
        if sn:
            conditions.append(License.sn.contains(sn))
        if activation_id:
            conditions.append(License.activation_id == activation_id)
        if is_revoked is not None:
            if is_revoked:
                conditions.append(License.revoked_at.is_not(None))
            else:
                conditions.append(License.revoked_at.is_(None))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(License.issued_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> License:
        """创建许可证"""
        db_obj = License(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        id: int, 
        obj_in: dict
    ) -> License:
        """更新许可证"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("许可证不存在")
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def revoke(self, db: AsyncSession, id: int, reason: str = None) -> License:
        """吊销许可证"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("许可证不存在")
        
        db_obj.revoked_at = datetime.now()
        if reason:
            db_obj.revoke_reason = reason
        
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除许可证"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("许可证不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_by_sn(self, db: AsyncSession, sn: str) -> int:
        """统计指定设备的许可证数量"""
        result = await db.execute(
            select(License).where(License.sn == sn)
        )
        return len(result.scalars().all())
    
    async def count_active(self, db: AsyncSession) -> int:
        """统计当前有效的许可证数量"""
        current_time = datetime.now()
        result = await db.execute(
            select(License)
            .where(
                and_(
                    License.revoked_at.is_(None),
                    or_(
                        License.expires_at.is_(None),
                        License.expires_at > current_time
                    )
                )
            )
        )
        return len(result.scalars().all())


# 创建实例
license_crud = CRUDLicense()
