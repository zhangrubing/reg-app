"""激活记录业务逻辑"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import activation_crud, channel_crud, device_crud
from backend.app.admin.model import Activation
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException
)
from backend.app.common.log import logger
from backend.app.common.auth.crypto import generate_activation_code, generate_license_signature, generate_secure_token


class ActivationService:
    """激活记录业务逻辑类"""
    
    async def create_activation(
        self,
        db: AsyncSession,
        channel_id: int,
        activation_code: Optional[str] = None,
        expires_days: Optional[int] = None,
        max_uses: int = 1,
        amount_due: float = 0.0,
        billing_period: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Activation:
        """创建激活记录"""
        # 验证渠道
        channel = await channel_crud.get(db, channel_id)
        if not channel:
            raise NotFoundException("渠道不存在")
        
        if channel.status != "active":
            raise BusinessException("渠道已禁用")
        
        # 生成激活码（如果未提供）
        if not activation_code:
            activation_code = generate_activation_code()
        
        # 检查激活码是否已存在
        existing = await activation_crud.get_by_code(db, activation_code)
        if existing:
            raise BusinessException("激活码已存在")
        
        # 计算过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # 创建激活记录
        activation_data = {
            "activation_code": activation_code,
            "channel_id": channel_id,
            "channel_code": channel.channel_code,
            "max_uses": max_uses,
            "expires_at": expires_at,
            "amount_due": amount_due,
            "billing_period": billing_period,
            "notes": notes,
            "status": "active"
        }
        
        activation = await activation_crud.create(db, activation_data)
        
        logger.info(f"创建激活记录成功: ID={activation.activation_id}, 代码={activation_code}")
        
        return activation
    
    async def activate_device(
        self,
        db: AsyncSession,
        sn: str,
        channel_code: str,
        activation_code: str,
        ip_address: Optional[str] = None,
        client_meta: Optional[Dict[str, Any]] = None,
        is_offline: bool = False
    ) -> Dict[str, Any]:
        """激活设备"""
        # 验证激活码
        activation = await activation_crud.get_by_code(db, activation_code)
        if not activation:
            raise NotFoundException("激活码无效")
        
        if activation.status != "active":
            raise BusinessException("激活码已使用")
        
        if activation.expires_at and activation.expires_at < datetime.now():
            raise BusinessException("激活码已过期")
        
        # 验证渠道代码
        if activation.channel_code != channel_code:
            raise InvalidParamsException("渠道代码不匹配")
        
        # 检查设备是否已激活
        device = await device_crud.get_by_sn(db, sn)
        if device and device.status == "activated":
            raise BusinessException("设备已激活")
        
        # 更新激活记录
        update_data = {
            "sn": sn,
            "activated_at": datetime.now(),
            "status": "used",
            "ip_address": ip_address,
            "client_meta": client_meta,
            "is_offline": is_offline
        }
        
        activation = await activation_crud.update(db, activation.activation_id, update_data)
        
        # 创建设备或更新设备状态
        if not device:
            device_data = {
                "sn": sn,
                "channel_id": activation.channel_id,
                "status": "activated",
                "activated_at": datetime.now()
            }
            device = await device_crud.create(db, device_data)
        else:
            device = await device_crud.update(
                db,
                device.device_id,
                {
                    "status": "activated",
                    "channel_id": activation.channel_id,
                    "activated_at": datetime.now()
                }
            )
        
        # 生成许可证数据
        license_data = {
            "sn": sn,
            "issued_at": datetime.now().isoformat(),
            "expires_at": activation.expires_at.isoformat() if activation.expires_at else None,
            "channel_code": channel_code,
            "activation_id": activation.activation_id,
            "features": {"premium": True},  # TODO: 根据配置生成特性
            "nonce": generate_activation_code(16),
            "issuer": "英智软件注册系统",
            "pubkey_id": "v1"
        }
        
        # 生成签名
        signature = generate_license_signature(license_data)
        license_data["signature"] = signature
        
        logger.info(f"设备激活成功: SN={sn}, 激活ID={activation.activation_id}")
        
        return {
            "activation_id": activation.activation_id,
            "license_data": license_data,
            "expires_at": activation.expires_at,
            "device_id": device.device_id
        }
    
    async def get_activation_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        channel_id: Optional[int] = None,
        sn: Optional[str] = None
    ) -> List[Activation]:
        """获取激活记录列表"""
        return await activation_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            channel_id=channel_id,
            sn=sn
        )
    
    async def get_activation_detail(self, db: AsyncSession, activation_id: int) -> Activation:
        """获取激活记录详情"""
        activation = await activation_crud.get(db, activation_id)
        if not activation:
            raise NotFoundException("激活记录不存在")
        return activation
    
    async def update_activation(
        self,
        db: AsyncSession,
        activation_id: int,
        update_data: Dict[str, Any]
    ) -> Activation:
        """更新激活记录"""
        return await activation_crud.update(db, activation_id, update_data)
    
    async def delete_activation(self, db: AsyncSession, activation_id: int) -> None:
        """删除激活记录"""
        await activation_crud.delete(db, activation_id)
    
    async def get_activation_status(self, db: AsyncSession, sn: str) -> Dict[str, Any]:
        """获取设备激活状态"""
        # 查找设备
        device = await device_crud.get_by_sn(db, sn)
        if not device:
            return {
                "activated": False,
                "message": "设备未找到"
            }
        
        # 查找最新激活记录
        activation = await activation_crud.get_latest_by_sn(db, sn)
        
        result = {
            "activated": device.status == "activated",
            "device_status": device.status,
            "first_seen": device.first_seen,
            "last_seen": device.last_seen,
            "bound_channel": device.channel_id
        }
        
        if activation:
            result.update({
                "activation_id": activation.activation_id,
                "activated_at": activation.activated_at,
                "expires_at": activation.expires_at,
                "status": activation.status,
                "is_offline": activation.is_offline
            })
        
        return result
    
    async def get_activation_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取激活统计信息"""
        from sqlalchemy import func
        
        # 总激活记录数
        total_result = await db.execute(select(func.count(Activation.activation_id)))
        total_count = total_result.scalar()
        
        # 活跃激活码数
        active_count = await activation_crud.count_by_status(db, "active")
        
        # 已使用激活码数
        used_count = await activation_crud.count_by_status(db, "used")
        
        # 过期激活码数
        expired_activations = await activation_crud.get_expired_activations(db)
        expired_count = len(expired_activations)
        
        # 今日激活数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await db.execute(
            select(func.count(Activation.activation_id))
            .where(Activation.activated_at >= today_start)
        )
        today_count = today_result.scalar()
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "used_count": used_count,
            "expired_count": expired_count,
            "today_count": today_count
        }
    
    async def batch_create_activations(
        self,
        db: AsyncSession,
        channel_id: int,
        count: int,
        expires_days: Optional[int] = None,
        max_uses: int = 1
    ) -> List[Activation]:
        """批量创建激活码"""
        if count <= 0 or count > 1000:
            raise InvalidParamsException("批量创建数量必须在1-1000之间")
        
        activations = []
        for i in range(count):
            try:
                activation = await self.create_activation(
                    db=db,
                    channel_id=channel_id,
                    expires_days=expires_days,
                    max_uses=max_uses
                )
                activations.append(activation)
            except Exception as e:
                logger.error(f"批量创建激活码失败第{i+1}个: {str(e)}")
                continue
        
        logger.info(f"批量创建激活码完成: 成功创建{len(activations)}个")
        
        return activations
    
    async def revoke_activation(
        self,
        db: AsyncSession,
        activation_id: int,
        reason: Optional[str] = None
    ) -> Activation:
        """吊销激活码"""
        activation = await activation_crud.get(db, activation_id)
        if not activation:
            raise NotFoundException("激活记录不存在")
        
        if activation.status == "revoked":
            raise BusinessException("激活码已吊销")
        
        update_data = {
            "status": "revoked",
            "notes": f"吊销原因: {reason}" if reason else "已吊销"
        }
        
        activation = await activation_crud.update(db, activation_id, update_data)
        
        logger.info(f"激活码吊销成功: ID={activation_id}")
        
        return activation


# 创建实例
activation_service = ActivationService()
