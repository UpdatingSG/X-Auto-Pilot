import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class XAccountResponse(BaseModel):
    id: uuid.UUID
    x_user_id: str
    handle: str
    connected: bool = True
    is_active: bool
    needs_reauth: bool = False

    model_config = {"from_attributes": True}


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class XAccountConnectRequest(BaseModel):
    handle: str = Field(min_length=1, max_length=64)
    x_user_id: str | None = Field(default=None, max_length=32)
    token_expires_at: datetime | None = None


class TokenRefreshResponse(BaseModel):
    refreshed: bool


class OAuthCompleteRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)
