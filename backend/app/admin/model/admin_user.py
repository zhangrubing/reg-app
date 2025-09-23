"""管理员用户模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from backend.app.database.db import Base


class AdminUser(Base):
    """管理员用户表"""
    __tablename__ = "admin_user"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    email = Column(String(128), unique=True, nullable=False, comment="邮箱")
    password_hash = Column(String(256), nullable=False, comment="密码哈希")
    full_name = Column(String(128), comment="全名")
    phone = Column(String(32), comment="电话")
    avatar = Column(String(256), comment="头像URL")
    status = Column(String(32), default="active", comment="状态")
    role = Column(String(32), default="admin", comment="角色")
    department = Column(String(64), comment="部门")
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(45), comment="最后登录IP")
    login_count = Column(Integer, default=0, comment="登录次数")
    mfa_enabled = Column(Boolean, default=False, comment="MFA是否启用")
    totp_secret_enc = Column(Text, comment="TOTP密钥（加密存储）")
    webauthn_credentials = Column(JSONB, comment="WebAuthn凭据")
    backup_codes_hash = Column(JSONB, comment="备份码哈希数组")
    password_changed_at = Column(DateTime, comment="密码修改时间")
    failed_login_attempts = Column(Integer, default=0, comment="失败登录次数")
    locked_until = Column(DateTime, comment="锁定直到")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<AdminUser(username='{self.username}', email='{self.email}')>"
