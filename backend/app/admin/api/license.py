"""许可证管理API"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import license_service
from backend.app.admin.schema import (
    LicenseCreate, LicenseUpdate, LicenseResponse, 
    LicenseListResponse, LicenseStatisticsResponse,
    LicenseVerifyRequest, LicenseVerifyResponse,
    LicenseRevokeRequest, LicenseRenewRequest,
    LicenseFileVerifyRequest, LicenseFileVerifyResponse,
    LicenseSimpleResponse
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_user

router = APIRouter()


@router.post("", summary="生成许可证")
async def generate_license(
    license_data: LicenseCreate = Body(..., description="许可证数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseResponse:
    """生成新的许可证"""
    try:
        license_record = await license_service.generate_license(
            db=db,
            sn=license_data.sn,
            activation_id=license_data.activation_id,
            expires_days=license_data.expires_days,
            features=license_data.features
        )
        
        return response_success(license_record)
        
    except Exception as e:
        logger.error(f"生成许可证失败: {str(e)}")
        raise


@router.get("", summary="获取许可证列表")
async def get_licenses(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    sn: Optional[str] = Query(None, description="设备序列号筛选"),
    activation_id: Optional[int] = Query(None, description="激活记录ID筛选"),
    is_revoked: Optional[bool] = Query(None, description="是否已吊销筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseListResponse:
    """获取许可证列表"""
    try:
        licenses = await license_service.get_device_licenses(
            db=db,
            sn=sn
        ) if sn else await license_service.get_license_list(
            db=db,
            skip=skip,
            limit=limit,
            sn=sn,
            activation_id=activation_id,
            is_revoked=is_revoked
        )
        
        return response_success(licenses)
        
    except Exception as e:
        logger.error(f"获取许可证列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取许可证统计")
async def get_license_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseStatisticsResponse:
    """获取许可证统计信息"""
    try:
        statistics = await license_service.get_license_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取许可证统计失败: {str(e)}")
        raise


@router.get("/{license_id}", summary="获取许可证详情")
async def get_license(
    license_id: int = Path(..., description="许可证ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseResponse:
    """获取许可证详情"""
    try:
        license_record = await license_service.get_license_detail(db, license_id)
        
        return response_success(license_record)
        
    except Exception as e:
        logger.error(f"获取许可证详情失败: {str(e)}")
        raise


@router.put("/{license_id}", summary="更新许可证")
async def update_license(
    license_id: int = Path(..., description="许可证ID"),
    update_data: LicenseUpdate = Body(..., description="更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseResponse:
    """更新许可证信息"""
    try:
        license_record = await license_service.update_license(
            db=db,
            license_id=license_id,
            update_data=update_data
        )
        
        return response_success(license_record)
        
    except Exception as e:
        logger.error(f"更新许可证失败: {str(e)}")
        raise


@router.post("/verify", summary="验证许可证")
async def verify_license(
    verify_data: LicenseVerifyRequest = Body(..., description="验证数据"),
    db: AsyncSession = Depends(get_db)
) -> LicenseVerifyResponse:
    """验证许可证（无需登录）"""
    try:
        result = await license_service.verify_license(
            db=db,
            sn=verify_data.sn,
            license_data=verify_data.license_data,
            signature=verify_data.signature
        )
        
        return response_success(result)
        
    except Exception as e:
        logger.error(f"验证许可证失败: {str(e)}")
        raise


@router.post("/verify-file", summary="验证许可证文件")
async def verify_license_file(
    verify_data: LicenseFileVerifyRequest = Body(..., description="验证数据")
) -> LicenseFileVerifyResponse:
    """验证许可证文件（离线验证，无需登录）"""
    try:
        result = await license_service.validate_license_file(
            license_data=verify_data.license_data,
            signature=verify_data.signature,
            public_key=verify_data.public_key
        )
        
        return response_success(result)
        
    except Exception as e:
        logger.error(f"验证许可证文件失败: {str(e)}")
        raise


@router.post("/{license_id}/revoke", summary="吊销许可证")
async def revoke_license(
    license_id: int = Path(..., description="许可证ID"),
    revoke_data: LicenseRevokeRequest = Body(..., description="吊销数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseResponse:
    """吊销许可证"""
    try:
        license_record = await license_service.revoke_license(
            db=db,
            license_id=license_id,
            reason=revoke_data.reason
        )
        
        return response_success(license_record)
        
    except Exception as e:
        logger.error(f"吊销许可证失败: {str(e)}")
        raise


@router.post("/{license_id}/renew", summary="续期许可证")
async def renew_license(
    license_id: int = Path(..., description="许可证ID"),
    renew_data: LicenseRenewRequest = Body(..., description="续期数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> LicenseResponse:
    """续期许可证"""
    try:
        license_record = await license_service.renew_license(
            db=db,
            license_id=license_id,
            extend_days=renew_data.extend_days
        )
        
        return response_success(license_record)
        
    except Exception as e:
        logger.error(f"续期许可证失败: {str(e)}")
        raise


@router.get("/device/{sn}", summary="获取设备许可证")
async def get_device_licenses(
    sn: str = Path(..., description="设备序列号"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[LicenseResponse]:
    """获取指定设备的所有许可证"""
    try:
        licenses = await license_service.get_device_licenses(db, sn)
        
        return response_success(licenses)
        
    except Exception as e:
        logger.error(f"获取设备许可证失败: {str(e)}")
        raise


@router.delete("/{license_id}", summary="删除许可证")
async def delete_license(
    license_id: int = Path(..., description="许可证ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, str]:
    """删除许可证"""
    try:
        await license_service.delete_license(db, license_id)
        
        return response_success({"message": "许可证删除成功"})
        
    except Exception as e:
        logger.error(f"删除许可证失败: {str(e)}")
        raise
