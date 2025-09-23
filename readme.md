# 应用软件注册激活系统设计文档

## 1. 概述

本设计文档描述了一个应用软件注册激活系统的整体方案，包括服务端架构、数据库设计、API
接口、安全策略、激活文件格式、客户端流程，以及统计与结算机制。

该系统支持 **在线激活** 与
**离线激活**，并提供渠道管理、激活记录统计、结算与审计功能。

------------------------------------------------------------------------

## 2. 核心概念

-   **设备（Device）**：每台设备拥有唯一序列号 SN。
-   **渠道（Channel）**：销售或分发渠道，拥有 `channel_code` 与
    `api_key`。
-   **激活记录（Activation）**：一次激活操作的完整记录。
-   **激活文件（License
    File）**：设备本地存储的签名文件，判断设备是否已激活。
-   **服务端（Server）**：管理激活、渠道、统计与结算。
-   **管理员（Admin）**：操作后台、管理渠道和账单。

------------------------------------------------------------------------

## 3. 激活流程

### 3.1 在线激活

1.  客户端获取设备序列号 SN。
2.  用户输入渠道激活码。
3.  客户端向服务端发起请求（包含 SN、渠道码、激活码等）。
4.  服务端验证信息并生成签名 License 文件。
5.  客户端保存 License 文件至固定目录，并校验合法性。
6.  服务端记录激活事件，用于统计与结算。

### 3.2 离线激活

1.  客户端生成激活请求文件（包含 SN 等信息）。
2.  渠道提交请求至服务端，服务端生成签名 License 文件。
3.  用户将 License 文件导入设备指定目录，完成激活。
4.  服务端仍记录激活日志，标记为离线激活。

------------------------------------------------------------------------

## 4. 安全设计

-   使用 **非对称加密签名（RSA/ECDSA）**，服务端持私钥，客户端内置公钥。
-   License 文件中包含 SN、激活时间、到期时间、渠道等信息，防篡改。
-   服务端支持公钥版本切换，便于密钥轮换。
-   渠道认证采用 API Key 或 HMAC。
-   支持撤销激活（Revocation List），客户端定期检查。

------------------------------------------------------------------------

## 5. 数据库设计

### 5.1 渠道表

``` sql
CREATE TABLE channel (
  channel_id   SERIAL PRIMARY KEY,
  channel_code VARCHAR(64) UNIQUE NOT NULL,
  name         VARCHAR(128) NOT NULL,
  api_key      VARCHAR(128) UNIQUE NOT NULL,
  secret_hmac  VARCHAR(256),
  owner_contact VARCHAR(256),
  status       VARCHAR(32) DEFAULT 'active',
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP
);
```

### 5.2 设备表

``` sql
CREATE TABLE device (
  device_id   SERIAL PRIMARY KEY,
  sn          VARCHAR(128) UNIQUE NOT NULL,
  first_seen  TIMESTAMP,
  last_seen   TIMESTAMP,
  bound_channel_id INTEGER,
  status      VARCHAR(32) DEFAULT 'unknown',
  local_info  JSONB,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 激活记录表

``` sql
CREATE TABLE activation (
  activation_id SERIAL PRIMARY KEY,
  sn            VARCHAR(128) NOT NULL,
  channel_id    INTEGER REFERENCES channel(channel_id),
  channel_code  VARCHAR(64),
  activation_code VARCHAR(128),
  issued_by     VARCHAR(128),
  activated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at    TIMESTAMP,
  license_blob  TEXT,
  ip_address    VARCHAR(45),
  client_meta   JSONB,
  amount_due    NUMERIC(12,2) DEFAULT 0.00,
  billing_period VARCHAR(64),
  payment_status VARCHAR(32) DEFAULT 'unsettled',
  status        VARCHAR(32) DEFAULT 'active',
  notes         TEXT
);
```

### 5.4 审计日志表

``` sql
CREATE TABLE audit_log (
  id SERIAL PRIMARY KEY,
  actor VARCHAR(128),
  action VARCHAR(128),
  target_type VARCHAR(64),
  target_id VARCHAR(128),
  detail JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

------------------------------------------------------------------------

## 6. API 设计

### 6.1 激活接口

**POST /api/v1/activate**\
请求示例：

``` json
{
  "sn": "S123456789",
  "channel_code": "CH_ABC_2025",
  "activation_code": "ACT-XXXX-YYYY",
  "client_meta": {"os":"Windows", "version":"1.2.3", "mac":"xx:xx"},
  "offline_request": false
}
```

响应示例：

``` json
{
  "status":"ok",
  "license":"<base64 license>",
  "activation_id":123
}
```

### 6.2 撤销接口

**POST /api/v1/revoke**\
撤销某个设备的激活。

### 6.3 管理接口

-   渠道管理：新增/修改/停用渠道\
-   激活统计：按渠道/时间导出报表\
-   结算管理：账单生成、支付状态更新

------------------------------------------------------------------------

## 7. License 文件格式

``` json
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
  "signature": "BASE64(RSA-SIGN(sha256, payload))"
}
```

------------------------------------------------------------------------

## 8. 本地存放位置

-   Windows: `C:\ProgramData\<product_name>\license.json`
-   macOS: `/Library/Application Support/<product_name>/license.json`
-   Linux: `/etc/<product_name>/license.json`

------------------------------------------------------------------------

## 9. 客户端激活示例（Python）

``` python
import requests, base64

API = "https://activation.example.com/api/v1/activate"
sn = get_device_sn()
payload = {
  "sn": sn,
  "channel_code": "CH_ABC_2025",
  "activation_code": "ACT-XXXX-YYYY",
  "client_meta": {"os":"Windows", "version":"1.0.0"}
}
r = requests.post(API, json=payload, timeout=10)
if r.status_code == 200:
    data = r.json()
    license_b64 = data['license']
    license_json = base64.b64decode(license_b64)
    with open("/etc/myapp/license.json","wb") as f:
        f.write(license_json)
```

------------------------------------------------------------------------

## 10. 统计与结算

-   每条激活记录保存渠道、金额、账期、支付状态。\
-   提供后台导出 CSV/Excel 报表。\
-   支持退款、撤销、补单。

------------------------------------------------------------------------

## 11. 防作弊措施

-   渠道配额限制：每日/总次数限制。\
-   IP 异常检测：批量激活告警。\
-   一次性激活码：防止重复使用。\
-   撤销机制：支持远程撤销 License。\
-   License 签名校验：防止伪造。

------------------------------------------------------------------------

## 12. 总结

该系统提供了完整的应用软件注册激活方案，支持渠道管理、设备唯一识别、License
签名验证、在线/离线激活、统计结算与防作弊机制，能够满足企业级软件发行与渠道结算需求。

