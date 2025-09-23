import os
import sqlite3
from pathlib import Path
import aiosqlite

try:
    from .config import DB_PATH
    from .crypto import hash_password
except ImportError:
    # 当直接运行文件时的导入方式
    from config import DB_PATH
    from crypto import hash_password


SCHEMA_SQL = '''
PRAGMA journal_mode=DELETE;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0,
  token_version INTEGER NOT NULL DEFAULT 0,
  mfa_secret TEXT,
  mfa_enabled INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP,
  last_login_ip TEXT,
  login_count INTEGER DEFAULT 0
);

-- 渠道表
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  api_key TEXT NOT NULL,
  secret_hmac TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 设备表
CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sn TEXT UNIQUE NOT NULL,
  channel_id INTEGER,
  status TEXT DEFAULT 'pending',
  first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  activated_at TIMESTAMP,
  FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- 激活码表
CREATE TABLE IF NOT EXISTS activations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  activation_code TEXT UNIQUE NOT NULL,
  channel_id INTEGER,
  sn TEXT,
  status TEXT DEFAULT 'active',
  expires_at TIMESTAMP,
  max_uses INTEGER DEFAULT 1,
  used_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  activated_at TIMESTAMP,
  ip_address TEXT,
  client_meta TEXT,
  FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT,
  action TEXT,
  detail TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS sys_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  category TEXT NOT NULL,
  message TEXT NOT NULL,
  context TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 许可证表
CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sn TEXT NOT NULL,
  activation_id INTEGER,
  license_data TEXT NOT NULL,
  signature TEXT NOT NULL,
  issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  revoked_at TIMESTAMP,
  FOREIGN KEY (activation_id) REFERENCES activations(id)
);
'''


async def init_db():
    """初始化数据库"""
    # 确保数据库目录存在
    try:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        try:
            os.makedirs(Path(DB_PATH).parent, exist_ok=True)
        except Exception:
            pass
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_channels_code ON channels(channel_code)",
            "CREATE INDEX IF NOT EXISTS idx_channels_api_key ON channels(api_key)",
            "CREATE INDEX IF NOT EXISTS idx_devices_sn ON devices(sn)",
            "CREATE INDEX IF NOT EXISTS idx_devices_channel ON devices(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_activations_code ON activations(activation_code)",
            "CREATE INDEX IF NOT EXISTS idx_activations_channel ON activations(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_activations_sn ON activations(sn)",
            "CREATE INDEX IF NOT EXISTS idx_licenses_sn ON licenses(sn)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_sys_logs_created ON sys_logs(created_at)",
        ]
        
        for index_sql in indexes:
            try:
                await db.execute(index_sql)
            except Exception:
                pass
        
        # 创建默认管理员用户
        async with db.execute("SELECT COUNT(1) FROM users WHERE is_admin = 1") as cur:
            row = await cur.fetchone()
            admin_count = row[0] if row else 0
        
        if admin_count == 0:
            await db.execute(
                "INSERT INTO users(username, password_hash, is_admin) VALUES(?, ?, 1)",
                ("admin", hash_password("admin123"))
            )
        
        # 创建默认渠道
        async with db.execute("SELECT COUNT(1) FROM channels") as cur:
            row = await cur.fetchone()
            channel_count = row[0] if row else 0
        
        if channel_count == 0:
            await db.execute(
                """INSERT INTO channels(channel_code, name, api_key, secret_hmac) 
                   VALUES(?, ?, ?, ?)""",
                ("CH001", "官方渠道", "test_api_key_12345", "test_secret_hmac_67890")
            )
        
        await db.commit()


async def get_db():
    """获取数据库连接"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
