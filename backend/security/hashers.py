from __future__ import annotations

import hashlib
from typing import Literal


def sha256_base64(data: bytes) -> str:
    return hashlib.sha256(data).digest().hex()


def hash_text(value: str, algorithm: Literal['sha256'] = 'sha256') -> str:
    if algorithm != 'sha256':
        raise ValueError('Unsupported hash algorithm')
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

