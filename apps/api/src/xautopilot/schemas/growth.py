"""Pydantic schemas for growth dashboard."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContentTypeBreakdown(BaseModel):
    content_type: str
    count: int
    avg_impressions: float = 0.0
    avg_engagement_rate: float = 0.0
    avg_bookmarks: float = 0.0


class ReplyPerformance(BaseModel):
    post_id: uuid.UUID
    preview_text: str | None
    impressions: int
    likes: int
    replies: int
    engagement_rate: float
    published_at: datetime


class GrowthStreak(BaseModel):
    reply_days: int


class GrowthDashboardResponse(BaseModel):
    growth_mode: bool
    period: str
    daily_targets: dict[str, int]
    today_counts: dict[str, int]
    week_counts: dict[str, int]
    follower_delta_7d: int | None = None
    content_breakdown: list[ContentTypeBreakdown] = Field(default_factory=list)
    reply_performance: list[ReplyPerformance] = Field(default_factory=list)
    streak: GrowthStreak
