"""Redis工具模块"""
from __future__ import annotations

import json
from typing import Any, Optional
import redis.asyncio as redis
from backend.app.core.config import settings
from backend.app.common.log import logger


class RedisClient:
    """Redis客户端"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            raise
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis连接已关闭")
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis获取失败: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """设置值"""
        if not self.redis_client:
            return False
        try:
            return await self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis设置失败: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis删除失败: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis检查失败: {str(e)}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Redis设置过期时间失败: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.redis_client:
            return -2
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Redis获取TTL失败: {str(e)}")
            return -2
    
    async def get_json(self, key: str) -> Optional[Any]:
        """获取JSON值"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"JSON解析失败: {value}")
                return None
        return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """设置JSON值"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, expire)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON序列化失败: {str(e)}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增"""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis递增失败: {str(e)}")
            return None
    
    async def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """递减"""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.decr(key, amount)
        except Exception as e:
            logger.error(f"Redis递减失败: {str(e)}")
            return None
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希值"""
        if not self.redis_client:
            return None
        try:
            return await self.redis_client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis哈希获取失败: {str(e)}")
            return None
    
    async def hset(
        self,
        name: str,
        key: str,
        value: str
    ) -> bool:
        """设置哈希值"""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.hset(name, key, value))
        except Exception as e:
            logger.error(f"Redis哈希设置失败: {str(e)}")
            return False
    
    async def hdel(self, name: str, key: str) -> bool:
        """删除哈希键"""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.hdel(name, key))
        except Exception as e:
            logger.error(f"Redis哈希删除失败: {str(e)}")
            return False
    
    async def hgetall(self, name: str) -> dict[str, str]:
        """获取所有哈希值"""
        if not self.redis_client:
            return {}
        try:
            return await self.redis_client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis获取所有哈希失败: {str(e)}")
            return {}


# 创建全局Redis客户端实例
redis_client = RedisClient()


# 缓存装饰器
def cache(expire: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # 尝试从缓存获取
            cached_result = await redis_client.get_json(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                await redis_client.set_json(cache_key, result, expire)
                logger.debug(f"缓存设置: {cache_key}")
            
            return result
        return wrapper
    return decorator


# 清除缓存函数
async def clear_cache(pattern: str):
    """清除匹配模式的缓存"""
    if not redis_client.redis_client:
        return
    
    try:
        keys = await redis_client.redis_client.keys(pattern)
        if keys:
            await redis_client.redis_client.delete(*keys)
            logger.info(f"清除缓存: {pattern} ({len(keys)} 个键)")
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")


# 导出
__all__ = ["redis_client", "RedisClient", "cache", "clear_cache"]
