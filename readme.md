# 应用软件注册与激活系统设计文档（含 2FA 增强安全性）

## 1. 概述
本设计文档描述一个完整的**应用软件注册与激活系统**，并在管理与高风险操作层面引入类似 Google Authenticator 的两步验证（2FA）机制以增强安全性。
系统支持在线激活与离线激活，并提供渠道管理、激活记录统计、结算与审计功能。

---

## 2. 关键实体 & 概念
- **device（设备）**：每台设备拥有唯一序列号（SN）。
- **channel（渠道）**：销售/分发渠道，拥有 `channel_code`、`api_key`、结算信息。
- **activation（激活记录）**：一次激活行为的完整日志。
- **license_file（激活文件）**：设备本地存储的签名文件，用于判断激活状态。
- **admin（管理员）**：操作后台、审批离线激活、导出结算等高权限用户。

---

## 3. 概览流程

### 3.1 在线激活
1. 客户端读取设备 SN（自动或由用户输入）。
2. 用户输入渠道激活码（或通过渠道 API 自动下发）。
3. 客户端向服务端 POST `/api/v1/activate`（包含 SN、channel_code、activation_code、client_meta）。
4. 服务端：
   - 验证渠道与激活码（计配额/次数/有效期）；
   - 如果需要对人为操作（如渠道管理员操作）进行二次确认，则触发 2FA 验证；
   - 生成签名 License（或返回需要客户端完成的挑战-响应）；
   - 记录激活日志用于结算。
5. 客户端写入 license 到固定目录并本地验证签名，激活完成。

### 3.2 离线激活
1. 设备生成 `activation_request.json`（包含 SN、client_meta、nonce、timestamp）。
2. 渠道或客户将文件上传/发送至服务端（或通过后台人工审核）。
3. 服务端验证并签发带签名的 `license.json` 文件返回给渠道/客户。
4. 客户端把 `license.json` 放置到设备固定目录并触发本地校验，激活完成。
5. 服务端记录该激活为“离线激活”并保留审批信息。

---

## 4. 加入 2FA 的总体策略（原则）
1. **对人（管理员、渠道管理员）**：使用 TOTP（兼容 Google Authenticator）和/或 WebAuthn（FIDO2）进行登录与高风险操作确认。
2. **对机器（渠道自动化、设备）**：使用强机器认证（API Key + HMAC、客户端证书 mTLS、设备预置密钥 + 挑战-响应），而不是 TOTP。
3. 对敏感操作（撤销、批量发码、导出结算）强制二次 2FA。
4. 所有秘密（TOTP seed、device_secret、api_secret）加密存储，推荐使用 KMS 或 HSM 管理密钥。
5. 提供备份码（一次性）与人工恢复流程以避免锁死。

---

## 5. 详细安全设计

### 5.1 非对称签名（License）
- 服务端使用 RSA-4096 或 ECDSA 签名 License。
- 客户端内置公钥用于本地验签，license 中包含 `pubkey_id` 以支持公钥轮换。

### 5.2 传输与鉴权
- 全部 API 使用 HTTPS（TLS1.2/1.3）。
- 渠道 API：`X-API-KEY` + HMAC 签名（`X-SIGNATURE`），并携带 `timestamp` 防重放。
- 管理后台：用户名+密码 + 2FA（TOTP/WebAuthn）。

### 5.3 设备认证（推荐）
- **方案 A：设备预置 secret + 挑战-响应（HMAC）**
  - 设备出厂注入 `device_secret`，服务器保存其 hash 或指纹。
  - 激活时先请求 challenge，再返回 `HMAC(device_secret, challenge||sn||ts)` 完成认证。
- **方案 B：客户端证书 + mTLS**
  - 为设备签发 X.509 客户端证书，激活 API 要求 mTLS。
- **方案 C（可选）：TPM / Secure Element + Attestation**
  - 使用 TPM/SE 存储私钥并做平台完整性证明（适用于高安全场景）。

