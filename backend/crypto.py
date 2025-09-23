import hashlib
import hmac
import secrets
import time
import jwt
from typing import Tuple, Optional

try:
    from .config import APP_SECRET, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
except ImportError:
    # 当直接运行文件时的导入方式
    from config import APP_SECRET, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS


def hash_password(password: str) -> str:
    """哈希密码"""
    salt = secrets.token_bytes(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + pwdhash.hex()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    try:
        salt, pwdhash = hashed.split(':')
        salt = bytes.fromhex(salt)
        pwdhash = bytes.fromhex(pwdhash)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(pwdhash, new_hash)
    except Exception:
        return False


def sign_token(payload: dict, secret: str, expires_in: int = JWT_EXPIRATION_HOURS * 3600) -> str:
    """签名JWT令牌"""
    payload = payload.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload["iat"] = int(time.time())
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_token(token: str, secret: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, "令牌已过期"
    except jwt.InvalidTokenError:
        return False, None, "令牌无效"


def generate_hmac_signature(message: str, secret: str) -> str:
    """生成HMAC签名"""
    return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def verify_hmac_signature(message: str, signature: str, secret: str) -> bool:
    """验证HMAC签名"""
    expected = generate_hmac_signature(message, secret)
    return hmac.compare_digest(expected, signature)


def generate_secure_token(length: int = 32) -> str:
    """生成安全令牌"""
    return secrets.token_urlsafe(length)


def generate_activation_code(length: int = 16) -> str:
    """生成激活码"""
    return secrets.token_hex(length // 2).upper()


def generate_device_sn(prefix: str = "DEV") -> str:
    """生成设备序列号"""
    timestamp = str(int(time.time()))[-8:]
    random_part = secrets.token_hex(4).upper()
    return f"{prefix}{timestamp}{random_part}"
