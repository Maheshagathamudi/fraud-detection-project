from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import get_engine
from app.core.redis_client import get_redis_client

router = APIRouter(tags=["health"])


@router.get("/health/live", summary="Check whether the API process is alive")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", summary="Check whether the API can accept requests")
async def readiness() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        settings = get_settings()
        if settings.redis_url:
            client = get_redis_client(settings.redis_url)
            await client.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="A required service is unavailable") from exc
    return {"status": "ready"}
