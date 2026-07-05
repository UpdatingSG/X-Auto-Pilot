"""Background publish + metrics sync ticks."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.content import Draft
from xautopilot.services.analytics_service import sync_post_metrics
from xautopilot.services.metrics_sync_service import list_due_metrics_sync_jobs
from xautopilot.services.twitter_publish_service import (
    DraftNotPublishableError,
    XAccountNotConnectedError,
    XPublishError,
    publish_draft,
)
from xautopilot.services.x_token_service import XAccountNeedsReauthError

log = logging.getLogger("xautopilot.worker")


@dataclass
class PublishTickResult:
    draft_id: UUID
    user_id: UUID
    success: bool
    x_tweet_id: str | None = None
    error: str | None = None


@dataclass
class MetricsSyncTickResult:
    job_id: UUID
    post_id: UUID
    label: str
    success: bool
    error: str | None = None


async def list_due_scheduled_drafts(
    session: AsyncSession, *, now: datetime | None = None
) -> list[Draft]:
    now = now or datetime.now(UTC)
    result = await session.execute(
        select(Draft)
        .options(selectinload(Draft.variants))
        .where(Draft.status == "scheduled", Draft.scheduled_at <= now)
        .order_by(Draft.scheduled_at.asc())
    )
    return list(result.scalars().all())


async def run_publish_tick(session: AsyncSession, *, now: datetime | None = None) -> list[PublishTickResult]:
    results: list[PublishTickResult] = []
    for draft in await list_due_scheduled_drafts(session, now=now):
        try:
            post = await publish_draft(session, draft.user_id, draft.id)
            results.append(
                PublishTickResult(
                    draft_id=draft.id,
                    user_id=draft.user_id,
                    success=True,
                    x_tweet_id=post.x_tweet_id,
                )
            )
            log.info("Auto-published draft %s as tweet %s", draft.id, post.x_tweet_id)
        except XAccountNeedsReauthError:
            msg = "X account needs reauthorization"
            results.append(
                PublishTickResult(draft_id=draft.id, user_id=draft.user_id, success=False, error=msg)
            )
            log.warning("Publish tick skipped draft %s: %s", draft.id, msg)
        except (XAccountNotConnectedError, DraftNotPublishableError, XPublishError) as exc:
            results.append(
                PublishTickResult(
                    draft_id=draft.id,
                    user_id=draft.user_id,
                    success=False,
                    error=str(exc),
                )
            )
            log.warning("Publish tick failed draft %s: %s", draft.id, exc)
        except Exception as exc:
            results.append(
                PublishTickResult(
                    draft_id=draft.id,
                    user_id=draft.user_id,
                    success=False,
                    error=str(exc),
                )
            )
            log.exception("Publish tick error draft %s", draft.id)
    return results


async def run_metrics_sync_tick(
    session: AsyncSession, *, now: datetime | None = None
) -> list[MetricsSyncTickResult]:
    results: list[MetricsSyncTickResult] = []
    for job in await list_due_metrics_sync_jobs(session, now=now):
        try:
            await sync_post_metrics(session, job.user_id, job.post_id)
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.error_message = None
            results.append(
                MetricsSyncTickResult(
                    job_id=job.id,
                    post_id=job.post_id,
                    label=job.label,
                    success=True,
                )
            )
            log.info("Metrics sync %s completed for post %s", job.label, job.post_id)
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.completed_at = datetime.now(UTC)
            results.append(
                MetricsSyncTickResult(
                    job_id=job.id,
                    post_id=job.post_id,
                    label=job.label,
                    success=False,
                    error=str(exc),
                )
            )
            log.warning("Metrics sync %s failed for post %s: %s", job.label, job.post_id, exc)
    return results


async def run_worker_tick(session: AsyncSession, *, now: datetime | None = None) -> dict:
    published = await run_publish_tick(session, now=now)
    metrics = await run_metrics_sync_tick(session, now=now)
    await session.commit()
    return {
        "published": [
            {
                "draft_id": str(r.draft_id),
                "success": r.success,
                "x_tweet_id": r.x_tweet_id,
                "error": r.error,
            }
            for r in published
        ],
        "metrics_synced": [
            {
                "job_id": str(r.job_id),
                "post_id": str(r.post_id),
                "label": r.label,
                "success": r.success,
                "error": r.error,
            }
            for r in metrics
        ],
    }
