import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from xautopilot.database import Base

DEFAULT_WINDOWS = [
    {"start": "09:00", "end": "09:45", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"start": "13:00", "end": "13:45", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"start": "19:00", "end": "19:45", "days": [1, 2, 3, 4, 5, 6, 7]},
]


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tweets_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    threads_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    replies_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    quote_tweets_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    growth_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_schedule_replies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    posting_windows: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: DEFAULT_WINDOWS)
    jitter_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    require_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
