from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.content import (
    DraftGenerateRequest,
    DraftResponse,
    DraftUpdate,
    VariantResponse,
)
from xautopilot.schemas.schedule import ScheduleDraftRequest
from xautopilot.services.content_plan_service import IdeaNotFoundError
from xautopilot.services.reply_target_service import InvalidReplyTargetError
from xautopilot.services.draft_service import (
    DraftNotFoundError,
    IdeaNotApprovedError,
    generate_draft_from_idea,
    generate_reply_draft_from_target,
    get_draft,
    list_drafts,
    update_draft,
)
from xautopilot.services.llm_service import LLMBudgetExceededError, LLMError, LLMNotConfiguredError
from xautopilot.services.publish_service import (
    DraftNotSchedulableError,
    DraftNotScheduledError,
    cancel_schedule,
    schedule_draft,
)

router = APIRouter(prefix="/v1/drafts", tags=["drafts"])


def _draft_response(draft) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        idea_id=draft.idea_id,
        content_type=draft.content_type,
        category=draft.category,
        status=draft.status,
        selected_variant_id=draft.selected_variant_id,
        scheduled_at=draft.scheduled_at,
        generation_metadata=draft.generation_metadata or {},
        variants=[VariantResponse.model_validate(v) for v in draft.variants],
        created_at=draft.created_at,
    )


@router.get("", response_model=list[DraftResponse])
async def get_drafts(
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    drafts = await list_drafts(db, current_user.id, status=status)
    return [_draft_response(d) for d in drafts]


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft_by_id(
    draft_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft = await get_draft(db, current_user.id, draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    return _draft_response(draft)


@router.post("/generate", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
async def generate_draft(
    data: DraftGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not data.idea_id and not data.reply_target_id:
        raise HTTPException(status_code=400, detail="idea_id or reply_target_id required")
    if data.idea_id and data.reply_target_id:
        raise HTTPException(status_code=400, detail="Provide idea_id or reply_target_id, not both")
    try:
        if data.reply_target_id:
            draft = await generate_reply_draft_from_target(
                db, current_user.id, data.reply_target_id
            )
        else:
            draft = await generate_draft_from_idea(db, current_user.id, data.idea_id)  # type: ignore[arg-type]
    except IdeaNotFoundError:
        raise HTTPException(status_code=404, detail="Idea or reply target not found") from None
    except InvalidReplyTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except IdeaNotApprovedError:
        raise HTTPException(status_code=400, detail="Idea must be approved first") from None
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except LLMBudgetExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return _draft_response(draft)


@router.patch("/{draft_id}", response_model=DraftResponse)
async def patch_draft(
    draft_id: UUID,
    data: DraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft = await update_draft(
            db, current_user.id, draft_id, data.status, data.selected_variant_id
        )
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    return _draft_response(draft)


@router.post("/{draft_id}/schedule", response_model=DraftResponse)
async def schedule_draft_endpoint(
    draft_id: UUID,
    data: ScheduleDraftRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft = await schedule_draft(
            db,
            current_user.id,
            draft_id,
            scheduled_at=data.scheduled_at,
            timezone=current_user.timezone,
        )
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except DraftNotSchedulableError:
        raise HTTPException(status_code=400, detail="Draft must be approved to schedule") from None
    return _draft_response(draft)


@router.delete("/{draft_id}/schedule", response_model=DraftResponse)
async def cancel_draft_schedule(
    draft_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft = await cancel_schedule(db, current_user.id, draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except DraftNotScheduledError:
        raise HTTPException(status_code=400, detail="Draft is not scheduled") from None
    return _draft_response(draft)
