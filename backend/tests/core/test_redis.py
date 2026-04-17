from unittest.mock import AsyncMock, patch

import pytest

from app.core.redis import get_redis


@pytest.mark.asyncio
async def test_get_redis_yields_client():
    mock_redis = AsyncMock()
    with patch("app.core.redis.redis_pool", mock_redis):
        async for r in get_redis():
            assert r is mock_redis
            break
