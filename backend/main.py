"""FastAPI主应用"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.common.log import logger
from backend.app.common.exception.errors import BaseErrorException
from backend.app.database import init_db, redis_client
from backend.app.admin.api import admin_router
from backend.app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("正在启动应用...")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
    
    # 连接Redis
    try:
        await redis_client.connect()
        logger.info("Redis连接成功")
    except Exception as e:
        logger.error(f"Redis连接失败: {str(e)}")
        # 不中断应用启动，Redis为可选组件
    
    yield
    
    # 关闭
    logger.info("正在关闭应用...")
    
    # 断开Redis连接
    try:
        await redis_client.disconnect()
        logger.info("Redis连接已关闭")
    except Exception as e:
        logger.error(f"Redis断开连接失败: {str(e)}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="英智软件注册系统API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 异常处理
@app.exception_handler(BaseErrorException)
async def custom_exception_handler(request: Request, exc: BaseErrorException):
    """自定义异常处理"""
    logger.error(f"请求异常: {request.url.path} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理的异常: {request.url.path} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 1000,
            "message": "内部服务器错误",
            "detail": str(exc) if settings.debug else "服务器内部错误",
            "timestamp": logger.time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = logger.time.time()
    
    # 记录请求
    logger.info(f"请求开始: {request.method} {request.url.path}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应
    process_time = logger.time.time() - start_time
    logger.info(
        f"请求完成: {request.method} {request.url.path} - "
        f"状态码: {response.status_code} - "
        f"处理时间: {process_time:.3f}s"
    )
    
    # 添加处理时间头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": logger.time.strftime("%Y-%m-%d %H:%M:%S")
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


# 注册路由
app.include_router(
    admin_router,
    prefix="/admin",
    tags=["管理后台"]
)

app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["API接口"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
