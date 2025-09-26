from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..config import (
    PLATFORM_SIGNING_ALGORITHM,
    PLATFORM_SIGNING_KEY_PATH,
    PLATFORM_SIGNING_PUBLIC_KEY_PATH,
)

SUPPORTED_PLATFORM_ALG = {"EdDSA": "Ed25519"}


class PlatformKeyPair:
    """Holder for platform signing keys."""

    def __init__(self, private_key: ed25519.Ed25519PrivateKey) -> None:
        self._private = private_key
        self._public = private_key.public_key()

    @property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        return self._private

    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        return self._public

    def export_private_pem(self) -> bytes:
        return self._private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def export_public_pem(self) -> bytes:
        return self._public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


def _load_private_key_from_file(path: Path) -> Optional[ed25519.Ed25519PrivateKey]:
    if not path.exists():
        return None
    data = path.read_bytes()
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except ValueError:
        return None
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise RuntimeError("Platform signing key must be Ed25519")
    return key


def _ensure_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def ensure_platform_keypair() -> PlatformKeyPair:
    """Load or generate the platform signing key pair."""

    if PLATFORM_SIGNING_ALGORITHM not in SUPPORTED_PLATFORM_ALG:
        raise RuntimeError(
            f"Unsupported PLATFORM_SIGNING_ALGORITHM={PLATFORM_SIGNING_ALGORITHM}."
        )

    priv_path = Path(PLATFORM_SIGNING_KEY_PATH)
    pub_path = Path(PLATFORM_SIGNING_PUBLIC_KEY_PATH)

    private_key = _load_private_key_from_file(priv_path)
    if private_key is None:
        _ensure_parent(priv_path)
        private_key = ed25519.Ed25519PrivateKey.generate()
        priv_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        pub_path.write_bytes(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    elif not pub_path.exists():
        _ensure_parent(pub_path)
        pub_path.write_bytes(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    return PlatformKeyPair(private_key)


def load_public_key_from_pem(pem_data: str) -> ed25519.Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem_data.encode("utf-8"))
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError("Public key must be Ed25519")
    return key


def export_public_key_pem(public_key: ed25519.Ed25519PublicKey) -> str:
    return (
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
        .strip()
    )

