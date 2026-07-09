"""Growth mode and auto-schedule replies on schedules

Revision ID: 0011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column("growth_mode", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "schedules",
        sa.Column("auto_schedule_replies", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("schedules", "auto_schedule_replies")
    op.drop_column("schedules", "growth_mode")
