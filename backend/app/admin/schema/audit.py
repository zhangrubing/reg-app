"""审计日志Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    log_id: int = Field(..., description="日志ID")
    username: str = Field(..., description="用户名")
    action: str = Field(..., description="操作")
    detail: str = Field(..., description="详细描述")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    items: List[AuditLogResponse] = Field(..., description="审计日志列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class SystemLogResponse(BaseModel):
    """系统日志响应"""
    log_id: int = Field(..., description="日志ID")
    level: str = Field(..., description="日志级别")
    category: str = Field(..., description="日志类别")
    message: str = Field(..., description="日志消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class SystemLogListResponse(BaseModel):
    """系统日志列表响应"""
    items: List[SystemLogResponse] = Field(..., description="系统日志列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class AuditStatisticsResponse(BaseModel):
    """审计统计响应"""
    today_audit_logs: int = Field(..., description="今日审计日志数")
    total_system_logs: int = Field(..., description="系统日志总数")
    weekly_trend: List[Dict[str, Any]] = Field(..., description="最近7天趋势")
    action_statistics: List[Dict[str, Any]] = Field(..., description="操作类型统计")
    system_log_levels: Dict[str, int] = Field(..., description="系统日志级别统计")


class LogSearchRequest(BaseModel):
    """日志搜索请求"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=100)
    log_type: str = Field("all", description="日志类型: all, audit, system")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")


class LogSearchResponse(BaseModel):
    """日志搜索响应"""
    audit_logs: List[AuditLogResponse] = Field(..., description="审计日志结果")
    system_logs: List[SystemLogResponse] = Field(..., description="系统日志结果")


class LogExportRequest(BaseModel):
    """日志导出请求"""
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    log_type: str = Field("all", description="日志类型: all, audit, system")
    format: str = Field("json", description="导出格式: json, csv")


class LogCleanupRequest(BaseModel):
    """日志清理请求"""
    days: int = Field(30, ge=7, le=365, description="保留天数")
    cleanup_audit: bool = Field(True, description="清理审计日志")
    cleanup_system: bool = Field(True, description="清理系统日志")


class LogCleanupResponse(BaseModel):
    """日志清理响应"""
    audit_logs_deleted: int = Field(..., description="删除的审计日志数")
    system_logs_deleted: int = Field(..., description="删除的系统日志数")
    message: str = Field(..., description="清理结果消息")


class UserActionLogRequest(BaseModel):
    """用户操作日志请求"""
    username: str = Field(..., description="用户名")
    action: str = Field(..., description="操作")
    detail: str = Field(..., description="详细描述")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_path: Optional[str] = Field(None, description="请求路径")


class SystemEventLogRequest(BaseModel):
    """系统事件日志请求"""
    level: str = Field(..., description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    category: str = Field(..., description="日志类别")
    message: str = Field(..., description="日志消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
