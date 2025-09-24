"""管理后台API路由导出模块"""
from __future__ import annotations

# 直接导入admin模块的路由
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.admin.api import admin_router

__all__ = ["admin_router"]
