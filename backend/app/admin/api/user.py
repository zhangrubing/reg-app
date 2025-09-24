"""用户管理API"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.admin.service import user_service
from backend.app.admin.schema import (
    UserCreate, UserUpdate, UserResponse, 
    UserListResponse, UserStatisticsResponse,
    UserLoginRequest, UserLoginResponse,
    PasswordResetRequest, UserSimpleResponse,
    UserProfileResponse, UserPasswordChangeRequest
)
from backend.app.common.response.response_schema import response_success
from backend.app.common.log import logger
from backend.app.common.deps import get_current_user, get_current_admin_user
from backend.app.common.auth.jwt import create_access_token

router = APIRouter()


@router.post("/register", summary="用户注册")
async def register_user(
    user_data: UserCreate = Body(..., description="用户数据"),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """用户注册"""
    try:
        user = await user_service.create_user(
            db=db,
            username=user_data.username,
            password=user_data.password,
            is_admin=user_data.is_admin,
            status=user_data.status,
            email=user_data.email,
            phone=user_data.phone,
            real_name=user_data.real_name
        )
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise


@router.post("/login", summary="用户登录")
async def login_user(
    login_data: UserLoginRequest = Body(..., description="登录数据"),
    db: AsyncSession = Depends(get_db)
) -> UserLoginResponse:
    """用户登录"""
    try:
        user = await user_service.authenticate_user(
            db=db,
            username=login_data.username,
            password=login_data.password
        )
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": str(user.user_id), "username": user.username, "is_admin": user.is_admin}
        )
        
        return response_success(UserLoginResponse(
            user_id=user.user_id,
            username=user.username,
            is_admin=user.is_admin,
            token=access_token,
            expires_at=datetime.now() + timedelta(hours=24)
        ))
        
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise


@router.get("/profile", summary="获取用户资料")
async def get_user_profile(
    current_user = Depends(get_current_user)
) -> UserProfileResponse:
    """获取当前用户资料"""
    try:
        return response_success(UserProfileResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            phone=current_user.phone,
            real_name=current_user.real_name,
            login_count=current_user.login_count,
            last_login_at=current_user.last_login_at,
            last_login_ip=current_user.last_login_ip,
            created_at=current_user.created_at
        ))
        
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        raise


@router.put("/profile", summary="更新用户资料")
async def update_user_profile(
    user_data: UserUpdate = Body(..., description="用户数据"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """更新当前用户资料"""
    try:
        user = await user_service.update_user(
            db=db,
            user_id=current_user.user_id,
            email=user_data.email,
            phone=user_data.phone,
            real_name=user_data.real_name
        )
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        raise


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: UserPasswordChangeRequest = Body(..., description="密码数据"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """修改当前用户密码"""
    try:
        # 验证旧密码
        from backend.app.common.auth.crypto import verify_password
        if not verify_password(password_data.old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")
        
        # 更新密码
        await user_service.update_user(
            db=db,
            user_id=current_user.user_id,
            password=password_data.new_password
        )
        
        return response_success({"message": "密码修改成功"})
        
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        raise


@router.get("", summary="获取用户列表（管理员）")
async def get_users(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    is_admin: Optional[bool] = Query(None, description="管理员筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserListResponse:
    """获取用户列表（需要管理员权限）"""
    try:
        users = await user_service.get_user_list(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            is_admin=is_admin,
            search=search
        )
        
        return response_success(users)
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise


@router.get("/statistics", summary="获取用户统计（管理员）")
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserStatisticsResponse:
    """获取用户统计信息（需要管理员权限）"""
    try:
        statistics = await user_service.get_user_statistics(db)
        
        return response_success(statistics)
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        raise


@router.get("/{user_id}", summary="获取用户详情（管理员）")
async def get_user(
    user_id: int = Path(..., description="用户ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserResponse:
    """获取用户详情（需要管理员权限）"""
    try:
        user = await user_service.get_user_detail(db, user_id)
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"获取用户详情失败: {str(e)}")
        raise


@router.put("/{user_id}", summary="更新用户（管理员）")
async def update_user(
    user_id: int = Path(..., description="用户ID"),
    update_data: UserUpdate = Body(..., description="更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserResponse:
    """更新用户信息（需要管理员权限）"""
    try:
        user = await user_service.update_user(
            db=db,
            user_id=user_id,
            username=update_data.username,
            password=update_data.password,
            is_admin=update_data.is_admin,
            status=update_data.status,
            email=update_data.email,
            phone=update_data.phone,
            real_name=update_data.real_name
        )
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"更新用户失败: {str(e)}")
        raise


@router.post("/{user_id}/reset-password", summary="重置用户密码（管理员）")
async def reset_user_password(
    user_id: int = Path(..., description="用户ID"),
    password_data: PasswordResetRequest = Body(..., description="密码数据"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserResponse:
    """重置用户密码（需要管理员权限）"""
    try:
        user = await user_service.reset_user_password(
            db=db,
            user_id=user_id,
            new_password=password_data.new_password
        )
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"重置用户密码失败: {str(e)}")
        raise


@router.post("/{user_id}/toggle-status", summary="切换用户状态（管理员）")
async def toggle_user_status(
    user_id: int = Path(..., description="用户ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> UserResponse:
    """切换用户状态（需要管理员权限）"""
    try:
        user = await user_service.toggle_user_status(db, user_id)
        
        return response_success(user)
        
    except Exception as e:
        logger.error(f"切换用户状态失败: {str(e)}")
        raise


@router.delete("/{user_id}", summary="删除用户（管理员）")
async def delete_user(
    user_id: int = Path(..., description="用户ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """删除用户（需要管理员权限）"""
    try:
        await user_service.delete_user(db, user_id)
        
        return response_success({"message": "用户删除成功"})
        
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise


@router.get("/simple/list", summary="获取用户简要列表（管理员）")
async def get_simple_users(
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)
) -> List[UserSimpleResponse]:
    """获取用户简要列表（需要管理员权限）"""
    try:
        users = await user_service.get_user_list(
            db=db,
            skip=0,
            limit=1000,  # 获取所有用户
            status=status
        )
        
        # 转换为简要响应
        simple_users = [
            UserSimpleResponse(
                user_id=user.user_id,
                username=user.username,
                is_admin=user.is_admin,
                status=user.status
            )
            for user in users
        ]
        
        return response_success(simple_users)
        
    except Exception as e:
        logger.error(f"获取用户简要列表失败: {str(e)}")
        raise
