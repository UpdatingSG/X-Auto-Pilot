from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.reply_target import ReplyTargetCreate, ReplyTargetResponse
from xautopilot.services.reply_target_service import (
    ReplyTargetNotFoundError,
    create_reply_target,
    delete_reply_target,
    list_reply_targets,
)

router = APIRouter(prefix="/v1/reply-targets", tags=["reply-targets"])


@router.get("", response_model=list[ReplyTargetResponse])
async def get_reply_targets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    targets = await list_reply_targets(db, current_user.id)
    return [ReplyTargetResponse.model_validate(t) for t in targets]


@router.post("", response_model=ReplyTargetResponse, status_code=status.HTTP_201_CREATED)
async def add_reply_target(
    data: ReplyTargetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await create_reply_target(
        db,
        current_user.id,
        author_handle=data.author_handle,
        tweet_text=data.tweet_text,
        x_tweet_id=data.x_tweet_id,
        x_user_id=data.x_user_id or "unknown",
    )
    return ReplyTargetResponse.model_validate(target)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reply_target(
    target_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_reply_target(db, current_user.id, target_id)
    except ReplyTargetNotFoundError:
        raise HTTPException(status_code=404, detail="Reply target not found") from None
