"""Revision ID: 0010 — reply targets + idea linkage"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reply_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("x_tweet_id", sa.String(32), nullable=False),
        sa.Column("x_user_id", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("author_handle", sa.String(64), nullable=False),
        sa.Column("tweet_text", sa.Text(), nullable=False),
        sa.Column("conversation_context", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "x_tweet_id", name="uq_reply_targets_user_tweet"),
    )
    op.add_column(
        "content_ideas",
        sa.Column("reply_target_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_content_ideas_reply_target",
        "content_ideas",
        "reply_targets",
        ["reply_target_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_content_ideas_reply_target", "content_ideas", type_="foreignkey")
    op.drop_column("content_ideas", "reply_target_id")
    op.drop_table("reply_targets")
