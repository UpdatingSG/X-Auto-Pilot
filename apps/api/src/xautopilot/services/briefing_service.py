"""Daily engagement briefing — discover, draft, and act on reply opportunities."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.content import Draft
from xautopilot.models.published_post import PublishedPost
from xautopilot.models.reply_target import ReplyTarget
from xautopilot.schemas.briefing import (
    BriefingAction,
    BriefingResponse,
    BriefingTarget,
    DailyTargets,
)
from xautopilot.services.analytics_service import build_reach_hints
from xautopilot.services.learning_service import build_weight_hints
from xautopilot.services.reply_discovery_service import discover_from_watchlist, discover_reply_targets
from xautopilot.services.reply_target_service import list_active_reply_targets
from xautopilot.services.schedule_service import get_schedule
from xautopilot.services.voice_profile_service import get_active_voice_profile


async def _count_published_today(session: AsyncSession, user_id: UUID, content_type: str) -> int:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count())
        .select_from(PublishedPost)
        .where(
            PublishedPost.user_id == user_id,
            PublishedPost.content_type == content_type,
            PublishedPost.published_at >= today,
        )
    )
    return int(result.scalar_one())


async def _pending_reply_drafts(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Draft)
        .where(
            Draft.user_id == user_id,
            Draft.content_type == "reply",
            Draft.status.in_(["ready", "approved", "scheduled"]),
        )
    )
    return int(result.scalar_one())


def _target_to_briefing(target, *, source: str, has_draft: bool = False) -> BriefingTarget:
    return BriefingTarget(
        x_tweet_id=target.x_tweet_id,
        author_handle=target.author_handle,
        tweet_text=target.tweet_text,
        author_followers=getattr(target, "author_followers", 0),
        likes=getattr(target, "likes", 0),
        relevance_score=getattr(target, "relevance_score", 0.0) or 0.0,
        source=source,
        reply_target_id=str(target.id) if hasattr(target, "id") and target.id else None,
        has_draft=has_draft,
    )


async def get_daily_briefing(session: AsyncSession, user_id: UUID) -> BriefingResponse:
    schedule = await get_schedule(session, user_id)
    voice = await get_active_voice_profile(session, user_id)
    active_targets = await list_active_reply_targets(session, user_id)

    discovery = await discover_reply_targets(session, user_id, limit=8)
    watchlist = await discover_from_watchlist(session, user_id, limit=5)

    existing_ids = {t.x_tweet_id for t in active_targets}
    fresh: list[BriefingTarget] = []
    for tweet in discovery.targets:
        if tweet.x_tweet_id in existing_ids:
            continue
        fresh.append(_target_to_briefing(tweet, source=discovery.source))
    for tweet in watchlist.targets:
        if tweet.x_tweet_id in existing_ids:
            continue
        if any(f.x_tweet_id == tweet.x_tweet_id for f in fresh):
            continue
        fresh.append(_target_to_briefing(tweet, source="watchlist"))

    fresh.sort(key=lambda t: (t.relevance_score, t.likes, t.author_followers), reverse=True)

    draft_target_ids: set[str] = set()
    draft_result = await session.execute(
        select(Draft.generation_metadata).where(
            Draft.user_id == user_id,
            Draft.content_type == "reply",
            Draft.status.in_(["ready", "approved", "scheduled"]),
        )
    )
    for (metadata,) in draft_result.all():
        if metadata and metadata.get("reply_target_id"):
            draft_target_ids.add(str(metadata["reply_target_id"]))

    queued: list[BriefingTarget] = []
    for target in active_targets[:10]:
        queued.append(
            _target_to_briefing(
                target,
                source="saved",
                has_draft=str(target.id) in draft_target_ids,
            )
        )

    replies_today = await _count_published_today(session, user_id, "reply")
    tweets_today = await _count_published_today(session, user_id, "tweet")
    threads_today = await _count_published_today(session, user_id, "thread")

    reply_goal = schedule.replies_per_day if schedule.growth_mode else min(schedule.replies_per_day, 3)
    tweet_goal = 1 if schedule.growth_mode else schedule.tweets_per_day

    targets = DailyTargets(
        replies_goal=reply_goal,
        replies_sent=replies_today,
        tweets_goal=tweet_goal,
        tweets_sent=tweets_today,
        threads_goal=1 if schedule.threads_per_week > 0 else 0,
        threads_sent=threads_today,
    )

    hints = await build_reach_hints(session, user_id)
    if voice and voice.learned_weights:
        hints = build_weight_hints(voice.learned_weights) + hints

    actions: list[BriefingAction] = []
    if replies_today < reply_goal:
        remaining = reply_goal - replies_today
        actions.append(
            BriefingAction(
                priority="high",
                action="send_replies",
                detail=f"Send {remaining} more replies today to hit your growth target.",
            )
        )
    if fresh:
        actions.append(
            BriefingAction(
                priority="high",
                action="import_fresh",
                detail=f"{len(fresh)} fresh posts found — import and draft replies within 30 min for best visibility.",
            )
        )
    pending = await _pending_reply_drafts(session, user_id)
    if pending > 0:
        actions.append(
            BriefingAction(
                priority="medium",
                action="approve_drafts",
                detail=f"{pending} reply drafts waiting — approve and schedule them.",
            )
        )
    if not voice or not voice.favorite_creators:
        actions.append(
            BriefingAction(
                priority="medium",
                action="add_watchlist",
                detail="Add 10–20 niche creators to your watchlist in Voice Profile for faster discovery.",
            )
        )

    return BriefingResponse(
        date=date.today(),
        growth_mode=schedule.growth_mode,
        targets=targets,
        fresh_opportunities=fresh[:10],
        saved_targets=queued,
        actions=actions,
        hints=hints[:6],
        discovery_message=discovery.message,
    )
