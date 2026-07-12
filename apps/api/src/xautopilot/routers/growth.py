"""Growth feature API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.briefing import BriefingResponse
from xautopilot.schemas.growth import GrowthDashboardResponse
from xautopilot.services.briefing_service import get_daily_briefing, run_quick_reply_workflow
from xautopilot.services.growth_service import get_growth_dashboard
from xautopilot.services.learning_service import apply_learned_weights

router = APIRouter(prefix="/v1/growth", tags=["growth"])

MIGRATION_HINT = (
    "Database schema is behind the app version. Redeploy the API on Render "
    "(migrations run automatically on startup) or run: cd apps/api && alembic upgrade head"
)


def _is_missing_schema_error(exc: ProgrammingError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return any(
        token in message
        for token in (
            "undefinedcolumn",
            "undefinedtable",
            "does not exist",
            "no such column",
            "no such table",
        )
    )


def _handle_db_schema(exc: ProgrammingError) -> None:
    if not _is_missing_schema_error(exc):
        raise exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=MIGRATION_HINT,
    ) from exc


@router.get("/briefing", response_model=BriefingResponse)
async def daily_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_daily_briefing(db, current_user.id)
    except ProgrammingError as exc:
        _handle_db_schema(exc)


@router.get("/dashboard", response_model=GrowthDashboardResponse)
async def growth_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_growth_dashboard(db, current_user.id)
    except ProgrammingError as exc:
        _handle_db_schema(exc)


@router.post("/quick-replies")
async def quick_replies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One-click: discover opportunities, import, and draft replies."""
    try:
        return await run_quick_reply_workflow(db, current_user.id)
    except ProgrammingError as exc:
        _handle_db_schema(exc)


@router.post("/learn")
async def run_learning_cycle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await apply_learned_weights(db, current_user.id)
    except ProgrammingError as exc:
        _handle_db_schema(exc)
