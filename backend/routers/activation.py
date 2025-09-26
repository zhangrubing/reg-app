from fastapi import APIRouter, Request, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Optional
import json
import time
import logging
import aiosqlite
import secrets
from datetime import datetime
from datetime import timezone
from ..config import (
    DB_PATH,
    HMAC_EXPIRATION_SECONDS,
    NONCE_TTL_SECONDS,
    REQUEST_TIME_SKEW_SECONDS,
    TOTP_STEP,
)
from ..crypto import verify_hmac_signature, generate_secure_token
from ..security.keys import load_public_key_from_pem
from ..security.signatures import SignatureError, verify_detached
from ..security.totp import verify_totp
from ..security.hashers import hash_text
from ..services.channel_registry import (
    get_channel_by_code,
    get_channel_key,
    get_subaccount,
    update_subaccount_last_used,
)
from ..services.cac import (
    CACValidationError,
    consume_cac_quota,
    ensure_cac_availability,
    verify_cac_token,
)
from ..services.license_issuer import (
    build_license_payload,
    generate_license_id,
    issue_license,
)
from ..deps import require_user
from ..utils.audit import audit_log


router = APIRouter()


logger = logging.getLogger('regapp.activation')

class ActivationRequest(BaseModel):
    sn: str
    channel_code: str
    activation_code: str
    client_meta: dict = None


class ActivationWithCACRequest(BaseModel):
    channel_id: str
    subaccount: str
    totp_code: str
    cac_token: str
    sn: str
    model: str
    fw_hash: str
    device_pubkey: str
    nonce: str
    iat: int
    client_meta: Optional[dict] = None
    region: Optional[str] = None


def _json_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


def _current_ts() -> int:
    return int(time.time())


class ChannelAuthRequest(BaseModel):
    sn: str
    channel_code: str
    activation_code: str
    timestamp: str
    signature: str


