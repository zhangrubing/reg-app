"""依赖项模块"""
from __future__ import annotations

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from backend.app.database import get_db
from backend.app.admin.model import AdminUser
from backend.app.admin.crud import user_crud
from backend.app.common.auth.jwt import decode_access_token
from backend.app.common.exception.errors import AuthenticationException, AuthorizationException

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """获取当前用户"""
    try:
        # 解码JWT令牌
        payload = decode_access_token(credentials.credentials)
        if not payload:
            raise AuthenticationException("无效的认证令牌")
        
        user_id = int(payload.get("sub"))
        if not user_id:
            raise AuthenticationException("无效的用户ID")
        
        # 获取用户信息
        user = await user_crud.get(db, user_id)
        if not user:
            raise AuthenticationException("用户不存在")
        
        # 检查用户状态
        if user.status != "active":
            raise AuthenticationException("用户账户已被禁用")
        
        return user
        
    except AuthenticationException:
        raise
    except Exception as e:
        raise AuthenticationException(f"认证失败: {str(e)}")


async def get_current_admin_user(
    current_user: AdminUser = Depends(get_current_user)
) -> AdminUser:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise AuthorizationException("需要管理员权限")
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[AdminUser]:
    """可选地获取当前用户"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except Exception:
        return None


class RateLimitDeps:
    """速率限制依赖项"""
    
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds
    
    async def __call__(self):
        # 这里可以实现速率限制逻辑
        # 例如使用Redis存储请求计数
        return True


# 创建常用的依赖项实例
rate_limit_10_per_minute = RateLimitDeps(times=10, seconds=60)
rate_limit_100_per_hour = RateLimitDeps(times=100, seconds=3600)
