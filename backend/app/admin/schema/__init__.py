"""Schema数据模型模块"""
from __future__ import annotations

from .activation import *
from .channel import *
from .device import *
from .license import *
from .user import *
from .audit import *

__all__ = [
    # 激活记录相关
    "ActivationCreate", "ActivationUpdate", "ActivationResponse", "ActivationListResponse",
    "ActivationStatisticsResponse", "BatchActivationCreate",
    
    # 渠道相关
    "ChannelCreate", "ChannelUpdate", "ChannelResponse", "ChannelListResponse",
    "ChannelStatisticsResponse", "ChannelDetailResponse",
    
    # 设备相关
    "DeviceCreate", "DeviceUpdate", "DeviceResponse", "DeviceListResponse",
    "DeviceStatisticsResponse", "DeviceDetailResponse",
    
    # 许可证相关
    "LicenseCreate", "LicenseUpdate", "LicenseResponse", "LicenseListResponse",
    "LicenseStatisticsResponse", "LicenseVerifyRequest", "LicenseVerifyResponse",
    
    # 用户相关
    "UserCreate", "UserUpdate", "UserResponse", "UserListResponse",
    "UserStatisticsResponse", "UserLoginRequest", "UserLoginResponse",
    "PasswordResetRequest",
    
    # 审计日志相关
    "AuditLogResponse", "AuditLogListResponse", "SystemLogResponse", "SystemLogListResponse",
    "AuditStatisticsResponse", "LogSearchRequest", "LogExportRequest"
]
