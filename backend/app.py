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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD
    )
