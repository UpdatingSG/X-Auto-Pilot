import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TopPostSummary(BaseModel):
    post_id: uuid.UUID
    preview_text: str | None
    engagement_rate: float
    impressions: int


class OverviewResponse(BaseModel):
    period: str
    posts_published: int
    total_impressions: int
    avg_engagement_rate: float
    top_post: TopPostSummary | None = None


class PostMetricsSnapshot(BaseModel):
    impressions: int
    likes: int
    replies: int
    reposts: int
    bookmarks: int
    quotes: int
    engagement_rate: float
    captured_at: datetime

    model_config = {"from_attributes": True}


class PostAnalyticsItem(BaseModel):
    post_id: uuid.UUID
    draft_id: uuid.UUID
    x_tweet_id: str
    preview_text: str | None
    category: str | None
    content_type: str | None = None
    published_at: datetime
    metrics: PostMetricsSnapshot | None = None

    model_config = {"from_attributes": True}


class InsightsResponse(BaseModel):
    period: str
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    best_posting_hour: int | None = None
    best_category: str | None = None
    recommended_adjustments: dict[str, list[str]] = Field(default_factory=dict)
