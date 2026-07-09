from dataclasses import asdict

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.reply_target import (
    DiscoverReplyTargetsRequest,
    DiscoverReplyTargetsResponse,
    DiscoveredReplyTarget,
    ImportReplyTargetsRequest,
    ImportReplyTargetsResponse,
    ReplyTargetCreate,
    ReplyTargetFromUrlRequest,
    ReplyTargetResponse,
    ReplyTargetUpdateTweetId,
)
from xautopilot.services.reply_discovery_service import (
    ReplyDiscoveryError,
    discover_from_watchlist,
    discover_reply_targets,
    import_discovered_targets,
    lookup_reply_target_from_url,
)
from xautopilot.services.quote_discovery_service import discover_quote_opportunities
from xautopilot.services.reply_target_service import (
    InvalidReplyTargetError,
    ReplyTargetNotFoundError,
    create_reply_target,
    delete_reply_target,
    list_reply_targets,
    update_reply_target_tweet_id,
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
    try:
        target = await create_reply_target(
            db,
            current_user.id,
            author_handle=data.author_handle,
            tweet_text=data.tweet_text,
            x_tweet_id=data.x_tweet_id,
            x_user_id=data.x_user_id or "unknown",
        )
    except InvalidReplyTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ReplyTargetResponse.model_validate(target)


@router.post("/discover", response_model=DiscoverReplyTargetsResponse)
async def discover_targets(
    data: DiscoverReplyTargetsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await discover_reply_targets(
            db,
            current_user.id,
            min_followers=data.min_followers,
            limit=data.limit,
            topics=data.topics,
        )
    except ReplyDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return DiscoverReplyTargetsResponse(
        source=result.source,
        message=result.message,
        targets=[DiscoveredReplyTarget.model_validate(asdict(t)) for t in result.targets],
    )


@router.post("/discover/watchlist", response_model=DiscoverReplyTargetsResponse)
async def discover_watchlist_targets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await discover_from_watchlist(db, current_user.id, limit=10)
    except ReplyDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return DiscoverReplyTargetsResponse(
        source=result.source,
        message=result.message,
        targets=[DiscoveredReplyTarget.model_validate(asdict(t)) for t in result.targets],
    )


@router.post("/discover/quotes", response_model=DiscoverReplyTargetsResponse)
async def discover_quote_targets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await discover_quote_opportunities(db, current_user.id, limit=5)
    return DiscoverReplyTargetsResponse(
        source=result.source,
        message=result.message,
        targets=[DiscoveredReplyTarget.model_validate(asdict(t)) for t in result.targets],
    )


@router.post("/discover/import", response_model=ImportReplyTargetsResponse)
async def import_targets(
    data: ImportReplyTargetsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from xautopilot.services.x_client import DiscoveredTweet

    discovered = [DiscoveredTweet(**t.model_dump()) for t in data.targets]
    created = await import_discovered_targets(db, current_user.id, discovered)
    return ImportReplyTargetsResponse(
        imported=len(created),
        targets=[ReplyTargetResponse.model_validate(t) for t in created],
    )


@router.post("/from-url", response_model=DiscoveredReplyTarget)
async def reply_target_from_url(
    data: ReplyTargetFromUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tweet = await lookup_reply_target_from_url(db, current_user.id, data.url)
    except ReplyDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return DiscoveredReplyTarget.model_validate(asdict(tweet))


@router.post("/from-url/import", response_model=ReplyTargetResponse, status_code=status.HTTP_201_CREATED)
async def import_reply_target_from_url(
    data: ReplyTargetFromUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from xautopilot.services.x_client import DiscoveredTweet

    try:
        tweet = await lookup_reply_target_from_url(db, current_user.id, data.url)
    except ReplyDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    created = await import_discovered_targets(
        db,
        current_user.id,
        [DiscoveredTweet(**tweet.__dict__)],
    )
    if not created:
        raise HTTPException(status_code=409, detail="This tweet is already in your reply targets")
    return ReplyTargetResponse.model_validate(created[0])


@router.patch("/{target_id}", response_model=ReplyTargetResponse)
async def patch_reply_target_tweet_id(
    target_id: UUID,
    data: ReplyTargetUpdateTweetId,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        target = await update_reply_target_tweet_id(
            db, current_user.id, target_id, data.x_tweet_id
        )
    except ReplyTargetNotFoundError:
        raise HTTPException(status_code=404, detail="Reply target not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
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
