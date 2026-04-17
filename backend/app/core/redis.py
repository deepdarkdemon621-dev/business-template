from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import get_settings

_settings = get_settings()
redis_pool = Redis(host=_settings.redis_host, port=_settings.redis_port, decode_responses=True)


async def get_redis() -> AsyncGenerator[Redis]:
    yield redis_pool
