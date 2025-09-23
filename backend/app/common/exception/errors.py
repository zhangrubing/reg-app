"""错误定义模块"""
from __future__ import annotations

from typing import Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ErrorCode:
    """错误码定义"""
    # 通用错误
    SUCCESS = (0, "成功")
    INTERNAL_ERROR = (1000, "内部服务器错误")
    INVALID_PARAMS = (1001, "参数错误")
    UNAUTHORIZED = (1002, "未授权")
    FORBIDDEN = (1003, "权限不足")
    NOT_FOUND = (1004, "资源不存在")
    METHOD_NOT_ALLOWED = (1005, "方法不允许")
    
    # 认证相关错误
    INVALID_CREDENTIALS = (2000, "用户名或密码错误")
    TOKEN_EXPIRED = (2001, "令牌已过期")
    TOKEN_INVALID = (2002, "令牌无效")
    MFA_REQUIRED = (2003, "需要二次验证")
    MFA_INVALID = (2004, "二次验证失败")
    
    # 渠道相关错误
    CHANNEL_NOT_FOUND = (3000, "渠道不存在")
    CHANNEL_DISABLED = (3001, "渠道已禁用")
    INVALID_API_KEY = (3002, "API密钥无效")
    HMAC_SIGNATURE_INVALID = (3003, "HMAC签名无效")
    
    # 激活相关错误
    ACTIVATION_CODE_INVALID = (4000, "激活码无效")
    ACTIVATION_CODE_EXPIRED = (4001, "激活码已过期")
    ACTIVATION_CODE_USED = (4002, "激活码已使用")
    DEVICE_ALREADY_ACTIVATED = (4003, "设备已激活")
    QUOTA_EXCEEDED = (4004, "配额不足")
    
    # 设备相关错误
    DEVICE_NOT_FOUND = (5000, "设备不存在")
    DEVICE_SECRET_INVALID = (5001, "设备密钥无效")
    CHALLENGE_EXPIRED = (5002, "挑战已过期")
    CHALLENGE_INVALID = (5003, "挑战无效")


class ErrorDetail(BaseModel):
    """错误详情模型"""
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    detail: Optional[Any] = Field(None, description="详细错误信息")
    field: Optional[str] = Field(None, description="错误字段")


class BaseErrorException(HTTPException):
    """基础错误异常"""
    
    def __init__(
        self,
        error_code: tuple[int, str],
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: Any = None,
        field: str = None,
        headers: dict[str, Any] | None = None
    ):
        self.error_code = error_code[0]
        self.error_message = error_code[1]
        self.field = field
        
        error_detail = ErrorDetail(
            code=self.error_code,
            message=self.error_message,
            detail=detail,
            field=field
        )
        
        super().__init__(
            status_code=status_code,
            detail=error_detail.model_dump(),
            headers=headers
        )


class InternalErrorException(BaseErrorException):
    """内部服务器错误"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.INTERNAL_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class InvalidParamsException(BaseErrorException):
    """参数错误"""
    def __init__(self, detail: Any = None, field: str = None):
        super().__init__(
            ErrorCode.INVALID_PARAMS,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            field=field
        )


class UnauthorizedException(BaseErrorException):
    """未授权错误"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ForbiddenException(BaseErrorException):
    """权限不足错误"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class NotFoundException(BaseErrorException):
    """资源不存在错误"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class InvalidCredentialsException(BaseErrorException):
    """认证凭据无效"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.INVALID_CREDENTIALS,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class TokenExpiredException(BaseErrorException):
    """令牌过期"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.TOKEN_EXPIRED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class MFARequiredException(BaseErrorException):
    """需要二次验证"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.MFA_REQUIRED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class MFAInvalidException(BaseErrorException):
    """二次验证失败"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.MFA_INVALID,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ChannelNotFoundException(BaseErrorException):
    """渠道不存在"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.CHANNEL_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ChannelDisabledException(BaseErrorException):
    """渠道已禁用"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.CHANNEL_DISABLED,
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class InvalidAPIKeyException(BaseErrorException):
    """API密钥无效"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.INVALID_API_KEY,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class HMACSignatureInvalidException(BaseErrorException):
    """HMAC签名无效"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.HMAC_SIGNATURE_INVALID,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ActivationCodeInvalidException(BaseErrorException):
    """激活码无效"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.ACTIVATION_CODE_INVALID,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ActivationCodeExpiredException(BaseErrorException):
    """激活码已过期"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.ACTIVATION_CODE_EXPIRED,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class DeviceAlreadyActivatedException(BaseErrorException):
    """设备已激活"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.DEVICE_ALREADY_ACTIVATED,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class QuotaExceededException(BaseErrorException):
    """配额不足"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.QUOTA_EXCEEDED,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class DeviceNotFoundException(BaseErrorException):
    """设备不存在"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.DEVICE_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ChallengeExpiredException(BaseErrorException):
    """挑战已过期"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.CHALLENGE_EXPIRED,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ChallengeInvalidException(BaseErrorException):
    """挑战无效"""
    def __init__(self, detail: Any = None):
        super().__init__(
            ErrorCode.CHALLENGE_INVALID,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
