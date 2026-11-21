from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis_client import get_redis_client

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment.lower() != "development" and not settings.api_key:
        raise RuntimeError("API_KEY must be configured outside development")
    try:
        yield
    finally:
        if settings.redis_url:
            await get_redis_client(settings.redis_url).aclose()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A transaction risk decision service. A risk outcome is a signal for review, not proof of fraud.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins.strip() == "*" else [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.add_middleware(RateLimitMiddleware, limit=settings.requests_per_minute)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
