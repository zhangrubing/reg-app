"""TOTP 2FA工具模块"""
from __future__ import annotations

import base64
import secrets
from typing import Optional
import pyotp
from cryptography.fernet import Fernet
from backend.app.core.config import settings
from backend.app.common.log import logger


class TOTPManager:
    """TOTP管理器"""
    
    def __init__(self):
        self.issuer = settings.totp_issuer
        self.digits = settings.totp_digits
        self.period = settings.totp_period
    
    def generate_secret(self) -> str:
        """生成TOTP密钥"""
        # 生成32字节的随机密钥
        secret = secrets.token_bytes(32)
        return base64.b32encode(secret).decode('utf-8')
    
    def generate_qr_code_uri(
        self,
        secret: str,
        username: str,
        issuer: Optional[str] = None
    ) -> str:
        """生成二维码URI"""
        totp = pyotp.TOTP(
            secret,
            digits=self.digits,
            interval=self.period
        )
        
        return totp.provisioning_uri(
            name=username,
            issuer_name=issuer or self.issuer
        )
    
    def verify_token(
        self,
        secret: str,
        token: str,
        valid_window: int = 1
    ) -> bool:
        """验证TOTP令牌"""
        try:
            totp = pyotp.TOTP(
                secret,
                digits=self.digits,
                interval=self.period
            )
            return totp.verify(token, valid_window=valid_window)
        except Exception as e:
            logger.error(f"TOTP验证失败: {str(e)}")
            return False
    
    def get_current_token(self, secret: str) -> str:
        """获取当前TOTP令牌"""
        totp = pyotp.TOTP(
            secret,
            digits=self.digits,
            interval=self.period
        )
        return totp.now()


class TOTPCrypto:
    """TOTP加密工具"""
    
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_secret(self, secret: str) -> str:
        """加密TOTP密钥"""
        try:
            encrypted = self.cipher.encrypt(secret.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"TOTP密钥加密失败: {str(e)}")
            raise
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """解密TOTP密钥"""
        try:
            encrypted_data = base64.b64decode(encrypted_secret.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"TOTP密钥解密失败: {str(e)}")
            raise


class BackupCodeManager:
    """备份码管理器"""
    
    def __init__(self):
        self.code_length = 8
        self.code_count = 10
    
    def generate_backup_codes(self) -> list[str]:
        """生成备份码"""
        codes = []
        for _ in range(self.code_count):
            # 生成8位随机码
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(self.code_length))
            codes.append(code)
        return codes
    
    def hash_code(self, code: str) -> str:
        """哈希备份码"""
        import hashlib
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    def verify_backup_code(
        self,
        code: str,
        hashed_codes: list[str]
    ) -> bool:
        """验证备份码"""
        code_hash = self.hash_code(code)
        return code_hash in hashed_codes


# 创建全局实例
totp_manager = TOTPManager()
backup_code_manager = BackupCodeManager()


# 辅助函数
def generate_encryption_key() -> bytes:
    """生成加密密钥"""
    return Fernet.generate_key()


def create_totp_crypto(encryption_key: bytes) -> TOTPCrypto:
    """创建TOTP加密实例"""
    return TOTPCrypto(encryption_key)


# 导出
__all__ = [
    "TOTPManager",
    "TOTPCrypto", 
    "BackupCodeManager",
    "totp_manager",
    "backup_code_manager",
    "generate_encryption_key",
    "create_totp_crypto"
]
