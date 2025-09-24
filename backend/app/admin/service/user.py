"""用户业务逻辑"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import user_crud
from backend.app.admin.model import AdminUser
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException,
    AuthenticationException
)
from backend.app.common.log import logger
from backend.app.common.auth.crypto import hash_password, verify_password, generate_secure_token


class UserService:
    """用户业务逻辑类"""
    
    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
        is_admin: bool = False,
        status: str = "active",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        real_name: Optional[str] = None
    ) -> AdminUser:
        """创建用户"""
        # 验证用户名格式
        if len(username) < 3 or len(username) > 50:
            raise InvalidParamsException("用户名长度必须在3-50个字符之间")
        
        # 检查用户名是否已存在
        existing = await user_crud.get_by_username(db, username)
        if existing:
            raise BusinessException("用户名已存在")
        
        # 验证密码强度
        if len(password) < 6:
            raise InvalidParamsException("密码长度至少为6个字符")
        
        # 创建用户数据
        user_data = {
            "username": username,
            "password_hash": hash_password(password),
            "is_admin": is_admin,
            "status": status,
            "email": email,
            "phone": phone,
            "real_name": real_name
        }
        
        user = await user_crud.create(db, user_data)
        
        logger.info(f"创建用户成功: ID={user.user_id}, 用户名={username}")
        
        return user
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> AdminUser:
        """用户认证"""
        # 查找用户
        user = await user_crud.get_by_username(db, username)
        if not user:
            raise AuthenticationException("用户名或密码错误")
        
        # 检查用户状态
        if user.status != "active":
            raise AuthenticationException("用户账户已被禁用")
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            raise AuthenticationException("用户名或密码错误")
        
        # 更新最后登录信息
        await user_crud.update_last_login(db, user.user_id, ip_address)
        
        logger.info(f"用户登录成功: ID={user.user_id}, 用户名={username}")
        
        return user
    
    async def update_user(
        self,
        db: AsyncSession,
        user_id: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        is_admin: Optional[bool] = None,
        status: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        real_name: Optional[str] = None
    ) -> AdminUser:
        """更新用户信息"""
        user = await user_crud.get(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        
        update_data = {}
        
        # 验证并更新用户名
        if username is not None:
            if len(username) < 3 or len(username) > 50:
                raise InvalidParamsException("用户名长度必须在3-50个字符之间")
            
            # 检查新用户名是否已存在
            existing = await user_crud.get_by_username(db, username)
            if existing and existing.user_id != user_id:
                raise BusinessException("用户名已存在")
            
            update_data["username"] = username
        
        # 更新密码
        if password is not None:
            if len(password) < 6:
                raise InvalidParamsException("密码长度至少为6个字符")
            update_data["password_hash"] = hash_password(password)
        
        # 更新其他字段
        if is_admin is not None:
            update_data["is_admin"] = is_admin
        if status is not None:
            update_data["status"] = status
        if email is not None:
            update_data["email"] = email
        if phone is not None:
            update_data["phone"] = phone
        if real_name is not None:
            update_data["real_name"] = real_name
        
        if update_data:
            user = await user_crud.update(db, user_id, update_data)
            logger.info(f"更新用户成功: ID={user_id}")
        
        return user
    
    async def delete_user(self, db: AsyncSession, user_id: int) -> None:
        """删除用户"""
        user = await user_crud.get(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        
        # 检查是否是最后一个管理员
        if user.is_admin:
            admin_count = await user_crud.count_admin(db)
            if admin_count <= 1:
                raise BusinessException("不能删除最后一个管理员用户")
        
        await user_crud.delete(db, user_id)
        
        logger.info(f"删除用户成功: ID={user_id}, 用户名={user.username}")
    
    async def get_user_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取用户统计信息"""
        from sqlalchemy import func
        
        # 总用户数
        total_result = await db.execute(select(func.count(AdminUser.user_id)))
        total_count = total_result.scalar()
        
        # 活跃用户數
        active_count = await user_crud.count_active(db)
        
        # 管理员用户数
        admin_count = await user_crud.count_admin(db)
        
        # 今日新注册用户数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await db.execute(
            select(func.count(AdminUser.user_id))
            .where(AdminUser.created_at >= today_start)
        )
        today_count = today_result.scalar()
        
        # 最近7天用户注册趋势
        seven_days_ago = datetime.now() - timedelta(days=7)
        trend_result = await db.execute(
            select(
                func.date(AdminUser.created_at).label('date'),
                func.count(AdminUser.user_id).label('count')
            )
            .where(AdminUser.created_at >= seven_days_ago)
            .group_by(func.date(AdminUser.created_at))
            .order_by(func.date(AdminUser.created_at))
        )
        
        trend_data = [{"date": str(row[0]), "count": row[1]} for row in trend_result.fetchall()]
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "admin_count": admin_count,
            "today_count": today_count,
            "weekly_trend": trend_data
        }
    
    async def reset_user_password(
        self,
        db: AsyncSession,
        user_id: int,
        new_password: str
    ) -> AdminUser:
        """重置用户密码"""
        if len(new_password) < 6:
            raise InvalidParamsException("密码长度至少为6个字符")
        
        user = await user_crud.get(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        
        user = await user_crud.update(
            db,
            user_id,
            {"password_hash": hash_password(new_password)}
        )
        
        logger.info(f"重置用户密码成功: ID={user_id}")
        
        return user
    
    async def toggle_user_status(self, db: AsyncSession, user_id: int) -> AdminUser:
        """切换用户状态"""
        user = await user_crud.get(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        
        new_status = "inactive" if user.status == "active" else "active"
        
        # 检查是否是最后一个管理员
        if user.is_admin and new_status == "inactive":
            admin_count = await user_crud.count_admin(db)
            if admin_count <= 1:
                raise BusinessException("不能禁用最后一个管理员用户")
        
        user = await user_crud.update(db, user_id, {"status": new_status})
        
        logger.info(f"切换用户状态成功: ID={user_id}, 新状态={new_status}")
        
        return user
    
    async def get_user_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        is_admin: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[AdminUser]:
        """获取用户列表"""
        return await user_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            is_admin=is_admin,
            search=search
        )
    
    async def get_recent_login_users(
        self,
        db: AsyncSession,
        days: int = 7,
        limit: int = 10
    ) -> List[AdminUser]:
        """获取最近登录的用户"""
        from sqlalchemy import and_
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(AdminUser)
            .where(
                and_(
                    AdminUser.last_login_at.is_not(None),
                    AdminUser.last_login_at >= cutoff_date
                )
            )
            .order_by(AdminUser.last_login_at.desc())
            .limit(limit)
        )
        
        return result.scalars().all()


# 创建实例
user_service = UserService()
