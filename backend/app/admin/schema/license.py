"""许可证Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LicenseCreate(BaseModel):
    """创建许可证"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    activation_id: int = Field(..., description="激活记录ID")
    expires_days: Optional[int] = Field(None, description="有效期天数")
    features: Optional[Dict[str, Any]] = Field(None, description="功能特性")


class LicenseUpdate(BaseModel):
    """更新许可证"""
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    features: Optional[Dict[str, Any]] = Field(None, description="功能特性")


class LicenseResponse(BaseModel):
    """许可证响应"""
    license_id: int = Field(..., description="许可证ID")
    sn: str = Field(..., description="设备序列号")
    activation_id: int = Field(..., description="激活记录ID")
    license_data: Dict[str, Any] = Field(..., description="许可证数据")
    signature: str = Field(..., description="签名")
    issued_at: datetime = Field(..., description="签发时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    revoked_at: Optional[datetime] = Field(None, description="吊销时间")
    revoke_reason: Optional[str] = Field(None, description="吊销原因")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class LicenseListResponse(BaseModel):
    """许可证列表响应"""
    items: List[LicenseResponse] = Field(..., description="许可证列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class LicenseStatisticsResponse(BaseModel):
    """许可证统计响应"""
    total_count: int = Field(..., description="总许可证数")
    active_count: int = Field(..., description="有效许可证数")
    revoked_count: int = Field(..., description="已吊销许可证数")
    expired_count: int = Field(..., description="过期许可证数")


class LicenseVerifyRequest(BaseModel):
    """许可证验证请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    license_data: Dict[str, Any] = Field(..., description="许可证数据")
    signature: str = Field(..., description="签名")


class LicenseVerifyResponse(BaseModel):
    """许可证验证响应"""
    valid: bool = Field(..., description="是否有效")
    license_id: Optional[int] = Field(None, description="许可证ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    features: Dict[str, Any] = Field(default_factory=dict, description="功能特性")
    error: Optional[str] = Field(None, description="错误信息")


class LicenseRevokeRequest(BaseModel):
    """许可证吊销请求"""
    reason: Optional[str] = Field(None, description="吊销原因", max_length=500)


class LicenseRenewRequest(BaseModel):
    """许可证续期请求"""
    extend_days: int = Field(..., description="延长天数", ge=1, le=3650)


class LicenseFileResponse(BaseModel):
    """许可证文件响应"""
    license_data: Dict[str, Any] = Field(..., description="许可证数据")
    signature: str = Field(..., description="签名")


class LicenseFileVerifyRequest(BaseModel):
    """许可证文件验证请求"""
    license_data: Dict[str, Any] = Field(..., description="许可证数据")
    signature: str = Field(..., description="签名")
    public_key: Optional[str] = Field(None, description="公钥")


class LicenseFileVerifyResponse(BaseModel):
    """许可证文件验证响应"""
    valid: bool = Field(..., description="是否有效")
    sn: Optional[str] = Field(None, description="设备序列号")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    features: Dict[str, Any] = Field(default_factory=dict, description="功能特性")
    error: Optional[str] = Field(None, description="错误信息")


class LicenseSimpleResponse(BaseModel):
    """许可证简要响应"""
    license_id: int = Field(..., description="许可证ID")
    sn: str = Field(..., description="设备序列号")
    status: str = Field(..., description="状态")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
