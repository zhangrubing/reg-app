"""渠道业务逻辑"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.admin.crud import channel_crud
from backend.app.admin.model import Channel
from backend.app.common.exception.errors import (
    NotFoundException,
    BusinessException,
    InvalidParamsException
)
from backend.app.common.log import logger
from backend.app.common.auth.crypto import generate_api_key, generate_hmac_secret


class ChannelService:
    """渠道业务逻辑类"""
    
    async def create_channel(
        self,
        db: AsyncSession,
        channel_code: str,
        name: str,
        status: str = "active",
        description: Optional[str] = None,
        contact_person: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Channel:
        """创建渠道"""
        # 验证渠道代码是否已存在
        existing = await channel_crud.get_by_code(db, channel_code)
        if existing:
            raise BusinessException("渠道代码已存在")
        
        # 生成API密钥和HMAC密钥
        api_key = generate_api_key()
        secret_hmac = generate_hmac_secret()
        
        # 创建渠道数据
        channel_data = {
            "channel_code": channel_code,
            "name": name,
            "api_key": api_key,
            "secret_hmac": secret_hmac,
            "status": status,
            "description": description,
            "contact_person": contact_person,
            "contact_email": contact_email,
            "contact_phone": contact_phone
        }
        
        channel = await channel_crud.create(db, channel_data)
        
        logger.info(f"创建渠道成功: ID={channel.channel_id}, 代码={channel_code}")
        
        return channel
    
    async def update_channel(
        self,
        db: AsyncSession,
        channel_id: int,
        name: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        contact_person: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Channel:
        """更新渠道信息"""
        channel = await channel_crud.get(db, channel_id)
        if not channel:
            raise NotFoundException("渠道不存在")
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if status is not None:
            update_data["status"] = status
        if description is not None:
            update_data["description"] = description
        if contact_person is not None:
            update_data["contact_person"] = contact_person
        if contact_email is not None:
            update_data["contact_email"] = contact_email
        if contact_phone is not None:
            update_data["contact_phone"] = contact_phone
        
        if update_data:
            channel = await channel_crud.update(db, channel_id, update_data)
            logger.info(f"更新渠道成功: ID={channel_id}")
        
        return channel
    
    async def regenerate_api_key(
        self,
        db: AsyncSession,
        channel_id: int
    ) -> Dict[str, str]:
        """重新生成API密钥"""
        channel = await channel_crud.get(db, channel_id)
        if not channel:
            raise NotFoundException("渠道不存在")
        
        # 生成新的API密钥和HMAC密钥
        new_api_key = generate_api_key()
        new_secret_hmac = generate_hmac_secret()
        
        update_data = {
            "api_key": new_api_key,
            "secret_hmac": new_secret_hmac
        }
        
        await channel_crud.update(db, channel_id, update_data)
        
        logger.info(f"重新生成API密钥成功: 渠道ID={channel_id}")
        
        return {
            "api_key": new_api_key,
            "secret_hmac": new_secret_hmac
        }
    
    async def get_channel_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """获取渠道统计信息"""
        from sqlalchemy import func
        
        # 总渠道数
        total_result = await db.execute(select(func.count(Channel.channel_id)))
        total_count = total_result.scalar()
        
        # 活跃渠道数
        active_count = await channel_crud.count_active(db)
        
        # 禁用渠道数
        disabled_result = await db.execute(
            select(func.count(Channel.channel_id))
            .where(Channel.status == "inactive")
        )
        disabled_count = disabled_result.scalar()
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "disabled_count": disabled_count
        }
    
    async def delete_channel(self, db: AsyncSession, channel_id: int) -> None:
        """删除渠道"""
        channel = await channel_crud.get(db, channel_id)
        if not channel:
            raise NotFoundException("渠道不存在")
        
        # 检查是否有相关的激活记录
        from backend.app.admin.crud import activation_crud
        activation_count = await activation_crud.count_by_channel(db, channel_id)
        
        if activation_count > 0:
            raise BusinessException(f"渠道有关联的激活记录({activation_count}条)，无法删除")
        
        await channel_crud.delete(db, channel_id)
        
        logger.info(f"删除渠道成功: ID={channel_id}")
    
    async def get_channel_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Channel]:
        """获取渠道列表"""
        return await channel_crud.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            search=search
        )
    
    
    async def get_channel_detail(self, db: AsyncSession, channel_id: int) -> Dict[str, Any]:
        """获取渠道详情（包含统计信息）"""
        channel = await channel_crud.get(db, channel_id)
        if not channel:
            raise NotFoundException("渠道不存在")
        
        # 获取相关统计信息
        from backend.app.admin.crud import activation_crud, device_crud
        
        activation_count = await activation_crud.count_by_channel(db, channel_id)
        device_count = await device_crud.count_by_channel(db, channel_id)
        
        return {
            "channel": channel,
            "statistics": {
                "activation_count": activation_count,
                "device_count": device_count
            }
        }


# 创建实例
channel_service = ChannelService()
