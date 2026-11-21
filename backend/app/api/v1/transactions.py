from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_session_factory
from app.api.dependencies import verify_api_key
from app.models.transaction import TransactionRecord
from app.models.review_event import ReviewEvent
from app.schemas.transaction import ReviewEventResponse, ReviewRequest, TransactionListResponse, TransactionRequest, TransactionResponse
from app.services.transactions import IdempotencyConflict, ReviewConflict, process_transaction, resolve_review, transaction_to_response

router = APIRouter(prefix="/transactions", tags=["transactions"], dependencies=[Depends(verify_api_key)])


def get_db_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    payload: TransactionRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    session: Session = Depends(get_db_session),
):
    try:
        result = process_transaction(session, payload, idempotency_key)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return transaction_to_response(result)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, pattern="^(approve|review|decline)$"),
    session: Session = Depends(get_db_session),
):
    query = select(TransactionRecord)
    count_query = select(func.count()).select_from(TransactionRecord)
    if action:
        query = query.where(TransactionRecord.action == action)
        count_query = count_query.where(TransactionRecord.action == action)
    items = session.scalars(query.order_by(TransactionRecord.created_at.desc()).limit(limit).offset(offset)).all()
    total = session.scalar(count_query) or 0
    return {"items": [transaction_to_response(item) for item in items], "total": total}


@router.get("/summary")
def transaction_summary(session: Session = Depends(get_db_session)):
    total = session.scalar(select(func.count()).select_from(TransactionRecord)) or 0
    rows = session.execute(
        select(TransactionRecord.action, func.count()).group_by(TransactionRecord.action)
    ).all()
    counts = {"approve": 0, "review": 0, "decline": 0}
    counts.update({action: count for action, count in rows})
    avg_score = session.scalar(select(func.avg(TransactionRecord.score)))
    open_reviews = session.scalar(select(func.count()).select_from(TransactionRecord).where(TransactionRecord.review_status == "pending")) or 0
    return {"total": total, "actions": counts, "open_reviews": open_reviews, "average_score": round(float(avg_score or 0), 2)}


@router.get("/review-queue", response_model=TransactionListResponse)
def list_review_queue(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
):
    query = select(TransactionRecord).where(TransactionRecord.review_status == "pending")
    count_query = select(func.count()).select_from(TransactionRecord).where(TransactionRecord.review_status == "pending")
    items = session.scalars(query.order_by(TransactionRecord.created_at.asc()).limit(limit).offset(offset)).all()
    total = session.scalar(count_query) or 0
    return {"items": [transaction_to_response(item) for item in items], "total": total}


@router.post("/{transaction_id}/review", response_model=TransactionResponse)
def review_transaction(
    transaction_id: int,
    payload: ReviewRequest,
    session: Session = Depends(get_db_session),
    actor: str = Depends(verify_api_key),
):
    try:
        record = resolve_review(session, transaction_id, payload.outcome, payload.note, actor)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return transaction_to_response(record)


@router.get("/{transaction_id}/review-events", response_model=list[ReviewEventResponse])
def review_history(transaction_id: int, session: Session = Depends(get_db_session)):
    if session.get(TransactionRecord, transaction_id) is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    events = session.scalars(
        select(ReviewEvent).where(ReviewEvent.transaction_id == transaction_id).order_by(ReviewEvent.created_at.asc())
    ).all()
    return events
