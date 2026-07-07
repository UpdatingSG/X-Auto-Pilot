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
            pub_ok = sum(1 for p in summary["published"] if p["success"])
            met_ok = sum(1 for m in summary["metrics_synced"] if m["success"])
            if pub_ok or met_ok:
                log.info("Worker tick: published=%s metrics_synced=%s", pub_ok, met_ok)
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
