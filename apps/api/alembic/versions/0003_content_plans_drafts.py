"""Content plans, ideas, drafts

Revision ID: 0003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "plan_date"),
    )

    op.create_table(
        "content_ideas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_plans.id", ondelete="CASCADE")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="proposed"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("hook_idea", sa.Text()),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_ideas.id", ondelete="SET NULL")),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("category", sa.String(32)),
        sa.Column("status", sa.String(32), nullable=False, server_default="generating"),
        sa.Column("selected_variant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("generation_metadata", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "draft_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE")),
        sa.Column("variant_index", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text()),
        sa.Column("thread_tweets", postgresql.JSON()),
        sa.Column("scores", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("draft_variants")
    op.drop_table("drafts")
    op.drop_table("content_ideas")
    op.drop_table("content_plans")
