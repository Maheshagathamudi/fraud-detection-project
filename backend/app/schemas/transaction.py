from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Literal["USD"] = "USD"
    customer_token: str = Field(min_length=3, max_length=128)
    instrument_token: str = Field(min_length=3, max_length=128)
    merchant_token: str = Field(min_length=3, max_length=128)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(timezone.utc)

class RuleReason(BaseModel):
    rule_id: str
    points: int
    reason: str


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    currency: str
    occurred_at: datetime
    score: int
    action: Literal["approve", "review", "decline"]
    review_status: Literal["not_required", "pending", "approved", "declined"]
    model_probability: float | None
    model_version: str | None
    policy_version: str
    reasons: list[RuleReason]
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int


class ReviewRequest(BaseModel):
    outcome: Literal["approve", "decline"]
    note: str | None = Field(default=None, max_length=1000)


class ReviewEventResponse(BaseModel):
    id: int
    transaction_id: int
    outcome: Literal["approve", "decline"]
    actor: str
    note: str | None
    created_at: datetime