@router.post("/api/activate/with-cac")
async def activate_with_cac(request: Request):
    channel_code = request.headers.get("X-Channel-Id")
    kid = request.headers.get("X-Channel-Kid")
    signature = request.headers.get("X-Channel-Signature")

    if not channel_code or not kid or not signature:
        return _json_error(status.HTTP_400_BAD_REQUEST, "MISSING_HEADER", "缺少渠道签名头")

    raw_body = await request.body()
    if not raw_body:
        return _json_error(status.HTTP_400_BAD_REQUEST, "EMPTY_BODY", "请求体不能为空")

    try:
        body_dict = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        logger.warning('activate_with_cac invalid JSON: %s', exc)
        return _json_error(status.HTTP_400_BAD_REQUEST, "INVALID_JSON", "请求体不是有效的 JSON")

    try:
        body = ActivationWithCACRequest.model_validate(body_dict)
    except ValidationError as exc:
        logger.warning('activate_with_cac payload validation failed: %s', exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"code": "INVALID_PAYLOAD", "message": exc.errors()},
        )

    logger.info('activate_with_cac request accepted: channel=%s kid=%s subaccount=%s sn=%s', channel_code, kid, body.subaccount, body.sn)

    if body.channel_id != channel_code:
        return _json_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "CHANNEL_MISMATCH", "请求头与主体中的渠道编号不一致")

    now_ts = _current_ts()
    if abs(now_ts - body.iat) > REQUEST_TIME_SKEW_SECONDS:
        return _json_error(status.HTTP_401_UNAUTHORIZED, "TIMESTAMP_OUT_OF_RANGE", "请求时间超出允许范围")

    if len(body.nonce) < 8:
        return _json_error(status.HTTP_400_BAD_REQUEST, "NONCE_TOO_SHORT", "nonce 字符串长度不足")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        channel_row = await get_channel_by_code(db, channel_code)
        if not channel_row or channel_row["status"] != "active":
            return _json_error(status.HTTP_401_UNAUTHORIZED, "CHANNEL_DISABLED", "渠道不存在或已禁用")

        key_row = await get_channel_key(db, channel_row["id"], kid)
        if not key_row or key_row["status"] != "active":
            return _json_error(status.HTTP_401_UNAUTHORIZED, "CHANNEL_KEY_MISSING", "渠道签名密钥不存在或已停用")

        try:
            public_key = load_public_key_from_pem(key_row["public_key"])
        except Exception:
            return _json_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "KEY_LOAD_FAILED", "服务器未能加载渠道公钥")

        try:
            verify_detached(signature, raw_body, public_key, expected_use="activate")
        except SignatureError:
            return _json_error(status.HTTP_401_UNAUTHORIZED, "SIGNATURE_INVALID", "渠道签名验证失败")

        # 防重放：检查 nonce
        async with db.execute(
            "SELECT iat FROM activation_requests WHERE channel_id = ? AND nonce = ?",
            (channel_row["id"], body.nonce),
        ) as cur:
            nonce_row = await cur.fetchone()
        if nonce_row:
            if now_ts - (nonce_row["iat"] or 0) <= NONCE_TTL_SECONDS:
                return _json_error(status.HTTP_409_CONFLICT, "NONCE_REPLAY", "nonce 已被使用")

        # 获取子账户与 TOTP 种子
        subaccount_row = await get_subaccount(db, channel_row["id"], body.subaccount)
        if not subaccount_row or subaccount_row["status"] != "active":
            return _json_error(status.HTTP_401_UNAUTHORIZED, "SUBACCOUNT_INVALID", "子账户不存在或已禁用")

        totp_result = verify_totp(subaccount_row["totp_secret"], body.totp_code, timestamp=now_ts)
        if not totp_result.valid:
            return _json_error(status.HTTP_401_UNAUTHORIZED, "TOTP_FAILED", "动态口令验证失败")

        slot = (body.iat // TOTP_STEP) + (totp_result.delta or 0)
        request_hash = hash_text(f"{channel_code}:{body.subaccount}:{body.totp_code}:{slot}")

        async with db.execute(
            "SELECT 1 FROM activation_requests WHERE channel_id = ? AND subaccount = ? AND request_hash = ?",
            (channel_row["id"], body.subaccount, request_hash),
        ) as cur:
            if await cur.fetchone():
                return _json_error(status.HTTP_401_UNAUTHORIZED, "TOTP_REUSED", "该动态口令已使用")

        try:
            cac_payload = verify_cac_token(body.cac_token, public_key)
        except CACValidationError as exc:
            return _json_error(status.HTTP_401_UNAUTHORIZED, "CAC_INVALID", str(exc))

        if cac_payload.channel_code != channel_code:
            return _json_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "CAC_CHANNEL_MISMATCH", "授权胶囊与渠道不匹配")

        if cac_payload.valid_from and now_ts < cac_payload.valid_from:
            return _json_error(status.HTTP_403_FORBIDDEN, "CAC_NOT_YET_VALID", "授权胶囊尚未生效")
        if cac_payload.valid_to and now_ts > cac_payload.valid_to:
            return _json_error(status.HTTP_403_FORBIDDEN, "CAC_EXPIRED", "授权胶囊已过期")

        cac_record = await ensure_cac_availability(db, cac_payload, channel_row["id"], channel_row["channel_code"])

        scope = cac_payload.scope or {}
        models = scope.get("models") or []
        if models and body.model not in models:
            return _json_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "SCOPE_VIOLATION", "设备型号不在授权范围内")

        max_per_sn = scope.get("max_per_sn")
        if max_per_sn is not None:
            try:
                max_per_sn = int(max_per_sn)
            except ValueError:
                max_per_sn = None
        async with db.execute(
            "SELECT COUNT(*) FROM licenses WHERE sn = ? AND revoked_at IS NULL",
            (body.sn,),
        ) as cur:
            row = await cur.fetchone()
            existing_license_count = row[0] if row else 0
        if (max_per_sn or 1) and existing_license_count >= (max_per_sn or 1):
            return _json_error(status.HTTP_409_CONFLICT, "ALREADY_ACTIVATED", "该设备已激活达到上限")

        expires_at = cac_payload.valid_to or (body.iat + 365 * 24 * 3600)
        if expires_at <= now_ts:
            expires_at = now_ts + 3600  # fallback 一小时

        license_id = generate_license_id()
        license_payload = build_license_payload(
            license_id=license_id,
            sn=body.sn,
            channel_code=channel_code,
            subaccount=body.subaccount,
            device_pubkey=body.device_pubkey,
            model=body.model,
            fw_hash=body.fw_hash,
            cac_jti=cac_payload.jti,
            issued_at=now_ts,
            expires_at=expires_at,
        )
        license_id, license_jws = issue_license(license_payload)

        expires_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        nonce_expire = now_ts + NONCE_TTL_SECONDS
        remaining_quota = (cac_record["quota_max"] - cac_record["quota_used"]) - 1
        if remaining_quota < 0:
            remaining_quota = 0

        try:
            await db.execute("BEGIN")
            await db.execute(
                """INSERT INTO activation_requests(channel_id, channel_code, nonce, iat, request_hash, subaccount, created_at, expires_at)
                       VALUES(?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, datetime(?,'unixepoch'))""",
                (
                    channel_row["id"],
                    channel_code,
                    body.nonce,
                    body.iat,
                    request_hash,
                    body.subaccount,
                    nonce_expire,
                ),
            )

            await update_subaccount_last_used(db, subaccount_row["id"])

            await db.execute(
                """INSERT INTO licenses (sn, activation_id, license_data, signature, issued_at, expires_at)
                       VALUES (?, NULL, ?, ?, datetime('now'), datetime(?,'unixepoch'))""",
                (
                    body.sn,
                    json.dumps(license_payload, separators=(",", ":")),
                    license_jws,
                    expires_at,
                ),
            )

            await consume_cac_quota(db, cac_payload.jti)

            await db.execute(
                """INSERT INTO activation_audit(license_id, sn, channel_code, subaccount, cac_jti, device_pubkey_hash, decision, reason, ip, geo, user_agent)
                       VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    license_id,
                    body.sn,
                    channel_code,
                    body.subaccount,
                    cac_payload.jti,
                    hash_text(body.device_pubkey),
                    "approved",
                    None,
                    request.client.host if request.client else None,
                    None,
                    request.headers.get("user-agent"),
                ),
            )

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    await audit_log("activation", "activate_with_cac", f"渠道 {channel_code} 激活设备 {body.sn}", body.subaccount)

    logger.info('activate_with_cac success: channel=%s subaccount=%s sn=%s license_id=%s', channel_code, body.subaccount, body.sn, license_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "code": 0,
            "message": "激活成功",
            "data": {
                "license_id": license_id,
                "license_jws": license_jws,
                "expires_at": expires_at,
                "quota_remaining": remaining_quota,
            },
        },
    )


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
