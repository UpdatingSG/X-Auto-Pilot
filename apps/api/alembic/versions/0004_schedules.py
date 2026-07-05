"""Schedules table + draft scheduled_at

Revision ID: 0004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tweets_per_day", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("threads_per_week", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("replies_per_day", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("quote_tweets_per_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("posting_windows", postgresql.JSON(), nullable=False),
        sa.Column("jitter_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("require_approval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column("drafts", sa.Column("scheduled_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("drafts", "scheduled_at")
    op.drop_table("schedules")
