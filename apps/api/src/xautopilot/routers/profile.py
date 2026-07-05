from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.voice_profile import VoiceProfileCreate, VoiceProfileResponse
from xautopilot.services.voice_profile_service import (
    create_voice_profile,
    get_active_voice_profile,
)

router = APIRouter(prefix="/v1/profile", tags=["profile"])


@router.get("/voice", response_model=VoiceProfileResponse)
async def get_voice_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_active_voice_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No voice profile yet")
    return profile


@router.post("/voice", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def save_voice_profile(
    data: VoiceProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_voice_profile(db, current_user.id, data)
