"""审计日志管理API"""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import audit_service
from backend.app.admin.schema import (
    AuditLogResponse, AuditLogListResponse,
    SystemLogResponse, SystemLogListResponse,
    AuditStatisticsResponse, LogSearchRequest, LogSearchResponse,
    LogExportRequest, LogCleanupRequest, LogCleanupResponse,
    UserActionLogRequest, SystemEventLogRequest
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_admin_user

router = APIRouter()


@router.get("/logs", summary="获取审计日志列表")
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    username: Optional[str] = Query(None, description="用户名筛选"),
    action: Optional[str] = Query(None, description="操作筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> AuditLogListResponse:
    """获取审计日志列表"""
    try:
        logs = await audit_service.get_audit_logs(
            db=db,
            skip=skip,
            limit=limit,
            username=username,
            action=action,
            start_date=start_date,
            end_date=end_date
        )
        
        return response_success(logs)
        
    except Exception as e:
        logger.error(f"获取审计日志列表失败: {str(e)}")
        raise


@router.get("/system-logs", summary="获取系统日志列表")
async def get_system_logs(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    level: Optional[str] = Query(None, description="日志级别筛选"),
    category: Optional[str] = Query(None, description="日志类别筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> SystemLogListResponse:
    """获取系统日志列表"""
    try:
        logs = await audit_service.get_system_logs(
            db=db,
            skip=skip,
            limit=limit,
            level=level,
            category=category,
            start_date=start_date,
            end_date=end_date
        )
        
        return response_success(logs)
        
    except Exception as e:
        logger.error(f"获取系统日志列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取审计统计")
async def get_audit_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> AuditStatisticsResponse:
    """获取审计日志统计信息"""
    try:
        statistics = await audit_service.get_audit_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取审计统计失败: {str(e)}")
        raise


@router.post("/search", summary="搜索日志")
async def search_logs(
    search_data: LogSearchRequest = Body(..., description="搜索数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> LogSearchResponse:
    """搜索日志"""
    try:
        results = await audit_service.search_logs(
            db=db,
            query=search_data.query,
            log_type=search_data.log_type,
            limit=search_data.limit
        )
        
        return response_success(results)
        
    except Exception as e:
        logger.error(f"搜索日志失败: {str(e)}")
        raise


@router.post("/export", summary="导出日志")
async def export_logs(
    export_data: LogExportRequest = Body(..., description="导出数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> bytes:
    """导出日志数据"""
    try:
        export_content = await audit_service.export_logs(
            db=db,
            start_date=export_data.start_date,
            end_date=export_data.end_date,
            log_type=export_data.log_type,
            format=export_data.format
        )
        
        # 返回文件响应
        from fastapi.responses import Response
        filename = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_data.format}"
        
        return Response(
            content=export_content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"导出日志失败: {str(e)}")
        raise


@router.post("/cleanup", summary="清理旧日志")
async def cleanup_logs(
    cleanup_data: LogCleanupRequest = Body(..., description="清理数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> LogCleanupResponse:
    """清理旧日志"""
    try:
        result = await audit_service.cleanup_old_logs(
            db=db,
            days=cleanup_data.days,
            cleanup_audit=cleanup_data.cleanup_audit,
            cleanup_system=cleanup_data.cleanup_system
        )
        
        return response_success(LogCleanupResponse(
            audit_logs_deleted=result["audit_logs_deleted"],
            system_logs_deleted=result["system_logs_deleted"],
            message=f"日志清理完成，共删除 {result['audit_logs_deleted'] + result['system_logs_deleted']} 条记录"
        ))
        
    except Exception as e:
        logger.error(f"清理日志失败: {str(e)}")
        raise


@router.post("/user-action", summary="记录用户操作")
async def log_user_action(
    log_data: UserActionLogRequest = Body(..., description="日志数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> AuditLogResponse:
    """记录用户操作日志"""
    try:
        log = await audit_service.log_user_action(
            db=db,
            username=log_data.username,
            action=log_data.action,
            detail=log_data.detail,
            ip_address=log_data.ip_address,
            user_agent=log_data.user_agent,
            request_path=log_data.request_path
        )
        
        return response_success(log)
        
    except Exception as e:
        logger.error(f"记录用户操作失败: {str(e)}")
        raise


@router.post("/system-event", summary="记录系统事件")
async def log_system_event(
    log_data: SystemEventLogRequest = Body(..., description="日志数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> SystemLogResponse:
    """记录系统事件日志"""
    try:
        log = await audit_service.log_system_event(
            db=db,
            level=log_data.level,
            category=log_data.category,
            message=log_data.message,
            context=log_data.context
        )
        
        return response_success(log)
        
    except Exception as e:
        logger.error(f"记录系统事件失败: {str(e)}")
        raise


@router.delete("/logs/{log_id}", summary="删除审计日志")
async def delete_audit_log(
    log_id: int = Path(..., description="日志ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """删除审计日志"""
    try:
        await audit_service.delete_audit_log(db, log_id)
        
        return response_success({"message": "审计日志删除成功"})
        
    except Exception as e:
        logger.error(f"删除审计日志失败: {str(e)}")
        raise


@router.delete("/system-logs/{log_id}", summary="删除系统日志")
async def delete_system_log(
    log_id: int = Path(..., description="日志ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """删除系统日志"""
    try:
        await audit_service.delete_system_log(db, log_id)
        
        return response_success({"message": "系统日志删除成功"})
        
    except Exception as e:
        logger.error(f"删除系统日志失败: {str(e)}")
        raise


@router.get("/recent", summary="获取最近日志")
async def get_recent_logs(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> Dict[str, List]:
    """获取最近的日志"""
    try:
        # 获取最近的审计日志
        recent_audit_logs = await audit_service.get_audit_logs(db, limit=limit)
        
        # 获取最近的系统日志
        recent_system_logs = await audit_service.get_system_logs(db, limit=limit)
        
        return response_success({
            "recent_audit_logs": recent_audit_logs,
            "recent_system_logs": recent_system_logs
        })
        
    except Exception as e:
        logger.error(f"获取最近日志失败: {str(e)}")
        raise
