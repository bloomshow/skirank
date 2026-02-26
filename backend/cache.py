import os
import json
from typing import Any, Optional
import redis.asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    value = await r.get(key)
    if value is None:
        return None
    return json.loads(value)


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_invalidate_pattern(pattern: str) -> None:
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)
