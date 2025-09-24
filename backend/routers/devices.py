from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import aiosqlite
from ..config import DB_PATH
from ..deps import require_user
from ..web import render


router = APIRouter()


class DeviceUpdateForm(BaseModel):
    status: str
    channel_id: int


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request, user: dict = Depends(require_user)):
    """设备管理页面"""
    return render(request, "devices.html", page_title="设备管理", page_description="追踪设备激活状态、渠道归属与生命周期")


@router.get("/api/devices")
async def api_get_devices(user: dict = Depends(require_user)):
    """API获取设备列表"""
    devices = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("""
            SELECT d.id, d.sn, d.status, d.first_seen, d.last_seen, d.activated_at,
                   c.channel_code, c.name as channel_name
            FROM devices d
            LEFT JOIN channels c ON d.channel_id = c.id
            ORDER BY d.first_seen DESC
        """)).fetchall()
        
        for row in rows:
            devices.append({
                "id": row[0],
                "sn": row[1],
                "status": row[2],
                "first_seen": row[3],
                "last_seen": row[4],
                "activated_at": row[5],
                "channel_code": row[6],
                "channel_name": row[7]
            })
    
    return JSONResponse({"ok": True, "data": devices})


@router.get("/api/devices/stats")
async def api_get_device_stats(user: dict = Depends(require_user)):
    """API获取设备统计"""
    stats = {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 总设备数
        row = await (await db.execute("SELECT COUNT(*) FROM devices")).fetchone()
        stats["total"] = row[0] if row else 0
        
        # 已激活设备数
        row = await (await db.execute(
            "SELECT COUNT(*) FROM devices WHERE status = 'activated'"
        )).fetchone()
        stats["activated"] = row[0] if row else 0
        
        # 待激活设备数
        row = await (await db.execute(
            "SELECT COUNT(*) FROM devices WHERE status = 'pending'"
        )).fetchone()
        stats["pending"] = row[0] if row else 0
        
        # 今日新增设备
        row = await (await db.execute(
            "SELECT COUNT(*) FROM devices WHERE date(first_seen) = date('now')"
        )).fetchone()
        stats["today_new"] = row[0] if row else 0
    
    return JSONResponse({"ok": True, "data": stats})


@router.get("/api/devices/{device_id}")
async def api_get_device(device_id: int, user: dict = Depends(require_user)):
    """API获取单个设备详情"""
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("""
            SELECT d.id, d.sn, d.status, d.first_seen, d.last_seen, d.activated_at,
                   c.channel_code, c.name as channel_name, c.id as channel_id
            FROM devices d
            LEFT JOIN channels c ON d.channel_id = c.id
            WHERE d.id = ?
        """, (device_id,))).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="设备不存在")
        
        device = {
            "id": row[0],
            "sn": row[1],
            "status": row[2],
            "first_seen": row[3],
            "last_seen": row[4],
            "activated_at": row[5],
            "channel_code": row[6],
            "channel_name": row[7],
            "channel_id": row[8]
        }
    
    return JSONResponse({"ok": True, "data": device})


@router.put("/api/devices/{device_id}")
async def api_update_device(
    request: Request,
    device_id: int,
    form: DeviceUpdateForm,
    user: dict = Depends(require_user)
):
    """API更新设备信息"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查设备是否存在
        row = await (await db.execute(
            "SELECT sn FROM devices WHERE id = ?", (device_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="设备不存在")
        
        # 检查渠道是否存在
        row = await (await db.execute(
            "SELECT id FROM channels WHERE id = ?", (form.channel_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=400, detail="渠道不存在")
        
        # 更新设备
        await db.execute(
            "UPDATE devices SET status = ?, channel_id = ?, last_seen = datetime('now') WHERE id = ?",
            (form.status, form.channel_id, device_id)
        )
        await db.commit()
    
    return JSONResponse({"ok": True})


@router.delete("/api/devices/{device_id}")
async def api_delete_device(
    request: Request,
    device_id: int,
    user: dict = Depends(require_user)
):
    """API删除设备"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查设备是否存在
        row = await (await db.execute(
            "SELECT sn FROM devices WHERE id = ?", (device_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="设备不存在")
        
        # 删除设备
        await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        await db.commit()
    
    return JSONResponse({"ok": True})
