import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(provided_key: str | None = Security(api_key_header)) -> str:
    settings = get_settings()
    if not settings.api_key and settings.environment.lower() == "development":
        return "local-development"
    if not settings.api_key or not provided_key or not hmac.compare_digest(settings.api_key, provided_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return "api-key-client"
