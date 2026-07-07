"""Unit tests for posting window slot allocation."""

import random
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from xautopilot.services.slot_allocator import allocate_slot, count_in_window, parse_windows


WINDOWS = [
    {"start": "09:00", "end": "09:45", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"start": "13:00", "end": "13:45", "days": [1, 2, 3, 4, 5, 6, 7]},
    {"start": "19:00", "end": "19:45", "days": [1, 2, 3, 4, 5, 6, 7]},
]


def _slot_at(hour: int, minute: int = 0, day: date | None = None) -> datetime:
    tz = ZoneInfo("UTC")
    target = day or date(2030, 1, 7)
    return datetime.combine(target, time(hour, minute), tzinfo=tz)


def test_three_drafts_use_three_different_windows():
    rng = random.Random(42)
    occupied: list[datetime] = []
    slots: list[datetime] = []

    for _ in range(3):
        slot = allocate_slot(
            posting_windows=WINDOWS,
            occupied=occupied,
            timezone="UTC",
            jitter_minutes=0,
            target_date=date(2030, 1, 7),
            rng=rng,
            max_per_window=1,
            daily_quota=3,
        )
        slots.append(slot)
        occupied.append(slot)

    windows = parse_windows(WINDOWS)
    tz = ZoneInfo("UTC")
    used_windows: set[int] = set()
    for slot in slots:
        for idx, window in enumerate(windows):
            if count_in_window([slot], window, date(2030, 1, 7), tz) == 1:
                used_windows.add(idx)
    assert used_windows == {0, 1, 2}


def test_fourth_draft_moves_to_next_day():
    rng = random.Random(7)
    occupied: list[datetime] = []
    for i in range(3):
        slot = allocate_slot(
            posting_windows=WINDOWS,
            occupied=occupied,
            timezone="UTC",
            jitter_minutes=0,
            target_date=date(2030, 1, 7),
            rng=rng,
            max_per_window=1,
            daily_quota=3,
        )
        occupied.append(slot)

    fourth = allocate_slot(
        posting_windows=WINDOWS,
        occupied=occupied,
        timezone="UTC",
        jitter_minutes=0,
        target_date=date(2030, 1, 7),
        rng=rng,
        max_per_window=1,
        daily_quota=3,
    )
    assert fourth.astimezone(ZoneInfo("UTC")).date() == date(2030, 1, 8)


def test_daily_quota_blocks_extra_posts_same_day():
    rng = random.Random(99)
    target = date(2030, 1, 7)
    occupied = [
        _slot_at(9, 10, target),
        _slot_at(13, 10, target),
        _slot_at(19, 10, target),
    ]
    next_slot = allocate_slot(
        posting_windows=WINDOWS,
        occupied=occupied,
        timezone="UTC",
        jitter_minutes=0,
        target_date=target,
        rng=rng,
        max_per_window=1,
        daily_quota=3,
    )
    assert next_slot.astimezone(ZoneInfo("UTC")).date() == date(2030, 1, 8)
