import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass
class PostingWindow:
    start: time
    end: time
    days: list[int]  # 1=Mon .. 7=Sun (ISO)


def parse_windows(raw: list[dict]) -> list[PostingWindow]:
    windows: list[PostingWindow] = []
    for w in raw:
        sh, sm = map(int, w["start"].split(":"))
        eh, em = map(int, w["end"].split(":"))
        windows.append(
            PostingWindow(
                start=time(sh, sm),
                end=time(eh, em),
                days=w.get("days", [1, 2, 3, 4, 5, 6, 7]),
            )
        )
    return windows


def _random_time_in_window(window: PostingWindow, target_date: date, tz: ZoneInfo, rng: random.Random) -> datetime:
    start_dt = datetime.combine(target_date, window.start, tzinfo=tz)
    end_dt = datetime.combine(target_date, window.end, tzinfo=tz)
    span_seconds = int((end_dt - start_dt).total_seconds())
    offset = rng.randint(0, max(span_seconds, 0))
    return start_dt + timedelta(seconds=offset)


def de_round_time(dt: datetime, rng: random.Random) -> datetime:
    minute = dt.minute
    if minute in (0, 30):
        offset = rng.choice([-7, -3, 3, 7, 12, -12])
        dt = dt + timedelta(minutes=offset)
    second = rng.randint(3, 47)
    return dt.replace(second=second, microsecond=0)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def count_posts_on_date(occupied: list[datetime], target: date, tz: ZoneInfo) -> int:
    return sum(1 for other in occupied if other.astimezone(tz).date() == target)


def count_in_window(
    occupied: list[datetime], window: PostingWindow, target: date, tz: ZoneInfo
) -> int:
    return sum(
        1
        for other in occupied
        if other.astimezone(tz).date() == target
        and window.start <= other.astimezone(tz).time() <= window.end
    )


def _slot_fits_window(slot: datetime, window: PostingWindow, target: date, tz: ZoneInfo) -> bool:
    local = slot.astimezone(tz)
    return local.date() == target and window.start <= local.time() <= window.end


def _clamp_to_window(
    slot: datetime, window: PostingWindow, target: date, tz: ZoneInfo
) -> datetime:
    local = slot.astimezone(tz)
    if local.date() != target:
        return slot
    if local.time() < window.start:
        return datetime.combine(target, window.start, tzinfo=tz)
    if local.time() > window.end:
        return datetime.combine(target, window.end, tzinfo=tz)
    return slot


def avoid_collisions(
    slot: datetime, occupied: list[datetime], min_gap_minutes: int = 20
) -> datetime:
    slot = _ensure_utc(slot)
    occupied_utc = [_ensure_utc(other) for other in occupied]
    gap = timedelta(minutes=min_gap_minutes)
    changed = True
    while changed:
        changed = False
        for other in occupied_utc:
            if abs(slot - other) < gap:
                slot = other + gap
                changed = True
    return slot


def allocate_slot(
    posting_windows: list[dict],
    occupied: list[datetime],
    timezone: str,
    jitter_minutes: int,
    target_date: date | None = None,
    rng: random.Random | None = None,
    min_gap_minutes: int = 20,
    max_per_window: int = 1,
    daily_quota: int | None = None,
    max_days_ahead: int = 14,
) -> datetime:
    """Pick the next available window: one post per window, then next window or next day."""
    rng = rng or random.Random()
    tz = ZoneInfo(timezone)
    start_date = target_date or datetime.now(tz).date()
    occupied_utc = [_ensure_utc(other) for other in occupied]
    now = _ensure_utc(datetime.now(UTC))
    windows_all = parse_windows(posting_windows)

    for day_offset in range(max_days_ahead):
        candidate_date = start_date + timedelta(days=day_offset)
        iso_dow = datetime.combine(candidate_date, time(12), tzinfo=tz).isoweekday()
        day_windows = sorted(
            [w for w in windows_all if iso_dow in w.days],
            key=lambda w: w.start,
        )
        if not day_windows:
            day_windows = sorted(windows_all, key=lambda w: w.start)

        if daily_quota is not None and count_posts_on_date(occupied_utc, candidate_date, tz) >= daily_quota:
            continue

        for window in day_windows:
            if count_in_window(occupied_utc, window, candidate_date, tz) >= max_per_window:
                continue

            slot = _random_time_in_window(window, candidate_date, tz, rng)

            jitter_secs = rng.randint(0, jitter_minutes * 60)
            if rng.random() > 0.5:
                jitter_secs = -jitter_secs
            slot = slot + timedelta(seconds=jitter_secs)
            slot = _clamp_to_window(slot, window, candidate_date, tz)
            slot = de_round_time(slot, rng)
            slot = _clamp_to_window(slot, window, candidate_date, tz)

            if not _slot_fits_window(slot, window, candidate_date, tz):
                continue

            slot = avoid_collisions(slot, occupied_utc, min_gap_minutes)
            if not _slot_fits_window(slot, window, candidate_date, tz):
                continue

            if slot <= now:
                continue

            return _ensure_utc(slot)

    raise ValueError("No available posting slot within the configured horizon")
