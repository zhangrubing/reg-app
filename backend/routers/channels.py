from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import aiosqlite
from ..config import DB_PATH
from ..deps import require_user, require_admin
from ..utils.audit import audit_log
from ..web import render


router = APIRouter()


class ChannelForm(BaseModel):
    channel_code: str
    name: str
    api_key: str
    secret_hmac: str


@router.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request, user: dict = Depends(require_user)):
    """渠道管理页面"""
    return render(request, "channels.html", page_title="渠道管理", page_description="配置渠道信息、API 密钥与停用策略")


@router.get("/api/channels")
async def api_get_channels(user: dict = Depends(require_user)):
    """API获取渠道列表"""
    channels = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("""
            SELECT id, channel_code, name, api_key, secret_hmac, status, created_at
            FROM channels
            ORDER BY created_at DESC
        """)).fetchall()
        
        for row in rows:
            channels.append({
                "id": row[0],
                "channel_code": row[1],
                "name": row[2],
                "api_key": row[3],
                "secret_hmac": row[4],
                "status": row[5],
                "created_at": row[6]
            })
    
    return JSONResponse({"ok": True, "data": channels})


@router.post("/api/channels")
async def api_create_channel(
    request: Request,
    form: ChannelForm,
    user: dict = Depends(require_admin)
):
    """API创建渠道"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查渠道代码是否已存在
        row = await (await db.execute(
            "SELECT id FROM channels WHERE channel_code = ?", 
            (form.channel_code,)
        )).fetchone()
        
        if row:
            raise HTTPException(status_code=400, detail="渠道代码已存在")
        
        # 创建渠道
        cursor = await db.execute(
            """INSERT INTO channels (channel_code, name, api_key, secret_hmac) 
               VALUES (?, ?, ?, ?)""",
            (form.channel_code, form.name, form.api_key, form.secret_hmac)
        )
        channel_id = cursor.lastrowid
        await db.commit()
        
        await audit_log(user["username"], "create_channel", 
                       f"创建渠道: {form.channel_code} - {form.name}", request)
        
        return JSONResponse({"ok": True, "data": {"id": channel_id}})


@router.put("/api/channels/{channel_id}")
async def api_update_channel(
    request: Request,
    channel_id: int,
    form: ChannelForm,
    user: dict = Depends(require_admin)
):
    """API更新渠道"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查渠道是否存在
        row = await (await db.execute(
            "SELECT channel_code, name FROM channels WHERE id = ?", 
            (channel_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="渠道不存在")
        
        old_code, old_name = row
        
        # 检查渠道代码是否被其他渠道使用
        row = await (await db.execute(
            "SELECT id FROM channels WHERE channel_code = ? AND id != ?", 
            (form.channel_code, channel_id)
        )).fetchone()
        
        if row:
            raise HTTPException(status_code=400, detail="渠道代码已存在")
        
        # 更新渠道
        await db.execute(
            """UPDATE channels SET channel_code = ?, name = ?, 
               api_key = ?, secret_hmac = ? WHERE id = ?""",
            (form.channel_code, form.name, form.api_key, form.secret_hmac, channel_id)
        )
        await db.commit()
        
        await audit_log(user["username"], "update_channel", 
                       f"更新渠道: {old_code} -> {form.channel_code}", request)
        
        return JSONResponse({"ok": True})


@router.delete("/api/channels/{channel_id}")
async def api_delete_channel(
    request: Request,
    channel_id: int,
    user: dict = Depends(require_admin)
):
    """API删除渠道"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查渠道是否存在
        row = await (await db.execute(
            "SELECT channel_code, name FROM channels WHERE id = ?", 
            (channel_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="渠道不存在")
        
        channel_code, name = row
        
        # 检查是否有关联的设备
        row = await (await db.execute(
            "SELECT COUNT(*) FROM devices WHERE channel_id = ?", 
            (channel_id,)
        )).fetchone()
        
        if row and row[0] > 0:
            raise HTTPException(status_code=400, detail="渠道下存在设备，无法删除")
        
        # 删除渠道
        await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()
        
        await audit_log(user["username"], "delete_channel", 
                       f"删除渠道: {channel_code} - {name}", request)
        
        return JSONResponse({"ok": True})


@router.post("/api/channels/{channel_id}/toggle")
async def api_toggle_channel(
    request: Request,
    channel_id: int,
    user: dict = Depends(require_admin)
):
    """API切换渠道状态"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查渠道是否存在
        row = await (await db.execute(
            "SELECT channel_code, name, status FROM channels WHERE id = ?", 
            (channel_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="渠道不存在")
        
        channel_code, name, current_status = row
        new_status = "inactive" if current_status == "active" else "active"
        
        # 更新状态
        await db.execute(
            "UPDATE channels SET status = ? WHERE id = ?", 
            (new_status, channel_id)
        )
        await db.commit()
        
        action = "disable_channel" if new_status == "inactive" else "enable_channel"
        await audit_log(user["username"], action, 
                       f"切换渠道状态: {channel_code} - {name} -> {new_status}", request)
        
        return JSONResponse({"ok": True, "data": {"status": new_status}})
