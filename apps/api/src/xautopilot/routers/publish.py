from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.schedule import PublishedPostResponse, QueueItemResponse
from xautopilot.services.draft_service import DraftNotFoundError
from xautopilot.services.publish_service import list_publish_queue
from xautopilot.services.twitter_publish_service import (
    DraftNotPublishableError,
    XAccountNotConnectedError,
    XPublishError,
    XPublishForbiddenError,
    XRateLimitError,
    list_published_posts,
    publish_draft,
)
from xautopilot.services.x_token_service import XAccountNeedsReauthError, XTokenRefreshError

router = APIRouter(prefix="/v1/publish", tags=["publish"])


def _preview(draft) -> str | None:
    if draft.selected_variant_id:
        for v in draft.variants:
            if v.id == draft.selected_variant_id:
                return v.content_text
    return draft.variants[0].content_text if draft.variants else None


def _post_response(post) -> PublishedPostResponse:
    return PublishedPostResponse(
        id=post.id,
        draft_id=post.draft_id,
        x_tweet_id=post.x_tweet_id,
        content_type=post.content_type,
        preview_text=post.preview_text,
        status="published",
        published_at=post.published_at,
    )


@router.get("/queue", response_model=list[QueueItemResponse])
async def publish_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    drafts = await list_publish_queue(db, current_user.id)
    return [
        QueueItemResponse(
            draft_id=d.id,
            content_type=d.content_type,
            category=d.category,
            scheduled_at=d.scheduled_at,
            preview_text=_preview(d),
            status=d.status,
        )
        for d in drafts
        if d.scheduled_at
    ]


@router.get("/history", response_model=list[PublishedPostResponse])
async def publish_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    posts = await list_published_posts(db, current_user.id)
    return [_post_response(post) for post in posts]


@router.post("/{draft_id}", response_model=PublishedPostResponse)
async def publish_draft_now(
    draft_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        post = await publish_draft(db, current_user.id, draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except XAccountNotConnectedError:
        raise HTTPException(status_code=400, detail="X account not connected") from None
    except XAccountNeedsReauthError:
        raise HTTPException(
            status_code=401,
            detail="X session expired. Reconnect your account in Settings.",
        ) from None
    except XTokenRefreshError:
        raise HTTPException(
            status_code=401,
            detail="X session expired. Reconnect your account in Settings.",
        ) from None
    except XPublishForbiddenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except XPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except XRateLimitError as exc:
        headers = {}
        if exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=429,
            detail="X API rate limit exceeded. Try again later.",
            headers=headers,
        ) from None
    except DraftNotPublishableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _post_response(post)
