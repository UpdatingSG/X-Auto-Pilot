import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from xautopilot.database import Base


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    display_name: Mapped[str | None] = mapped_column(String(128))
    bio: Mapped[str | None] = mapped_column(Text)
    profession: Mapped[str | None] = mapped_column(String(128))

    interests: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expertise: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    writing_style: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tone: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    personality: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    vocabulary: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"use": [], "avoid": []}
    )
    emoji_prefs: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"enabled": True, "max_per_tweet": 2, "favorites": []},
    )
    hashtag_prefs: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"max_per_tweet": 2, "favorites": []},
    )
    favorite_creators: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    audience_type: Mapped[str | None] = mapped_column(String(64))
    never_discuss: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    learned_weights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
