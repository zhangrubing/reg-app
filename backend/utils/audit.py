import aiosqlite
from datetime import datetime

try:
    from ..config import DB_PATH
except ImportError:
    # 当直接运行文件时的导入方式
    from config import DB_PATH


async def audit_log(username: str, action: str, detail: str, request=None):
    """记录审计日志"""
    try:
        ip = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO audit_logs (username, action, detail, ip, user_agent) 
                   VALUES (?, ?, ?, ?, ?)""",
                (username, action, detail, ip, user_agent)
            )
            await db.commit()
    except Exception:
        # 审计日志失败不应该影响主流程
        pass


async def log_system_event(level: str, category: str, message: str, context: str = None):
    """记录系统日志"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO sys_logs (level, category, message, context) 
                   VALUES (?, ?, ?, ?)""",
                (level, category, message, context)
            )
            await db.commit()
    except Exception:
        pass
