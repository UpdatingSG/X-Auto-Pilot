"""Pydantic schemas for daily engagement briefing."""

import uuid
from datetime import date

from pydantic import BaseModel, Field


class DailyTargets(BaseModel):
    replies_goal: int
    replies_sent: int
    tweets_goal: int
    tweets_sent: int
    threads_goal: int
    threads_sent: int


class BriefingTarget(BaseModel):
    x_tweet_id: str
    author_handle: str
    tweet_text: str
    author_followers: int = 0
    likes: int = 0
    relevance_score: float = 0.0
    source: str
    reply_target_id: str | None = None
    has_draft: bool = False


class BriefingAction(BaseModel):
    priority: str
    action: str
    detail: str


class BriefingResponse(BaseModel):
    date: date
    growth_mode: bool
    targets: DailyTargets
    fresh_opportunities: list[BriefingTarget] = Field(default_factory=list)
    saved_targets: list[BriefingTarget] = Field(default_factory=list)
    actions: list[BriefingAction] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    discovery_message: str | None = None
