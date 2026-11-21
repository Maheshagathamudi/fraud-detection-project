from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    app_name: str = "Real-Time Fraud Detection API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./fraud_detection.db"
    redis_url: str | None = None
    api_key: str | None = None
    cors_origins: str = "*"
    run_outbox_worker: bool = False
    requests_per_minute: int = 120
    high_amount_threshold: Decimal = Decimal("2500.00")
    customer_velocity_limit: int = 5
    instrument_velocity_limit: int = 3
    approve_threshold: int = 30
    decline_threshold: int = 70
    model_artifact_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    """Use the psycopg 3 driver for Render's standard PostgreSQL connection URL."""
    url = get_settings().database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url
