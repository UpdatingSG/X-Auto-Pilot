import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReplyTargetCreate(BaseModel):
    author_handle: str = Field(min_length=1, max_length=64)
    tweet_text: str = Field(min_length=1, max_length=2000)
    x_tweet_id: str = Field(min_length=1, max_length=32)
    x_user_id: str | None = Field(default=None, max_length=32)


class ReplyTargetUpdateTweetId(BaseModel):
    x_tweet_id: str = Field(min_length=1, max_length=32)


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


class DiscoveredReplyTarget(BaseModel):
    x_tweet_id: str
    x_user_id: str
    author_handle: str
    tweet_text: str
    author_followers: int
    likes: int
    relevance_score: float = 0.0


class DiscoverReplyTargetsRequest(BaseModel):
    min_followers: int = Field(default=10_000, ge=1000, le=5_000_000)
    limit: int = Field(default=10, ge=1, le=25)
    topics: list[str] | None = None


class DiscoverReplyTargetsResponse(BaseModel):
    source: str
    message: str | None = None
    targets: list[DiscoveredReplyTarget]


class ImportReplyTargetsRequest(BaseModel):
    targets: list[DiscoveredReplyTarget] = Field(min_length=1, max_length=25)


class ReplyTargetFromUrlRequest(BaseModel):
    url: str = Field(min_length=10, max_length=500)


class ImportReplyTargetsResponse(BaseModel):
    imported: int
    targets: list[ReplyTargetResponse]