### 5.4 MFA（TOTP）实现要点
- 使用 RFC 6238 标准（Time-based One-Time Password）。
- 服务端存储 TOTP secret 时进行对称加密（KMS），备份码以哈希形式存储。
- 登录/敏感操作流程：
  - 用户启用 2FA -> 展示 `otpauth://` 二维码 -> 用户扫码并提交首次 OTP 以确认。
  - 之后登录或敏感操作需提交 OTP；若 WebAuthn 可用，优先使用 WebAuthn。

### 5.5 高风险操作的二次认证
- 在触发撤销、批量发码、结算导出等操作时，要求用户进行额外的 2FA 验证（同一账号/session 内需要再次校验）。

---

## 6. 数据库表（关键表及新增字段示例）

### 6.1 channel（渠道）
```sql
CREATE TABLE channel (
  channel_id SERIAL PRIMARY KEY,
  channel_code VARCHAR(64) UNIQUE NOT NULL,
  name VARCHAR(128) NOT NULL,
  api_key VARCHAR(128) UNIQUE NOT NULL,
  secret_hmac VARCHAR(256),
  owner_contact VARCHAR(256),
  admin_mfa_required BOOLEAN DEFAULT TRUE,
  channel_admin_user_id INTEGER,
  status VARCHAR(32) DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 device（设备）
```sql
CREATE TABLE device (
  device_id SERIAL PRIMARY KEY,
  sn VARCHAR(128) UNIQUE NOT NULL,
  first_seen TIMESTAMP,
  last_seen TIMESTAMP,
  bound_channel_id INTEGER,
  status VARCHAR(32) DEFAULT 'unknown',
  device_pubkey TEXT,
  device_secret_hash TEXT,
  cert_serial TEXT,
  attestation_info JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.3 activation（激活记录）
```sql
CREATE TABLE activation (
  activation_id SERIAL PRIMARY KEY,
  sn VARCHAR(128) NOT NULL,
  channel_id INTEGER REFERENCES channel(channel_id),
  channel_code VARCHAR(64),
  activation_code VARCHAR(128),
  issued_by VARCHAR(128),
  activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  license_blob TEXT,
  ip_address VARCHAR(45),
  client_meta JSONB,
  amount_due NUMERIC(12,2) DEFAULT 0.00,
  billing_period VARCHAR(64),
  payment_status VARCHAR(32) DEFAULT 'unsettled',
  status VARCHAR(32) DEFAULT 'active',
  is_offline BOOLEAN DEFAULT FALSE,
  twofa_verified BOOLEAN DEFAULT FALSE,
  notes TEXT
);
```

### 6.4 admin_user（管理员）- 新增 MFA 字段
```sql
ALTER TABLE admin_user
  ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN totp_secret_enc TEXT,         -- 加密存储
  ADD COLUMN webauthn_credentials JSONB,   -- WebAuthn 注册信息
  ADD COLUMN backup_codes_hash JSONB;      -- 备份码哈希数组
```

---

## 7. API 与 2FA 相关接口（示例）

### 7.1 激活（在线）
- **POST /api/v1/activate**
  - Body:
```json
{
  "sn":"S123456789",
  "channel_code":"CH_ABC_2025",
  "activation_code":"ACT-XXXX",
  "client_meta":{"os":"Windows","version":"1.2.3"},
  "challenge_response":"<可选的设备HMAC签名>"
}
```
  - 如果需要管理员人工确认或渠道二次验证，返回 `pending_2fa` 状态，客户端/渠道应提示输入 OTP 或等待审批。

### 7.2 管理后台 - TOTP 设置
- **POST /api/v1/admin/mfa/setup** — 生成并返回 `otpauth_uri`（用于二维码）
- **POST /api/v1/admin/mfa/confirm** — 提交首个 OTP，确认绑定并返回备份码
- **POST /api/v1/admin/mfa/verify** — 在登录/敏感操作时校验 OTP

### 7.3 设备挑战-响应流程（推荐）
- **POST /api/v1/activate/request_challenge** `{ "sn": "...", "channel_code":"..." }` → 返回 `{ "challenge": "...", "expires_at":"..." }`
- **POST /api/v1/activate/complete** `{ "sn":"...", "challenge":"...", "signature":"HMAC(...)","client_meta":{...} }` → 验证通过下发 license

---

## 8. License 文件示例（JSON）
```json
{
  "sn": "S123456789",
  "issued_at": "2025-09-23T08:30:12Z",
  "expires_at": "2026-09-23T08:30:12Z",
  "channel_code": "CH_ABC_2025",
  "activation_id": 12345,
  "features": { "premium": true, "max_users": 1 },
  "billing": { "amount": 10.00, "currency": "CNY", "period": "one-time" },
  "nonce": "random-uuid-xyz",
  "issuer": "activation.example.com",
  "pubkey_id": "v1",
  "signature": "BASE64(RSA-SIGN(sha256, canonical_payload))"
}
```

---

## 9. 客户端与服务端示例代码片段（要点）

### 9.1 TOTP 验证（Python / pyotp）
```python
import pyotp
# secret 从 DB 解密后使用
totp = pyotp.TOTP(secret)
if totp.verify(user_input_code, valid_window=1):
    # 通过
else:
    # 拒绝
```

### 9.2 设备 HMAC 签名（伪码）
- 客户端：`sig = HMAC_SHA256(device_secret, challenge + sn + timestamp)`
- 服务端：校验 sig 与 timestamp 是否在可接受窗口内，且 challenge 未被重复使用

---

## 10. 运维与监控建议（含 2FA 相关）
- 记录并告警：登录失败次数、2FA 失败次数、备份码使用、异常批量操作。
- 密钥管理：TOTP 秘钥、device_secret 和 API secret 使用 KMS/HSM 存储与访问控制。
- 备份策略：数据库与私钥定期备份，私钥备份应存放于受控 KMS/HSM。
- 审计：所有 2FA 相关动作（启用、禁用、备份码导出、验证失败）必须写入审计日志并保留至少 90 天。

---

## 11. 风险与缓解
- **风险**：管理员丢失 2FA 导致无法操作 -> **缓解**：提供人工 KYC 恢复流程与临时受限访问。
- **风险**：渠道 API Key 泄露 -> **缓解**：使用 HMAC + IP 白名单 + 撤销机制 + 公布密钥轮换策略。
- **风险**：离线激活被滥用 -> **缓解**：限制离线激活额度、人工审批、要求上传请求证据。

---

## 12. 交付清单（开发任务）
1. DB 表结构与 migration（含 MFA 字段）。
2. 激活 API（在线 / 离线 / challenge-response）。
3. 管理后台：渠道管理、激活日志、结算报表、MFA 管理页面。
4. 客户端激活工具：读取 SN、challenge-response、写入 license、验签。
5. KMS/HSM 集成或密钥安全存储方案。
6. 测试：单元测试、集成测试、渗透测试（包含 2FA 绕过场景）。
7. 部署与监控。

---

## 13.核心技术选型

后端框架：FastAPI（同步/异步混合友好、类型标注、文档自动化）

模板引擎：Jinja2（仅渲染外壳和注入少量上下文变量）

静态资源：StaticFiles 直接挂载，无构建工具

实时：SSE（HTTP 单向推流，浏览器原生 EventSource）

鉴权：HttpOnly Cookie + HS256 签名 token（单机足够；可换为服务端 session 存储）

前端：原生 JS，封装 20 来行工具函数（fetch + 401 跳转 + SSE）


---


## 14. 小结
本设计在原有激活流程基础上，针对**人**的登录与高风险操作引入了 TOTP/WebAuthn 的 MFA 方案；针对**机器**采用证书或挑战-响应的强认证机制。配合 KMS、审计与告警，能有效提升激活系统的安全性并降低滥用与作弊风险。

---
