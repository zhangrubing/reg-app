from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

SUPPORTED_JWS_ALG = {"EdDSA": ed25519.Ed25519PrivateKey}


class SignatureError(Exception):
    """Raised when signatures cannot be verified."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _ensure_algorithm(alg: str) -> None:
    if alg not in SUPPORTED_JWS_ALG:
        raise SignatureError(f"Unsupported algorithm: {alg}")


def sign_payload(payload: Dict[str, Any], private_key: ed25519.Ed25519PrivateKey,
                 *, kid: Optional[str] = None, alg: str = "EdDSA") -> str:
    """Create a compact JWS for JSON payload using Ed25519."""
    _ensure_algorithm(alg)
    header = {"alg": alg, "typ": "JWT"}
    if kid:
        header["kid"] = kid
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(payload_bytes)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = private_key.sign(signing_input)
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def sign_detached(body: bytes, private_key: ed25519.Ed25519PrivateKey,
                  *, kid: Optional[str] = None, alg: str = "EdDSA",
                  purpose: str = "activate") -> str:
    """Sign arbitrary body bytes as detached JWS (compact format)."""
    _ensure_algorithm(alg)
    header: Dict[str, Any] = {"alg": alg, "typ": "JOSE", "use": purpose}
    if kid:
        header["kid"] = kid
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(body)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = private_key.sign(signing_input)
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def verify_detached(signature: str, body: bytes, public_key: ed25519.Ed25519PublicKey,
                    expected_use: Optional[str] = None) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = signature.split('.')
    except ValueError as exc:
        raise SignatureError("Invalid signature format") from exc

    header = json.loads(_b64url_decode(header_b64))
    alg = header.get("alg")
    _ensure_algorithm(alg)
    if expected_use and header.get("use") not in (expected_use, None):
        raise SignatureError("Signature use mismatch")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig_bytes = _b64url_decode(signature_b64)

    try:
        public_key.verify(sig_bytes, signing_input)
    except Exception as exc:
        raise SignatureError("Signature verification failed") from exc

    attached_payload = _b64url_decode(payload_b64)
    if attached_payload != body:
        raise SignatureError("Detached payload mismatch")

    return header



def verify_compact(jws: str, public_key: ed25519.Ed25519PublicKey) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    try:
        header_b64, payload_b64, signature_b64 = jws.split('.')
    except ValueError as exc:
        raise SignatureError('Invalid JWS format') from exc

    header = json.loads(_b64url_decode(header_b64))
    alg = header.get('alg')
    _ensure_algorithm(alg)

    signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
    sig_bytes = _b64url_decode(signature_b64)

    try:
        public_key.verify(sig_bytes, signing_input)
    except Exception as exc:
        raise SignatureError('JWS verification failed') from exc

    payload_bytes = _b64url_decode(payload_b64)
    try:
        payload = json.loads(payload_bytes.decode('utf-8'))
    except Exception as exc:
        raise SignatureError('CAC payload must be JSON') from exc
    return header, payload
