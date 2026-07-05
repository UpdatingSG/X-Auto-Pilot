import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PostingWindowSchema(BaseModel):
    start: str
    end: str
    days: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])


class ScheduleUpdate(BaseModel):
    tweets_per_day: int | None = Field(default=None, ge=1, le=20)
    threads_per_week: int | None = Field(default=None, ge=0, le=14)
    replies_per_day: int | None = Field(default=None, ge=0, le=50)
    quote_tweets_per_day: int | None = Field(default=None, ge=0, le=10)
    posting_windows: list[PostingWindowSchema] | None = None
    jitter_minutes: int | None = Field(default=None, ge=0, le=60)
    require_approval: bool | None = None


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    tweets_per_day: int
    threads_per_week: int
    replies_per_day: int
    quote_tweets_per_day: int
    posting_windows: list[dict]
    jitter_minutes: int
    require_approval: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ScheduleDraftRequest(BaseModel):
    scheduled_at: datetime | None = None


class QueueItemResponse(BaseModel):
    draft_id: uuid.UUID
    content_type: str
    category: str | None
    scheduled_at: datetime
    preview_text: str | None
    status: str


class PublishedPostResponse(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    x_tweet_id: str
    content_type: str
    preview_text: str | None
    status: str = "published"
    published_at: datetime

    model_config = {"from_attributes": True}
