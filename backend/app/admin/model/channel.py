"""渠道模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from backend.app.database.db import Base


class Channel(Base):
    """渠道表"""
    __tablename__ = "channel"
    
    channel_id = Column(Integer, primary_key=True, autoincrement=True, comment="渠道ID")
    channel_code = Column(String(64), unique=True, nullable=False, comment="渠道代码")
    name = Column(String(128), nullable=False, comment="渠道名称")
    api_key = Column(String(128), unique=True, nullable=False, comment="API密钥")
    secret_hmac = Column(String(256), comment="HMAC密钥")
    owner_contact = Column(String(256), comment="所有者联系方式")
    admin_mfa_required = Column(Boolean, default=True, comment="管理员是否需要MFA")
    channel_admin_user_id = Column(Integer, comment="渠道管理员用户ID")
    status = Column(String(32), default="active", comment="状态")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Channel(channel_code='{self.channel_code}', name='{self.name}')>"
