"""Post metrics time-series snapshots

Revision ID: 0006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("published_posts.id", ondelete="CASCADE")),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("impressions", sa.Integer()),
        sa.Column("likes", sa.Integer()),
        sa.Column("replies", sa.Integer()),
        sa.Column("reposts", sa.Integer()),
        sa.Column("bookmarks", sa.Integer()),
        sa.Column("quotes", sa.Integer()),
        sa.Column("engagement_rate", sa.Float()),
        sa.Column("follower_count", sa.Integer()),
    )
    op.create_index("idx_post_metrics_post_time", "post_metrics", ["post_id", "captured_at"])


def downgrade() -> None:
    op.drop_index("idx_post_metrics_post_time", table_name="post_metrics")
    op.drop_table("post_metrics")
