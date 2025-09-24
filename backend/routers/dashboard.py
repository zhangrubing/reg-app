from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
import aiosqlite

try:
    from ..config import DB_PATH
    from ..deps import require_user
    from ..web import render
except ImportError:
    # 当直接运行文件时的导入方式
    from config import DB_PATH
    from deps import require_user
    from web import render


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return render(request, "index.html", page_title="欢迎", page_description="查看系统运行概览与快速导航")

@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """关于页面"""
    return render(request, "about.html", page_title="关于系统", page_description="平台架构、能力与合规说明")



@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_user)):
    """仪表板页面"""
    stats = {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 获取统计数据
        # 总设备数
        row = await (await db.execute("SELECT COUNT(*) as count FROM devices")).fetchone()
        stats["total_devices"] = row[0] if row else 0
        
        # 已激活设备数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM devices WHERE status = 'activated'"
        )).fetchone()
        stats["activated_devices"] = row[0] if row else 0
        
        # 总渠道数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM channels WHERE status = 'active'"
        )).fetchone()
        stats["active_channels"] = row[0] if row else 0
        
        # 总激活码数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM activations WHERE status = 'active'"
        )).fetchone()
        stats["active_activations"] = row[0] if row else 0
        
        # 今日激活数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM activations WHERE date(activated_at) = date('now')"
        )).fetchone()
        stats["today_activations"] = row[0] if row else 0
        
        # 最近激活记录
        recent_activations = await (await db.execute("""
            SELECT a.activation_code, a.sn, a.activated_at, c.channel_code, c.name as channel_name
            FROM activations a
            JOIN channels c ON a.channel_id = c.id
            WHERE a.activated_at IS NOT NULL
            ORDER BY a.activated_at DESC
            LIMIT 10
        """)).fetchall()
        
        stats["recent_activations"] = [
            {
                "activation_code": row[0],
                "sn": row[1],
                "activated_at": row[2],
                "channel_code": row[3],
                "channel_name": row[4]
            }
            for row in recent_activations
        ]
    
    return render(request, "dashboard.html", stats=stats, page_title="仪表盘", page_description="核心指标实时洞察与最新激活动态")


@router.get("/api/dashboard/stats")
async def api_dashboard_stats(user: dict = Depends(require_user)):
    """API获取仪表板统计数据"""
    stats = {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 总设备数
        row = await (await db.execute("SELECT COUNT(*) as count FROM devices")).fetchone()
        stats["total_devices"] = row[0] if row else 0
        
        # 已激活设备数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM devices WHERE status = 'activated'"
        )).fetchone()
        stats["activated_devices"] = row[0] if row else 0
        
        # 总渠道数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM channels WHERE status = 'active'"
        )).fetchone()
        stats["active_channels"] = row[0] if row else 0
        
        # 总激活码数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM activations WHERE status = 'active'"
        )).fetchone()
        stats["active_activations"] = row[0] if row else 0
        
        # 今日激活数
        row = await (await db.execute(
            "SELECT COUNT(*) as count FROM activations WHERE date(activated_at) = date('now')"
        )).fetchone()
        stats["today_activations"] = row[0] if row else 0
    
    return JSONResponse({"ok": True, "data": stats})
