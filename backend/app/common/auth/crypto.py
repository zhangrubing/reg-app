"""加密工具模块"""
from __future__ import annotations

import secrets
import string
import hashlib
import hmac
from typing import Optional
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from backend.app.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """生成安全随机令牌"""
    return secrets.token_urlsafe(length)


def generate_activation_code(length: int = 16) -> str:
    """生成激活码"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key(length: int = 32) -> str:
    """生成API密钥"""
    return secrets.token_urlsafe(length)


def generate_hmac_secret(length: int = 64) -> str:
    """生成HMAC密钥"""
    return secrets.token_urlsafe(length)


def generate_license_signature(data: dict, private_key: Optional[str] = None) -> str:
    """生成许可证签名"""
    # 简化的签名生成，实际项目中应该使用更安全的签名算法
    key = private_key or settings.secret_key
    message = str(sorted(data.items()))
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_license_signature(data: dict, signature: str, public_key: Optional[str] = None) -> bool:
    """验证许可证签名"""
    expected_signature = generate_license_signature(data, public_key)
    return hmac.compare_digest(signature, expected_signature)


def generate_challenge(length: int = 32) -> str:
    """生成挑战字符串"""
    return secrets.token_urlsafe(length)


def encrypt_data(data: bytes, key: Optional[bytes] = None) -> bytes:
    """加密数据"""
    cipher_key = key or settings.fernet_key
    f = Fernet(cipher_key)
    return f.encrypt(data)


def decrypt_data(encrypted_data: bytes, key: Optional[bytes] = None) -> bytes:
    """解密数据"""
    cipher_key = key or settings.fernet_key
    f = Fernet(cipher_key)
    return f.decrypt(encrypted_data)


def generate_totp_secret() -> str:
    """生成TOTP密钥"""
    return secrets.token_urlsafe(32)


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """哈希数据"""
    if algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    else:
        raise ValueError(f"不支持的哈希算法: {algorithm}")


def verify_hmac_signature(message: str, signature: str, secret: str) -> bool:
    """验证HMAC签名"""
    expected_signature = hmac.new(
        secret.encode(), 
        message.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def generate_hmac_signature(message: str, secret: str) -> str:
    """生成HMAC签名"""
    return hmac.new(
        secret.encode(), 
        message.encode(), 
        hashlib.sha256
    ).hexdigest()
