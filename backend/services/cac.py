from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiosqlite

from ..security.signatures import SignatureError, verify_compact


@dataclass
class CACPayload:
    raw: Dict[str, Any]
    jti: str
    channel_code: str
    quota_max: int
    valid_from: Optional[int]
    valid_to: Optional[int]
    scope: Dict[str, Any]
    policy: Dict[str, Any]


class CACValidationError(Exception):
    pass


async def load_cac_record(db: aiosqlite.Connection, jti: str) -> Optional[aiosqlite.Row]:
    async with db.execute(
        "SELECT id, jti, channel_id, channel_code, payload, quota_max, quota_used, valid_from, valid_to, status"
        " FROM cac_tokens WHERE jti = ?",
        (jti,),
    ) as cur:
        return await cur.fetchone()


async def upsert_cac(db: aiosqlite.Connection, channel_id: int, channel_code: str,
                     payload: Dict[str, Any], encrypted: int = 0) -> None:
    await db.execute(
        """INSERT INTO cac_tokens(jti, channel_id, channel_code, payload, quota_max, quota_used, valid_from, valid_to, status, encrypted)
               VALUES(:jti, :channel_id, :channel_code, :payload, :quota_max, :quota_used, :valid_from, :valid_to, :status, :encrypted)
               ON CONFLICT(jti) DO UPDATE SET
                 channel_id = excluded.channel_id,
                 channel_code = excluded.channel_code,
                 payload = excluded.payload,
                 quota_max = excluded.quota_max,
                 valid_from = excluded.valid_from,
                 valid_to = excluded.valid_to,
                 status = excluded.status,
                 encrypted = excluded.encrypted,
                 updated_at = CURRENT_TIMESTAMP""",
        {
            "jti": payload["jti"],
            "channel_id": channel_id,
            "channel_code": channel_code,
            "payload": json.dumps(payload, separators=(",", ":")),
            "quota_max": int(payload.get("quota", {}).get("max_activations", 0) or 0),
            "quota_used": 0,
            "valid_from": payload.get("quota", {}).get("valid_from"),
            "valid_to": payload.get("quota", {}).get("valid_to"),
            "status": payload.get("status", "active"),
            "encrypted": encrypted,
        },
    )


def parse_cac_payload(payload: Dict[str, Any]) -> CACPayload:
    try:
        jti = payload["jti"]
        channel_code = payload["channel_id"]
    except KeyError as exc:
        raise CACValidationError("CAC payload missing required fields") from exc

    quota = payload.get("quota", {})
    quota_max = int(quota.get("max_activations", 0) or 0)
    if quota_max <= 0:
        raise CACValidationError("CAC quota max must be > 0")

    return CACPayload(
        raw=payload,
        jti=jti,
        channel_code=channel_code,
        quota_max=quota_max,
        valid_from=quota.get("valid_from"),
        valid_to=quota.get("valid_to"),
        scope=payload.get("scope", {}),
        policy=payload.get("policy", {}),
    )


def verify_cac_token(cac_token: str, public_key) -> CACPayload:
    try:
        header, payload = verify_compact(cac_token, public_key)
    except SignatureError as exc:
        raise CACValidationError(str(exc)) from exc

    if header.get("typ") not in {"cac", "CAC"}:
        raise CACValidationError("Invalid CAC token type")

    return parse_cac_payload(payload)



async def ensure_cac_availability(db: aiosqlite.Connection, cac: CACPayload, channel_id: int, channel_code: str) -> Optional[aiosqlite.Row]:
    record = await load_cac_record(db, cac.jti)
    if record is None:
        await upsert_cac(db, channel_id, cac.channel_id, cac.raw)
        record = await load_cac_record(db, cac.jti)
    if record["status"] != 'active':
        raise CACValidationError('CAC token has been revoked')
    if record["quota_used"] >= record["quota_max"]:
        raise CACValidationError('CAC quota exhausted')
    return record


async def consume_cac_quota(db: aiosqlite.Connection, jti: str, amount: int = 1) -> None:
    await db.execute(
        "UPDATE cac_tokens SET quota_used = quota_used + ?, updated_at = CURRENT_TIMESTAMP WHERE jti = ?",
        (amount, jti),
    )
