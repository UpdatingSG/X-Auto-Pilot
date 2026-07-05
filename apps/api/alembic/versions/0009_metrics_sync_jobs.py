"""Revision ID: 0009 — scheduled metrics sync jobs"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metrics_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("published_posts.id", ondelete="CASCADE")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("sync_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("label", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_metrics_sync_jobs_due", "metrics_sync_jobs", ["status", "sync_at"])


def downgrade() -> None:
    op.drop_index("idx_metrics_sync_jobs_due", table_name="metrics_sync_jobs")
    op.drop_table("metrics_sync_jobs")
