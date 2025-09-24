"""设备管理API"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import device_service
from backend.app.admin.schema import (
    DeviceCreate, DeviceUpdate, DeviceResponse, 
    DeviceListResponse, DeviceStatisticsResponse,
    DeviceDetailResponse, DeviceHeartbeatRequest,
    DeviceBatchUpdateRequest, DeviceStatusCountResponse,
    DeviceSimpleResponse
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_user

router = APIRouter()


@router.post("", summary="注册设备")
async def register_device(
    device_data: DeviceCreate = Body(..., description="设备数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceResponse:
    """注册新设备"""
    try:
        device = await device_service.register_device(
            db=db,
            sn=device_data.sn,
            channel_id=device_data.channel_id,
            client_meta=device_data.client_meta
        )
        
        return response_success(device)
        
    except Exception as e:
        logger.error(f"注册设备失败: {str(e)}")
        raise


@router.get("", summary="获取设备列表")
async def get_devices(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    channel_id: Optional[int] = Query(None, description="渠道ID筛选"),
    sn: Optional[str] = Query(None, description="设备序列号筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceListResponse:
    """获取设备列表"""
    try:
        devices = await device_service.get_device_list(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            channel_id=channel_id,
            sn=sn
        )
        
        return response_success(devices)
        
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取设备统计")
async def get_device_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceStatisticsResponse:
    """获取设备统计信息"""
    try:
        statistics = await device_service.get_device_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取设备统计失败: {str(e)}")
        raise


@router.get("/status-counts", summary="获取设备状态统计")
async def get_device_status_counts(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceStatusCountResponse:
    """获取各状态设备数量统计"""
    try:
        from sqlalchemy import func
        from backend.app.admin.model import Device
        
        result = await db.execute(
            select(Device.status, func.count(Device.device_id))
            .group_by(Device.status)
        )
        
        status_counts = {}
        for row in result.fetchall():
            status_counts[row[0]] = row[1]
        
        # 确保所有状态都有值
        default_counts = {
            "pending": 0,
            "activated": 0,
            "suspended": 0,
            "expired": 0,
            "revoked": 0
        }
        default_counts.update(status_counts)
        
        return response_success(DeviceStatusCountResponse(**default_counts))
        
    except Exception as e:
        logger.error(f"获取设备状态统计失败: {str(e)}")
        raise


@router.get("/simple", summary="获取设备简要列表")
async def get_simple_devices(
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[DeviceSimpleResponse]:
    """获取设备简要列表"""
    try:
        devices = await device_service.get_device_list(
            db=db,
            skip=0,
            limit=1000,  # 获取所有设备
            status=status
        )
        
        # 转换为简要响应
        simple_devices = [
            DeviceSimpleResponse(
                device_id=device.device_id,
                sn=device.sn,
                status=device.status,
                last_seen=device.last_seen
            )
            for device in devices
        ]
        
        return response_success(simple_devices)
        
    except Exception as e:
        logger.error(f"获取设备简要列表失败: {str(e)}")
        raise


@router.get("/{device_id}", summary="获取设备详情")
async def get_device(
    device_id: int = Path(..., description="设备ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceDetailResponse:
    """获取设备详情"""
    try:
        device_detail = await device_service.get_device_detail(db, device_id)
        
        return response_success(device_detail)
        
    except Exception as e:
        logger.error(f"获取设备详情失败: {str(e)}")
        raise


@router.put("/{device_id}", summary="更新设备")
async def update_device(
    device_id: int = Path(..., description="设备ID"),
    update_data: DeviceUpdate = Body(..., description="更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeviceResponse:
    """更新设备信息"""
    try:
        device = await device_service.update_device_status(
            db=db,
            device_id=device_id,
            status=update_data.status,
            reason=update_data.notes
        )
        
        return response_success(device)
        
    except Exception as e:
        logger.error(f"更新设备失败: {str(e)}")
        raise


@router.post("/{device_id}/heartbeat", summary="设备心跳")
async def device_heartbeat(
    device_id: int = Path(..., description="设备ID"),
    heartbeat_data: DeviceHeartbeatRequest = Body(..., description="心跳数据"),
    db: AsyncSession = Depends(get_db)
) -> DeviceResponse:
    """设备心跳（无需登录）"""
    try:
        device = await device_service.heartbeat(
            db=db,
            sn=heartbeat_data.sn,
            client_meta=heartbeat_data.client_meta
        )
        
        return response_success(device)
        
    except Exception as e:
        logger.error(f"设备心跳失败: {str(e)}")
        raise


@router.post("/batch-update-status", summary="批量更新设备状态")
async def batch_update_device_status(
    batch_data: DeviceBatchUpdateRequest = Body(..., description="批量更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, any]:
    """批量更新设备状态"""
    try:
        result = await device_service.batch_update_device_status(
            db=db,
            device_ids=batch_data.device_ids,
            status=batch_data.status
        )
        
        return response_success(result)
        
    except Exception as e:
        logger.error(f"批量更新设备状态失败: {str(e)}")
        raise


@router.post("/cleanup-inactive", summary="清理未活动设备")
async def cleanup_inactive_devices(
    days: int = Query(90, ge=30, le=365, description="未活动天数"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, int]:
    """清理长时间未活动的设备"""
    try:
        deleted_count = await device_service.cleanup_inactive_devices(db, days)
        
        return response_success({"deleted_count": deleted_count})
        
    except Exception as e:
        logger.error(f"清理未活动设备失败: {str(e)}")
        raise


@router.delete("/{device_id}", summary="删除设备")
async def delete_device(
    device_id: int = Path(..., description="设备ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, str]:
    """删除设备"""
    try:
        await device_service.delete_device(db, device_id)
        
        return response_success({"message": "设备删除成功"})
        
    except Exception as e:
        logger.error(f"删除设备失败: {str(e)}")
        raise
