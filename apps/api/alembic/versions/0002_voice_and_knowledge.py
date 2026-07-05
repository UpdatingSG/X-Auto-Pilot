"""Voice profiles, knowledge sources, knowledge items

Revision ID: 0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("display_name", sa.String(128)),
        sa.Column("bio", sa.Text()),
        sa.Column("profession", sa.String(128)),
        sa.Column("interests", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("expertise", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("writing_style", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("tone", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("personality", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("vocabulary", postgresql.JSON(), nullable=False, server_default='{"use": [], "avoid": []}'),
        sa.Column("emoji_prefs", postgresql.JSON(), nullable=False),
        sa.Column("hashtag_prefs", postgresql.JSON(), nullable=False),
        sa.Column("favorite_creators", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("audience_type", sa.String(64)),
        sa.Column("never_discuss", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("learned_weights", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "version"),
    )
    op.create_index(
        "ix_voice_profiles_active",
        "voice_profiles",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_sources.id", ondelete="SET NULL")),
        sa.Column("external_id", sa.String(512), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("author", sa.String(256)),
        sa.Column("content_raw", sa.Text()),
        sa.Column("content_summary", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("user_id", "external_id"),
    )
    op.create_index("ix_knowledge_items_user_fetched", "knowledge_items", ["user_id", "fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_items_user_fetched", table_name="knowledge_items")
    op.drop_table("knowledge_items")
    op.drop_table("knowledge_sources")
    op.drop_index("ix_voice_profiles_active", table_name="voice_profiles")
    op.drop_table("voice_profiles")
