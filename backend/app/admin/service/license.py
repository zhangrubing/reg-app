"""许可证业务逻辑"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import license_crud, activation_crud, device_crud
from backend.app.admin.model import License
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException
)
from backend.app.common.log import logger
from backend.app.common.auth.crypto import generate_license_signature, verify_license_signature


class LicenseService:
    """许可证业务逻辑类"""
    
    async def generate_license(
        self,
        db: AsyncSession,
        sn: str,
        activation_id: int,
        expires_days: Optional[int] = None,
        features: Optional[Dict[str, Any]] = None
    ) -> License:
        """生成许可证"""
        # 验证激活记录
        activation = await activation_crud.get(db, activation_id)
        if not activation:
            raise NotFoundException("激活记录不存在")
        
        if activation.sn != sn:
            raise InvalidParamsException("设备序列号与激活记录不匹配")
        
        if activation.status != "used":
            raise BusinessException("激活记录状态无效")
        
        # 验证设备
        device = await device_crud.get_by_sn(db, sn)
        if not device:
            raise NotFoundException("设备不存在")
        
        if device.status != "activated":
            raise BusinessException("设备未激活")
        
        # 计算过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        elif activation.expires_at:
            expires_at = activation.expires_at
        
        # 生成许可证数据
        license_data = {
            "sn": sn,
            "issued_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "channel_code": activation.channel_code,
            "activation_id": activation_id,
            "features": features or {"premium": True},
            "nonce": generate_license_signature(16),
            "issuer": "软件注册与激活系统",
            "pubkey_id": "v1"
        }
        
        # 生成签名
        signature = generate_license_signature(license_data)
        
        # 创建许可证记录
        license_record_data = {
            "sn": sn,
            "activation_id": activation_id,
            "license_data": license_data,
            "signature": signature,
            "expires_at": expires_at
        }
        
        license_record = await license_crud.create(db, license_record_data)
        
        logger.info(f"许可证生成成功: ID={license_record.license_id}, SN={sn}")
        
        return license_record
    
    async def verify_license(
        self,
        db: AsyncSession,
        sn: str,
        license_data: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """验证许可证"""
        # 验证签名
        if not verify_license_signature(license_data, signature):
            raise BusinessException("许可证签名无效")
        
        # 查找许可证记录
        license_record = await license_crud.get_active_by_sn(db, sn)
        if not license_record:
            raise NotFoundException("未找到有效的许可证")
        
        # 检查许可证是否被吊销
        if license_record.revoked_at:
            raise BusinessException("许可证已被吊销")
        
        # 检查许可证是否过期
        if license_record.expires_at and license_record.expires_at < datetime.now():
            raise BusinessException("许可证已过期")
        
        # 验证设备序列号
        if license_record.sn != sn:
            raise InvalidParamsException("许可证与设备不匹配")
        
        # 更新设备最后在线时间
        await device_crud.update_last_seen(db, sn)
        
        return {
            "valid": True,
            "license_id": license_record.license_id,
            "expires_at": license_record.expires_at,
            "features": license_data.get("features", {})
        }
    
    async def revoke_license(
        self,
        db: AsyncSession,
        license_id: int,
        reason: Optional[str] = None
    ) -> License:
        """吊销许可证"""
        license_record = await license_crud.get(db, license_id)
        if not license_record:
            raise NotFoundException("许可证不存在")
        
        if license_record.revoked_at:
            raise BusinessException("许可证已吊销")
        
        # 吊销许可证
        license_record = await license_crud.revoke(db, license_id, reason)
        
        # 更新相关设备状态
        device = await device_crud.get_by_sn(db, license_record.sn)
        if device and device.status == "activated":
            await device_crud.update(
                db,
                device.device_id,
                {"status": "suspended", "notes": f"许可证被吊销: {reason}" if reason else "许可证被吊销"}
            )
        
        logger.info(f"许可证吊销成功: ID={license_id}, SN={license_record.sn}")
        
        return license_record
    
    async def get_license_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        sn: Optional[str] = None,
        activation_id: Optional[int] = None,
        is_revoked: Optional[bool] = None
    ) -> List[License]:
        """获取许可证列表"""
        return await license_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sn=sn,
            activation_id=activation_id,
            is_revoked=is_revoked
        )
    
    async def get_license_detail(self, db: AsyncSession, license_id: int) -> License:
        """获取许可证详情"""
        license_record = await license_crud.get(db, license_id)
        if not license_record:
            raise NotFoundException("许可证不存在")
        return license_record
    
    async def update_license(
        self,
        db: AsyncSession,
        license_id: int,
        update_data: Dict[str, Any]
    ) -> License:
        """更新许可证"""
        return await license_crud.update(db, license_id, update_data)
    
    async def delete_license(self, db: AsyncSession, license_id: int) -> None:
        """删除许可证"""
        await license_crud.delete(db, license_id)
    
    async def get_license_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取许可证统计信息"""
        from sqlalchemy import func
        
        # 总许可证数
        total_result = await db.execute(select(func.count(License.license_id)))
        total_count = total_result.scalar()
        
        # 有效许可证数
        active_count = await license_crud.count_active(db)
        
        # 已吊销许可证数
        revoked_result = await db.execute(
            select(func.count(License.license_id))
            .where(License.revoked_at.is_not(None))
        )
        revoked_count = revoked_result.scalar()
        
        # 过期许可证数
        current_time = datetime.now()
        expired_result = await db.execute(
            select(func.count(License.license_id))
            .where(
                and_(
                    License.expires_at < current_time,
                    License.revoked_at.is_(None)
                )
            )
        )
        expired_count = expired_result.scalar()
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "revoked_count": revoked_count,
            "expired_count": expired_count
        }
    
    async def renew_license(
        self,
        db: AsyncSession,
        license_id: int,
        extend_days: int
    ) -> License:
        """续期许可证"""
        if extend_days <= 0:
            raise InvalidParamsException("续期天数必须大于0")
        
        license_record = await license_crud.get(db, license_id)
        if not license_record:
            raise NotFoundException("许可证不存在")
        
        if license_record.revoked_at:
            raise BusinessException("许可证已吊销，无法续期")
        
        # 计算新的过期时间
        current_time = datetime.now()
        if license_record.expires_at:
            if license_record.expires_at < current_time:
                # 已过期，从当前时间开始计算
                new_expires_at = current_time + timedelta(days=extend_days)
            else:
                # 未过期，在原有基础上延长
                new_expires_at = license_record.expires_at + timedelta(days=extend_days)
        else:
            # 永久许可证，设置为从当前时间开始的新期限
            new_expires_at = current_time + timedelta(days=extend_days)
        
        # 更新许可证
        license_record = await license_crud.update(
            db,
            license_id,
            {"expires_at": new_expires_at}
        )
        
        logger.info(f"许可证续期成功: ID={license_id}, 新过期时间={new_expires_at}")
        
        return license_record
    
    async def get_device_licenses(
        self,
        db: AsyncSession,
        sn: str
    ) -> List[License]:
        """获取设备的所有许可证"""
        device = await device_crud.get_by_sn(db, sn)
        if not device:
            raise NotFoundException("设备不存在")
        
        return await license_crud.get_by_sn(db, sn)
    
    async def validate_license_file(
        self,
        license_data: Dict[str, Any],
        signature: str,
        public_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证许可证文件（离线验证）"""
        try:
            # 验证签名
            if not verify_license_signature(license_data, signature, public_key):
                return {
                    "valid": False,
                    "error": "许可证签名无效"
                }
            
            # 检查过期时间
            expires_at_str = license_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at < datetime.now():
                    return {
                        "valid": False,
                        "error": "许可证已过期"
                    }
            
            return {
                "valid": True,
                "expires_at": expires_at_str,
                "features": license_data.get("features", {}),
                "sn": license_data.get("sn")
            }
        
        except Exception as e:
            return {
                "valid": False,
                "error": f"许可证验证失败: {str(e)}"
            }


# 创建实例
license_service = LicenseService()
