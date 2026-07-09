"""Growth feature API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.briefing import BriefingResponse
from xautopilot.schemas.growth import GrowthDashboardResponse
from xautopilot.services.briefing_service import get_daily_briefing
from xautopilot.services.growth_service import get_growth_dashboard
from xautopilot.services.learning_service import apply_learned_weights

router = APIRouter(prefix="/v1/growth", tags=["growth"])


@router.get("/briefing", response_model=BriefingResponse)
async def daily_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_daily_briefing(db, current_user.id)


@router.get("/dashboard", response_model=GrowthDashboardResponse)
async def growth_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_growth_dashboard(db, current_user.id)


@router.post("/learn")
async def run_learning_cycle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await apply_learned_weights(db, current_user.id)
