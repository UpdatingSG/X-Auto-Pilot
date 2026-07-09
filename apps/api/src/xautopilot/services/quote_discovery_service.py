"""Discover high-engagement tweets worth quoting."""

from __future__ import annotations

from xautopilot.config import settings
from xautopilot.services.reply_discovery_service import (
    DiscoverResult,
    ReplyDiscoveryError,
    _existing_tweet_ids,
    _score_tweet,
    discover_reply_targets,
)
from xautopilot.services.voice_profile_service import get_active_voice_profile
from xautopilot.services.x_client import DiscoveredTweet, get_x_client
from xautopilot.services.x_token_service import XAccountNeedsReauthError, get_valid_access_token


def _quote_score(tweet: DiscoveredTweet) -> float:
  base = _score_tweet(tweet, [])
  if tweet.likes >= 50:
      base += 0.15
  if tweet.likes >= 200:
      base += 0.1
  text = tweet.tweet_text.lower()
  if any(w in text for w in ("wrong", "unpopular", "hot take", "myth", "actually")):
      base += 0.1
  return round(min(base, 1.0), 3)


async def discover_quote_opportunities(session, user_id, *, limit: int = 5) -> DiscoverResult:
    """Find tweets suitable for quote-tweets with commentary."""
    result = await discover_reply_targets(session, user_id, min_followers=25_000, limit=limit * 3)
    scored: list[DiscoveredTweet] = []
    for tweet in result.targets:
        if tweet.likes < 30:
            continue
        tweet.relevance_score = _quote_score(tweet)
        scored.append(tweet)
    scored.sort(key=lambda t: (t.relevance_score, t.likes), reverse=True)
    return DiscoverResult(
        targets=scored[:limit],
        source="quote_discovery",
        message="High-engagement posts where a quote-tweet take may outperform a reply.",
    )
