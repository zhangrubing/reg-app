from __future__ import annotations

from typing import Any, Dict, Optional

import aiosqlite


async def get_channel_by_code(db: aiosqlite.Connection, channel_code: str) -> Optional[aiosqlite.Row]:
    async with db.execute(
        "SELECT id, channel_code, name, status FROM channels WHERE channel_code = ?",
        (channel_code,),
    ) as cur:
        row = await cur.fetchone()
    return row


async def get_channel_key(db: aiosqlite.Connection, channel_id: int, kid: str) -> Optional[aiosqlite.Row]:
    async with db.execute(
        """SELECT id, channel_id, channel_code, kid, algorithm, public_key, status
               FROM channel_keys WHERE channel_id = ? AND kid = ?""",
        (channel_id, kid),
    ) as cur:
        row = await cur.fetchone()
    return row


async def get_subaccount(db: aiosqlite.Connection, channel_id: int, subaccount: str) -> Optional[aiosqlite.Row]:
    async with db.execute(
        """SELECT id, channel_id, channel_code, subaccount, totp_secret, status, last_used_at
               FROM channel_subaccounts WHERE channel_id = ? AND subaccount = ?""",
        (channel_id, subaccount),
    ) as cur:
        row = await cur.fetchone()
    return row


async def update_subaccount_last_used(db: aiosqlite.Connection, subaccount_id: int) -> None:
    await db.execute(
        "UPDATE channel_subaccounts SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
        (subaccount_id,),
    )


async def upsert_channel_key(db: aiosqlite.Connection, data: Dict[str, Any]) -> None:
    await db.execute(
        """INSERT INTO channel_keys(channel_id, channel_code, kid, algorithm, public_key, status)
               VALUES(:channel_id, :channel_code, :kid, :algorithm, :public_key, :status)
               ON CONFLICT(channel_id, kid) DO UPDATE SET
                 algorithm=excluded.algorithm,
                 public_key=excluded.public_key,
                 status=excluded.status,
                 rotated_at=CURRENT_TIMESTAMP""",
        data,
    )


async def upsert_subaccount(db: aiosqlite.Connection, data: Dict[str, Any]) -> None:
    await db.execute(
        """INSERT INTO channel_subaccounts(channel_id, channel_code, subaccount, totp_secret, status)
               VALUES(:channel_id, :channel_code, :subaccount, :totp_secret, :status)
               ON CONFLICT(channel_id, subaccount) DO UPDATE SET
                 totp_secret=excluded.totp_secret,
                 status=excluded.status""",
        data,
    )

