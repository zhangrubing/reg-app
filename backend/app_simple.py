"""软件注册与激活系统主应用 - 简化版本"""
from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

# 基础配置
class Settings:
    """简化配置类"""
    app_name = "软件注册与激活系统"
    app_version = "1.0.0"
    debug = False
    host = "0.0.0.0"
    port = 8000
    reload = False
    secret_key = "your-secret-key-change-this-in-production"
    access_token_expire_minutes = 30
    refresh_token_expire_days = 7
    totp_issuer = "RegApp"
    log_level = "INFO"
    cors_origins = ["*"]

settings = Settings()

# Pydantic模型
class LoginForm(BaseModel):
    """登录表单"""
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    totp_code: Optional[str] = Field(None, description="TOTP验证码")

class ActivationRequest(BaseModel):
    """激活请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    channel_code: str = Field(..., description="渠道代码", min_length=1, max_length=64)
    activation_code: str = Field(..., description="激活码", min_length=1, max_length=128)
    client_meta: Optional[dict] = Field(default=None, description="客户端元数据")

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="软件注册与激活系统"
)

# 配置模板和静态文件
templates = Jinja2Templates(directory="../templates")
app.mount("/static", StaticFiles(directory="../static"), name="static")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简单的内存存储（实际应用中应该使用数据库）
users_db = {
    "admin": {
        "user_id": 1,
        "username": "admin",
        "password_hash": "$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL7FdWp0yFhzV9nX1bZGp0yZGp0y",  # password: admin123
        "mfa_enabled": False,
        "role": "admin"
    }
}

channels_db = {
    "CH001": {
        "channel_id": 1,
        "channel_code": "CH001",
        "name": "官方渠道",
        "api_key": "test_api_key_12345",
        "secret_hmac": "test_secret_hmac_67890",
        "status": "active"
    }
}

devices_db = {}
activations_db = {}

# 页面路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: Optional[str] = Form(None)
):
    """登录处理"""
    try:
        # 查找用户
        user = users_db.get(username)
        if not user or password != "admin123":  # 简化验证
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "用户名或密码错误"}
            )
        
        # 创建简单的会话
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session_id",
            value=f"session_{user['user_id']}_{username}",
            httponly=True,
            max_age=3600  # 1小时
        )
        return response
        
    except Exception as e:
        print(f"登录错误: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "登录失败，请重试"}
        )

@app.get("/logout")
async def logout():
    """登出"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """管理面板"""
    # 简单认证检查
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": {"username": "admin"}}
    )

# API路由
@app.post("/api/v1/activate")
async def activate_device(request: ActivationRequest):
    """设备激活API - 简化版本"""
    try:
        print(f"激活请求: SN={request.sn}, 渠道={request.channel_code}")
        
        # 验证渠道
        channel = channels_db.get(request.channel_code)
        if not channel or channel["status"] != "active":
            return JSONResponse(
                status_code=400,
                content={"code": 3000, "message": "渠道不存在或已禁用", "data": None}
            )
        
        # 检查设备
        if request.sn in devices_db and devices_db[request.sn]["status"] == "activated":
            return JSONResponse(
                status_code=400,
                content={"code": 4003, "message": "设备已激活", "data": None}
            )
        
        # 创建设备记录
        devices_db[request.sn] = {
            "sn": request.sn,
            "channel_code": request.channel_code,
            "status": "activated",
            "activated_at": datetime.now().isoformat()
        }
        
        # 生成许可证
        license_data = {
            "sn": request.sn,
            "issued_at": datetime.now().isoformat(),
            "expires_at": None,
            "channel_code": request.channel_code,
            "activation_id": len(activations_db) + 1,
            "features": {"premium": True},
            "nonce": secrets.token_urlsafe(16),
            "issuer": settings.app_name,
            "pubkey_id": "v1",
            "signature": "dummy_signature"
        }
        
        print(f"激活成功: SN={request.sn}")
        
        return JSONResponse(
            status_code=200,
            content={
                "code": 0,
                "message": "激活成功",
                "data": {
                    "activation_id": len(activations_db) + 1,
                    "license_data": license_data,
                    "expires_at": None
                }
            }
        )
        
    except Exception as e:
        print(f"激活错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"code": 1000, "message": "激活失败", "data": None}
        )

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return JSONResponse(
        status_code=200,
        content={
            "code": 0,
            "message": "系统运行正常",
            "data": {
                "status": "healthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_simple:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
