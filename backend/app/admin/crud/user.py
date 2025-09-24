"""用户CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from backend.app.admin.model import AdminUser
from backend.app.common.exception.errors import NotFoundException


class CRUDUser:
    """用户CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[AdminUser]:
        """根据ID获取用户"""
        result = await db.execute(select(AdminUser).where(AdminUser.user_id == id))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[AdminUser]:
        """根据用户名获取用户"""
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        is_admin: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[AdminUser]:
        """获取用户列表"""
        query = select(AdminUser)
        
        conditions = []
        if status:
            conditions.append(AdminUser.status == status)
        if is_admin is not None:
            conditions.append(AdminUser.is_admin == is_admin)
        if search:
            conditions.append(AdminUser.username.contains(search))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AdminUser.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> AdminUser:
        """创建用户"""
        db_obj = AdminUser(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        id: int, 
        obj_in: dict
    ) -> AdminUser:
        """更新用户"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("用户不存在")
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now()
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除用户"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("用户不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def update_last_login(self, db: AsyncSession, user_id: int, ip: str = None) -> None:
        """更新用户最后登录信息"""
        user = await self.get(db, user_id)
        if user:
            user.last_login_at = datetime.now()
            user.last_login_ip = ip
            user.login_count = (user.login_count or 0) + 1
            await db.flush()
    
    async def count_active(self, db: AsyncSession) -> int:
        """统计活跃用户数量"""
        result = await db.execute(
            select(AdminUser).where(AdminUser.status == "active")
        )
        return len(result.scalars().all())
    
    async def count_admin(self, db: AsyncSession) -> int:
        """统计管理员用户数量"""
        result = await db.execute(
            select(AdminUser).where(AdminUser.is_admin == True)
        )
        return len(result.scalars().all())


# 创建实例
user_crud = CRUDUser()
