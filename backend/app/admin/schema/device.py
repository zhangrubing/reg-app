"""设备Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """创建设备"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    channel_id: Optional[int] = Field(None, description="渠道ID")
    client_meta: Optional[Dict[str, Any]] = Field(None, description="客户端元数据")


class DeviceUpdate(BaseModel):
    """更新设备"""
    status: Optional[str] = Field(None, description="状态: pending, activated, suspended, expired, revoked")
    channel_id: Optional[int] = Field(None, description="渠道ID")
    notes: Optional[str] = Field(None, description="备注")


class DeviceResponse(BaseModel):
    """设备响应"""
    device_id: int = Field(..., description="设备ID")
    sn: str = Field(..., description="设备序列号")
    channel_id: Optional[int] = Field(None, description="渠道ID")
    status: str = Field(..., description="设备状态")
    first_seen: datetime = Field(..., description="首次在线时间")
    last_seen: datetime = Field(..., description="最后在线时间")
    activated_at: Optional[datetime] = Field(None, description="激活时间")
    client_meta: Optional[Dict[str, Any]] = Field(None, description="客户端元数据")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    items: List[DeviceResponse] = Field(..., description="设备列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class DeviceStatisticsResponse(BaseModel):
    """设备统计响应"""
    total_count: int = Field(..., description="总设备数")
    activated_count: int = Field(..., description="已激活设备数")
    pending_count: int = Field(..., description="待激活设备数")
    suspended_count: int = Field(..., description="暂停设备数")
    today_count: int = Field(..., description="今日新注册设备数")
    weekly_trend: List[Dict[str, Any]] = Field(..., description="最近7天趋势")


class DeviceDetailResponse(BaseModel):
    """设备详情响应"""
    device: DeviceResponse = Field(..., description="设备信息")
    activations: List[Dict[str, Any]] = Field(..., description="激活记录列表")
    channel: Optional[Dict[str, Any]] = Field(None, description="渠道信息")


class DeviceHeartbeatRequest(BaseModel):
    """设备心跳请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    client_meta: Optional[Dict[str, Any]] = Field(None, description="客户端元数据")


class DeviceBatchUpdateRequest(BaseModel):
    """设备批量更新请求"""
    device_ids: List[int] = Field(..., description="设备ID列表", min_items=1, max_items=100)
    status: str = Field(..., description="新状态")


class DeviceStatusCountResponse(BaseModel):
    """设备状态统计响应"""
    pending: int = Field(..., description="待激活")
    activated: int = Field(..., description="已激活")
    suspended: int = Field(..., description="已暂停")
    expired: int = Field(..., description="已过期")
    revoked: int = Field(..., description="已吊销")


class DeviceSimpleResponse(BaseModel):
    """设备简要响应"""
    device_id: int = Field(..., description="设备ID")
    sn: str = Field(..., description="设备序列号")
    status: str = Field(..., description="设备状态")
    last_seen: datetime = Field(..., description="最后在线时间")
