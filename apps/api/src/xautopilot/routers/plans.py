from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.content import IdeaResponse, IdeaStatusUpdate, PlanComposition, PlanResponse
from xautopilot.services.content_plan_service import (
    IdeaNotFoundError,
    generate_daily_plan,
    get_plan_composition,
    get_plan_for_date,
    update_idea_status,
)
from xautopilot.services.llm_service import LLMBudgetExceededError, LLMError, LLMNotConfiguredError

router = APIRouter(prefix="/v1/plans", tags=["plans"])


async def _plan_response(plan, db, user_id) -> PlanResponse:
    composition = await get_plan_composition(db, user_id, plan)
    return PlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        status=plan.status,
        ideas=[IdeaResponse.model_validate(i) for i in plan.ideas],
        composition=PlanComposition.model_validate(composition),
        created_at=plan.created_at,
    )


@router.get("/today", response_model=PlanResponse)
async def get_today_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_plan_for_date(db, current_user.id, date.today())
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan for today")
    return await _plan_response(plan, db, current_user.id)


@router.post("/generate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan(
    force: bool = Query(False, description="Replace today's existing plan with a fresh one"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        plan = await generate_daily_plan(db, current_user.id, date.today(), force=force)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except LLMBudgetExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
        ) from None
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Plan generation failed: {exc}") from None
    return await _plan_response(plan, db, current_user.id)


@router.patch("/{plan_id}/ideas/{idea_id}", response_model=IdeaResponse)
async def update_idea(
    plan_id: str,
    idea_id: str,
    data: IdeaStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    try:
        idea = await update_idea_status(
            db, current_user.id, UUID(plan_id), UUID(idea_id), data.status
        )
    except IdeaNotFoundError:
        raise HTTPException(status_code=404, detail="Idea not found") from None
    return idea
