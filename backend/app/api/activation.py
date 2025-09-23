"""激活API路由"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from backend.app.database import get_db
from backend.app.common import response_success, response_error, logger
from backend.app.common.exception.errors import (
    InvalidParamsException,
    ChannelNotFoundException,
    ChannelDisabledException,
    ActivationCodeInvalidException,
    ActivationCodeExpiredException,
    DeviceAlreadyActivatedException,
    QuotaExceededException
)
from backend.app.admin.model import Channel, Device, Activation
from backend.app.admin.crud import channel_crud, device_crud, activation_crud
from backend.app.common.auth import hmac_manager


router = APIRouter()


class OnlineActivationRequest(BaseModel):
    """在线激活请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    channel_code: str = Field(..., description="渠道代码", min_length=1, max_length=64)
    activation_code: str = Field(..., description="激活码", min_length=1, max_length=128)
    client_meta: Optional[dict] = Field(default=None, description="客户端元数据")
    challenge_response: Optional[str] = Field(default=None, description="挑战响应")


class OnlineActivationResponse(BaseModel):
    """在线激活响应"""
    activation_id: int = Field(..., description="激活记录ID")
    license_data: dict = Field(..., description="许可证数据")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class ChallengeRequest(BaseModel):
    """挑战请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    channel_code: str = Field(..., description="渠道代码", min_length=1, max_length=64)


class ChallengeResponse(BaseModel):
    """挑战响应"""
    challenge: str = Field(..., description="挑战字符串")
    expires_at: datetime = Field(..., description="过期时间")


class OfflineActivationRequest(BaseModel):
    """离线激活请求"""
    sn: str = Field(..., description="设备序列号", min_length=1, max_length=128)
    client_meta: Optional[dict] = Field(default=None, description="客户端元数据")
    nonce: str = Field(..., description="随机数")
    timestamp: datetime = Field(..., description="时间戳")


class LicenseFileResponse(BaseModel):
    """许可证文件响应"""
    license_data: dict = Field(..., description="许可证数据")
    signature: str = Field(..., description="签名")


async def verify_channel_auth(
    request: Request,
    x_api_key: str = Header(..., description="API密钥"),
    x_signature: str = Header(..., description="HMAC签名"),
    x_timestamp: str = Header(..., description="时间戳"),
    db: AsyncSession = Depends(get_db)
) -> Channel:
    """验证渠道认证"""
    # 查找渠道
    channel = await channel_crud.get_by_api_key(db, x_api_key)
    if not channel:
        raise InvalidAPIKeyException("API密钥无效")
    
    if channel.status != "active":
        raise ChannelDisabledException("渠道已禁用")
    
    # 验证HMAC签名
    if not channel.secret_hmac:
        raise InvalidAPIKeyException("渠道未配置HMAC密钥")
    
    # 构建消息（请求路径 + 时间戳）
    message = f"{request.url.path}{x_timestamp}"
    
    if not hmac_manager.verify_signature(message, x_signature, channel.secret_hmac):
        raise HMACSignatureInvalidException("HMAC签名无效")
    
    # 检查时间戳（防止重放攻击，允许5分钟误差）
    try:
        timestamp = int(x_timestamp)
        current_time = int(datetime.now().timestamp())
        if abs(current_time - timestamp) > 300:  # 5分钟
            raise InvalidParamsException("时间戳无效")
    except ValueError:
        raise InvalidParamsException("时间戳格式错误")
    
    return channel


@router.post("/online", response_model=dict)
async def online_activation(
    request: OnlineActivationRequest,
    request_obj: Request,
    channel: Channel = Depends(verify_channel_auth),
    db: AsyncSession = Depends(get_db)
):
    """在线激活"""
    logger.info(f"在线激活请求: SN={request.sn}, 渠道={request.channel_code}")
    
    # 验证参数
    if request.channel_code != channel.channel_code:
        raise InvalidParamsException("渠道代码不匹配")
    
    # 检查设备是否已激活
    existing_device = await device_crud.get_by_sn(db, request.sn)
    if existing_device and existing_device.status == "activated":
        raise DeviceAlreadyActivatedException("设备已激活")
    
    # 验证激活码
    activation_record = await activation_crud.get_by_code(db, request.activation_code)
    if not activation_record:
        raise ActivationCodeInvalidException("激活码无效")
    
    if activation_record.status != "active":
        raise ActivationCodeInvalidException("激活码已使用")
    
    if activation_record.expires_at and activation_record.expires_at < datetime.now():
        raise ActivationCodeExpiredException("激活码已过期")
    
    # 验证挑战响应（如果提供）
    if request.challenge_response:
        # TODO: 实现挑战响应验证逻辑
        pass
    
    # 创建设备记录（如果不存在）
    if not existing_device:
        device_data = {
            "sn": request.sn,
            "bound_channel_id": channel.channel_id,
            "status": "activated",
            "first_seen": datetime.now(),
            "last_seen": datetime.now()
        }
        device = await device_crud.create(db, device_data)
    else:
        device = await device_crud.update(
            db,
            existing_device.device_id,
            {"status": "activated", "last_seen": datetime.now()}
        )
    
    # 更新激活记录
    await activation_crud.update(
        db,
        activation_record.activation_id,
        {
            "sn": request.sn,
            "activated_at": datetime.now(),
            "status": "used",
            "ip_address": request_obj.client.host,
            "client_meta": request.client_meta
        }
    )
    
    # 生成许可证数据
    license_data = {
        "sn": request.sn,
        "issued_at": datetime.now().isoformat(),
        "expires_at": activation_record.expires_at.isoformat() if activation_record.expires_at else None,
        "channel_code": channel.channel_code,
        "activation_id": activation_record.activation_id,
        "features": {"premium": True},  # TODO: 根据配置生成特性
        "nonce": secrets.token_urlsafe(16),
        "issuer": settings.app_name,
        "pubkey_id": "v1"
    }
    
    # TODO: 生成签名
    license_data["signature"] = "dummy_signature"  # 临时签名
    
    logger.info(f"在线激活成功: SN={request.sn}, 激活ID={activation_record.activation_id}")
    
    return response_success({
        "activation_id": activation_record.activation_id,
        "license_data": license_data,
        "expires_at": activation_record.expires_at
    })


@router.post("/challenge", response_model=dict)
async def request_challenge(
    request: ChallengeRequest,
    channel: Channel = Depends(verify_channel_auth),
    db: AsyncSession = Depends(get_db)
):
    """请求挑战"""
    logger.info(f"挑战请求: SN={request.sn}, 渠道={request.channel_code}")
    
    # 验证渠道代码
    if request.channel_code != channel.channel_code:
        raise InvalidParamsException("渠道代码不匹配")
    
    # 生成挑战
    challenge = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # 存储挑战到Redis（用于后续验证）
    challenge_key = f"challenge:{request.sn}:{channel.channel_code}"
    challenge_data = {
        "challenge": challenge,
        "expires_at": expires_at.isoformat(),
        "sn": request.sn,
        "channel_code": request.channel_code
    }
    
    # TODO: 存储到Redis
    # await redis_client.set_json(challenge_key, challenge_data, expire=300)
    
    logger.info(f"挑战生成成功: SN={request.sn}")
    
    return response_success({
        "challenge": challenge,
        "expires_at": expires_at
    })


@router.post("/offline/request", response_model=dict)
async def offline_activation_request(
    request: OfflineActivationRequest,
    db: AsyncSession = Depends(get_db)
):
    """离线激活请求"""
    logger.info(f"离线激活请求: SN={request.sn}")
    
    # TODO: 实现离线激活请求逻辑
    # 1. 验证设备
    # 2. 生成离线激活请求记录
    # 3. 返回请求ID
    
    return response_success({
        "request_id": 12345,  # 临时ID
        "message": "离线激活请求已提交，请联系管理员处理"
    })


@router.post("/offline/complete/{request_id}", response_model=dict)
async def offline_activation_complete(
    request_id: int,
    db: AsyncSession = Depends(get_db)
):
    """完成离线激活"""
    logger.info(f"完成离线激活: 请求ID={request_id}")
    
    # TODO: 实现离线激活完成逻辑
    # 1. 验证请求ID
    # 2. 生成许可证文件
    # 3. 返回许可证数据
    
    license_data = {
        "sn": "S123456789",
        "issued_at": datetime.now().isoformat(),
        "expires_at": None,
        "channel_code": "CH_OFFLINE",
        "activation_id": request_id,
        "features": {"premium": True},
        "nonce": secrets.token_urlsafe(16),
        "issuer": settings.app_name,
        "pubkey_id": "v1",
        "signature": "offline_signature"
    }
    
    return response_success({
        "license_data": license_data
    })


@router.get("/status/{sn}", response_model=dict)
async def get_activation_status(
    sn: str,
    db: AsyncSession = Depends(get_db)
):
    """获取激活状态"""
    logger.info(f"查询激活状态: SN={sn}")
    
    # 查找设备
    device = await device_crud.get_by_sn(db, sn)
    if not device:
        return response_success({
            "activated": False,
            "message": "设备未找到"
        })
    
    # 查找最新激活记录
    activation = await activation_crud.get_latest_by_sn(db, sn)
    
    result = {
        "activated": device.status == "activated",
        "device_status": device.status,
        "first_seen": device.first_seen,
        "last_seen": device.last_seen,
        "bound_channel": device.bound_channel_id
    }
    
    if activation:
        result.update({
            "activation_id": activation.activation_id,
            "activated_at": activation.activated_at,
            "expires_at": activation.expires_at,
            "status": activation.status,
            "is_offline": activation.is_offline
        })
    
    return response_success(result)
