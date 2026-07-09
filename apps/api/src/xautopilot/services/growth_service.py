"""Growth dashboard metrics — leading indicators and content-type breakdown."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.post_metrics import PostMetrics
from xautopilot.models.published_post import PublishedPost
from xautopilot.schemas.growth import (
    ContentTypeBreakdown,
    GrowthDashboardResponse,
    GrowthStreak,
    ReplyPerformance,
)
from xautopilot.services.analytics_service import list_post_analytics, period_start
from xautopilot.services.schedule_service import get_schedule


async def _published_counts(session: AsyncSession, user_id: UUID, days: int) -> dict[str, int]:
    since = period_start(days)
    result = await session.execute(
        select(PublishedPost.content_type, func.count())
        .where(PublishedPost.user_id == user_id, PublishedPost.published_at >= since)
        .group_by(PublishedPost.content_type)
    )
    counts = {"tweet": 0, "thread": 0, "reply": 0, "quote_tweet": 0}
    for ctype, count in result.all():
        if ctype in counts:
            counts[ctype] = int(count)
    return counts


async def _follower_delta(session: AsyncSession, user_id: UUID, days: int) -> int | None:
    since = period_start(days)
    result = await session.execute(
        select(PostMetrics.follower_count, PostMetrics.captured_at)
        .join(PublishedPost, PostMetrics.post_id == PublishedPost.id)
        .where(PublishedPost.user_id == user_id, PostMetrics.follower_count.isnot(None))
        .order_by(PostMetrics.captured_at.asc())
    )
    rows = result.all()
    if len(rows) < 2:
        return None
    first = next((r[0] for r in rows if r[0] is not None), None)
    last = rows[-1][0]
    if first is None or last is None:
        return None
    return int(last) - int(first)


async def _reply_performance(session: AsyncSession, user_id: UUID) -> list[ReplyPerformance]:
    posts = await list_post_analytics(session, user_id, "30d")
    replies = [p for p in posts if getattr(p, "content_type", None) == "reply" or p.category == "engagement"]
    # Re-fetch with content_type from DB
    since = period_start(30)
    result = await session.execute(
        select(PublishedPost)
        .where(
            PublishedPost.user_id == user_id,
            PublishedPost.content_type == "reply",
            PublishedPost.published_at >= since,
        )
        .order_by(PublishedPost.published_at.desc())
        .limit(20)
    )
    reply_posts = list(result.scalars().all())
    post_ids = [p.id for p in reply_posts]
    if not post_ids:
        return []

    metrics_result = await session.execute(
        select(PostMetrics)
        .where(PostMetrics.post_id.in_(post_ids))
        .order_by(PostMetrics.captured_at.desc())
    )
    latest_by_post: dict = {}
    for m in metrics_result.scalars().all():
        if m.post_id not in latest_by_post:
            latest_by_post[m.post_id] = m

    out: list[ReplyPerformance] = []
    for post in reply_posts:
        m = latest_by_post.get(post.id)
        out.append(
            ReplyPerformance(
                post_id=post.id,
                preview_text=post.preview_text,
                impressions=m.impressions if m else 0,
                likes=m.likes if m else 0,
                replies=m.replies if m else 0,
                engagement_rate=m.engagement_rate if m else 0.0,
                published_at=post.published_at,
            )
        )
    return out


async def _streak_days(session: AsyncSession, user_id: UUID) -> int:
    """Count consecutive days with at least one published reply."""
    result = await session.execute(
        select(func.date_trunc("day", PublishedPost.published_at))
        .where(PublishedPost.user_id == user_id, PublishedPost.content_type == "reply")
        .group_by(func.date_trunc("day", PublishedPost.published_at))
        .order_by(func.date_trunc("day", PublishedPost.published_at).desc())
    )
    days = [row[0].date() if hasattr(row[0], "date") else row[0] for row in result.all()]
    if not days:
        return 0
    streak = 0
    expected = datetime.now(UTC).date()
    for day in days:
        if day == expected or day == expected - timedelta(days=1):
            streak += 1
            expected = day - timedelta(days=1)
        else:
            break
    return streak


async def get_growth_dashboard(session: AsyncSession, user_id: UUID) -> GrowthDashboardResponse:
    schedule = await get_schedule(session, user_id)
    counts_7d = await _published_counts(session, user_id, 7)
    counts_1d = await _published_counts(session, user_id, 1)

    posts = await list_post_analytics(session, user_id, "30d")
    by_type: dict[str, list] = {"tweet": [], "thread": [], "reply": [], "quote_tweet": []}
    since = period_start(30)
    type_result = await session.execute(
        select(PublishedPost.content_type, PublishedPost.id)
        .where(PublishedPost.user_id == user_id, PublishedPost.published_at >= since)
    )
    type_map = {row[1]: row[0] for row in type_result.all()}
    for post in posts:
        ctype = type_map.get(post.post_id, "tweet")
        if ctype in by_type and post.metrics:
            by_type[ctype].append(post.metrics)

    breakdown: list[ContentTypeBreakdown] = []
    for ctype, metrics_list in by_type.items():
        if not metrics_list:
            breakdown.append(ContentTypeBreakdown(content_type=ctype, count=0))
            continue
        avg_imp = sum(m.impressions for m in metrics_list) / len(metrics_list)
        avg_er = sum(m.engagement_rate for m in metrics_list) / len(metrics_list)
        avg_bm = sum(m.bookmarks for m in metrics_list) / len(metrics_list)
        breakdown.append(
            ContentTypeBreakdown(
                content_type=ctype,
                count=len(metrics_list),
                avg_impressions=round(avg_imp, 1),
                avg_engagement_rate=round(avg_er, 4),
                avg_bookmarks=round(avg_bm, 1),
            )
        )

    reply_goal = schedule.replies_per_day if schedule.growth_mode else min(schedule.replies_per_day, 3)
    streak = await _streak_days(session, user_id)

    return GrowthDashboardResponse(
        growth_mode=schedule.growth_mode,
        period="7d",
        daily_targets={
            "replies": reply_goal,
            "tweets": 1 if schedule.growth_mode else schedule.tweets_per_day,
            "threads_per_week": schedule.threads_per_week,
        },
        today_counts=counts_1d,
        week_counts=counts_7d,
        follower_delta_7d=await _follower_delta(session, user_id, 7),
        content_breakdown=breakdown,
        reply_performance=await _reply_performance(session, user_id),
        streak=GrowthStreak(reply_days=streak),
    )
