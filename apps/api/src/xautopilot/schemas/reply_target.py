import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReplyTargetCreate(BaseModel):
    author_handle: str = Field(min_length=1, max_length=64)
    tweet_text: str = Field(min_length=1, max_length=2000)
    x_tweet_id: str | None = Field(default=None, max_length=32)
    x_user_id: str | None = Field(default=None, max_length=32)


class ReplyTargetResponse(BaseModel):
    id: uuid.UUID
    author_handle: str
    tweet_text: str
    x_tweet_id: str
    x_user_id: str
    relevance_score: float | None
    discovered_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}
