"""Metrics sync job scheduling."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.metrics_sync_job import MetricsSyncJob
from xautopilot.models.published_post import PublishedPost

METRICS_SYNC_OFFSETS_HOURS = (1, 6, 24)


async def schedule_metrics_sync_jobs(session: AsyncSession, post: PublishedPost) -> list[MetricsSyncJob]:
    published_at = post.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)

    jobs: list[MetricsSyncJob] = []
    for hours in METRICS_SYNC_OFFSETS_HOURS:
        job = MetricsSyncJob(
            post_id=post.id,
            user_id=post.user_id,
            sync_at=published_at + timedelta(hours=hours),
            label=f"{hours}h",
        )
        session.add(job)
        jobs.append(job)
    await session.flush()
    return jobs


async def list_due_metrics_sync_jobs(
    session: AsyncSession, *, now: datetime | None = None
) -> list[MetricsSyncJob]:
    now = now or datetime.now(UTC)
    result = await session.execute(
        select(MetricsSyncJob)
        .where(MetricsSyncJob.status == "pending", MetricsSyncJob.sync_at <= now)
        .order_by(MetricsSyncJob.sync_at.asc())
    )
    return list(result.scalars().all())
