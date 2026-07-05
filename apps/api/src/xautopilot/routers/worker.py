from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.database import get_db
from xautopilot.services.worker_service import run_worker_tick

router = APIRouter(prefix="/v1/worker", tags=["worker"])


@router.post("/tick")
async def manual_worker_tick(db: AsyncSession = Depends(get_db)):
    """Run one publish + metrics sync tick. Dev/staging only by default."""
    if settings.app_env == "production" and not settings.worker_manual_tick_enabled:
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
    }
