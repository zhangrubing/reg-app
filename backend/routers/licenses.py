from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from ..config import DB_PATH
from ..deps import require_admin, require_user
from ..web import render

router = APIRouter()


def _row_to_license(row: aiosqlite.Row) -> Dict[str, Any]:
    license_id, sn, activation_id, license_data, signature, issued_at, expires_at, revoked_at = row
    data: Dict[str, Any] = {}
    if license_data:
        try:
            data = json.loads(license_data)
        except json.JSONDecodeError:
            data = {"raw": license_data}

    status = "active"
    expires_dt = datetime.fromisoformat(expires_at) if expires_at else None
    if revoked_at:
        status = "revoked"
    elif expires_dt and expires_dt < datetime.utcnow():
        status = "expired"

    return {
        "id": license_id,
        "sn": sn,
        "activation_id": activation_id,
        "license_data": data,
        "product_name": data.get("product_name"),
        "notes": data.get("notes"),
        "max_activations": data.get("max_activations"),
        "features": data.get("features"),
        "signature": signature,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "revoked_at": revoked_at,
        "status": status,
    }


def _build_where_clause(search: Optional[str], sn: Optional[str]) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    args: List[Any] = []
    if sn:
        clauses.append("sn LIKE ?")
        args.append(f"%{sn}%")
    if search:
        clauses.append("(sn LIKE ? OR license_data LIKE ?)")
        args.extend([f"%{search}%", f"%{search}%"])
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where_sql, args


@router.get("/licenses", response_class=HTMLResponse)
async def licenses_page(request: Request, user: dict = Depends(require_user)):
    """许可证管理页面"""
    return render(
        request,
        "licenses.html",
        page_title="许可证管理",
        page_description="生成许可证、设置有效期并管理吊销状态",
    )


@router.get("/api/licenses")
async def api_list_licenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="active/expired/revoked"),
    sn: Optional[str] = Query(None),
    user: dict = Depends(require_user),
):
    offset = (page - 1) * page_size
    where_sql, args = _build_where_clause(search, sn)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        count_sql = f"SELECT COUNT(*) FROM licenses {where_sql}"
        total = (await (await db.execute(count_sql, args)).fetchone())[0]

        query = (
            "SELECT id, sn, activation_id, license_data, signature, issued_at, expires_at, revoked_at "
            "FROM licenses "
            f"{where_sql} "
            "ORDER BY issued_at DESC "
            "LIMIT ? OFFSET ?"
        )
        rows = await (await db.execute(query, args + [page_size, offset])).fetchall()

    items = [_row_to_license(row) for row in rows]
    if status:
        items = [item for item in items if item["status"] == status]

    pages = (total + page_size - 1) // page_size if page_size else 1
    return {
        "ok": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(pages, 1),
        },
    }

@router.get("/api/licenses/stats")
async def api_license_stats(user: dict = Depends(require_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT id, sn, activation_id, license_data, signature, issued_at, expires_at, revoked_at FROM licenses"
        )).fetchall()

    items = [_row_to_license(row) for row in rows]
    total = len(items)
    active = sum(1 for item in items if item["status"] == "active")
    expired = sum(1 for item in items if item["status"] == "expired")
    revoked = sum(1 for item in items if item["status"] == "revoked")
    month_created = sum(
        1
        for item in items
        if item["issued_at"]
        and datetime.fromisoformat(item["issued_at"]).year == datetime.utcnow().year
        and datetime.fromisoformat(item["issued_at"]).month == datetime.utcnow().month
    )

    return {
        "ok": True,
        "data": {
            "total": total,
            "active": active,
            "expired": expired,
            "revoked": revoked,
            "month": month_created,
        },
    }


def _build_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    product_name = (payload.get("product_name") or payload.get("product") or "").strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="缺少产品名称")

    sn = (payload.get("sn") or "").strip()
    if not sn:
        raise HTTPException(status_code=400, detail="缺少设备序列号")

    try:
        max_activations = int(payload.get("max_activations") or 1)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="max_activations 需要是数字")

    valid_days = payload.get("valid_days")
    expires_at = payload.get("expires_at")
    expires_dt: Optional[datetime] = None
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="expires_at 格式错误，应为 ISO8601")
    elif valid_days:
        try:
            expires_dt = datetime.utcnow() + timedelta(days=int(valid_days))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="valid_days 需要是数字")

    data = {
        "product_name": product_name,
        "max_activations": max_activations,
        "notes": (payload.get("notes") or "").strip(),
        "features": payload.get("features") or [],
    }

    return {
        "sn": sn,
        "activation_id": payload.get("activation_id"),
        "license_data": json.dumps(data, ensure_ascii=False),
        "signature": payload.get("signature") or f"{sn}-{int(datetime.utcnow().timestamp())}",
        "expires_at": expires_dt.isoformat() if expires_dt else None,
    }


@router.post("/api/licenses")
async def api_create_license(payload: Dict[str, Any], user: dict = Depends(require_admin)):
    record = _build_payload(payload)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO licenses (sn, activation_id, license_data, signature, expires_at)
            VALUES (?, ?, ?, ?, ?)""",
            (
                record["sn"],
                record["activation_id"],
                record["license_data"],
                record["signature"],
                record["expires_at"],
            ),
        )
        await db.commit()
    return {"ok": True}


@router.put("/api/licenses/{license_id}")
async def api_update_license(license_id: int, payload: Dict[str, Any], user: dict = Depends(require_admin)):
    record = _build_payload(payload)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM licenses WHERE id = ?", (license_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="许可证不存在")
        await db.execute(
            """UPDATE licenses SET sn = ?, activation_id = ?, license_data = ?, signature = ?, expires_at = ?
            WHERE id = ?""",
            (
                record["sn"],
                record["activation_id"],
                record["license_data"],
                record["signature"],
                record["expires_at"],
                license_id,
            ),
        )
        await db.commit()
    return {"ok": True}


@router.post("/api/licenses/{license_id}/revoke")
async def api_revoke_license(license_id: int, user: dict = Depends(require_admin)):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM licenses WHERE id = ?", (license_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="许可证不存在")
        await db.execute(
            "UPDATE licenses SET revoked_at = datetime('now') WHERE id = ?",
            (license_id,),
        )
        await db.commit()
    return {"ok": True}


@router.delete("/api/licenses/{license_id}")
async def api_delete_license(license_id: int, user: dict = Depends(require_admin)):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM licenses WHERE id = ?", (license_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="许可证不存在")
        await db.execute("DELETE FROM licenses WHERE id = ?", (license_id,))
        await db.commit()
    return {"ok": True}


@router.get("/api/licenses/export")
async def api_export_licenses(user: dict = Depends(require_admin)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT id, sn, activation_id, license_data, signature, issued_at, expires_at, revoked_at FROM licenses"
        )).fetchall()

    items = [_row_to_license(row) for row in rows]
    headers = ["ID", "SN", "Activation ID", "Product", "Status", "Issued At", "Expires At", "Revoked At"]
    lines = [",".join(headers)]
    for item in items:
        lines.append(
            ",".join(
                [
                    str(item.get("id", "")),
                    item.get("sn", "") or "",
                    str(item.get("activation_id") or ""),
                    item.get("product_name") or "",
                    item.get("status", ""),
                    item.get("issued_at") or "",
                    item.get("expires_at") or "",
                    item.get("revoked_at") or "",
                ]
            )
        )

    csv_content = "\n".join(lines)
    csv_bytes = csv_content.encode("utf-8-sig")
    filename = f"licenses-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

