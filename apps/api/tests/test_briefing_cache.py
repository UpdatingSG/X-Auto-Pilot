"""Briefing discovery cache — avoid repeat X reads after Find & draft."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login
from xautopilot.services.discovery_cache_service import clear_discovery_cache, put_cached_discovery
from xautopilot.services.reply_discovery_service import DiscoverResult
from xautopilot.services.x_client import DiscoveredTweet


async def _setup(client: AsyncClient) -> dict[str, str]:
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    return headers


def _tweet(tid: str) -> DiscoveredTweet:
    return DiscoveredTweet(
        x_tweet_id=tid,
        x_user_id="1",
        author_handle="dev",
        tweet_text="What production timeout strategy has saved you from cascading failures?",
        author_followers=20_000,
        likes=40,
        relevance_score=0.9,
        reply_settings="everyone",
    )


async def test_briefing_reload_after_quick_replies_uses_cache(
    client: AsyncClient, monkeypatch
):
    clear_discovery_cache()
    headers = await _setup(client)

    search_calls = {"n": 0}
    watch_calls = {"n": 0}

    async def fake_search(*_args, **_kwargs):
        search_calls["n"] += 1
        return DiscoverResult(targets=[_tweet("9001")], source="search")

    async def fake_watch(*_args, **_kwargs):
        watch_calls["n"] += 1
        return DiscoverResult(targets=[_tweet("9002")], source="watchlist")

    monkeypatch.setattr(
        "xautopilot.services.briefing_service.discover_reply_targets",
        fake_search,
    )
    monkeypatch.setattr(
        "xautopilot.services.briefing_service.discover_from_watchlist",
        fake_watch,
    )
    # Quick-reply workflow imports discovery from reply_discovery_service
    monkeypatch.setattr(
        "xautopilot.services.reply_discovery_service.discover_reply_targets",
        fake_search,
    )
    monkeypatch.setattr(
        "xautopilot.services.reply_discovery_service.discover_from_watchlist",
        fake_watch,
    )

    # Warm cache the way Find & draft does (force refresh writes latest keys)
    me = (await client.get("/v1/auth/me", headers=headers)).json()
    user_id = me["id"]
    put_cached_discovery(
        f"search:{user_id}:warm",
        DiscoverResult(targets=[_tweet("9001")], source="search"),
        ttl_seconds=3600,
        user_id=user_id,
        kind="search",
    )
    put_cached_discovery(
        f"watchlist:{user_id}:warm",
        DiscoverResult(targets=[_tweet("9002")], source="watchlist"),
        ttl_seconds=3600,
        user_id=user_id,
        kind="watchlist",
    )

    response = await client.get("/v1/growth/briefing", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "cached" in (body.get("discovery_message") or "").lower()
    assert search_calls["n"] == 0
    assert watch_calls["n"] == 0


async def test_briefing_discovers_when_cache_empty(client: AsyncClient, monkeypatch):
    clear_discovery_cache()
    headers = await _setup(client)
    search_calls = {"n": 0}

    async def fake_search(*_args, **_kwargs):
        search_calls["n"] += 1
        return DiscoverResult(targets=[_tweet("9003")], source="search")

    async def fake_watch(*_args, **_kwargs):
        return DiscoverResult(targets=[], source="watchlist", message="no watchlist")

    monkeypatch.setattr(
        "xautopilot.services.briefing_service.discover_reply_targets",
        fake_search,
    )
    monkeypatch.setattr(
        "xautopilot.services.briefing_service.discover_from_watchlist",
        fake_watch,
    )

    response = await client.get("/v1/growth/briefing", headers=headers)
    assert response.status_code == 200
    assert search_calls["n"] == 1
