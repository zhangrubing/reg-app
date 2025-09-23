import os
from pathlib import Path


# App config and paths
APP_SECRET = os.environ.get("APP_SECRET", "change-this-secret-key-for-production")
APP_ENV = os.environ.get("APP_ENV", "v1.0")
APP_NAME = "软件注册与激活系统"

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

# 渠道配置
HMAC_EXPIRATION_SECONDS = 300  # 5分钟
