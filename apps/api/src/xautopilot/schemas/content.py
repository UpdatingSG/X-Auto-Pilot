import uuid
from datetime import date, datetime
from typing import Any

from typing import Any

from pydantic import BaseModel, Field


class PlanComposition(BaseModel):
    tweets: int = 0
    threads: int = 0
    replies: int = 0
    thread_days: list[str] = []
    is_thread_day: bool = False
    reply_targets_available: int = 0
    hints: list[str] = []


class IdeaResponse(BaseModel):
    id: uuid.UUID
    content_type: str
    category: str
    status: str
    title: str
    hook_idea: str | None
    rationale: str | None
    reply_target_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: uuid.UUID
    plan_date: date
    status: str
    ideas: list[IdeaResponse]
    composition: PlanComposition | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IdeaStatusUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected|skipped)$")


class VariantResponse(BaseModel):
    id: uuid.UUID
    variant_index: int
    content_text: str | None
    thread_tweets: list[dict] | None = None
    scores: dict[str, Any]
    is_selected: bool

    model_config = {"from_attributes": True}


class DraftResponse(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID | None
    content_type: str
    category: str | None
    status: str
    selected_variant_id: uuid.UUID | None
    scheduled_at: datetime | None = None
    generation_metadata: dict[str, Any] = {}
    variants: list[VariantResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class DraftGenerateRequest(BaseModel):
    idea_id: uuid.UUID | None = None
    reply_target_id: uuid.UUID | None = None


class DraftUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(approved|rejected)$")
    selected_variant_id: uuid.UUID | None = None
