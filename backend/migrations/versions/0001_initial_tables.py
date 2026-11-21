"""Create transaction decision and review audit tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("customer_token", sa.String(length=128), nullable=False),
        sa.Column("instrument_token", sa.String(length=128), nullable=False),
        sa.Column("merchant_token", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("review_status", sa.String(length=16), nullable=False, server_default="not_required"),
        sa.Column("model_probability", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_transactions_idempotency_key"),
    )
    op.create_index("ix_transactions_customer_token", "transactions", ["customer_token"])
    op.create_index("ix_transactions_instrument_token", "transactions", ["instrument_token"])
    op.create_index("ix_transactions_merchant_token", "transactions", ["merchant_token"])
    op.create_index("ix_transactions_occurred_at", "transactions", ["occurred_at"])
    op.create_index("ix_transactions_action", "transactions", ["action"])
    op.create_index("ix_transactions_review_status", "transactions", ["review_status"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])
    op.create_table(
        "review_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_events_transaction_id", "review_events", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_review_events_transaction_id", table_name="review_events")
    op.drop_table("review_events")
    op.drop_index("ix_transactions_review_status", table_name="transactions")
    op.drop_index("ix_transactions_created_at", table_name="transactions")
    op.drop_index("ix_transactions_action", table_name="transactions")
    op.drop_index("ix_transactions_occurred_at", table_name="transactions")
    op.drop_index("ix_transactions_merchant_token", table_name="transactions")
    op.drop_index("ix_transactions_instrument_token", table_name="transactions")
    op.drop_index("ix_transactions_customer_token", table_name="transactions")
    op.drop_table("transactions")
