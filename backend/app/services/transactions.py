import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.transaction import TransactionRecord
from app.models.review_event import ReviewEvent
from app.models.outbox_event import OutboxEvent
from app.rules.engine import evaluate_rules
from app.schemas.transaction import TransactionRequest
from app.services.model import score_features
from app.services.scoring import decide


class IdempotencyConflict(Exception):
    pass


class ReviewConflict(Exception):
    pass


def _request_hash(payload: TransactionRequest) -> str:
    canonical = payload.model_dump(mode="json")
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def process_transaction(session: Session, payload: TransactionRequest, idempotency_key: str) -> TransactionRecord:
    request_hash = _request_hash(payload)
    prior = session.scalar(select(TransactionRecord).where(TransactionRecord.idempotency_key == idempotency_key))
    if prior is not None:
        if prior.request_hash != request_hash:
            raise IdempotencyConflict("This Idempotency-Key was already used with a different request")
        return prior

    settings = get_settings()
    # Use server receipt time for velocity so a caller cannot evade these rules
    # by sending a backdated occurred_at value.
    received_at = datetime.now(timezone.utc)
    window_start = received_at - timedelta(minutes=10)
    customer_count = session.scalar(
        select(func.count()).select_from(TransactionRecord).where(
            TransactionRecord.customer_token == payload.customer_token,
            TransactionRecord.created_at >= window_start,
            TransactionRecord.created_at <= received_at,
        )
    ) or 0
    instrument_count = session.scalar(
        select(func.count()).select_from(TransactionRecord).where(
            TransactionRecord.instrument_token == payload.instrument_token,
            TransactionRecord.created_at >= window_start,
            TransactionRecord.created_at <= received_at,
        )
    ) or 0

    rules = evaluate_rules(
        amount=payload.amount,
        recent_customer_count=customer_count,
        recent_instrument_count=instrument_count,
        high_amount_threshold=settings.high_amount_threshold,
        customer_velocity_limit=settings.customer_velocity_limit,
        instrument_velocity_limit=settings.instrument_velocity_limit,
    )
    feature_values = {
        "amount": float(payload.amount),
        "customer_velocity_10m": float(customer_count),
        "instrument_velocity_10m": float(instrument_count),
        "hour_utc": float(received_at.hour),
        "is_weekend": float(received_at.weekday() >= 5),
    }
    model_probability, model_version = score_features(feature_values, settings.model_artifact_path)
    result = decide(
        rules=rules,
        model_probability=model_probability,
        low_threshold=settings.approve_threshold,
        high_threshold=settings.decline_threshold,
    )
    reasons = [{"rule_id": r.rule_id, "points": r.points, "reason": r.reason} for r in result.rule_reasons]
    if result.model_probability is not None:
        reasons.append({
            "rule_id": "model_probability",
            "points": round(result.model_probability * 60),
            "reason": f"Model {model_version} returned a risk probability of {result.model_probability:.3f}",
        })
    record = TransactionRecord(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        amount=payload.amount,
        currency=payload.currency,
        customer_token=payload.customer_token,
        instrument_token=payload.instrument_token,
        merchant_token=payload.merchant_token,
        occurred_at=payload.occurred_at,
        score=result.score,
        action=result.action,
        review_status="pending" if result.action == "review" else "not_required",
        model_probability=result.model_probability,
        model_version=model_version,
        policy_version=result.policy_version,
        reasons=reasons,
    )
    session.add(record)
    session.flush()
    if result.action in {"review", "decline"}:
        session.add(OutboxEvent(
            event_type=f"transaction.{result.action}",
            aggregate_id=record.id,
            payload={"transaction_id": record.id, "action": result.action, "score": result.score, "policy_version": result.policy_version, "reasons": reasons},
        ))
    try:
        session.commit()
    except IntegrityError:
        # A concurrent retry may have inserted the same key after the first lookup.
        session.rollback()
        prior = session.scalar(select(TransactionRecord).where(TransactionRecord.idempotency_key == idempotency_key))
        if prior is None:
            raise
        if prior.request_hash != request_hash:
            raise IdempotencyConflict("This Idempotency-Key was already used with a different request")
        return prior
    session.refresh(record)
    return record


def transaction_to_response(record: TransactionRecord) -> dict:
    created_at = record.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    occurred_at = record.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    return {
        "id": record.id,
        "amount": record.amount,
        "currency": record.currency,
        "occurred_at": occurred_at,
        "score": record.score,
        "action": record.action,
        "review_status": record.review_status,
        "model_probability": record.model_probability,
        "model_version": record.model_version,
        "policy_version": record.policy_version,
        "reasons": record.reasons,
        "created_at": created_at,
    }


def resolve_review(session: Session, transaction_id: int, outcome: str, note: str | None, actor: str) -> TransactionRecord:
    record = session.get(TransactionRecord, transaction_id)
    if record is None:
        raise LookupError("Transaction not found")
    if record.review_status != "pending":
        raise ReviewConflict("Transaction is not waiting for review")
    next_status = "approved" if outcome == "approve" else "declined"
    changed = session.execute(
        update(TransactionRecord)
        .where(TransactionRecord.id == transaction_id, TransactionRecord.review_status == "pending")
        .values(review_status=next_status)
    )
    if changed.rowcount != 1:
        session.rollback()
        raise ReviewConflict("Transaction review was already resolved")
    session.add(ReviewEvent(
        transaction_id=record.id,
        outcome=outcome,
        actor=actor,
        note=note,
    ))
    session.add(OutboxEvent(
        event_type="review.resolved",
        aggregate_id=record.id,
        payload={"transaction_id": record.id, "outcome": outcome, "review_status": next_status},
    ))
    session.commit()
    session.refresh(record)
    return record
