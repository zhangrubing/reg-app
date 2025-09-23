"""设备模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from backend.app.database.db import Base


class Device(Base):
    """设备表"""
    __tablename__ = "device"
    
    device_id = Column(Integer, primary_key=True, autoincrement=True, comment="设备ID")
    sn = Column(String(128), unique=True, nullable=False, comment="设备序列号")
    first_seen = Column(DateTime, comment="首次发现时间")
    last_seen = Column(DateTime, comment="最后发现时间")
    bound_channel_id = Column(Integer, ForeignKey("channel.channel_id"), comment="绑定的渠道ID")
    status = Column(String(32), default="unknown", comment="状态")
    device_pubkey = Column(Text, comment="设备公钥")
    device_secret_hash = Column(Text, comment="设备密钥哈希")
    cert_serial = Column(String(128), comment="证书序列号")
    attestation_info = Column(JSONB, comment="认证信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Device(sn='{self.sn}', status='{self.status}')>"
