"""JWT认证工具模块"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.app.core.config import settings
from backend.app.common.log import logger


# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTManager:
    """JWT管理器"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days
    
    def create_access_token(
        self,
        subject: str,
        claims: Optional[dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": subject,
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        }
        
        if claims:
            to_encode.update(claims)
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self,
        subject: str,
        claims: Optional[dict[str, Any]] = None
    ) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": subject,
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        }
        
        if claims:
            to_encode.update(claims)
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[dict[str, Any]]:
        """解码令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT解码失败: {str(e)}")
            return None
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[dict[str, Any]]:
        """验证令牌"""
        payload = self.decode_token(token)
        if not payload:
            return None
        
        # 检查令牌类型
        if payload.get("type") != token_type:
            logger.error(f"令牌类型不匹配: 期望 {token_type}, 实际 {payload.get('type')}")
            return None
        
        # 检查过期时间
        exp = payload.get("exp")
        if not exp:
            logger.error("令牌缺少过期时间")
            return None
        
        if datetime.utcnow() > datetime.fromtimestamp(exp):
            logger.error("令牌已过期")
            return None
        
        return payload


class PasswordManager:
    """密码管理器"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(password, hashed_password)
    
    @staticmethod
    def generate_api_key(length: int = 64) -> str:
        """生成API密钥"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """生成安全令牌"""
        import secrets
        return secrets.token_urlsafe(length)


class HMACManager:
    """HMAC管理器"""
    
    @staticmethod
    def generate_secret(length: int = 64) -> str:
        """生成HMAC密钥"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_signature(
        message: str,
        secret: str,
        algorithm: str = "sha256"
    ) -> str:
        """生成HMAC签名"""
        import hmac
        import hashlib
        import base64
        
        if algorithm not in ["sha256", "sha512"]:
            raise ValueError(f"不支持的算法: {algorithm}")
        
        hash_func = hashlib.sha256 if algorithm == "sha256" else hashlib.sha512
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hash_func
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_signature(
        message: str,
        signature: str,
        secret: str,
        algorithm: str = "sha256"
    ) -> bool:
        """验证HMAC签名"""
        try:
            expected_signature = HMACManager.generate_signature(message, secret, algorithm)
            # 使用hmac.compare_digest防止时序攻击
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"HMAC签名验证失败: {str(e)}")
            return False


# 创建全局实例
jwt_manager = JWTManager()
password_manager = PasswordManager()
hmac_manager = HMACManager()


# 辅助函数
def create_tokens(user_id: str, additional_claims: Optional[dict[str, Any]] = None) -> dict[str, str]:
    """创建令牌对"""
    claims = additional_claims or {}
    
    access_token = jwt_manager.create_access_token(user_id, claims)
    refresh_token = jwt_manager.create_refresh_token(user_id, claims)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """刷新访问令牌"""
    payload = jwt_manager.verify_token(refresh_token, "refresh")
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # 保留原有的claims
    claims = {k: v for k, v in payload.items() if k not in ["sub", "exp", "type", "iat"]}
    
    return jwt_manager.create_access_token(user_id, claims)


# 导出
__all__ = [
    "JWTManager",
    "PasswordManager",
    "HMACManager",
    "jwt_manager",
    "password_manager",
    "hmac_manager",
    "create_tokens",
    "refresh_access_token"
]
