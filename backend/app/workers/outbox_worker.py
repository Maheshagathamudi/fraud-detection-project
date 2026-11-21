"""Publish durable outbox events to a Redis Stream with at-least-once delivery."""
import json
import logging
import threading
import time
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import get_session_factory
from app.models.outbox_event import OutboxEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("outbox-worker")
STREAM_NAME = "fraud:alerts"


def publish_one(session_factory, redis_client: Redis) -> bool:
    session = session_factory()
    try:
        event = session.scalar(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if event is None:
            return False
        event.attempt_count += 1
        try:
            redis_client.xadd(
                STREAM_NAME,
                {
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "aggregate_id": str(event.aggregate_id),
                    "payload": json.dumps(event.payload, separators=(",", ":")),
                },
                maxlen=100000,
                approximate=True,
            )
            event.published_at = datetime.now(timezone.utc)
            event.last_error = None
            session.commit()
            logger.info("Published outbox event %s (%s)", event.id, event.event_type)
        except Exception as exc:
            event.last_error = str(exc)[:1000]
            session.commit()
            logger.exception("Could not publish outbox event %s", event.id)
            time.sleep(min(30, max(1, 2 ** min(event.attempt_count, 5))))
        return True
    finally:
        session.close()


def run_until_stopped(stop_event: threading.Event) -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for the outbox worker")
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    session_factory = get_session_factory()
    logger.info("Outbox worker publishing to Redis Stream %s", STREAM_NAME)
    try:
        while not stop_event.is_set():
            if not publish_one(session_factory, redis_client):
                stop_event.wait(0.5)
    finally:
        redis_client.close()


def main() -> None:
    run_until_stopped(threading.Event())


if __name__ == "__main__":
    main()
