from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import aiosqlite
from datetime import datetime
from ..config import DB_PATH
from ..deps import require_user, require_admin
from ..crypto import generate_activation_code
from ..web import render


router = APIRouter()


class ActivationCreateForm(BaseModel):
    channel_id: int
    count: int = 1
    expires_at: str = None
    max_uses: int = 1


@router.get("/activations", response_class=HTMLResponse)
async def activations_page(request: Request, user: dict = Depends(require_user)):
    """激活记录页面"""
    return render(request, "activations.html", page_title="激活记录", page_description="掌握激活码使用情况与渠道投放表现")


@router.get("/api/activations")
async def api_get_activations(user: dict = Depends(require_user)):
    """API获取激活记录列表"""
    activations = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("""
            SELECT a.id, a.activation_code, a.sn, a.status, a.expires_at, 
                   a.max_uses, a.used_count, a.created_at, a.activated_at,
                   c.channel_code, c.name as channel_name
            FROM activations a
            JOIN channels c ON a.channel_id = c.id
            ORDER BY a.created_at DESC
        """)).fetchall()
        
        for row in rows:
            activations.append({
                "id": row[0],
                "activation_code": row[1],
                "sn": row[2],
                "status": row[3],
                "expires_at": row[4],
                "max_uses": row[5],
                "used_count": row[6],
                "created_at": row[7],
                "activated_at": row[8],
                "channel_code": row[9],
                "channel_name": row[10]
            })
    
    return JSONResponse({"ok": True, "data": activations})


@router.post("/api/activations/generate")
async def api_generate_activations(
    request: Request,
    form: ActivationCreateForm,
    user: dict = Depends(require_admin)
):
    """API批量生成激活码"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查渠道是否存在
        row = await (await db.execute(
            "SELECT id FROM channels WHERE id = ?", (form.channel_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=400, detail="渠道不存在")
        
        # 生成激活码
        activation_codes = []
        for _ in range(form.count):
            code = generate_activation_code(16)
            activation_codes.append(code)
            
            await db.execute(
                """INSERT INTO activations (activation_code, channel_id, expires_at, max_uses) 
                   VALUES (?, ?, ?, ?)""",
                (code, form.channel_id, form.expires_at, form.max_uses)
            )
        
        await db.commit()
    
    return JSONResponse({
        "ok": True, 
        "data": {
            "count": len(activation_codes),
            "codes": activation_codes
        }
    })


@router.delete("/api/activations/{activation_id}")
async def api_delete_activation(
    request: Request,
    activation_id: int,
    user: dict = Depends(require_admin)
):
    """API删除激活码"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查激活码是否存在
        row = await (await db.execute(
            "SELECT activation_code, used_count FROM activations WHERE id = ?", 
            (activation_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="激活码不存在")
        
        if row[1] > 0:
            raise HTTPException(status_code=400, detail="已使用的激活码不能删除")
        
        # 删除激活码
        await db.execute("DELETE FROM activations WHERE id = ?", (activation_id,))
        await db.commit()
    
    return JSONResponse({"ok": True})


@router.post("/api/activations/{activation_id}/toggle")
async def api_toggle_activation(
    request: Request,
    activation_id: int,
    user: dict = Depends(require_admin)
):
    """API切换激活码状态"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查激活码是否存在
        row = await (await db.execute(
            "SELECT status, used_count FROM activations WHERE id = ?", 
            (activation_id,)
        )).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="激活码不存在")
        
        current_status, used_count = row
        
        if used_count > 0:
            raise HTTPException(status_code=400, detail="已使用的激活码不能禁用")
        
        new_status = "inactive" if current_status == "active" else "active"
        
        # 更新状态
        await db.execute(
            "UPDATE activations SET status = ? WHERE id = ?", 
            (new_status, activation_id)
        )
        await db.commit()
    
    return JSONResponse({"ok": True, "data": {"status": new_status}})


@router.get("/api/activations/stats")
async def api_get_activation_stats(user: dict = Depends(require_user)):
    """API获取激活统计"""
    stats = {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 总激活码数
        row = await (await db.execute("SELECT COUNT(*) FROM activations")).fetchone()
        stats["total"] = row[0] if row else 0
        
        # 活跃激活码数
        row = await (await db.execute(
            "SELECT COUNT(*) FROM activations WHERE status = 'active'"
        )).fetchone()
        stats["active"] = row[0] if row else 0
        
        # 已使用激活码数
        row = await (await db.execute(
            "SELECT COUNT(*) FROM activations WHERE used_count > 0"
        )).fetchone()
        stats["used"] = row[0] if row else 0
        
        # 今日生成的激活码
        row = await (await db.execute(
            "SELECT COUNT(*) FROM activations WHERE date(created_at) = date('now')"
        )).fetchone()
        stats["today_generated"] = row[0] if row else 0
        
        # 今日激活的设备
        row = await (await db.execute(
            "SELECT COUNT(*) FROM activations WHERE date(activated_at) = date('now')"
        )).fetchone()
        stats["today_activated"] = row[0] if row else 0
    
    return JSONResponse({"ok": True, "data": stats})
