import asyncio
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.redis_client import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    """A one-minute limit backed by Redis when configured, local memory otherwise."""

    def __init__(self, app, limit: int):
        super().__init__(app)
        self.limit = limit
        self.local_hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health/live") or request.url.path.endswith("/health/ready"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        bucket = int(time.time() // 60)
        settings = get_settings()
        try:
            if settings.redis_url:
                key = f"fraud:rate:{client}:{bucket}"
                redis_client = get_redis_client(settings.redis_url)
                count = await redis_client.incr(key)
                if count == 1:
                    await redis_client.expire(key, 65)
            else:
                now = time.monotonic()
                async with self.lock:
                    hits = self.local_hits[client]
                    while hits and now - hits[0] >= 60:
                        hits.popleft()
                    hits.append(now)
                    count = len(hits)
        except Exception:
            if settings.environment.lower() != "development":
                return JSONResponse(status_code=503, content={"detail": "Rate limit service unavailable"})
            now = time.monotonic()
            async with self.lock:
                hits = self.local_hits[client]
                while hits and now - hits[0] >= 60:
                    hits.popleft()
                hits.append(now)
                count = len(hits)
        if count > self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}, headers={"Retry-After": "60"})
        return await call_next(request)
