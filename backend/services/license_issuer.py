from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from ..security.keys import ensure_platform_keypair
from ..security.signatures import sign_payload


def _now_ts() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def generate_license_id(prefix: str = "LIC") -> str:
    return f"{prefix}-{datetime.utcnow():%y%m%d}-{secrets.randbelow(10**6):06d}"


def build_license_payload(*, license_id: str, sn: str, channel_code: str, subaccount: str,
                          device_pubkey: str, model: str, fw_hash: str, cac_jti: str,
                          issued_at: int, expires_at: int) -> Dict[str, Any]:
    return {
        "typ": "license",
        "license_id": license_id,
        "sn": sn,
        "channel": channel_code,
        "subaccount": subaccount,
        "device_pubkey": device_pubkey,
        "model": model,
        "fw_hash": fw_hash,
        "cac_jti": cac_jti,
        "iat": issued_at,
        "exp": expires_at,
        "version": 1,
    }


def issue_license(payload: Dict[str, Any], *, kid: str = "platform-v1") -> Tuple[str, str]:
    keypair = ensure_platform_keypair()
    jws = sign_payload(payload, keypair.private_key, kid=kid)
    return payload["license_id"], jws

