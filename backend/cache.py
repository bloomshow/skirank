import os
import json
from typing import Any, Optional
import redis.asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        value = await r.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception:
        pass


async def cache_invalidate_pattern(pattern: str) -> None:
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
