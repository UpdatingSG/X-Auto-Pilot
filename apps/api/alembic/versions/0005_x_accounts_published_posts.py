"""X accounts + published posts

Revision ID: 0005
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "x_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("x_user_id", sa.String(32), nullable=False),
        sa.Column("handle", sa.String(64), nullable=False),
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_enc", sa.LargeBinary()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("scopes", postgresql.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "published_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), unique=True),
        sa.Column("x_tweet_id", sa.String(32), nullable=False, unique=True),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("content_snapshot", postgresql.JSON(), nullable=False),
        sa.Column("preview_text", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("published_posts")
    op.drop_table("x_accounts")
