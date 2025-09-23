from typing import List, Optional
from datetime import datetime
import aiosqlite
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..config import DB_PATH as DATABASE_PATH
from ..deps import require_user, require_admin
from ..utils.audit import audit_log

router = APIRouter(prefix="/users", tags=["用户管理"])

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    is_admin: bool = Field(False, description="是否为管理员")
    status: str = Field("active", description="状态: active, inactive")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="密码")
    is_admin: Optional[bool] = Field(None, description="是否为管理员")
    status: Optional[str] = Field(None, description="状态: active, inactive")

class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    status: str
    created_at: str
    last_login: Optional[str] = None

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    pages: int

@router.get("/statistics", dependencies=[Depends(require_user)])
async def get_user_statistics():
    """获取用户统计信息"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 总用户数
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # 管理员数
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = (await cursor.fetchone())[0]
        
        # 活跃用户
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        active_users = (await cursor.fetchone())[0]
        
        # 今日登录用户
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE action = 'login' AND DATE(created_at) = DATE(?)",
            (today,)
        )
        today_login = (await cursor.fetchone())[0]
        
        return {
            "total_users": total_users,
            "admin_count": admin_count,
            "active_users": active_users,
            "today_login": today_login
        }

@router.get("", response_model=UserListResponse, dependencies=[Depends(require_admin)])
async def get_users(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    status: str = "",
    is_admin: Optional[bool] = None
):
    """获取用户列表"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    
    offset = (page - 1) * page_size
    
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("username LIKE ?")
            params.append(f"%{search}%")
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
        
        if is_admin is not None:
            where_conditions.append("is_admin = ?")
            params.append(is_admin)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        cursor = await db.execute(count_query, params)
        total = (await cursor.fetchone())[0]
        
        # 获取用户列表
        query = f"""
            SELECT id, username, is_admin, status, created_at, last_login 
            FROM users 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "username": row[1],
                "is_admin": bool(row[2]),
                "status": row[3],
                "created_at": row[4],
                "last_login": row[5]
            })
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": users,
            "total": total,
            "page": page,
            "pages": pages
        }

@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def get_user(user_id: int):
    """获取用户详情"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, username, is_admin, status, created_at, last_login FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "id": row[0],
            "username": row[1],
            "is_admin": bool(row[2]),
            "status": row[3],
            "created_at": row[4],
            "last_login": row[5]
        }

@router.post("", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(user: UserCreate):
    """创建用户"""
    from ..crypto import hash_password
    
    # 检查用户名是否已存在
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (user.username,))
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建用户
        hashed_password = hash_password(user.password)
        now = datetime.now().isoformat()
        
        cursor = await db.execute(
            """INSERT INTO users (username, password, is_admin, status, created_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (user.username, hashed_password, user.is_admin, user.status, now)
        )
        user_id = cursor.lastrowid
        await db.commit()
        
        # 记录审计日志
        await audit_log("create_user", f"创建用户: {user.username}", user_id)
        
        return {
            "id": user_id,
            "username": user.username,
            "is_admin": user.is_admin,
            "status": user.status,
            "created_at": now,
            "last_login": None
        }

@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def update_user(user_id: int, user_update: UserUpdate):
    """更新用户"""
    from ..crypto import hash_password
    
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 检查用户是否存在
        cursor = await db.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        old_username = row[0]
        
        # 构建更新语句
        update_fields = []
        params = []
        
        if user_update.username is not None:
            # 检查新用户名是否已存在
            cursor = await db.execute("SELECT id FROM users WHERE username = ? AND id != ?", 
                                    (user_update.username, user_id))
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            update_fields.append("username = ?")
            params.append(user_update.username)
        
        if user_update.password is not None:
            hashed_password = hash_password(user_update.password)
            update_fields.append("password = ?")
            params.append(hashed_password)
        
        if user_update.is_admin is not None:
            update_fields.append("is_admin = ?")
            params.append(user_update.is_admin)
        
        if user_update.status is not None:
            update_fields.append("status = ?")
            params.append(user_update.status)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有提供更新字段")
        
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute(query, params)
        await db.commit()
        
        # 记录审计日志
        changes = []
        if user_update.username is not None:
            changes.append(f"用户名: {old_username} -> {user_update.username}")
        if user_update.is_admin is not None:
            changes.append(f"管理员权限: {user_update.is_admin}")
        if user_update.status is not None:
            changes.append(f"状态: {user_update.status}")
        
        await audit_log("update_user", f"更新用户 #{user_id}: {', '.join(changes)}", user_id)
        
        # 返回更新后的用户信息
        cursor = await db.execute(
            "SELECT id, username, is_admin, status, created_at, last_login FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        return {
            "id": row[0],
            "username": row[1],
            "is_admin": bool(row[2]),
            "status": row[3],
            "created_at": row[4],
            "last_login": row[5]
        }

@router.delete("/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: int):
    """删除用户"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 检查用户是否存在
        cursor = await db.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        username = row[0]
        
        # 不能删除最后一个管理员
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
        is_admin = bool((await cursor.fetchone())[0])
        
        if is_admin and admin_count <= 1:
            raise HTTPException(status_code=400, detail="不能删除最后一个管理员用户")
        
        # 删除用户
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        
        # 记录审计日志
        await audit_log("delete_user", f"删除用户: {username}", user_id)
        
        return {"message": "用户删除成功"}

@router.post("/{user_id}/toggle-status", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def toggle_user_status(user_id: int):
    """切换用户状态"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 检查用户是否存在
        cursor = await db.execute("SELECT status, username FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        current_status = row[0]
        username = row[1]
        new_status = "inactive" if current_status == "active" else "active"
        
        await db.execute(
            "UPDATE users SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        
        # 记录审计日志
        await audit_log("toggle_user_status", f"切换用户状态: {username} ({current_status} -> {new_status})", user_id)
        
        # 返回更新后的用户信息
        cursor = await db.execute(
            "SELECT id, username, is_admin, status, created_at, last_login FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        return {
            "id": row[0],
            "username": row[1],
            "is_admin": bool(row[2]),
            "status": row[3],
            "created_at": row[4],
            "last_login": row[5]
        }

@router.post("/{user_id}/toggle-admin", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def toggle_user_admin(user_id: int):
    """切换用户管理员权限"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # 检查用户是否存在
        cursor = await db.execute("SELECT is_admin, username FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        current_is_admin = bool(row[0])
        username = row[1]
        
        # 不能撤销最后一个管理员
        if current_is_admin:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            admin_count = (await cursor.fetchone())[0]
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="不能撤销最后一个管理员权限")
        
        new_is_admin = not current_is_admin
        
        await db.execute(
            "UPDATE users SET is_admin = ?, updated_at = ? WHERE id = ?",
            (new_is_admin, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        
        # 记录审计日志
        await audit_log("toggle_admin", f"切换管理员权限: {username} ({current_is_admin} -> {new_is_admin})", user_id)
        
        # 返回更新后的用户信息
        cursor = await db.execute(
            "SELECT id, username, is_admin, status, created_at, last_login FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        return {
            "id": row[0],
            "username": row[1],
            "is_admin": bool(row[2]),
            "status": row[3],
            "created_at": row[4],
            "last_login": row[5]
        }
