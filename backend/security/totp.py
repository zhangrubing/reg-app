from __future__ import annotations

import time
from typing import Optional, Tuple

import pyotp

from ..config import TOTP_ALLOWED_DRIFT, TOTP_STEP


class TotpValidationResult:
    __slots__ = ("valid", "delta")

    def __init__(self, valid: bool, delta: Optional[int] = None) -> None:
        self.valid = valid
        self.delta = delta


def verify_totp(secret: str, code: str, *, timestamp: Optional[int] = None,
                step: int = TOTP_STEP, allowed_drift: int = TOTP_ALLOWED_DRIFT) -> TotpValidationResult:
    """Validate a TOTP code with configurable drift."""
    ts = timestamp or int(time.time())
    totp = pyotp.TOTP(secret, interval=step)
    # pyotp returns bool; to know drift we try windows
    if totp.verify(code, for_time=ts, valid_window=allowed_drift):
        # find the delta window used
        for delta in range(-allowed_drift, allowed_drift + 1):
            if totp.verify(code, for_time=ts + delta * step, valid_window=0):
                return TotpValidationResult(True, delta)
        return TotpValidationResult(True, 0)
    return TotpValidationResult(False, None)

