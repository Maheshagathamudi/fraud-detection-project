from functools import lru_cache

from redis.asyncio import Redis


@lru_cache(maxsize=2)
def get_redis_client(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)
