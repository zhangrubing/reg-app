import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.db import DB_PATH
import aiosqlite

async def update_db():
    """更新数据库表结构"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 检查用户表是否有status列
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'status' not in column_names:
            print("添加status列到users表...")
            await db.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        
        if 'last_login' not in column_names:
            print("添加last_login列到users表...")
            await db.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
        
        if 'updated_at' not in column_names:
            print("添加updated_at列到users表...")
            await db.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP")
        
        # 检查设备表是否有created_at列
        cursor = await db.execute("PRAGMA table_info(devices)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'created_at' not in column_names:
            print("添加created_at列到devices表...")
            await db.execute("ALTER TABLE devices ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        await db.commit()
        print("数据库更新完成！")

if __name__ == "__main__":
    asyncio.run(update_db())
