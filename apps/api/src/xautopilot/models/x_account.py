import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from xautopilot.database import Base


class XAccount(Base):
    __tablename__ = "x_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    x_user_id: Mapped[str] = mapped_column(String(32), nullable=False)
    handle: Mapped[str] = mapped_column(String(64), nullable=False)
    access_token_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    needs_reauth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
