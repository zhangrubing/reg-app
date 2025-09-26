"""应用配置模块"""
from __future__ import annotations

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    app_name: str = Field(default="英智软件注册系统", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    reload: bool = Field(default=False, description="自动重载")
    
    # 数据库配置
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/regapp",
        description="数据库连接URL"
    )
    
    # Redis配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    
    # JWT配置
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="JWT密钥"
    )
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间（分钟）")
    refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间（天）")
    
    # 2FA配置
    totp_issuer: str = Field(default="RegApp", description="TOTP发行者名称")
    totp_digits: int = Field(default=6, description="TOTP位数")
    totp_period: int = Field(default=30, description="TOTP周期（秒）")
    
    # 安全配置
    bcrypt_rounds: int = Field(default=12, description="bcrypt加密轮数")
    api_key_length: int = Field(default=64, description="API密钥长度")
    
    # 许可证配置
    license_private_key_path: Optional[str] = Field(
        default=None,
        description="许可证私钥文件路径"
    )
    license_public_key_path: Optional[str] = Field(
        default=None,
        description="许可证公钥文件路径"
    )
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    
    # CORS配置
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS允许的源"
    )
    
    # 文件上传配置
    max_file_size: int = Field(default=10 * 1024 * 1024, description="最大文件大小（字节）")
    upload_dir: str = Field(default="uploads", description="上传文件目录")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()
