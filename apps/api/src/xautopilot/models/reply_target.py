import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from xautopilot.database import Base


class ReplyTarget(Base):
    __tablename__ = "reply_targets"
    __table_args__ = (UniqueConstraint("user_id", "x_tweet_id", name="uq_reply_targets_user_tweet"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    x_tweet_id: Mapped[str] = mapped_column(String(32), nullable=False)
    x_user_id: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    author_handle: Mapped[str] = mapped_column(String(64), nullable=False)
    tweet_text: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_context: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
