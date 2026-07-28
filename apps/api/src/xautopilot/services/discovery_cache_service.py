"""In-process TTL cache for X discovery results (search / watchlist)."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from xautopilot.services.reply_discovery_service import DiscoverResult

# key -> (expires_at_monotonic, payload dict)
_CACHE: dict[str, tuple[float, dict]] = {}


def clear_discovery_cache() -> None:
    _CACHE.clear()


def discovery_cache_key(user_id, kind: str, **params) -> str:
    parts = [f"{k}={params[k]}" for k in sorted(params)]
    return f"{kind}:{user_id}:{':'.join(parts)}"


def _latest_key(user_id, kind: str) -> str:
    return f"latest:{kind}:{user_id}"


def get_cached_discovery(key: str):
    from xautopilot.services.reply_discovery_service import DiscoverResult
    from xautopilot.services.x_client import DiscoveredTweet

    entry = _CACHE.get(key)
    if entry is None:
        return None
    expires_at, payload = entry
    if time.monotonic() >= expires_at:
        _CACHE.pop(key, None)
        return None
    targets = [DiscoveredTweet(**t) for t in payload["targets"]]
    return DiscoverResult(
        targets=targets,
        source=payload["source"],
        message=payload.get("message"),
    )


def get_latest_cached_discovery(user_id: UUID | str, kind: str):
    """Return the most recent cached result for this user/kind, if still within TTL."""
    return get_cached_discovery(_latest_key(user_id, kind))


def put_cached_discovery(
    key: str,
    result: DiscoverResult,
    *,
    ttl_seconds: int,
    user_id: UUID | str | None = None,
    kind: str | None = None,
) -> None:
    ttl = max(1, int(ttl_seconds))
    payload = {
        "source": result.source,
        "message": result.message,
        "targets": [asdict(t) for t in result.targets],
    }
    expires = time.monotonic() + ttl
    _CACHE[key] = (expires, payload)
    if user_id is not None and kind is not None:
        _CACHE[_latest_key(user_id, kind)] = (expires, payload)
