"""日志系统模块"""
from __future__ import annotations

import sys
from pathlib import Path
from loguru import logger
from backend.app.core.config import settings


# 移除默认的logger
logger.remove()


# 配置控制台日志
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)


# 配置文件日志（如果指定了日志文件）
if settings.log_file:
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.log_file,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )


# 创建日志装饰器
def log_decorator(func_name: str = None):
    """日志装饰器，用于记录函数调用和异常"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            func_name_str = func_name or func.__name__
            logger.info(f"开始执行: {func_name_str}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"成功完成: {func_name_str}")
                return result
            except Exception as e:
                logger.error(f"执行失败: {func_name_str}, 错误: {str(e)}")
                raise
        return wrapper
    return decorator


def sync_log_decorator(func_name: str = None):
    """同步日志装饰器，用于记录函数调用和异常"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name_str = func_name or func.__name__
            logger.info(f"开始执行: {func_name_str}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"成功完成: {func_name_str}")
                return result
            except Exception as e:
                logger.error(f"执行失败: {func_name_str}, 错误: {str(e)}")
                raise
        return wrapper
    return decorator


# 导出logger
__all__ = ["logger", "log_decorator", "sync_log_decorator"]
