import os
from pathlib import Path


# App config and paths
APP_SECRET = os.environ.get("APP_SECRET", "change-this-secret-key-for-production")
APP_ENV = os.environ.get("APP_ENV", "v1.0")
APP_NAME = "英智软件注册系统"

# project root (repo root): backend/config.py -> backend -> repo_root
BASE_DIR = Path(__file__).resolve().parent.parent
# Use DB at repo root to avoid missing directories; ensure it's a str for sqlite
DB_PATH = str(BASE_DIR / "data/regapp.db")

# JWT配置
JWT_SECRET = os.environ.get("JWT_SECRET", "your-jwt-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

# 系统配置
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
RELOAD = DEBUG

# 安全配置
TOTP_ISSUER = APP_NAME
PASSWORD_MIN_LENGTH = 6

# 平台签名密钥配置
PLATFORM_SIGNING_ALGORITHM = os.environ.get("PLATFORM_SIGNING_ALGORITHM", "EdDSA")
PLATFORM_SIGNING_KEY_PATH = os.environ.get("PLATFORM_SIGNING_KEY_PATH", str(BASE_DIR / "data/platform_signing_ed25519.key"))
PLATFORM_SIGNING_PUBLIC_KEY_PATH = os.environ.get("PLATFORM_SIGNING_PUBLIC_KEY_PATH", str(BASE_DIR / "data/platform_signing_ed25519.pub"))
REQUEST_TIME_SKEW_SECONDS = int(os.environ.get("REQUEST_TIME_SKEW_SECONDS", "120"))
NONCE_TTL_SECONDS = int(os.environ.get("NONCE_TTL_SECONDS", "600"))

# TOTP配置
TOTP_STEP = int(os.environ.get("TOTP_STEP", "30"))
TOTP_ALLOWED_DRIFT = int(os.environ.get("TOTP_ALLOWED_DRIFT", "1"))

# 签名算法支持
CHANNEL_SIGNATURE_ALGORITHMS = ("EdDSA", "ES256")

# 渠道配置
HMAC_EXPIRATION_SECONDS = 300  # 5分钟
