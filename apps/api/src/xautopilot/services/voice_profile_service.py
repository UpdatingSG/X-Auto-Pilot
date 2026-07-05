from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.voice_profile import VoiceProfile
from xautopilot.schemas.voice_profile import VoiceProfileCreate


async def get_active_voice_profile(session: AsyncSession, user_id: UUID) -> VoiceProfile | None:
    result = await session.execute(
        select(VoiceProfile).where(
            VoiceProfile.user_id == user_id,
            VoiceProfile.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_next_version(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(
        select(VoiceProfile.version)
        .where(VoiceProfile.user_id == user_id)
        .order_by(VoiceProfile.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return (latest or 0) + 1


async def create_voice_profile(
    session: AsyncSession, user_id: UUID, data: VoiceProfileCreate
) -> VoiceProfile:
    await session.execute(
        update(VoiceProfile)
        .where(VoiceProfile.user_id == user_id, VoiceProfile.is_active.is_(True))
        .values(is_active=False)
    )

    version = await get_next_version(session, user_id)
    profile = VoiceProfile(
        user_id=user_id,
        version=version,
        is_active=True,
        display_name=data.display_name,
        bio=data.bio,
        profession=data.profession,
        interests=[i.model_dump() for i in data.interests],
        expertise=data.expertise,
        writing_style=data.writing_style,
        tone=data.tone,
        personality=data.personality,
        vocabulary=data.vocabulary.model_dump(),
        emoji_prefs=data.emoji_prefs
        or {"enabled": True, "max_per_tweet": 2, "favorites": []},
        hashtag_prefs=data.hashtag_prefs
        or {"max_per_tweet": 2, "favorites": []},
        favorite_creators=data.favorite_creators,
        audience_type=data.audience_type,
        never_discuss=data.never_discuss,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
