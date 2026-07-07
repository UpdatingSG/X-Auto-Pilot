from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.database import get_db
from xautopilot.services.worker_service import run_worker_tick

router = APIRouter(prefix="/v1/worker", tags=["worker"])


def _cron_authorized(x_worker_secret: str | None) -> bool:
    return bool(settings.worker_cron_secret) and x_worker_secret == settings.worker_cron_secret


@router.post("/tick")
async def manual_worker_tick(
    db: AsyncSession = Depends(get_db),
    x_worker_secret: str | None = Header(default=None, alias="X-Worker-Secret"),
):
    """Run one publish + metrics sync tick. Allowed in production with X-Worker-Secret."""
    if settings.app_env == "production" and not settings.worker_manual_tick_enabled:
        if not _cron_authorized(x_worker_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manual worker tick is disabled in production",
            )
    return await run_worker_tick(db)


@router.get("/status")
async def worker_status():
    return {
        "worker_enabled": settings.worker_enabled,
        "tick_interval_seconds": settings.worker_tick_interval_seconds,
        "manual_tick_enabled": settings.worker_manual_tick_enabled,
        "cron_tick_configured": bool(settings.worker_cron_secret),
    }
