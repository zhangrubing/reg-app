"""用户Schema"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    is_admin: bool = Field(False, description="是否为管理员")
    status: str = Field("active", description="状态: active, inactive")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号", max_length=20)
    real_name: Optional[str] = Field(None, description="真实姓名", max_length=64)


class UserUpdate(BaseModel):
    """更新用户"""
    username: Optional[str] = Field(None, description="用户名", min_length=3, max_length=50)
    password: Optional[str] = Field(None, description="密码", min_length=6, max_length=100)
    is_admin: Optional[bool] = Field(None, description="是否为管理员")
    status: Optional[str] = Field(None, description="状态: active, inactive")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号", max_length=20)
    real_name: Optional[str] = Field(None, description="真实姓名", max_length=64)


class UserResponse(BaseModel):
    """用户响应"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    is_admin: bool = Field(..., description="是否为管理员")
    status: str = Field(..., description="状态")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    real_name: Optional[str] = Field(None, description="真实姓名")
    login_count: int = Field(0, description="登录次数")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    last_login_ip: Optional[str] = Field(None, description="最后登录IP")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    pages: int = Field(..., description="总页数")


class UserStatisticsResponse(BaseModel):
    """用户统计响应"""
    total_count: int = Field(..., description="总用户数")
    active_count: int = Field(..., description="活跃用户数")
    admin_count: int = Field(..., description="管理员用户数")
    today_count: int = Field(..., description="今日新注册用户数")
    weekly_trend: List[Dict[str, Any]] = Field(..., description="最近7天趋势")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)


class UserLoginResponse(BaseModel):
    """用户登录响应"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    is_admin: bool = Field(..., description="是否为管理员")
    token: str = Field(..., description="访问令牌")
    expires_at: datetime = Field(..., description="过期时间")


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    user_id: int = Field(..., description="用户ID")
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)


class UserSimpleResponse(BaseModel):
    """用户简要响应"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    is_admin: bool = Field(..., description="是否为管理员")
    status: str = Field(..., description="状态")


class UserProfileResponse(BaseModel):
    """用户资料响应"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    real_name: Optional[str] = Field(None, description="真实姓名")
    login_count: int = Field(..., description="登录次数")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    last_login_ip: Optional[str] = Field(None, description="最后登录IP")
    created_at: datetime = Field(..., description="创建时间")


class UserPasswordChangeRequest(BaseModel):
    """用户密码修改请求"""
    old_password: str = Field(..., description="旧密码", min_length=6, max_length=100)
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)
