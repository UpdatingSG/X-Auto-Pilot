import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InterestItem(BaseModel):
    topic: str
    weight: float = 1.0


class VocabularyPrefs(BaseModel):
    use: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class VoiceProfileCreate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    profession: str | None = None
    interests: list[InterestItem] = Field(default_factory=list)
    expertise: list[str] = Field(default_factory=list)
    writing_style: dict[str, Any] = Field(default_factory=dict)
    tone: list[str] = Field(default_factory=list)
    personality: list[str] = Field(default_factory=list)
    vocabulary: VocabularyPrefs = Field(default_factory=VocabularyPrefs)
    emoji_prefs: dict[str, Any] | None = None
    hashtag_prefs: dict[str, Any] | None = None
    favorite_creators: list[dict[str, Any]] = Field(default_factory=list)
    audience_type: str | None = None
    never_discuss: list[str] = Field(default_factory=list)


class VoiceProfileResponse(BaseModel):
    id: uuid.UUID
    version: int
    is_active: bool
    display_name: str | None
    bio: str | None
    profession: str | None
    interests: list[dict[str, Any]]
    expertise: list[str]
    writing_style: dict[str, Any]
    tone: list[str]
    personality: list[str]
    vocabulary: dict[str, Any]
    emoji_prefs: dict[str, Any]
    hashtag_prefs: dict[str, Any]
    favorite_creators: list[dict[str, Any]]
    audience_type: str | None
    never_discuss: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
