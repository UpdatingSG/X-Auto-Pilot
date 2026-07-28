"""Unit tests for mid-size niche reply discovery scoring."""

from xautopilot.services.quote_discovery_service import _quote_score
from xautopilot.services.reply_discovery_service import (
    _looks_like_news_or_promo,
    _score_tweet,
)
from xautopilot.services.x_client import DiscoveredTweet


def _tweet(**overrides) -> DiscoveredTweet:
    base = dict(
        x_tweet_id="1",
        x_user_id="1",
        author_handle="eng",
        tweet_text="Postgres timeouts taught me more than any architecture diagram.",
        author_followers=12_000,
        likes=40,
        relevance_score=0.0,
    )
    base.update(overrides)
    return DiscoveredTweet(**base)


def test_prefers_mid_size_over_mega_accounts():
    mid = _score_tweet(_tweet(author_followers=12_000), ["postgres"])
    mega = _score_tweet(_tweet(author_followers=250_000), ["postgres"])
    assert mid > mega


def test_rejects_news_and_promo_copy():
    assert _looks_like_news_or_promo("BREAKING: This AI startup just raised Series B")
    assert _looks_like_news_or_promo("We're hiring backend engineers — join our team")
    assert not _looks_like_news_or_promo("Missing timeouts caused our last retry storm")


def test_quote_score_penalizes_promo():
    clean = _quote_score(_tweet(likes=80))
    promo = _quote_score(
        _tweet(tweet_text="BREAKING: This AI startup just raised Series B funding", likes=80)
    )
    assert clean > promo
