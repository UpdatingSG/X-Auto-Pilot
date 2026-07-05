from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.analytics import InsightsResponse, OverviewResponse, PostAnalyticsItem, PostMetricsSnapshot
from xautopilot.services.analytics_service import (
    PostNotFoundError,
    get_insights,
    get_overview,
    list_post_analytics,
    sync_post_metrics,
)
from xautopilot.services.twitter_publish_service import XRateLimitError
from xautopilot.services.x_account_service import XAccountNotFoundError
from xautopilot.services.x_token_service import XAccountNeedsReauthError

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewResponse)
async def analytics_overview(
    period: str = Query(default="7d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_overview(db, current_user.id, period)


@router.get("/posts", response_model=list[PostAnalyticsItem])
async def analytics_posts(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_post_analytics(db, current_user.id, period)


@router.get("/insights", response_model=InsightsResponse)
async def analytics_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_insights(db, current_user.id)


@router.post("/posts/{post_id}/sync", response_model=PostMetricsSnapshot)
async def sync_metrics(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await sync_post_metrics(db, current_user.id, post_id)
    except PostNotFoundError:
        raise HTTPException(status_code=404, detail="Published post not found") from None
    except XAccountNotFoundError:
        raise HTTPException(status_code=400, detail="X account not connected") from None
    except XAccountNeedsReauthError:
        raise HTTPException(
            status_code=401,
            detail="X session expired. Reconnect your account in Settings.",
        ) from None
    except XRateLimitError as exc:
        headers = {}
        if exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=429,
            detail="X API rate limit exceeded. Try again later.",
            headers=headers,
        ) from None
