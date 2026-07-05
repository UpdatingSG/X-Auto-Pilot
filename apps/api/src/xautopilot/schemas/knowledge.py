import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceConfig(BaseModel):
    url: HttpUrl | None = None
    subreddit: str | None = None
    query: str | None = None


class SourceCreate(BaseModel):
    source_type: Literal["rss", "hacker_news", "reddit", "devto", "manual_note"]
    name: str = Field(min_length=1, max_length=128)
    config: dict[str, Any]
    fetch_interval_minutes: int = Field(default=240, ge=15, le=1440)


class SourceResponse(BaseModel):
    id: uuid.UUID
    source_type: str
    name: str
    config: dict[str, Any]
    is_enabled: bool
    fetch_interval_minutes: int
    last_fetched_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FetchResultResponse(BaseModel):
    source_id: uuid.UUID
    items_ingested: int
    items_skipped: int


class KnowledgeItemResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID | None
    external_id: str
    title: str
    url: str | None
    author: str | None
    fetched_at: datetime

    model_config = {"from_attributes": True}
