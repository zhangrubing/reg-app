"""激活记录模型"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from backend.app.database.db import Base


class Activation(Base):
    """激活记录表"""
    __tablename__ = "activation"
    
    activation_id = Column(Integer, primary_key=True, autoincrement=True, comment="激活记录ID")
    sn = Column(String(128), nullable=False, comment="设备序列号")
    channel_id = Column(Integer, ForeignKey("channel.channel_id"), comment="渠道ID")
    channel_code = Column(String(64), comment="渠道代码")
    activation_code = Column(String(128), comment="激活码")
    issued_by = Column(String(128), comment="发放者")
    activated_at = Column(DateTime, default=func.now(), comment="激活时间")
    expires_at = Column(DateTime, comment="过期时间")
    license_blob = Column(Text, comment="许可证内容")
    ip_address = Column(String(45), comment="IP地址")
    client_meta = Column(JSONB, comment="客户端元数据")
    amount_due = Column(Numeric(12, 2), default=Decimal("0.00"), comment="应付金额")
    billing_period = Column(String(64), comment="结算周期")
    payment_status = Column(String(32), default="unsettled", comment="支付状态")
    status = Column(String(32), default="active", comment="状态")
    is_offline = Column(Boolean, default=False, comment="是否离线激活")
    twofa_verified = Column(Boolean, default=False, comment="2FA是否验证")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Activation(activation_id={self.activation_id}, sn='{self.sn}', status='{self.status}')>"
