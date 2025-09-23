"""API路由模块"""
from __future__ import annotations

from fastapi import APIRouter
from .activation import router as activation_router
from .device import router as device_router
from .channel import router as channel_router

# 创建API路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(activation_router, prefix="/activate", tags=["激活"])
api_router.include_router(device_router, prefix="/devices", tags=["设备"])
api_router.include_router(channel_router, prefix="/channels", tags=["渠道"])

__all__ = ["api_router"]
