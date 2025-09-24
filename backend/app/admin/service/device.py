"""设备业务逻辑"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import device_crud, channel_crud, activation_crud
from backend.app.admin.model import Device
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException
)
from backend.app.common.log import logger


class DeviceService:
    """设备业务逻辑类"""
    
    async def register_device(
        self,
        db: AsyncSession,
        sn: str,
        channel_id: Optional[int] = None,
        client_meta: Optional[Dict[str, Any]] = None
    ) -> Device:
        """注册设备"""
        # 检查设备是否已存在
        existing_device = await device_crud.get_by_sn(db, sn)
        if existing_device:
            # 更新设备最后在线时间
            await device_crud.update_last_seen(db, sn)
            return existing_device
        
        # 创建设备
        device_data = {
            "sn": sn,
            "channel_id": channel_id,
            "status": "pending",
            "client_meta": client_meta
        }
        
        device = await device_crud.create(db, device_data)
        
        logger.info(f"设备注册成功: SN={sn}, ID={device.device_id}")
        
        return device
    
    async def update_device_status(
        self,
        db: AsyncSession,
        device_id: int,
        status: str,
        reason: Optional[str] = None
    ) -> Device:
        """更新设备状态"""
        device = await device_crud.get(db, device_id)
        if not device:
            raise NotFoundException("设备不存在")
        
        valid_statuses = ["pending", "activated", "suspended", "expired", "revoked"]
        if status not in valid_statuses:
            raise InvalidParamsException(f"无效的设备状态，可选值: {', '.join(valid_statuses)}")
        
        update_data = {"status": status}
        if reason:
            update_data["notes"] = reason
        
        device = await device_crud.update(db, device_id, update_data)
        
        logger.info(f"设备状态更新成功: ID={device_id}, 状态={status}")
        
        return device
    
    async def get_device_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取设备统计信息"""
        from sqlalchemy import func
        
        # 总设备数
        total_result = await db.execute(select(func.count(Device.device_id)))
        total_count = total_result.scalar()
        
        # 已激活设备数
        activated_count = await device_crud.count_by_status(db, "activated")
        
        # 待激活设备数
        pending_count = await device_crud.count_by_status(db, "pending")
        
        # 暂停设备数
        suspended_count = await device_crud.count_by_status(db, "suspended")
        
        # 今日新注册设备数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await db.execute(
            select(func.count(Device.device_id))
            .where(Device.created_at >= today_start)
        )
        today_count = today_result.scalar()
        
        # 最近7天设备注册趋势
        seven_days_ago = datetime.now() - timedelta(days=7)
        trend_result = await db.execute(
            select(
                func.date(Device.created_at).label('date'),
                func.count(Device.device_id).label('count')
            )
            .where(Device.created_at >= seven_days_ago)
            .group_by(func.date(Device.created_at))
            .order_by(func.date(Device.created_at))
        )
        
        trend_data = [{"date": str(row[0]), "count": row[1]} for row in trend_result.fetchall()]
        
        return {
            "total_count": total_count,
            "activated_count": activated_count,
            "pending_count": pending_count,
            "suspended_count": suspended_count,
            "today_count": today_count,
            "weekly_trend": trend_data
        }
    
    async def get_device_detail(self, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """获取设备详情（包含激活信息）"""
        device = await device_crud.get(db, device_id)
        if not device:
            raise NotFoundException("设备不存在")
        
        # 获取激活记录
        activations = await activation_crud.get_by_sn(db, device.sn)
        
        # 获取渠道信息
        channel = None
        if device.channel_id:
            channel = await channel_crud.get(db, device.channel_id)
        
        return {
            "device": device,
            "activations": activations,
            "channel": channel
        }
    
    async def batch_update_device_status(
        self,
        db: AsyncSession,
        device_ids: List[int],
        status: str
    ) -> Dict[str, Any]:
        """批量更新设备状态"""
        valid_statuses = ["pending", "activated", "suspended", "expired", "revoked"]
        if status not in valid_statuses:
            raise InvalidParamsException(f"无效的设备状态，可选值: {', '.join(valid_statuses)}")
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for device_id in device_ids:
            try:
                await self.update_device_status(db, device_id, status)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"设备ID {device_id}: {str(e)}")
        
        logger.info(f"批量更新设备状态完成: 成功{success_count}个, 失败{failed_count}个")
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def cleanup_inactive_devices(
        self,
        db: AsyncSession,
        days: int = 90
    ) -> int:
        """清理长时间未活动的设备"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 获取长时间未活动的设备
        from sqlalchemy import and_
        
        result = await db.execute(
            select(Device)
            .where(
                and_(
                    Device.last_seen < cutoff_date,
                    Device.status.in_(["pending", "suspended"])
                )
            )
        )
        inactive_devices = result.scalars().all()
        
        # 删除设备
        deleted_count = 0
        for device in inactive_devices:
            try:
                await device_crud.delete(db, device.device_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除设备失败 ID={device.device_id}: {str(e)}")
                continue
        
        logger.info(f"清理未活动设备完成: 删除{deleted_count}个设备")
        
        return deleted_count
    
    async def get_device_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        channel_id: Optional[int] = None,
        sn: Optional[str] = None
    ) -> List[Device]:
        """获取设备列表"""
        return await device_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            channel_id=channel_id,
            sn=sn
        )
    
    async def delete_device(self, db: AsyncSession, device_id: int) -> None:
        """删除设备"""
        device = await device_crud.get(db, device_id)
        if not device:
            raise NotFoundException("设备不存在")
        
        await device_crud.delete(db, device_id)
        
        logger.info(f"删除设备成功: ID={device_id}, SN={device.sn}")
    
    async def heartbeat(self, db: AsyncSession, sn: str, client_meta: Optional[Dict[str, Any]] = None) -> Device:
        """设备心跳"""
        device = await device_crud.get_by_sn(db, sn)
        if not device:
            raise NotFoundException("设备不存在")
        
        # 更新设备最后在线时间和客户端信息
        update_data = {"last_seen": datetime.now()}
        if client_meta:
            update_data["client_meta"] = client_meta
        
        device = await device_crud.update(db, device.device_id, update_data)
        
        return device


# 创建实例
device_service = DeviceService()
