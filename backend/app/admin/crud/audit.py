"""审计日志CRUD操作"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.app.admin.model import AuditLog, SystemLog
from backend.app.common.exception.errors import NotFoundException


class CRUDAuditLog:
    """审计日志CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[AuditLog]:
        """根据ID获取审计日志"""
        result = await db.execute(select(AuditLog).where(AuditLog.log_id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        username: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """获取审计日志列表"""
        query = select(AuditLog)
        
        conditions = []
        if username:
            conditions.append(AuditLog.username.contains(username))
        if action:
            conditions.append(AuditLog.action.contains(action))
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> AuditLog:
        """创建审计日志"""
        db_obj = AuditLog(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除审计日志"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("审计日志不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_by_date_range(
        self, 
        db: AsyncSession, 
        start_date: datetime, 
        end_date: datetime
    ) -> int:
        """统计指定日期范围内的审计日志数量"""
        result = await db.execute(
            select(func.count(AuditLog.log_id))
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            )
        )
        return result.scalar()
    
    async def get_action_statistics(
        self, 
        db: AsyncSession, 
        days: int = 30
    ) -> List[dict]:
        """获取操作类型统计"""
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(
                AuditLog.action,
                func.count(AuditLog.log_id).label('count')
            )
            .where(AuditLog.created_at >= start_date)
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.log_id).desc())
            .limit(10)
        )
        
        return [{"action": row[0], "count": row[1]} for row in result.fetchall()]
    
    async def cleanup_old_logs(self, db: AsyncSession, days: int = 30) -> int:
        """清理旧日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(AuditLog).where(AuditLog.created_at < cutoff_date)
        )
        old_logs = result.scalars().all()
        
        for log in old_logs:
            await db.delete(log)
        
        await db.flush()
        return len(old_logs)


class CRUDSystemLog:
    """系统日志CRUD操作类"""
    
    async def get(self, db: AsyncSession, id: int) -> Optional[SystemLog]:
        """根据ID获取系统日志"""
        result = await db.execute(select(SystemLog).where(SystemLog.log_id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        level: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SystemLog]:
        """获取系统日志列表"""
        query = select(SystemLog)
        
        conditions = []
        if level:
            conditions.append(SystemLog.level == level)
        if category:
            conditions.append(SystemLog.category.contains(category))
        if start_date:
            conditions.append(SystemLog.created_at >= start_date)
        if end_date:
            conditions.append(SystemLog.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(SystemLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict) -> SystemLog:
        """创建系统日志"""
        db_obj = SystemLog(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> None:
        """删除系统日志"""
        db_obj = await self.get(db, id)
        if not db_obj:
            raise NotFoundException("系统日志不存在")
        
        await db.delete(db_obj)
        await db.flush()
    
    async def count_by_level(self, db: AsyncSession, level: str) -> int:
        """统计指定级别的系统日志数量"""
        result = await db.execute(
            select(func.count(SystemLog.log_id))
            .where(SystemLog.level == level)
        )
        return result.scalar()
    
    async def cleanup_old_logs(self, db: AsyncSession, days: int = 30) -> int:
        """清理旧日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(SystemLog).where(SystemLog.created_at < cutoff_date)
        )
        old_logs = result.scalars().all()
        
        for log in old_logs:
            await db.delete(log)
        
        await db.flush()
        return len(old_logs)


# 创建实例
audit_crud = CRUDAuditLog()
system_log_crud = CRUDSystemLog()
