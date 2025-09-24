"""渠道Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    """创建渠道"""
    channel_code: str = Field(..., description="渠道代码", min_length=2, max_length=64)
    name: str = Field(..., description="渠道名称", min_length=1, max_length=128)
    status: str = Field("active", description="状态: active, inactive")
    description: Optional[str] = Field(None, description="渠道描述", max_length=500)
    contact_person: Optional[str] = Field(None, description="联系人", max_length=64)
    contact_email: Optional[str] = Field(None, description="联系邮箱", max_length=128)
    contact_phone: Optional[str] = Field(None, description="联系电话", max_length=32)


class ChannelUpdate(BaseModel):
    """更新渠道"""
    name: Optional[str] = Field(None, description="渠道名称", min_length=1, max_length=128)
    status: Optional[str] = Field(None, description="状态: active, inactive")
    description: Optional[str] = Field(None, description="渠道描述", max_length=500)
    contact_person: Optional[str] = Field(None, description="联系人", max_length=64)
    contact_email: Optional[str] = Field(None, description="联系邮箱", max_length=128)
    contact_phone: Optional[str] = Field(None, description="联系电话", max_length=32)


class ChannelResponse(BaseModel):
    """渠道响应"""
    channel_id: int = Field(..., description="渠道ID")
    channel_code: str = Field(..., description="渠道代码")
    name: str = Field(..., description="渠道名称")
    api_key: str = Field(..., description="API密钥")
    secret_hmac: str = Field(..., description="HMAC密钥")
    status: str = Field(..., description="状态")
    description: Optional[str] = Field(None, description="渠道描述")
    contact_person: Optional[str] = Field(None, description="联系人")
    contact_email: Optional[str] = Field(None, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    """渠道列表响应"""
    items: List[ChannelResponse] = Field(..., description="渠道列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class ChannelStatisticsResponse(BaseModel):
    """渠道统计响应"""
    total_count: int = Field(..., description="总渠道数")
    active_count: int = Field(..., description="活跃渠道数")
    disabled_count: int = Field(..., description="禁用渠道数")


class ChannelDetailResponse(BaseModel):
    """渠道详情响应"""
    channel: ChannelResponse = Field(..., description="渠道信息")
    statistics: ChannelStatisticsInfo = Field(..., description="统计信息")


class ChannelStatisticsInfo(BaseModel):
    """渠道统计信息"""
    activation_count: int = Field(..., description="激活记录数")
    device_count: int = Field(..., description="设备数")


class ApiKeyRegenerateResponse(BaseModel):
    """API密钥重新生成响应"""
    api_key: str = Field(..., description="新的API密钥")
    secret_hmac: str = Field(..., description="新的HMAC密钥")


class ChannelSimpleResponse(BaseModel):
    """渠道简要响应"""
    channel_id: int = Field(..., description="渠道ID")
    channel_code: str = Field(..., description="渠道代码")
    name: str = Field(..., description="渠道名称")
    status: str = Field(..., description="状态")
