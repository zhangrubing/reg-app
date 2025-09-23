from typing import List, Optional
from datetime import datetime, timedelta
import aiosqlite
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ..config import DB_PATH as DATABASE_PATH
from ..deps import require_admin

router = APIRouter(prefix="/audit", tags=["审计日志"])

class AuditLogResponse(BaseModel):
    id: int
    username: str
    action: str
    detail: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str

class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    pages: int

class SystemLogResponse(BaseModel):
    id: int
    level: str
    category: str
    message: str
    context: Optional[str] = None
    created_at: str

class SystemLogListResponse(BaseModel):
    items: List[SystemLogResponse]
    total: int
    page: int
    pages: int

@router.get("/logs", response_model=AuditLogListResponse, dependencies=[Depends(require_admin)])
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    username: str = Query(""),
    action: str = Query(""),
    start_date: str = Query(""),
    end_date: str = Query("")
):
    """获取审计日志列表"""
    offset = (page - 1) * page_size
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if username:
            where_conditions.append("username LIKE ?")
            params.append(f"%{username}%")
        
        if action:
            where_conditions.append("action LIKE ?")
            params.append(f"%{action}%")
        
        if start_date:
            where_conditions.append("DATE(created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(created_at) <= ?")
            params.append(end_date)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) FROM audit_logs {where_clause}"
        cursor = await db.execute(count_query, params)
        total = (await cursor.fetchone())[0]
        
        # 获取审计日志列表
        query = f"""
            SELECT id, username, action, detail, ip, user_agent, created_at 
            FROM audit_logs 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "username": row[1],
                "action": row[2],
                "detail": row[3],
                "ip": row[4],
                "user_agent": row[5],
                "created_at": row[6]
            })
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": logs,
            "total": total,
            "page": page,
            "pages": pages
        }

@router.get("/system-logs", response_model=SystemLogListResponse, dependencies=[Depends(require_admin)])
async def get_system_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str = Query(""),
    category: str = Query(""),
    start_date: str = Query(""),
    end_date: str = Query("")
):
    """获取系统日志列表"""
    offset = (page - 1) * page_size
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if level:
            where_conditions.append("level = ?")
            params.append(level)
        
        if category:
            where_conditions.append("category LIKE ?")
            params.append(f"%{category}%")
        
        if start_date:
            where_conditions.append("DATE(created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(created_at) <= ?")
            params.append(end_date)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) FROM sys_logs {where_clause}"
        cursor = await db.execute(count_query, params)
        total = (await cursor.fetchone())[0]
        
        # 获取系统日志列表
        query = f"""
            SELECT id, level, category, message, context, created_at 
            FROM sys_logs 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "level": row[1],
                "category": row[2],
                "message": row[3],
                "context": row[4],
                "created_at": row[5]
            })
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": logs,
            "total": total,
            "page": page,
            "pages": pages
        }

@router.get("/statistics", dependencies=[Depends(require_admin)])
async def get_audit_statistics():
    """获取审计日志统计信息"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 今日审计日志数量
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE DATE(created_at) = ?",
            (today,)
        )
        today_logs = (await cursor.fetchone())[0]
        
        # 系统日志数量
        cursor = await db.execute("SELECT COUNT(*) FROM sys_logs")
        system_logs = (await cursor.fetchone())[0]
        
        # 最近7天的审计日志趋势
        cursor = await db.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM audit_logs
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        trend_data = await cursor.fetchall()
        
        # 操作类型统计
        cursor = await db.execute("""
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
        """)
        action_stats = await cursor.fetchall()
        
        return {
            "today_audit_logs": today_logs,
            "total_system_logs": system_logs,
            "weekly_trend": [{"date": row[0], "count": row[1]} for row in trend_data],
            "action_statistics": [{"action": row[0], "count": row[1]} for row in action_stats]
        }

@router.delete("/logs/{log_id}", dependencies=[Depends(require_admin)])
async def delete_audit_log(log_id: int):
    """删除审计日志"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM audit_logs WHERE id = ?", (log_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="日志不存在")
        
        await db.execute("DELETE FROM audit_logs WHERE id = ?", (log_id,))
        await db.commit()
        
        return {"message": "审计日志删除成功"}

@router.delete("/system-logs/{log_id}", dependencies=[Depends(require_admin)])
async def delete_system_log(log_id: int):
    """删除系统日志"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM sys_logs WHERE id = ?", (log_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="日志不存在")
        
        await db.execute("DELETE FROM sys_logs WHERE id = ?", (log_id,))
        await db.commit()
        
        return {"message": "系统日志删除成功"}

@router.delete("/cleanup", dependencies=[Depends(require_admin)])
async def cleanup_old_logs(
    days: int = Query(30, ge=7, le=365, description="保留最近多少天的日志")
):
    """清理旧日志"""
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 清理审计日志
        cursor = await db.execute(
            "DELETE FROM audit_logs WHERE DATE(created_at) < ?",
            (cutoff_date,)
        )
        audit_deleted = cursor.rowcount
        
        # 清理系统日志
        cursor = await db.execute(
            "DELETE FROM sys_logs WHERE DATE(created_at) < ?",
            (cutoff_date,)
        )
        system_deleted = cursor.rowcount
        
        await db.commit()
        
        return {
            "message": "日志清理完成",
            "audit_logs_deleted": audit_deleted,
            "system_logs_deleted": system_deleted,
            "retention_days": days
        }
