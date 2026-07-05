import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xautopilot.database import Base

if TYPE_CHECKING:
    from xautopilot.models.post_metrics import PostMetrics


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    x_tweet_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    preview_text: Mapped[str | None] = mapped_column(Text)

    metrics_snapshots: Mapped[list["PostMetrics"]] = relationship(
        back_populates="post",
        order_by="desc(PostMetrics.captured_at)",
    )
