from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.schedule import DEFAULT_WINDOWS, LEGACY_NARROW_WINDOWS, Schedule


def _normalize_window(window: dict) -> dict:
    return {
        "start": window.get("start"),
        "end": window.get("end"),
        "days": list(window.get("days") or [1, 2, 3, 4, 5, 6, 7]),
    }


def _is_legacy_narrow_windows(windows: list | None) -> bool:
    if not windows or len(windows) != len(LEGACY_NARROW_WINDOWS):
        return False
    legacy = [_normalize_window(w) for w in LEGACY_NARROW_WINDOWS]
    current = [_normalize_window(w) for w in windows]
    return current == legacy


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

    # Existing accounts used 45-minute windows (max ~3 slots/day). Widen in place
    # so reply quotas of 10–15 can actually be scheduled same-day.
    if _is_legacy_narrow_windows(schedule.posting_windows):
        schedule.posting_windows = DEFAULT_WINDOWS
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
