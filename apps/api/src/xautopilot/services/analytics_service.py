from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.post_metrics import PostMetrics
from xautopilot.models.published_post import PublishedPost
from xautopilot.schemas.analytics import (
    InsightsResponse,
    OverviewResponse,
    PostAnalyticsItem,
    PostMetricsSnapshot,
    TopPostSummary,
)


def parse_period_days(period: str) -> int:
    if period.endswith("d") and period[:-1].isdigit():
        return int(period[:-1])
    return 7


def period_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def calculate_engagement_rate(
    impressions: int,
    likes: int,
    replies: int,
    reposts: int,
    bookmarks: int,
    quotes: int,
) -> float:
    if impressions <= 0:
        return 0.0
    engagements = likes + replies + reposts + bookmarks + quotes
    return round(engagements / impressions, 4)


async def _posts_in_period(
    session: AsyncSession, user_id: UUID, days: int
) -> list[PublishedPost]:
    since = period_start(days)
    result = await session.execute(
        select(PublishedPost)
        .options(selectinload(PublishedPost.metrics_snapshots))
        .where(PublishedPost.user_id == user_id, PublishedPost.published_at >= since)
        .order_by(PublishedPost.published_at.desc())
    )
    return list(result.scalars().all())


def _latest_metrics(post: PublishedPost) -> PostMetrics | None:
    if not post.metrics_snapshots:
        return None
    return post.metrics_snapshots[0]


async def get_overview(session: AsyncSession, user_id: UUID, period: str) -> OverviewResponse:
    days = parse_period_days(period)
    posts = await _posts_in_period(session, user_id, days)

    total_impressions = 0
    engagement_rates: list[float] = []
    top_post: TopPostSummary | None = None

    for post in posts:
        latest = _latest_metrics(post)
        if latest is None:
            continue
        impressions = latest.impressions or 0
        rate = latest.engagement_rate or 0.0
        total_impressions += impressions
        engagement_rates.append(rate)
        if top_post is None or rate > top_post.engagement_rate:
            top_post = TopPostSummary(
                post_id=post.id,
                preview_text=post.preview_text,
                engagement_rate=rate,
                impressions=impressions,
            )

    avg_rate = round(sum(engagement_rates) / len(engagement_rates), 4) if engagement_rates else 0.0

    return OverviewResponse(
        period=period,
        posts_published=len(posts),
        total_impressions=total_impressions,
        avg_engagement_rate=avg_rate,
        top_post=top_post,
    )


async def list_post_analytics(
    session: AsyncSession, user_id: UUID, period: str
) -> list[PostAnalyticsItem]:
    days = parse_period_days(period)
    posts = await _posts_in_period(session, user_id, days)
    items: list[PostAnalyticsItem] = []

    for post in posts:
        latest = _latest_metrics(post)
        metrics = None
        if latest is not None:
            metrics = PostMetricsSnapshot(
                impressions=latest.impressions or 0,
                likes=latest.likes or 0,
                replies=latest.replies or 0,
                reposts=latest.reposts or 0,
                bookmarks=latest.bookmarks or 0,
                quotes=latest.quotes or 0,
                engagement_rate=latest.engagement_rate or 0.0,
                captured_at=latest.captured_at,
            )
        category = post.content_snapshot.get("category") if post.content_snapshot else None
        items.append(
            PostAnalyticsItem(
                post_id=post.id,
                draft_id=post.draft_id,
                x_tweet_id=post.x_tweet_id,
                preview_text=post.preview_text,
                category=category,
                published_at=post.published_at,
                metrics=metrics,
            )
        )

    return items


async def get_insights(session: AsyncSession, user_id: UUID) -> InsightsResponse:
    posts = await list_post_analytics(session, user_id, "7d")
    with_metrics = [p for p in posts if p.metrics is not None]

    if not with_metrics:
        return InsightsResponse(period="7d")

    ranked = sorted(with_metrics, key=lambda p: p.metrics.engagement_rate if p.metrics else 0, reverse=True)
    best = ranked[0]
    worst = ranked[-1] if len(ranked) > 1 else None

    what_worked: list[str] = []
    if best.preview_text and best.category:
        what_worked.append(f"{best.category} posts like \"{best.preview_text[:60]}...\"")

    what_failed: list[str] = []
    if worst and worst.post_id != best.post_id and worst.metrics and worst.metrics.engagement_rate < 0.02:
        what_failed.append(f"Low engagement on {worst.category or 'general'} content")

    best_hour = best.published_at.astimezone(UTC).hour
    best_category = best.category

    adjustments: dict[str, list[str]] = {"increase_weight": [], "decrease_weight": []}
    if best_category:
        adjustments["increase_weight"].append(best_category)
    if worst and worst.category and worst.category != best_category:
        adjustments["decrease_weight"].append(worst.category)

    return InsightsResponse(
        period="7d",
        what_worked=what_worked,
        what_failed=what_failed,
        best_posting_hour=best_hour,
        best_category=best_category,
        recommended_adjustments=adjustments,
    )


class PostNotFoundError(Exception):
    pass


async def get_published_post(
    session: AsyncSession, user_id: UUID, post_id: UUID
) -> PublishedPost:
    result = await session.execute(
        select(PublishedPost)
        .options(selectinload(PublishedPost.metrics_snapshots))
        .where(PublishedPost.id == post_id, PublishedPost.user_id == user_id)
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFoundError
    return post


async def sync_post_metrics(
    session: AsyncSession,
    user_id: UUID,
    post_id: UUID,
    x_client=None,
) -> PostMetricsSnapshot:
    from xautopilot.services.x_account_service import XAccountNotFoundError, get_x_account
    from xautopilot.services.x_client import XApiRateLimitError, XApiUnauthorizedError, get_x_client
    from xautopilot.services.x_token_service import (
        XAccountNeedsReauthError,
        get_valid_access_token,
        mark_account_needs_reauth,
    )
    from xautopilot.services.twitter_publish_service import XRateLimitError

    post = await get_published_post(session, user_id, post_id)
    try:
        await get_x_account(session, user_id)
    except XAccountNotFoundError as exc:
        raise exc

    client = x_client or get_x_client()
    try:
        access_token = await get_valid_access_token(session, user_id)
        raw = await client.get_tweet_metrics(access_token, post.x_tweet_id)
    except XApiUnauthorizedError:
        await mark_account_needs_reauth(session, user_id)
        raise XAccountNeedsReauthError from None
    except XApiRateLimitError as exc:
        raise XRateLimitError(exc.retry_after_seconds) from exc

    rate = calculate_engagement_rate(
        raw.impressions, raw.likes, raw.replies, raw.reposts, raw.bookmarks, raw.quotes
    )
    snapshot = PostMetrics(
        post_id=post.id,
        impressions=raw.impressions,
        likes=raw.likes,
        replies=raw.replies,
        reposts=raw.reposts,
        bookmarks=raw.bookmarks,
        quotes=raw.quotes,
        engagement_rate=rate,
        follower_count=raw.follower_count,
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)

    return PostMetricsSnapshot(
        impressions=snapshot.impressions or 0,
        likes=snapshot.likes or 0,
        replies=snapshot.replies or 0,
        reposts=snapshot.reposts or 0,
        bookmarks=snapshot.bookmarks or 0,
        quotes=snapshot.quotes or 0,
        engagement_rate=snapshot.engagement_rate or 0.0,
        captured_at=snapshot.captured_at,
    )
