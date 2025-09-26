from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiosqlite
import secrets
from datetime import datetime
from ..config import DB_PATH, HMAC_EXPIRATION_SECONDS
from ..crypto import verify_hmac_signature, generate_secure_token
from ..deps import require_user
from ..utils.audit import audit_log


router = APIRouter()


class ActivationRequest(BaseModel):
    sn: str
    channel_code: str
    activation_code: str
    client_meta: dict = None


class ChannelAuthRequest(BaseModel):
    sn: str
    channel_code: str
    activation_code: str
    timestamp: str
    signature: str


@router.post("/api/v1/activate")
async def activate_device(
    request: ActivationRequest,
    user: dict = Depends(require_user)
):
    """设备激活API"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # 验证渠道
            row = await (await db.execute(
                "SELECT id, status FROM channels WHERE channel_code = ?", 
                (request.channel_code,)
            )).fetchone()
            
            if not row or row[1] != "active":
                return JSONResponse(
                    status_code=400,
                    content={"code": 3000, "message": "渠道不存在或已禁用", "data": None}
                )
            
            channel_id = row[0]
            
            # 检查设备
            row = await (await db.execute(
                "SELECT id, status FROM devices WHERE sn = ?", 
                (request.sn,)
            )).fetchone()
            
            if row and row[1] == "activated":
                return JSONResponse(
                    status_code=400,
                    content={"code": 4003, "message": "设备已激活", "data": None}
                )
            
            # 验证激活码
            row = await (await db.execute("""
                SELECT id, expires_at, max_uses, used_count, status 
                FROM activations 
                WHERE activation_code = ? AND channel_id = ? AND status = 'active'
            """, (request.activation_code, channel_id))).fetchone()
            
            if not row:
                return JSONResponse(
                    status_code=400,
                    content={"code": 4000, "message": "激活码无效", "data": None}
                )
            
            activation_id, expires_at, max_uses, used_count, status = row
            
            # 检查激活码是否过期
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_dt:
                    return JSONResponse(
                        status_code=400,
                        content={"code": 4001, "message": "激活码已过期", "data": None}
                    )
            
            # 检查使用次数
            if max_uses and used_count >= max_uses:
                return JSONResponse(
                    status_code=400,
                    content={"code": 4002, "message": "激活码使用次数已达上限", "data": None}
                )
            
            # 开始事务
            async with db.execute("BEGIN"):
                # 创建设备或更新设备状态
                if not row or row[1] != "activated":
                    if not row:
                        # 创建新设备
                        await db.execute(
                            """INSERT INTO devices (sn, channel_id, status, activated_at) 
                               VALUES (?, ?, 'activated', datetime('now'))""",
                            (request.sn, channel_id)
                        )
                    else:
                        # 更新现有设备
                        await db.execute(
                            """UPDATE devices SET status = 'activated', 
                               channel_id = ?, activated_at = datetime('now') 
                               WHERE sn = ?""",
                            (channel_id, request.sn)
                        )
                
                # 更新激活记录
                await db.execute(
                    """UPDATE activations 
                       SET sn = ?, activated_at = datetime('now'), 
                           used_count = used_count + 1, ip_address = ?, 
                           client_meta = ?, status = CASE WHEN used_count + 1 >= max_uses THEN 'used' ELSE 'active' END
                       WHERE id = ?""",
                    (request.sn, "127.0.0.1", str(request.client_meta) if request.client_meta else None, activation_id)
                )
                
                # 生成许可证
                license_data = {
                    "sn": request.sn,
                    "issued_at": datetime.now().isoformat(),
                    "expires_at": expires_at,
                    "channel_code": request.channel_code,
                    "activation_id": activation_id,
                    "features": {"premium": True},
                    "nonce": generate_secure_token(16),
                    "issuer": "英智软件注册系统",
                    "pubkey_id": "v1"
                }
                
                # 生成签名
                signature = generate_secure_token(32)
                
                # 保存许可证
                await db.execute(
                    """INSERT INTO licenses (sn, activation_id, license_data, signature) 
                       VALUES (?, ?, ?, ?)""",
                    (request.sn, activation_id, str(license_data), signature)
                )
            
            await db.commit()
            
            await audit_log(user["username"], "activate_device", 
                           f"激活设备: {request.sn} via {request.channel_code}", None)
            
            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": "激活成功",
                    "data": {
                        "activation_id": activation_id,
                        "license_data": license_data,
                        "signature": signature,
                        "expires_at": expires_at
                    }
                }
            )
            
    except Exception as e:
        await audit_log("system", "activate_error", f"激活失败: {str(e)}", None)
        return JSONResponse(
            status_code=500,
            content={"code": 1000, "message": "激活失败", "data": None}
        )


@router.post("/api/v1/channel/activate")
async def channel_activate(
    request: ChannelAuthRequest,
    x_api_key: str = Header(...),
    x_signature: str = Header(...),
    x_timestamp: str = Header(...)
):
    """渠道认证激活"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # 验证渠道
            row = await (await db.execute(
                "SELECT id, secret_hmac, status FROM channels WHERE api_key = ?", 
                (x_api_key,)
            )).fetchone()
            
            if not row or row[2] != "active":
                return JSONResponse(
                    status_code=401,
                    content={"code": 3002, "message": "API密钥无效", "data": None}
                )
            
            channel_id, secret_hmac, status = row
            
            # 验证时间戳
            try:
                timestamp = int(x_timestamp)
                current_time = int(datetime.now().timestamp())
                if abs(current_time - timestamp) > HMAC_EXPIRATION_SECONDS:
                    return JSONResponse(
                        status_code=400,
                        content={"code": 1001, "message": "时间戳无效", "data": None}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"code": 1001, "message": "时间戳格式错误", "data": None}
                )
            
            # 验证HMAC签名
            message = f"/api/v1/channel/activate{x_timestamp}"
            if not verify_hmac_signature(message, x_signature, secret_hmac):
                return JSONResponse(
                    status_code=401,
                    content={"code": 3003, "message": "HMAC签名无效", "data": None}
                )
            
            # 验证渠道代码是否匹配
            row = await (await db.execute(
                "SELECT id FROM channels WHERE id = ? AND channel_code = ?", 
                (channel_id, request.channel_code)
            )).fetchone()
            
            if not row:
                return JSONResponse(
                    status_code=400,
                    content={"code": 3004, "message": "渠道代码不匹配", "data": None}
                )
            
            # 处理激活逻辑（同上面的activate_device，但使用渠道认证）
            # 这里可以复用上面的逻辑，但为了清晰起见，我重新实现
            
            # 检查设备
            row = await (await db.execute(
                "SELECT id, status FROM devices WHERE sn = ?", 
                (request.sn,)
            )).fetchone()
            
            if row and row[1] == "activated":
                return JSONResponse(
                    status_code=400,
                    content={"code": 4003, "message": "设备已激活", "data": None}
                )
            
            # 验证激活码
            row = await (await db.execute("""
                SELECT id, expires_at, max_uses, used_count, status 
                FROM activations 
                WHERE activation_code = ? AND channel_id = ? AND status = 'active'
            """, (request.activation_code, channel_id))).fetchone()
            
            if not row:
                return JSONResponse(
                    status_code=400,
                    content={"code": 4000, "message": "激活码无效", "data": None}
                )
            
            activation_id, expires_at, max_uses, used_count, status = row
            
            # 检查激活码是否过期
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_dt:
                    return JSONResponse(
                        status_code=400,
                        content={"code": 4001, "message": "激活码已过期", "data": None}
                    )
            
            # 检查使用次数
            if max_uses and used_count >= max_uses:
                return JSONResponse(
                    status_code=400,
                    content={"code": 4002, "message": "激活码使用次数已达上限", "data": None}
                )
            
            # 开始事务
            async with db.execute("BEGIN"):
                # 创建设备或更新设备状态
                if not row or row[1] != "activated":
                    if not row:
                        # 创建新设备
                        await db.execute(
                            """INSERT INTO devices (sn, channel_id, status, activated_at) 
                               VALUES (?, ?, 'activated', datetime('now'))""",
                            (request.sn, channel_id)
                        )
                    else:
                        # 更新现有设备
                        await db.execute(
                            """UPDATE devices SET status = 'activated', 
                               channel_id = ?, activated_at = datetime('now') 
                               WHERE sn = ?""",
                            (channel_id, request.sn)
                        )
                
                # 更新激活记录
                await db.execute(
                    """UPDATE activations 
                       SET sn = ?, activated_at = datetime('now'), 
                           used_count = used_count + 1, ip_address = ?, 
                           client_meta = ?, status = CASE WHEN used_count + 1 >= max_uses THEN 'used' ELSE 'active' END
                       WHERE id = ?""",
                    (request.sn, "127.0.0.1", str(request.client_meta) if request.client_meta else None, activation_id)
                )
                
                # 生成许可证
                license_data = {
                    "sn": request.sn,
                    "issued_at": datetime.now().isoformat(),
                    "expires_at": expires_at,
                    "channel_code": request.channel_code,
                    "activation_id": activation_id,
                    "features": {"premium": True},
                    "nonce": generate_secure_token(16),
                    "issuer": "英智软件注册系统",
                    "pubkey_id": "v1"
                }
                
                # 生成签名
                signature = generate_secure_token(32)
                
                # 保存许可证
                await db.execute(
                    """INSERT INTO licenses (sn, activation_id, license_data, signature) 
                       VALUES (?, ?, ?, ?)""",
                    (request.sn, activation_id, str(license_data), signature)
                )
            
            await db.commit()
            
            await audit_log("channel", "channel_activate", 
                           f"渠道激活设备: {request.sn} via {request.channel_code}", None)
            
            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": "渠道激活成功",
                    "data": {
                        "activation_id": activation_id,
                        "license_data": license_data,
                        "signature": signature,
                        "expires_at": expires_at
                    }
                }
            )
            
    except Exception as e:
        await audit_log("system", "channel_activate_error", f"渠道激活失败: {str(e)}", None)
        return JSONResponse(
            status_code=500,
            content={"code": 1000, "message": "渠道激活失败", "data": None}
        )
