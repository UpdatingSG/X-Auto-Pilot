"""Discover tweets worth replying to via X API search and URL parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.reply_eligibility_service import discovered_tweet_is_safe_for_auto_reply
from xautopilot.models.reply_target import ReplyTarget
from xautopilot.services.reply_target_service import (
    _reply_context_metadata,
    create_reply_target,
)
from xautopilot.services.voice_profile_service import get_active_voice_profile
from xautopilot.services.x_account_service import XAccountNotFoundError, get_x_account
from xautopilot.services.x_client import DiscoveredTweet, XApiError, get_x_client
from xautopilot.services.x_token_service import XAccountNeedsReauthError, get_valid_access_token


def _passes_reply_filter(tweet: DiscoveredTweet, *, replyable_only: bool) -> bool:
    if getattr(tweet, "reply_block_confirmed", False):
        return False
    if not replyable_only:
        return True
    return discovered_tweet_is_safe_for_auto_reply(
        reply_block_confirmed=tweet.reply_block_confirmed,
        reply_warning=tweet.reply_warning,
        reply_settings=tweet.reply_settings,
    )


TWEET_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/(?P<handle>[A-Za-z0-9_]{1,15})/status/(?P<tweet_id>\d+)",
    re.IGNORECASE,
)

DEFAULT_TOPICS = [
    "backend",
    "system design",
    "distributed systems",
    "postgresql",
    "AI engineering",
    "LLM",
    "devops",
]

# Fallback when search API is unavailable on the connected X app tier.
CURATED_ACCOUNTS = [
    "rakyll",
    "mipsytipsy",
    "swyx",
    "kelseyhightower",
    "abndrsn",
    "tekbog",
    "dan_abramov",
    "levelsio",
]


class ReplyDiscoveryError(Exception):
    pass


@dataclass
class DiscoverResult:
    targets: list[DiscoveredTweet]
    source: str
    message: str | None = None


def parse_tweet_url(url: str) -> tuple[str, str]:
    match = TWEET_URL_RE.search(url.strip())
    if not match:
        parsed = urlparse(url.strip())
        if parsed.path:
            match = TWEET_URL_RE.search(f"https://x.com{parsed.path}")
    if not match:
        raise ReplyDiscoveryError("Paste a valid X post URL like https://x.com/handle/status/123")
    return match.group("handle"), match.group("tweet_id")


def _build_search_query(topics: list[str]) -> str:
    terms = topics[:6] or DEFAULT_TOPICS[:4]
    quoted = [f'"{t}"' if " " in t else t for t in terms]
    keyword_clause = " OR ".join(quoted)
    return f"({keyword_clause}) -is:retweet -is:reply lang:en"


def _score_tweet(tweet: DiscoveredTweet, topics: list[str]) -> float:
    text = tweet.tweet_text.lower()
    score = 0.35
    if tweet.author_followers >= 10_000:
        score += 0.15
    if tweet.author_followers >= 50_000:
        score += 0.1
    if tweet.likes >= 5:
        score += 0.1
    if tweet.likes >= 25:
        score += 0.1
    if "?" in tweet.tweet_text:
        score += 0.1
    if any(topic.lower() in text for topic in topics):
        score += 0.15
    return round(min(score, 1.0), 3)


async def _existing_tweet_ids(session: AsyncSession, user_id) -> set[str]:
    result = await session.execute(
        select(ReplyTarget.x_tweet_id).where(ReplyTarget.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def _viewer_x_user_id(session: AsyncSession, user_id) -> str | None:
    try:
        account = await get_x_account(session, user_id)
        return account.x_user_id
    except XAccountNotFoundError:
        return None


async def discover_reply_targets(
    session: AsyncSession,
    user_id,
    *,
    min_followers: int = 10_000,
    limit: int = 10,
    topics: list[str] | None = None,
    replyable_only: bool = False,
) -> DiscoverResult:
    voice = await get_active_voice_profile(session, user_id)
    if topics:
        topic_list = topics
    elif voice and voice.interests:
        topic_list = [i["topic"] for i in voice.interests if i.get("topic")]
    elif voice and voice.profession:
        topic_list = [voice.profession, *DEFAULT_TOPICS[:2]]
    else:
        topic_list = DEFAULT_TOPICS

    existing = await _existing_tweet_ids(session, user_id)
    client = get_x_client()

    if settings.x_api_mode == "mock":
        return DiscoverResult(
            targets=_mock_discoveries(existing, min_followers, limit),
            source="mock",
            message="Mock discovery — connect X and use live API mode for real niche search.",
        )

    try:
        access_token = await get_valid_access_token(session, user_id)
    except XAccountNotFoundError:
        return DiscoverResult(
            targets=[],
            source="none",
            message="Connect your X account in Settings to discover reply opportunities.",
        )
    except XAccountNeedsReauthError as exc:
        raise ReplyDiscoveryError("Reconnect your X account in Settings before discovering targets.") from exc

    viewer_id = await _viewer_x_user_id(session, user_id)
    candidates: list[DiscoveredTweet] = []
    source = "search"
    message: str | None = None

    try:
        query = _build_search_query(topic_list)
        candidates = await client.search_recent_tweets(
            access_token,
            query=query,
            max_results=min(limit * 3, 50),
            viewer_x_user_id=viewer_id,
        )
    except Exception as exc:
        source = "curated_accounts"
        message = (
            "Recent search is unavailable on your X API tier — showing tweets from curated engineering accounts instead."
        )
        for handle in CURATED_ACCOUNTS:
            try:
                tweets = await client.get_user_recent_tweets(
                    access_token, handle, max_results=5, viewer_x_user_id=viewer_id
                )
                candidates.extend(tweets)
            except Exception:
                continue

    filtered: list[DiscoveredTweet] = []
    for tweet in candidates:
        if tweet.x_tweet_id in existing:
            continue
        if tweet.author_followers < min_followers:
            continue
        if not _passes_reply_filter(tweet, replyable_only=replyable_only):
            continue
        if len(tweet.tweet_text.strip()) < 20:
            continue
        tweet.relevance_score = _score_tweet(tweet, topic_list)
        filtered.append(tweet)

    filtered.sort(key=lambda t: (t.relevance_score, t.likes, t.author_followers), reverse=True)
    unique: list[DiscoveredTweet] = []
    seen: set[str] = set()
    for tweet in filtered:
        if tweet.x_tweet_id in seen:
            continue
        seen.add(tweet.x_tweet_id)
        unique.append(tweet)
        if len(unique) >= limit:
            break

    if not unique:
        unique = (
            _mock_discoveries(existing, min_followers, limit, replyable_only=replyable_only)
            if settings.x_api_mode == "mock"
            else []
        )

    if replyable_only and not unique and not message:
        message = (
            "No posts found that allow open replies. Authors who limit replies usually require "
            "that they follow you — not just that you follow them. Paste a post URL on Engagement "
            "or use Quote opportunities."
        )

    return DiscoverResult(targets=unique, source=source, message=message)


def _watchlist_handles(voice) -> list[str]:
    handles: list[str] = []
    for creator in voice.favorite_creators or []:
        if isinstance(creator, str):
            handles.append(creator.lstrip("@"))
        elif isinstance(creator, dict) and creator.get("handle"):
            handles.append(str(creator["handle"]).lstrip("@"))
    return handles[:25]


async def discover_from_watchlist(
    session: AsyncSession,
    user_id,
    *,
    limit: int = 10,
    replyable_only: bool = False,
) -> DiscoverResult:
    """Fetch recent tweets from favorite_creators on the voice profile."""
    voice = await get_active_voice_profile(session, user_id)
    handles = _watchlist_handles(voice) if voice else []
    if not handles:
        return DiscoverResult(targets=[], source="watchlist", message="Add creators to your watchlist in Voice Profile.")

    existing = await _existing_tweet_ids(session, user_id)
    client = get_x_client()

    if settings.x_api_mode == "mock":
        mock_targets = _mock_discoveries(existing, 5_000, limit)
        for i, t in enumerate(mock_targets):
            t.author_handle = handles[i % len(handles)]
        return DiscoverResult(targets=mock_targets, source="watchlist")

    try:
        access_token = await get_valid_access_token(session, user_id)
    except XAccountNotFoundError:
        return DiscoverResult(
            targets=[],
            source="watchlist",
            message="Connect your X account in Settings to monitor your watchlist.",
        )
    except XAccountNeedsReauthError as exc:
        raise ReplyDiscoveryError("Reconnect your X account before checking watchlist.") from exc

    viewer_id = await _viewer_x_user_id(session, user_id)
    topic_list = [i["topic"] for i in (voice.interests if voice else []) if i.get("topic")]
    candidates: list[DiscoveredTweet] = []
    for handle in handles:
        try:
            tweets = await client.get_user_recent_tweets(
                access_token, handle, max_results=3, viewer_x_user_id=viewer_id
            )
            candidates.extend(tweets)
        except Exception:
            continue

    filtered: list[DiscoveredTweet] = []
    for tweet in candidates:
        if tweet.x_tweet_id in existing:
            continue
        if not _passes_reply_filter(tweet, replyable_only=replyable_only):
            continue
        tweet.relevance_score = _score_tweet(tweet, topic_list) + 0.1
        filtered.append(tweet)

    filtered.sort(key=lambda t: (t.relevance_score, t.likes), reverse=True)
    unique: list[DiscoveredTweet] = []
    seen: set[str] = set()
    for tweet in filtered:
        if tweet.x_tweet_id in seen:
            continue
        seen.add(tweet.x_tweet_id)
        unique.append(tweet)
        if len(unique) >= limit:
            break

    return DiscoverResult(
        targets=unique,
        source="watchlist",
        message=f"Monitoring {len(handles)} creators from your watchlist.",
    )


def _mock_discoveries(
    existing: set[str], min_followers: int, limit: int, *, replyable_only: bool = False
) -> list[DiscoveredTweet]:
    samples = [
        DiscoveredTweet(
            x_tweet_id="9000000000000000001",
            x_user_id="1001",
            author_handle="indie_dev",
            tweet_text="Most production incidents start as a missing timeout or a retry storm. What guardrail saved you recently?",
            author_followers=8_500,
            likes=48,
            relevance_score=0.92,
            reply_settings="everyone",
        ),
        DiscoveredTweet(
            x_tweet_id="9000000000000000002",
            x_user_id="1002",
            author_handle="backend_bits",
            tweet_text="The best backend engineers I know obsess over observability before they obsess over microservices.",
            author_followers=12_000,
            likes=120,
            relevance_score=0.9,
            reply_settings="everyone",
        ),
        DiscoveredTweet(
            x_tweet_id="9000000000000000003",
            x_user_id="1003",
            author_handle="kelseyhightower",
            tweet_text="Kubernetes won't fix a bad system design. What's the hardest distributed systems lesson you learned the hard way?",
            author_followers=180_000,
            likes=85,
            relevance_score=0.88,
        ),
        DiscoveredTweet(
            x_tweet_id="9000000000000000004",
            x_user_id="1004",
            author_handle="abndrsn",
            tweet_text="If your AI feature can't fail gracefully, it's not production-ready yet. Curious how teams are testing retrieval failures.",
            author_followers=95_000,
            likes=31,
            relevance_score=0.86,
        ),
        DiscoveredTweet(
            x_tweet_id="9000000000000000005",
            x_user_id="1005",
            author_handle="mipsytipsy",
            tweet_text="Latency budgets are a product decision, not just an infra decision. Who owns yours?",
            author_followers=140_000,
            likes=54,
            relevance_score=0.84,
        ),
    ]
    out: list[DiscoveredTweet] = []
    for tweet in samples:
        if tweet.x_tweet_id in existing:
            continue
        if tweet.author_followers < min_followers:
            continue
        if not _passes_reply_filter(tweet, replyable_only=replyable_only):
            continue
        out.append(tweet)
        if len(out) >= limit:
            break
    return out


async def lookup_reply_target_from_url(
    session: AsyncSession,
    user_id,
    url: str,
) -> DiscoveredTweet:
    handle, tweet_id = parse_tweet_url(url)
    client = get_x_client()

    if settings.x_api_mode == "mock":
        return DiscoveredTweet(
            x_tweet_id=tweet_id,
            x_user_id="mock-user",
            author_handle=handle,
            tweet_text="Mock tweet loaded from URL — deploy with X_API_MODE=live to fetch real tweet text.",
            author_followers=50_000,
            likes=10,
            relevance_score=0.8,
        )

    try:
        access_token = await get_valid_access_token(session, user_id)
    except XAccountNotFoundError:
        raise ReplyDiscoveryError("Connect your X account in Settings before importing from URL.")
    except XAccountNeedsReauthError as exc:
        raise ReplyDiscoveryError("Reconnect your X account in Settings before importing from URL.") from exc

    viewer_id = await _viewer_x_user_id(session, user_id)
    try:
        tweet = await client.lookup_tweet(access_token, tweet_id, viewer_x_user_id=viewer_id)
    except XApiError as exc:
        raise ReplyDiscoveryError(str(exc)) from exc
    if tweet.author_handle.lower() != handle.lower():
        tweet.author_handle = handle
    return tweet


async def import_discovered_targets(
    session: AsyncSession,
    user_id,
    targets: list[DiscoveredTweet],
) -> list[ReplyTarget]:
    existing = await _existing_tweet_ids(session, user_id)
    created: list[ReplyTarget] = []
    for target in targets:
        if target.x_tweet_id in existing:
            continue
        created.append(
            await create_reply_target(
                session,
                user_id,
                author_handle=target.author_handle,
                tweet_text=target.tweet_text,
                x_tweet_id=target.x_tweet_id,
                x_user_id=target.x_user_id,
                conversation_context=_reply_context_metadata(
                    reply_allowed=target.reply_allowed,
                    reply_block_reason=target.reply_block_reason,
                    reply_warning=target.reply_warning,
                    reply_block_confirmed=target.reply_block_confirmed,
                    reply_settings=target.reply_settings,
                ),
            )
        )
        existing.add(target.x_tweet_id)
    return created
