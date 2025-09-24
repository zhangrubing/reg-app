"""审计日志业务逻辑"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import audit_crud, system_log_crud
from backend.app.admin.model import AuditLog, SystemLog
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException
)
from backend.app.common.log import logger


class AuditService:
    """审计日志业务逻辑类"""
    
    async def log_user_action(
        self,
        db: AsyncSession,
        username: str,
        action: str,
        detail: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_path: Optional[str] = None
    ) -> AuditLog:
        """记录用户操作日志"""
        # 构建详细描述
        full_detail = detail
        if request_path:
            full_detail = f"{detail} (路径: {request_path})"
        
        log_data = {
            "username": username,
            "action": action,
            "detail": full_detail,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        audit_log = await audit_crud.create(db, log_data)
        
        # 异步记录到系统日志
        logger.info(f"用户操作日志: {username} - {action} - {detail}")
        
        return audit_log
    
    async def log_system_event(
        self,
        db: AsyncSession,
        level: str,
        category: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SystemLog:
        """记录系统事件日志"""
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            raise InvalidParamsException(f"无效的日志级别，可选值: {', '.join(valid_levels)}")
        
        log_data = {
            "level": level,
            "category": category,
            "message": message,
            "context": context
        }
        
        system_log = await system_log_crud.create(db, log_data)
        
        # 根据级别记录到系统日志
        log_method = getattr(logger, level.lower())
        log_method(f"系统日志: {category} - {message}")
        
        return system_log
    
    async def get_audit_logs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        username: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """获取审计日志列表"""
        return await audit_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            username=username,
            action=action,
            start_date=start_date,
            end_date=end_date
        )
    
    async def get_system_logs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        level: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SystemLog]:
        """获取系统日志列表"""
        return await system_log_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            level=level,
            category=category,
            start_date=start_date,
            end_date=end_date
        )
    
    async def get_audit_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取审计日志统计信息"""
        # 今日审计日志数量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = await audit_crud.count_by_date_range(db, today_start, datetime.now())
        
        # 系统日志总数
        from sqlalchemy import func
        total_system_logs_result = await db.execute(select(func.count(SystemLog.log_id)))
        total_system_logs = total_system_logs_result.scalar()
        
        # 最近7天的审计日志趋势
        seven_days_ago = datetime.now() - timedelta(days=7)
        trend_data = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            count = await audit_crud.count_by_date_range(db, date_start, date_end)
            trend_data.append({
                "date": date_start.strftime("%Y-%m-%d"),
                "count": count
            })
        
        # 操作类型统计
        action_stats = await audit_crud.get_action_statistics(db, days=30)
        
        # 系统日志级别统计
        level_stats = {}
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            count = await system_log_crud.count_by_level(db, level)
            level_stats[level] = count
        
        return {
            "today_audit_logs": today_count,
            "total_system_logs": total_system_logs,
            "weekly_trend": list(reversed(trend_data)),  # 按时间升序
            "action_statistics": action_stats,
            "system_log_levels": level_stats
        }
    
    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        days: int = 30,
        cleanup_audit: bool = True,
        cleanup_system: bool = True
    ) -> Dict[str, int]:
        """清理旧日志"""
        if days < 7:
            raise InvalidParamsException("日志保留天数至少为7天")
        
        result = {
            "audit_logs_deleted": 0,
            "system_logs_deleted": 0
        }
        
        # 清理审计日志
        if cleanup_audit:
            try:
                audit_deleted = await audit_crud.cleanup_old_logs(db, days)
                result["audit_logs_deleted"] = audit_deleted
                logger.info(f"清理审计日志完成: 删除{audit_deleted}条记录")
            except Exception as e:
                logger.error(f"清理审计日志失败: {str(e)}")
        
        # 清理系统日志
        if cleanup_system:
            try:
                system_deleted = await system_log_crud.cleanup_old_logs(db, days)
                result["system_logs_deleted"] = system_deleted
                logger.info(f"清理系统日志完成: 删除{system_deleted}条记录")
            except Exception as e:
                logger.error(f"清理系统日志失败: {str(e)}")
        
        return result
    
    async def delete_audit_log(self, db: AsyncSession, log_id: int) -> None:
        """删除审计日志"""
        audit_log = await audit_crud.get(db, log_id)
        if not audit_log:
            raise NotFoundException("审计日志不存在")
        
        await audit_crud.delete(db, log_id)
        
        logger.info(f"删除审计日志成功: ID={log_id}")
    
    async def delete_system_log(self, db: AsyncSession, log_id: int) -> None:
        """删除系统日志"""
        system_log = await system_log_crud.get(db, log_id)
        if not system_log:
            raise NotFoundException("系统日志不存在")
        
        await system_log_crud.delete(db, log_id)
        
        logger.info(f"删除系统日志成功: ID={log_id}")
    
    async def search_logs(
        self,
        db: AsyncSession,
        query: str,
        log_type: str = "all",
        limit: int = 100
    ) -> Dict[str, List[Any]]:
        """搜索日志"""
        if log_type not in ["all", "audit", "system"]:
            raise InvalidParamsException("无效的日志类型")
        
        results = {
            "audit_logs": [],
            "system_logs": []
        }
        
        # 搜索审计日志
        if log_type in ["all", "audit"]:
            audit_results = await db.execute(
                select(AuditLog)
                .where(
                    or_(
                        AuditLog.username.contains(query),
                        AuditLog.action.contains(query),
                        AuditLog.detail.contains(query)
                    )
                )
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )
            results["audit_logs"] = audit_results.scalars().all()
        
        # 搜索系统日志
        if log_type in ["all", "system"]:
            system_results = await db.execute(
                select(SystemLog)
                .where(
                    or_(
                        SystemLog.level.contains(query),
                        SystemLog.category.contains(query),
                        SystemLog.message.contains(query),
                        SystemLog.context.contains(query)
                    )
                )
                .order_by(SystemLog.created_at.desc())
                .limit(limit)
            )
            results["system_logs"] = system_results.scalars().all()
        
        return results
    
    async def export_logs(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        log_type: str = "all",
        format: str = "json"
    ) -> bytes:
        """导出日志"""
        if format not in ["json", "csv"]:
            raise InvalidParamsException("不支持的导出格式")
        
        # 获取日志数据
        logs_data = {}
        
        if log_type in ["all", "audit"]:
            audit_logs = await audit_crud.get_multi(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=10000  # 限制导出数量
            )
            logs_data["audit_logs"] = [
                {
                    "id": log.log_id,
                    "username": log.username,
                    "action": log.action,
                    "detail": log.detail,
                    "ip": log.ip_address,
                    "user_agent": log.user_agent,
                    "created_at": log.created_at.isoformat()
                }
                for log in audit_logs
            ]
        
        if log_type in ["all", "system"]:
            system_logs = await system_log_crud.get_multi(
                db=db,
                start_date=start_date,
                end_date=end_date,
                limit=10000  # 限制导出数量
            )
            logs_data["system_logs"] = [
                {
                    "id": log.log_id,
                    "level": log.level,
                    "category": log.category,
                    "message": log.message,
                    "context": log.context,
                    "created_at": log.created_at.isoformat()
                }
                for log in system_logs
            ]
        
        # 根据格式返回数据
        if format == "json":
            import json
            return json.dumps(logs_data, ensure_ascii=False, indent=2).encode('utf-8')
        else:  # CSV
            import csv
            import io
            
            output = io.StringIO()
            
            if log_type == "all" or log_type == "audit":
                if logs_data.get("audit_logs"):
                    output.write("审计日志\n")
                    writer = csv.DictWriter(output, fieldnames=["id", "username", "action", "detail", "ip", "user_agent", "created_at"])
                    writer.writeheader()
                    writer.writerows(logs_data["audit_logs"])
                    output.write("\n")
            
            if log_type == "all" or log_type == "system":
                if logs_data.get("system_logs"):
                    output.write("系统日志\n")
                    writer = csv.DictWriter(output, fieldnames=["id", "level", "category", "message", "context", "created_at"])
                    writer.writeheader()
                    writer.writerows(logs_data["system_logs"])
            
            return output.getvalue().encode('utf-8')


# 创建实例
audit_service = AuditService()
