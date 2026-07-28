"""Discovery result TTL cache — avoids repeat X reads within the TTL window."""

from uuid import uuid4

from xautopilot.services.discovery_cache_service import (
    clear_discovery_cache,
    get_cached_discovery,
    put_cached_discovery,
)
from xautopilot.services.reply_discovery_service import DiscoverResult
from xautopilot.services.x_client import DiscoveredTweet


def _tweet(tid: str = "111") -> DiscoveredTweet:
    return DiscoveredTweet(
        x_tweet_id=tid,
        x_user_id="42",
        author_handle="dev",
        tweet_text="A useful question about production timeouts and retries.",
        author_followers=12_000,
        likes=10,
        relevance_score=0.9,
        reply_settings="everyone",
    )


def test_discovery_cache_miss_then_hit():
    clear_discovery_cache()
    user_id = uuid4()
    key = f"search:{user_id}:limit=8"

    assert get_cached_discovery(key) is None

    put_cached_discovery(
        key,
        DiscoverResult(targets=[_tweet()], source="search", message=None),
        ttl_seconds=3600,
    )
    cached = get_cached_discovery(key)
    assert cached is not None
    assert cached.source == "search"
    assert len(cached.targets) == 1
    assert cached.targets[0].x_tweet_id == "111"


def test_discovery_cache_expires(monkeypatch):
    clear_discovery_cache()
    user_id = uuid4()
    key = f"search:{user_id}:limit=8"
    put_cached_discovery(
        key,
        DiscoverResult(targets=[_tweet("222")], source="search"),
        ttl_seconds=60,
        user_id=user_id,
        kind="search",
    )

    import xautopilot.services.discovery_cache_service as cache_mod

    original_monotonic = cache_mod.time.monotonic

    monkeypatch.setattr(
        cache_mod.time,
        "monotonic",
        lambda: original_monotonic() + 120,
    )
    assert get_cached_discovery(key) is None
    from xautopilot.services.discovery_cache_service import get_latest_cached_discovery

    assert get_latest_cached_discovery(user_id, "search") is None


def test_latest_cache_shared_across_param_keys():
    clear_discovery_cache()
    user_id = uuid4()
    put_cached_discovery(
        f"search:{user_id}:limit=15",
        DiscoverResult(targets=[_tweet("333")], source="search"),
        ttl_seconds=3600,
        user_id=user_id,
        kind="search",
    )
    from xautopilot.services.discovery_cache_service import get_latest_cached_discovery

    latest = get_latest_cached_discovery(user_id, "search")
    assert latest is not None
    assert latest.targets[0].x_tweet_id == "333"
