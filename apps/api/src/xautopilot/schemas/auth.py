import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: EmailStr | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}
