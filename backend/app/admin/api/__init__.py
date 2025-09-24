"""管理后台API路由模块"""
from __future__ import annotations

from fastapi import APIRouter
from .activation import router as activation_router
from .channel import router as channel_router
from .device import router as device_router
from .license import router as license_router
from .user import router as user_router
from .audit import router as audit_router
from .dashboard import router as dashboard_router

# 创建管理后台路由
admin_router = APIRouter(prefix="/admin", tags=["管理后台"])

# 注册子路由
admin_router.include_router(activation_router, prefix="/activations")
admin_router.include_router(channel_router, prefix="/channels")
admin_router.include_router(device_router, prefix="/devices")
admin_router.include_router(license_router, prefix="/licenses")
admin_router.include_router(user_router, prefix="/users")
admin_router.include_router(audit_router, prefix="/audit")
admin_router.include_router(dashboard_router, prefix="/dashboard")

__all__ = ["admin_router"]
