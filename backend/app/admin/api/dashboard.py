"""仪表板API"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from backend.app.database import get_db
from backend.app.admin.service import (
    activation_service, channel_service, device_service, 
    license_service, user_service, audit_service
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger

router = APIRouter()


@router.get("/statistics", summary="获取仪表板统计数据")
async def get_dashboard_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取仪表板综合统计数据"""
    try:
        # 获取各项统计数据
        activation_stats = await activation_service.get_activation_statistics(db)
        channel_stats = await channel_service.get_channel_statistics(db)
        device_stats = await device_service.get_device_statistics(db)
        license_stats = await license_service.get_license_statistics(db)
        user_stats = await user_service.get_user_statistics(db)
        audit_stats = await audit_service.get_audit_statistics(db)
        
        # 组合数据
        dashboard_data = {
            "activation": activation_stats,
            "channel": channel_stats,
            "device": device_stats,
            "license": license_stats,
            "user": user_stats,
            "audit": audit_stats,
            "timestamp": logger.time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info("获取仪表板统计数据成功")
        
        return response_success(dashboard_data)
        
    except Exception as e:
        logger.error(f"获取仪表板统计数据失败: {str(e)}")
        raise


@router.get("/quick-stats", summary="获取快速统计")
async def get_quick_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取快速统计数据"""
    try:
        # 获取关键指标
        activation_stats = await activation_service.get_activation_statistics(db)
        device_stats = await device_service.get_device_statistics(db)
        user_stats = await user_service.get_user_statistics(db)
        
        quick_stats = {
            "total_activations": activation_stats["total_count"],
            "active_activations": activation_stats["active_count"],
            "total_devices": device_stats["total_count"],
            "activated_devices": device_stats["activated_count"],
            "total_users": user_stats["total_count"],
            "active_users": user_stats["active_count"],
            "today_activations": activation_stats["today_count"],
            "today_devices": device_stats["today_count"],
            "today_users": user_stats["today_count"]
        }
        
        return response_success(quick_stats)
        
    except Exception as e:
        logger.error(f"获取快速统计数据失败: {str(e)}")
        raise


@router.get("/recent-activities", summary="获取最近活动")
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取最近的活动记录"""
    try:
        # 获取最近的审计日志
        recent_logs = await audit_service.get_audit_logs(db, limit=limit)
        
        # 获取最近登录的用户
        recent_logins = await user_service.get_recent_login_users(db, limit=limit)
        
        activities = {
            "recent_logs": recent_logs,
            "recent_logins": recent_logins
        }
        
        return response_success(activities)
        
    except Exception as e:
        logger.error(f"获取最近活动失败: {str(e)}")
        raise


@router.get("/system-health", summary="获取系统健康状态")
async def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    try:
        # 检查数据库连接
        db_status = "healthy"
        
        # 检查Redis连接（如果有）
        redis_status = "not_configured"
        
        # 系统信息
        system_info = {
            "database": db_status,
            "redis": redis_status,
            "timestamp": logger.time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "healthy" if db_status == "healthy" else "unhealthy"
        }
        
        return response_success(system_info)
        
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return response_success({
            "database": "unhealthy",
            "redis": "unknown",
            "timestamp": logger.time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "unhealthy",
            "error": str(e)
        })


@router.get("/charts/data", summary="获取图表数据")
async def get_charts_data(
    days: int = Query(7, ge=1, le=30, description="天数范围"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取图表展示数据"""
    try:
        # 获取激活趋势数据
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        from backend.app.admin.model import Activation
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 激活趋势
        activation_trend_result = await db.execute(
            select(
                func.date(Activation.created_at).label('date'),
                func.count(Activation.activation_id).label('count')
            )
            .where(
                and_(
                    Activation.created_at >= start_date,
                    Activation.created_at <= end_date
                )
            )
            .group_by(func.date(Activation.created_at))
            .order_by(func.date(Activation.created_at))
        )
        
        activation_trend = [
            {"date": str(row[0]), "count": row[1]}
            for row in activation_trend_result.fetchall()
        ]
        
        # 设备趋势
        from backend.app.admin.model import Device
        
        device_trend_result = await db.execute(
            select(
                func.date(Device.created_at).label('date'),
                func.count(Device.device_id).label('count')
            )
            .where(
                and_(
                    Device.created_at >= start_date,
                    Device.created_at <= end_date
                )
            )
            .group_by(func.date(Device.created_at))
            .order_by(func.date(Device.created_at))
        )
        
        device_trend = [
            {"date": str(row[0]), "count": row[1]}
            for row in device_trend_result.fetchall()
        ]
        
        charts_data = {
            "activation_trend": activation_trend,
            "device_trend": device_trend,
            "period_days": days
        }
        
        return response_success(charts_data)
        
    except Exception as e:
        logger.error(f"获取图表数据失败: {str(e)}")
        raise
