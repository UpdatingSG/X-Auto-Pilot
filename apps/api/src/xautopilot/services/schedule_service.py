from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.schedule import DEFAULT_WINDOWS, Schedule


async def get_schedule(session: AsyncSession, user_id: UUID) -> Schedule:
    result = await session.execute(select(Schedule).where(Schedule.user_id == user_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        schedule = Schedule(
            user_id=user_id,
            posting_windows=DEFAULT_WINDOWS,
        )
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
    return schedule


async def update_schedule(session: AsyncSession, user_id: UUID, data: dict) -> Schedule:
    schedule = await get_schedule(session, user_id)
    for key, value in data.items():
        if value is not None and hasattr(schedule, key):
            setattr(schedule, key, value)
    await session.commit()
    await session.refresh(schedule)
    return schedule
