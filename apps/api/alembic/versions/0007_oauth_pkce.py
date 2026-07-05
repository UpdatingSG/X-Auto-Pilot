"""OAuth PKCE states + x_accounts.needs_reauth

Revision ID: 0007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_pkce_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("state", sa.String(128), nullable=False, unique=True),
        sa.Column("code_verifier", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_oauth_pkce_states_state", "oauth_pkce_states", ["state"])
    op.add_column(
        "x_accounts",
        sa.Column("needs_reauth", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("x_accounts", "needs_reauth")
    op.drop_index("idx_oauth_pkce_states_state", table_name="oauth_pkce_states")
    op.drop_table("oauth_pkce_states")
