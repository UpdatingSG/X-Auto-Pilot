import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from xautopilot.database import Base


class SourceType(StrEnum):
    RSS = "rss"
    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    DEVTO = "devto"
    MANUAL_NOTE = "manual_note"


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=240)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="SET NULL")
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(256))
    content_raw: Mapped[str | None] = mapped_column(Text)
    content_summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
