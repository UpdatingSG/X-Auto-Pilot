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


def _slot_after_occupied(
    occupied: list[datetime],
    posting_windows: list[dict],
    timezone: str,
    min_gap_minutes: int,
    target_date: date,
    rng: random.Random,
) -> datetime:
    """Place the next post at least min_gap after the latest occupied slot."""
    tz = ZoneInfo(timezone)
    slot = max(_ensure_utc(other) for other in occupied) + timedelta(minutes=min_gap_minutes)
    slot = de_round_time(slot, rng)
    slot = avoid_collisions(slot, occupied, min_gap_minutes)

    windows = parse_windows(posting_windows)
    local = slot.astimezone(tz)
    local_time = local.time()
    local_date = local.date()

    in_window = any(
        local_date.isoweekday() in window.days and window.start <= local_time <= window.end
        for window in windows
    )
    if in_window:
        return _ensure_utc(slot)

    # Drifted outside windows after de-rounding — pick the next window start.
    for offset in range(8):
        candidate_date = local_date + timedelta(days=offset)
        iso_dow = candidate_date.isoweekday()
        day_windows = [w for w in windows if iso_dow in w.days] or windows
        for window in sorted(day_windows, key=lambda w: w.start):
            start_dt = datetime.combine(candidate_date, window.start, tzinfo=tz)
            if start_dt >= local:
                candidate = de_round_time(start_dt, rng)
                return avoid_collisions(candidate, occupied, min_gap_minutes)

    return _ensure_utc(slot)


def allocate_slot(
    posting_windows: list[dict],
    occupied: list[datetime],
    timezone: str,
    jitter_minutes: int,
    target_date: date | None = None,
    rng: random.Random | None = None,
    min_gap_minutes: int = 20,
) -> datetime:
    """Pick a human-like posting time within configured windows."""
    rng = rng or random.Random()
    tz = ZoneInfo(timezone)
    target = target_date or datetime.now(tz).date()
    occupied_utc = [_ensure_utc(other) for other in occupied]

    if occupied_utc:
        slot = _slot_after_occupied(
            occupied_utc, posting_windows, timezone, min_gap_minutes, target, rng
        )
        if slot <= _ensure_utc(datetime.now(UTC)):
            slot = slot + timedelta(days=1)
        return _ensure_utc(slot)

    iso_dow = datetime.combine(target, time(12), tzinfo=tz).isoweekday()

    windows = [w for w in parse_windows(posting_windows) if iso_dow in w.days]
    if not windows:
        windows = parse_windows(posting_windows)

    window = min(
        windows,
        key=lambda w: sum(
            1
            for o in occupied
            if o.astimezone(tz).date() == target and w.start <= o.astimezone(tz).time() <= w.end
        ),
    )
    slot = _random_time_in_window(window, target, tz, rng)

    jitter_secs = rng.randint(0, jitter_minutes * 60)
    if rng.random() > 0.5:
        jitter_secs = -jitter_secs
    slot = slot + timedelta(seconds=jitter_secs)

    slot = avoid_collisions(slot, occupied_utc, min_gap_minutes)
    slot = de_round_time(slot, rng)
    slot = avoid_collisions(slot, occupied_utc, min_gap_minutes)

    if slot <= _ensure_utc(datetime.now(UTC)):
        slot = slot + timedelta(days=1)

    return _ensure_utc(slot)
