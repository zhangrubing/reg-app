from typing import Optional
from fastapi import Request, HTTPException


def require_user(request: Request) -> dict:
    """要求用户认证"""
    if getattr(request.state, 'user', None) is None:
        raise HTTPException(status_code=401, detail="需要登录")
    return request.state.user


def require_admin():
    """要求管理员权限"""
    async def dep(request: Request):
        user: Optional[dict] = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="需要登录")
        if user.get("is_admin"):
            return user
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return dep


def optional_user(request: Request) -> Optional[dict]:
    """可选用户认证"""
    return getattr(request.state, 'user', None)
