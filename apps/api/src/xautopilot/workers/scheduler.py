"""APScheduler background worker."""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from xautopilot.config import settings
from xautopilot.database import async_session_factory
from xautopilot.services.worker_service import run_worker_tick

log = logging.getLogger("xautopilot.worker")


async def _scheduled_tick() -> None:
    async with async_session_factory() as session:
        try:
            summary = await run_worker_tick(session)
            pub_ok = summary.get("published_ok", 0)
            met_ok = summary.get("metrics_ok", 0)
            if pub_ok or met_ok or summary.get("published_failed") or summary.get("metrics_failed"):
                log.info(
                    "Worker tick: published_ok=%s published_failed=%s metrics_ok=%s metrics_failed=%s",
                    pub_ok,
                    summary.get("published_failed", 0),
                    met_ok,
                    summary.get("metrics_failed", 0),
                )
        except Exception:
            await session.rollback()
            log.exception("Worker tick failed")


def start_worker_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_tick,
        "interval",
        seconds=settings.worker_tick_interval_seconds,
        id="xautopilot_worker_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()
    log.info(
        "Background worker started (interval=%ss, immediate first tick)",
        settings.worker_tick_interval_seconds,
    )
    return scheduler
