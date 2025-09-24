"""激活记录Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActivationCreate(BaseModel):
    """创建激活记录"""
    channel_id: int = Field(..., description="渠道ID")
    activation_code: Optional[str] = Field(None, description="激活码，留空则自动生成")
    expires_days: Optional[int] = Field(None, description="有效期天数")
    max_uses: int = Field(1, ge=1, le=100, description="最大使用次数")
    amount_due: float = Field(0.0, ge=0, description="应付金额")
    billing_period: Optional[str] = Field(None, description="结算周期")
    notes: Optional[str] = Field(None, description="备注")


class ActivationUpdate(BaseModel):
    """更新激活记录"""
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    status: Optional[str] = Field(None, description="状态: active, used, revoked")
    notes: Optional[str] = Field(None, description="备注")


class ActivationResponse(BaseModel):
    """激活记录响应"""
    activation_id: int = Field(..., description="激活记录ID")
    sn: Optional[str] = Field(None, description="设备序列号")
    channel_id: int = Field(..., description="渠道ID")
    channel_code: str = Field(..., description="渠道代码")
    activation_code: str = Field(..., description="激活码")
    issued_by: Optional[str] = Field(None, description="发放者")
    activated_at: Optional[datetime] = Field(None, description="激活时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    license_blob: Optional[str] = Field(None, description="许可证内容")
    ip_address: Optional[str] = Field(None, description="IP地址")
    client_meta: Optional[Dict[str, Any]] = Field(None, description="客户端元数据")
    amount_due: float = Field(0.0, description="应付金额")
    billing_period: Optional[str] = Field(None, description="结算周期")
    payment_status: str = Field("unsettled", description="支付状态")
    status: str = Field(..., description="状态")
    is_offline: bool = Field(False, description="是否离线激活")
    twofa_verified: bool = Field(False, description="2FA是否验证")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ActivationListResponse(BaseModel):
    """激活记录列表响应"""
    items: List[ActivationResponse] = Field(..., description="激活记录列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class ActivationStatisticsResponse(BaseModel):
    """激活统计响应"""
    total_count: int = Field(..., description="总激活记录数")
    active_count: int = Field(..., description="活跃激活码数")
    used_count: int = Field(..., description="已使用激活码数")
    expired_count: int = Field(..., description="过期激活码数")
    today_count: int = Field(..., description="今日激活数")


class BatchActivationCreate(BaseModel):
    """批量创建激活码"""
    channel_id: int = Field(..., description="渠道ID")
    count: int = Field(..., ge=1, le=1000, description="创建数量")
    expires_days: Optional[int] = Field(None, description="有效期天数")
    max_uses: int = Field(1, ge=1, le=100, description="最大使用次数")


class DeviceActivationRequest(BaseModel):
    """设备激活请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    channel_code: str = Field(..., description="渠道代码", min_length=1, max_length=64)
    activation_code: str = Field(..., description="激活码", min_length=1, max_length=128)
    client_meta: Optional[Dict[str, Any]] = Field(None, description="客户端元数据")


class DeviceActivationResponse(BaseModel):
    """设备激活响应"""
    activation_id: int = Field(..., description="激活记录ID")
    license_data: Dict[str, Any] = Field(..., description="许可证数据")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    device_id: int = Field(..., description="设备ID")


class ActivationStatusResponse(BaseModel):
    """激活状态响应"""
    activated: bool = Field(..., description="是否已激活")
    device_status: Optional[str] = Field(None, description="设备状态")
    first_seen: Optional[datetime] = Field(None, description="首次在线时间")
    last_seen: Optional[datetime] = Field(None, description="最后在线时间")
    bound_channel: Optional[int] = Field(None, description="绑定渠道ID")
    activation_id: Optional[int] = Field(None, description="激活记录ID")
    activated_at: Optional[datetime] = Field(None, description="激活时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    status: Optional[str] = Field(None, description="激活状态")
    is_offline: Optional[bool] = Field(None, description="是否离线激活")
