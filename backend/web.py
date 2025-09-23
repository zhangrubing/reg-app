from fastapi.templating import Jinja2Templates
from fastapi import Request

try:
    from .config import BASE_DIR, APP_ENV, APP_NAME
except ImportError:
    # 当直接运行文件时的导入方式
    from config import BASE_DIR, APP_ENV, APP_NAME


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render(request: Request, name: str, **ctx):
    """渲染模板"""
    base = {
        "request": request, 
        "user": getattr(request.state, 'user', None), 
        "env": APP_ENV,
        "app_name": APP_NAME
    }
    base.update(ctx)
    return templates.TemplateResponse(name, base)
