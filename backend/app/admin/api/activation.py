"""激活记录管理API"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import activation_service
from backend.app.admin.schema import (
    ActivationCreate, ActivationUpdate, ActivationResponse, 
    ActivationListResponse, ActivationStatisticsResponse,
    BatchActivationCreate, DeviceActivationRequest, DeviceActivationResponse,
    ActivationStatusResponse
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_user

router = APIRouter()


@router.post("", summary="创建激活记录")
async def create_activation(
    activation_data: ActivationCreate = Body(..., description="激活记录数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationResponse:
    """创建新的激活记录"""
    try:
        activation = await activation_service.create_activation(
            db=db,
            channel_id=activation_data.channel_id,
            activation_code=activation_data.activation_code,
            expires_days=activation_data.expires_days,
            max_uses=activation_data.max_uses,
            amount_due=activation_data.amount_due,
            billing_period=activation_data.billing_period,
            notes=activation_data.notes
        )
        
        return response_success(activation)
        
    except Exception as e:
        logger.error(f"创建激活记录失败: {str(e)}")
        raise


@router.post("/batch", summary="批量创建激活码")
async def batch_create_activations(
    batch_data: BatchActivationCreate = Body(..., description="批量创建数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[ActivationResponse]:
    """批量创建激活码"""
    try:
        activations = await activation_service.batch_create_activations(
            db=db,
            channel_id=batch_data.channel_id,
            count=batch_data.count,
            expires_days=batch_data.expires_days,
            max_uses=batch_data.max_uses
        )
        
        return response_success(activations)
        
    except Exception as e:
        logger.error(f"批量创建激活码失败: {str(e)}")
        raise


@router.get("", summary="获取激活记录列表")
async def get_activations(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    channel_id: Optional[int] = Query(None, description="渠道ID筛选"),
    sn: Optional[str] = Query(None, description="设备序列号筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationListResponse:
    """获取激活记录列表"""
    try:
        activations = await activation_service.get_activation_list(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            channel_id=channel_id,
            sn=sn
        )
        
        return response_success(activations)
        
    except Exception as e:
        logger.error(f"获取激活记录列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取激活统计")
async def get_activation_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationStatisticsResponse:
    """获取激活统计信息"""
    try:
        statistics = await activation_service.get_activation_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取激活统计失败: {str(e)}")
        raise


@router.get("/{activation_id}", summary="获取激活记录详情")
async def get_activation(
    activation_id: int = Path(..., description="激活记录ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationResponse:
    """获取激活记录详情"""
    try:
        activation = await activation_service.get_activation_detail(db, activation_id)
        
        return response_success(activation)
        
    except Exception as e:
        logger.error(f"获取激活记录详情失败: {str(e)}")
        raise


@router.put("/{activation_id}", summary="更新激活记录")
async def update_activation(
    activation_id: int = Path(..., description="激活记录ID"),
    update_data: ActivationUpdate = Body(..., description="更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationResponse:
    """更新激活记录"""
    try:
        activation = await activation_service.update_activation(
            db=db,
            activation_id=activation_id,
            update_data=update_data
        )
        
        return response_success(activation)
        
    except Exception as e:
        logger.error(f"更新激活记录失败: {str(e)}")
        raise


@router.delete("/{activation_id}", summary="删除激活记录")
async def delete_activation(
    activation_id: int = Path(..., description="激活记录ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, str]:
    """删除激活记录"""
    try:
        await activation_service.delete_activation(db, activation_id)
        
        return response_success({"message": "激活记录删除成功"})
        
    except Exception as e:
        logger.error(f"删除激活记录失败: {str(e)}")
        raise


@router.post("/{activation_id}/revoke", summary="吊销激活码")
async def revoke_activation(
    activation_id: int = Path(..., description="激活记录ID"),
    reason: Optional[str] = Query(None, description="吊销原因"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> ActivationResponse:
    """吊销激活码"""
    try:
        activation = await activation_service.revoke_activation(
            db=db,
            activation_id=activation_id,
            reason=reason
        )
        
        return response_success(activation)
        
    except Exception as e:
        logger.error(f"吊销激活码失败: {str(e)}")
        raise


@router.post("/activate", summary="设备激活")
async def activate_device(
    activation_data: DeviceActivationRequest = Body(..., description="激活数据"),
    db: AsyncSession = Depends(get_db)
) -> DeviceActivationResponse:
    """设备激活（无需登录）"""
    try:
        result = await activation_service.activate_device(
            db=db,
            sn=activation_data.sn,
            channel_code=activation_data.channel_code,
            activation_code=activation_data.activation_code,
            client_meta=activation_data.client_meta
        )
        
        return response_success(result)
        
    except Exception as e:
        logger.error(f"设备激活失败: {str(e)}")
        raise


@router.get("/status/{sn}", summary="获取激活状态")
async def get_activation_status(
    sn: str = Path(..., description="设备序列号"),
    db: AsyncSession = Depends(get_db)
) -> ActivationStatusResponse:
    """获取设备激活状态"""
    try:
        status = await activation_service.get_activation_status(db, sn)
        
        return response_success(status)
        
    except Exception as e:
        logger.error(f"获取激活状态失败: {str(e)}")
        raise
