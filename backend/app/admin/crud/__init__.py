"""CRUD操作模块"""
from __future__ import annotations

from .activation import activation_crud
from .channel import channel_crud
from .device import device_crud
from .license import license_crud
from .user import user_crud
from .audit import audit_crud

__all__ = [
    "activation_crud",
    "channel_crud", 
    "device_crud",
    "license_crud",
    "user_crud",
    "audit_crud"
]
