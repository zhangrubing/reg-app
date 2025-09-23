"""认证模块"""
from __future__ import annotations

from .jwt import (
    JWTManager,
    PasswordManager,
    HMACManager,
    jwt_manager,
    password_manager,
    hmac_manager,
    create_tokens,
    refresh_access_token
)
from .totp import (
    TOTPManager,
    TOTPCrypto,
    BackupCodeManager,
    totp_manager,
    backup_code_manager,
    generate_encryption_key,
    create_totp_crypto
)

__all__ = [
    "JWTManager",
    "PasswordManager", 
    "HMACManager",
    "jwt_manager",
    "password_manager",
    "hmac_manager",
    "create_tokens",
    "refresh_access_token",
    "TOTPManager",
    "TOTPCrypto",
    "BackupCodeManager",
    "totp_manager",
    "backup_code_manager",
    "generate_encryption_key",
    "create_totp_crypto"
]
