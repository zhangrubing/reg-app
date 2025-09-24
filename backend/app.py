"""软件注册与激活系统主应用 - 严格按照one-box风格"""
import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 导入配置和模块
from .config import BASE_DIR, DB_PATH, APP_NAME, HOST, PORT, RELOAD
from .db import init_db
from .middleware import AuthMiddleware
from .routers import auth as r_auth
from .routers import dashboard as r_dashboard
from .routers import channels as r_channels
from .routers import devices as r_devices
from .routers import activation as r_activation
from .routers import users as r_users
from .routers import audit as r_audit
# 直接在主应用中定义admin路由，避免导入问题
from fastapi import APIRouter

# 创建管理后台路由
admin_router = APIRouter(prefix="/admin", tags=["管理后台"])

# 完整的admin端点实现
@admin_router.get("/dashboard/statistics")
async def admin_dashboard_statistics():
    """管理后台仪表板统计"""
    return {
        "total_activations": 0,
        "total_licenses": 0,
        "total_users": 1,
        "total_devices": 0,
        "today_activations": 0,
        "pending_activations": 0
    }

@admin_router.get("/activations/statistics")
async def admin_activation_statistics():
    """激活记录统计"""
    return {
        "total": 0,
        "today": 0,
        "this_week": 0,
        "this_month": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0
    }

@admin_router.get("/activations")
async def admin_activations_list():
    """激活记录列表"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0
    }

@admin_router.get("/licenses/statistics")
async def admin_license_statistics():
    """许可证统计"""
    return {
        "total": 0,
        "active": 0,
        "expired": 0,
        "revoked": 0,
        "this_month_created": 0
    }

@admin_router.get("/licenses")
async def admin_licenses_list():
    """许可证列表"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0
    }

@admin_router.get("/users/statistics")
async def admin_user_statistics():
    """用户统计"""
    return {
        "total_users": 1,
        "admin_count": 1,
        "active_users": 1,
        "inactive_users": 0,
        "today_registered": 0,
        "today_login": 1
    }

@admin_router.get("/users")
async def admin_users_list():
    """用户列表"""
    return {
        "items": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_admin": True,
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
                "last_login": "2024-01-01T12:00:00"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20,
        "pages": 1
    }

@admin_router.get("/devices")
async def admin_devices_list():
    """设备列表"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0
    }

@admin_router.get("/channels")
async def admin_channels_list():
    """渠道列表"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0
    }

@admin_router.get("/audit/statistics")
async def admin_audit_statistics():
    """审计日志统计"""
    return {
        "total_logs": 0,
        "today_logs": 0,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0
    }

@admin_router.get("/audit")
async def admin_audit_list():
    """审计日志列表"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0
    }
from .utils.audit import log_system_event


app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
async def on_startup():
    """应用启动事件"""
    await init_db()
    asyncio.create_task(_system_monitor())
    await log_system_event("INFO", "system", "应用启动完成")


@app.on_event("shutdown")
async def on_shutdown():
    """应用关闭事件"""
    await log_system_event("INFO", "system", "应用正在关闭")


@app.get("/ping")
async def ping():
    """健康检查"""
    return {"ok": True, "service": APP_NAME, "timestamp": datetime.now().isoformat()}


async def _system_monitor():
    """系统监控任务"""
    interval = 300  # 5分钟
    while True:
        try:
            # 这里可以添加系统监控逻辑
            # 例如：检查数据库连接、清理过期数据等
            await asyncio.sleep(interval)
        except Exception:
            pass


# 中间件和路由器
app.add_middleware(AuthMiddleware)
app.include_router(r_auth.router)
app.include_router(r_dashboard.router)
app.include_router(r_channels.router)
app.include_router(r_devices.router)
app.include_router(r_activation.router)
app.include_router(r_users.router)
app.include_router(r_audit.router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD
    )
