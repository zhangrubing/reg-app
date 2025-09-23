"""响应格式标准化模块"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = Field(..., description="响应码")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: str = Field(..., description="时间戳")


class PaginationModel(BaseModel):
    """分页信息模型"""
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    total: int = Field(..., description="总记录数")
    pages: int = Field(..., description="总页数")


class PaginatedResponseModel(BaseModel, Generic[T]):
    """分页响应模型"""
    code: int = Field(..., description="响应码")
    message: str = Field(..., description="响应消息")
    data: list[T] = Field(..., description="数据列表")
    pagination: PaginationModel = Field(..., description="分页信息")
    timestamp: str = Field(..., description="时间戳")


def response_success(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
    """成功响应"""
    from datetime import datetime
    
    return {
        "code": 0,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }


def response_error(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """错误响应"""
    from datetime import datetime
    
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }


def response_pagination(
    data: list[Any],
    page: int,
    size: int,
    total: int,
    message: str = "操作成功"
) -> dict[str, Any]:
    """分页响应"""
    from datetime import datetime
    
    pages = (total + size - 1) // size
    
    return {
        "code": 0,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": pages
        },
        "timestamp": datetime.now().isoformat()
    }


# 常用响应模型
class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class MessageResponse(BaseModel):
    """消息响应"""
    message: str = Field(..., description="消息内容")


class StatusResponse(BaseModel):
    """状态响应"""
    status: bool = Field(..., description="状态")
    message: str = Field(..., description="消息")


class IDResponse(BaseModel):
    """ID响应"""
    id: int = Field(..., description="ID")


class ListResponse(BaseModel):
    """列表响应"""
    items: list[Any] = Field(..., description="项目列表")
    total: int = Field(..., description="总数")


class FileResponse(BaseModel):
    """文件响应"""
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="文件URL")
    size: int = Field(..., description="文件大小（字节）")
    content_type: str = Field(..., description="文件类型")


class QRCodeResponse(BaseModel):
    """二维码响应"""
    qr_code: str = Field(..., description="二维码Base64数据")
    secret: str = Field(..., description="密钥")
    otpauth_uri: str = Field(..., description="OTPAuth URI")


class BackupCodesResponse(BaseModel):
    """备份码响应"""
    codes: list[str] = Field(..., description="备份码列表")


# 导出
__all__ = [
    "ResponseModel",
    "PaginationModel", 
    "PaginatedResponseModel",
    "response_success",
    "response_error",
    "response_pagination",
    "TokenResponse",
    "MessageResponse",
    "StatusResponse",
    "IDResponse",
    "ListResponse",
    "FileResponse",
    "QRCodeResponse",
    "BackupCodesResponse"
]
