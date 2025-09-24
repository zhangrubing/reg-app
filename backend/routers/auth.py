from typing import Optional
import aiosqlite
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

try:
    from ..config import DB_PATH, APP_SECRET
    from ..crypto import verify_password, sign_token
    from ..deps import require_user
    from ..utils.audit import audit_log
    from ..web import render
except ImportError:
    # 当直接运行文件时的导入方式
    from config import DB_PATH, APP_SECRET
    from crypto import verify_password, sign_token
    from deps import require_user
    from utils.audit import audit_log
    from web import render


router = APIRouter()


class LoginForm(BaseModel):
    username: str
    password: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return render(request, "login.html", page_title="登录", page_description="进入软件注册与激活管理平台")


@router.post("/api/login")
async def api_login(request: Request, form: LoginForm):
    """API登录"""
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute(
            "SELECT id, username, password_hash, is_admin, token_version FROM users WHERE username=?",
            (form.username,),
        )).fetchone()
        
        if not row or not verify_password(form.password, row[2]):
            await audit_log(form.username, "login_failed", "用户名或密码错误", request)
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        payload = {
            "uid": row[0], 
            "username": row[1], 
            "is_admin": bool(row[3]), 
            "ver": int(row[4])
        }
        token = sign_token(payload, APP_SECRET)
        
        resp = JSONResponse({"ok": True, "user": {"username": row[1], "is_admin": bool(row[3])}})
        resp.set_cookie(
            "auth", 
            token, 
            httponly=True, 
            samesite="lax", 
            secure=False, 
            max_age=8 * 3600, 
            path="/"
        )
        
        # 更新登录信息
        await db.execute(
            """UPDATE users SET last_login_at = datetime('now'), 
               last_login_ip = ?, login_count = login_count + 1 
               WHERE id = ?""",
            (request.client.host if request.client else None, row[0])
        )
        await db.commit()
        
        await audit_log(row[1], "login", "登录成功", request)
        return resp


@router.post("/api/logout")
async def api_logout(request: Request):
    """API登出"""
    user = getattr(request.state, 'user', None)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("auth", path="/")
    
    if user:
        await audit_log(user["username"], "logout", "退出登录", request)
    
    return resp


@router.get("/logout")
async def logout_redirect():
    """登出重定向"""
    resp = RedirectResponse("/login")
    resp.delete_cookie("auth", path="/")
    return resp


@router.get("/api/me")
async def api_me(request: Request, user: dict = Depends(require_user)):
    """获取当前用户信息"""
    return {"user": user}
