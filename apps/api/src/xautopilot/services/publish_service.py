import random
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.content import Draft
from xautopilot.services.draft_service import DraftNotFoundError, get_draft
from xautopilot.services.schedule_service import get_schedule
from xautopilot.services.slot_allocator import _ensure_utc, allocate_slot, avoid_collisions


class DraftNotSchedulableError(Exception):
    pass


class DraftNotScheduledError(Exception):
    pass


async def get_occupied_slots(session: AsyncSession, user_id: UUID, exclude_draft_id: UUID | None = None) -> list[datetime]:
    query = select(Draft.scheduled_at).where(
        Draft.user_id == user_id,
        Draft.status == "scheduled",
        Draft.scheduled_at.isnot(None),
    )
    if exclude_draft_id is not None:
        query = query.where(Draft.id != exclude_draft_id)
    result = await session.execute(query)
    return [_ensure_utc(row[0]) for row in result.all() if row[0]]


async def schedule_draft(
    session: AsyncSession,
    user_id: UUID,
    draft_id: UUID,
    scheduled_at: datetime | None = None,
    timezone: str = "UTC",
    rng: random.Random | None = None,
) -> Draft:
    draft = await get_draft(session, user_id, draft_id)

    if draft.status == "scheduled":
        raise DraftNotSchedulableError
    if draft.status != "approved":
        raise DraftNotSchedulableError

    schedule = await get_schedule(session, user_id)
    occupied = await get_occupied_slots(session, user_id, exclude_draft_id=draft_id)

    if scheduled_at is None:
        slot = allocate_slot(
            posting_windows=schedule.posting_windows,
            occupied=occupied,
            timezone=timezone,
            jitter_minutes=schedule.jitter_minutes,
            rng=rng,
        )
        slot = avoid_collisions(_ensure_utc(slot), occupied)
    else:
        slot = scheduled_at.astimezone(UTC)

    draft.scheduled_at = slot
    draft.status = "scheduled"
    await session.commit()
    await session.refresh(draft)
    return draft


async def cancel_schedule(session: AsyncSession, user_id: UUID, draft_id: UUID) -> Draft:
    draft = await get_draft(session, user_id, draft_id)
    if draft.status != "scheduled":
        raise DraftNotScheduledError
    draft.scheduled_at = None
    draft.status = "approved"
    await session.commit()
    await session.refresh(draft)
    return draft


async def list_publish_queue(session: AsyncSession, user_id: UUID) -> list[Draft]:
    result = await session.execute(
        select(Draft)
        .options(selectinload(Draft.variants))
        .where(Draft.user_id == user_id, Draft.status == "scheduled")
        .order_by(Draft.scheduled_at.asc())
    )
    return list(result.scalars().all())
