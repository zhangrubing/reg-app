"""渠道管理API"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import channel_service
from backend.app.admin.schema import (
    ChannelCreate, ChannelUpdate, ChannelResponse, 
    ChannelListResponse, ChannelStatisticsResponse,
    ChannelDetailResponse, ApiKeyRegenerateResponse,
    ChannelSimpleResponse
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_user

router = APIRouter()


@router.post("", summary="创建渠道")
async def create_channel(
    channel_data: ChannelCreate = Body(..., description="渠道数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ChannelResponse:
    """创建新的渠道"""
    try:
        channel = await channel_service.create_channel(
            db=db,
            channel_code=channel_data.channel_code,
            name=channel_data.name,
            status=channel_data.status,
            description=channel_data.description,
            contact_person=channel_data.contact_person,
            contact_email=channel_data.contact_email,
            contact_phone=channel_data.contact_phone
        )
        
        return response_success(channel)
        
    except Exception as e:
        logger.error(f"创建渠道失败: {str(e)}")
        raise


@router.get("", summary="获取渠道列表")
async def get_channels(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ChannelListResponse:
    """获取渠道列表"""
    try:
        channels = await channel_service.get_channel_list(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            search=search
        )
        
        return response_success(channels)
        
    except Exception as e:
        logger.error(f"获取渠道列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取渠道统计")
async def get_channel_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ChannelStatisticsResponse:
    """获取渠道统计信息"""
    try:
        statistics = await channel_service.get_channel_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取渠道统计失败: {str(e)}")
        raise


@router.get("/simple", summary="获取渠道简要列表")
async def get_simple_channels(
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[ChannelSimpleResponse]:
    """获取渠道简要列表（用于下拉选择）"""
    try:
        channels = await channel_service.get_channel_list(
            db=db,
            skip=0,
            limit=1000,  # 获取所有渠道
            status=status
        )
        
        # 转换为简要响应
        simple_channels = [
            ChannelSimpleResponse(
                channel_id=channel.channel_id,
                channel_code=channel.channel_code,
                name=channel.name,
                status=channel.status
            )
            for channel in channels
        ]
        
        return response_success(simple_channels)
        
    except Exception as e:
        logger.error(f"获取渠道简要列表失败: {str(e)}")
        raise


@router.get("/{channel_id}", summary="获取渠道详情")
async def get_channel(
    channel_id: int = Path(..., description="渠道ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ChannelDetailResponse:
    """获取渠道详情"""
    try:
        channel_detail = await channel_service.get_channel_detail(db, channel_id)
        
        return response_success(channel_detail)
        
    except Exception as e:
        logger.error(f"获取渠道详情失败: {str(e)}")
        raise


@router.put("/{channel_id}", summary="更新渠道")
async def update_channel(
    channel_id: int = Path(..., description="渠道ID"),
    update_data: ChannelUpdate = Body(..., description="更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ChannelResponse:
    """更新渠道信息"""
    try:
        channel = await channel_service.update_channel(
            db=db,
            channel_id=channel_id,
            name=update_data.name,
            status=update_data.status,
            description=update_data.description,
            contact_person=update_data.contact_person,
            contact_email=update_data.contact_email,
            contact_phone=update_data.contact_phone
        )
        
        return response_success(channel)
        
    except Exception as e:
        logger.error(f"更新渠道失败: {str(e)}")
        raise


@router.post("/{channel_id}/regenerate-keys", summary="重新生成API密钥")
async def regenerate_api_keys(
    channel_id: int = Path(..., description="渠道ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ApiKeyRegenerateResponse:
    """重新生成渠道的API密钥和HMAC密钥"""
    try:
        keys = await channel_service.regenerate_api_key(db, channel_id)
        
        return response_success(keys)
        
    except Exception as e:
        logger.error(f"重新生成API密钥失败: {str(e)}")
        raise


@router.delete("/{channel_id}", summary="删除渠道")
async def delete_channel(
    channel_id: int = Path(..., description="渠道ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, str]:
    """删除渠道"""
    try:
        await channel_service.delete_channel(db, channel_id)
        
        return response_success({"message": "渠道删除成功"})
        
    except Exception as e:
        logger.error(f"删除渠道失败: {str(e)}")
        raise
