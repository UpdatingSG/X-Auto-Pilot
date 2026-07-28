"""Discover high-engagement tweets worth quoting."""

from __future__ import annotations

from xautopilot.services.reply_discovery_service import (
    DEFAULT_MAX_FOLLOWERS,
    DiscoverResult,
    _looks_like_news_or_promo,
    _score_tweet,
    discover_reply_targets,
)
from xautopilot.services.x_client import DiscoveredTweet


def _quote_score(tweet: DiscoveredTweet) -> float:
    base = _score_tweet(tweet, [])
    if tweet.likes >= 50:
        base += 0.15
    if tweet.likes >= 200:
        base += 0.1
    text = tweet.tweet_text.lower()
    if any(w in text for w in ("wrong", "unpopular", "hot take", "myth", "actually")):
        base += 0.1
    if _looks_like_news_or_promo(tweet.tweet_text):
        base -= 0.3
    return round(min(max(base, 0.0), 1.0), 3)


async def discover_quote_opportunities(session, user_id, *, limit: int = 5) -> DiscoverResult:
    """Find mid-size niche posts suitable for quote-tweets (not news mega-accounts)."""
    result = await discover_reply_targets(
        session,
        user_id,
        min_followers=5_000,
        max_followers=DEFAULT_MAX_FOLLOWERS,
        limit=limit * 3,
        force_refresh=True,
    )
    scored: list[DiscoveredTweet] = []
    for tweet in result.targets:
        if tweet.likes < 20:
            continue
        if _looks_like_news_or_promo(tweet.tweet_text):
            continue
        tweet.relevance_score = _quote_score(tweet)
        scored.append(tweet)
    scored.sort(key=lambda t: (t.relevance_score, t.likes), reverse=True)
    return DiscoverResult(
        targets=scored[:limit],
        source="quote_discovery",
        message="Niche posts where a sharp quote take may outperform a reply — not news/promo.",
    )
