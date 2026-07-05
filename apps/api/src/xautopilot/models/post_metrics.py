import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xautopilot.database import Base

if TYPE_CHECKING:
    from xautopilot.models.published_post import PublishedPost


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("published_posts.id", ondelete="CASCADE"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    impressions: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    replies: Mapped[int | None] = mapped_column(Integer)
    reposts: Mapped[int | None] = mapped_column(Integer)
    bookmarks: Mapped[int | None] = mapped_column(Integer)
    quotes: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    follower_count: Mapped[int | None] = mapped_column(Integer)

    post: Mapped["PublishedPost"] = relationship(back_populates="metrics_snapshots")
