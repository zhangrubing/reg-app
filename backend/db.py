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
  status TEXT DEFAULT 'active',
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
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

-- 渠道密钥表
CREATE TABLE IF NOT EXISTS channel_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL,
  channel_code TEXT NOT NULL,
  kid TEXT NOT NULL,
  algorithm TEXT NOT NULL,
  public_key TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  rotated_at TIMESTAMP,
  FOREIGN KEY (channel_id) REFERENCES channels(id),
  UNIQUE(channel_id, kid)
);

-- 渠道子账户与TOTP
CREATE TABLE IF NOT EXISTS channel_subaccounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL,
  channel_code TEXT NOT NULL,
  subaccount TEXT NOT NULL,
  totp_secret TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  last_used_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(channel_id, subaccount),
  FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- 渠道授权胶囊 CAC
CREATE TABLE IF NOT EXISTS cac_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jti TEXT UNIQUE NOT NULL,
  channel_id INTEGER NOT NULL,
  channel_code TEXT NOT NULL,
  payload TEXT NOT NULL,
  quota_max INTEGER NOT NULL,
  quota_used INTEGER NOT NULL DEFAULT 0,
  valid_from INTEGER,
  valid_to INTEGER,
  status TEXT DEFAULT 'active',
  encrypted INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- 激活请求防重放
CREATE TABLE IF NOT EXISTS activation_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id INTEGER NOT NULL,
  channel_code TEXT NOT NULL,
  nonce TEXT NOT NULL,
  iat INTEGER NOT NULL,
  request_hash TEXT NOT NULL,
  subaccount TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  UNIQUE(channel_id, nonce),
  FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- 许可证撤销表
CREATE TABLE IF NOT EXISTS license_revoke_list (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  license_id TEXT NOT NULL,
  channel_code TEXT,
  reason TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(license_id)
);

-- 激活审计表
CREATE TABLE IF NOT EXISTS activation_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  license_id TEXT,
  sn TEXT,
  channel_code TEXT,
  subaccount TEXT,
  cac_jti TEXT,
  device_pubkey_hash TEXT,
  decision TEXT,
  reason TEXT,
  ip TEXT,
  geo TEXT,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            "CREATE INDEX IF NOT EXISTS idx_cac_tokens_jti ON cac_tokens(jti)",
            "CREATE INDEX IF NOT EXISTS idx_cac_tokens_channel ON cac_tokens(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_channel_keys_channel ON channel_keys(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_channel_subaccounts_channel ON channel_subaccounts(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_activation_requests_nonce ON activation_requests(channel_id, nonce)",
            "CREATE INDEX IF NOT EXISTS idx_license_revoke_list ON license_revoke_list(license_id)",
            "CREATE INDEX IF NOT EXISTS idx_activation_audit_created ON activation_audit(created_at)",
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
