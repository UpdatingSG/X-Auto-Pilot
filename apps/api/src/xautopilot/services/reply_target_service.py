from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.reply_target import ReplyTarget
from xautopilot.services.reply_eligibility_service import reply_meta_from_context
from xautopilot.services.x_tweet_id import is_valid_x_tweet_id, normalize_x_tweet_id


def _reply_context_metadata(
    *,
    reply_allowed: bool = True,
    reply_block_reason: str | None = None,
    reply_settings: str | None = None,
) -> dict:
    return {
        "reply_allowed": reply_allowed,
        "reply_block_reason": reply_block_reason,
        "reply_settings": reply_settings,
    }


class ReplyTargetNotFoundError(Exception):
    pass


class InvalidReplyTargetError(Exception):
    pass


async def list_reply_targets(session: AsyncSession, user_id: UUID) -> list[ReplyTarget]:
    result = await session.execute(
        select(ReplyTarget)
        .where(ReplyTarget.user_id == user_id)
        .order_by(ReplyTarget.discovered_at.desc())
    )
    return list(result.scalars().all())


async def list_active_reply_targets(session: AsyncSession, user_id: UUID) -> list[ReplyTarget]:
    now = datetime.now(UTC)
    targets = await list_reply_targets(session, user_id)
    active: list[ReplyTarget] = []
    for target in targets:
        if target.expires_at is None:
            active.append(target)
            continue
        expires = target.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires > now:
            active.append(target)
    return active


async def create_reply_target(
    session: AsyncSession,
    user_id: UUID,
    *,
    author_handle: str,
    tweet_text: str,
    x_tweet_id: str | None = None,
    x_user_id: str = "unknown",
    conversation_context: dict | list | None = None,
) -> ReplyTarget:
    handle = author_handle.lstrip("@")
    if not x_tweet_id or not is_valid_x_tweet_id(x_tweet_id):
        raise InvalidReplyTargetError(
            "A numeric X tweet ID is required (from the post URL) to publish replies."
        )
    tweet_id = normalize_x_tweet_id(x_tweet_id)
    target = ReplyTarget(
        user_id=user_id,
        x_tweet_id=tweet_id,
        x_user_id=x_user_id,
        author_handle=handle,
        tweet_text=tweet_text,
        conversation_context=conversation_context
        if conversation_context is not None
        else _reply_context_metadata(),
        expires_at=datetime.now(UTC) + timedelta(hours=48),
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return target


async def get_reply_target(session: AsyncSession, user_id: UUID, target_id: UUID) -> ReplyTarget:
    result = await session.execute(
        select(ReplyTarget).where(ReplyTarget.id == target_id, ReplyTarget.user_id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise ReplyTargetNotFoundError
    return target


async def update_reply_target_tweet_id(
    session: AsyncSession,
    user_id: UUID,
    target_id: UUID,
    x_tweet_id: str,
) -> ReplyTarget:
    target = await get_reply_target(session, user_id, target_id)
    target.x_tweet_id = normalize_x_tweet_id(x_tweet_id)
    await session.commit()
    await session.refresh(target)
    return target


async def delete_reply_target(session: AsyncSession, user_id: UUID, target_id: UUID) -> None:
    target = await get_reply_target(session, user_id, target_id)
    await session.delete(target)
    await session.commit()


async def repair_reply_target_from_url(
    session: AsyncSession,
    user_id: UUID,
    target_id: UUID,
    url: str,
) -> ReplyTarget:
    """Re-fetch tweet ID and text from an X post URL — fixes stale manual targets."""
    from xautopilot.services.reply_discovery_service import (
        ReplyDiscoveryError,
        lookup_reply_target_from_url,
    )

    target = await get_reply_target(session, user_id, target_id)
    try:
        tweet = await lookup_reply_target_from_url(session, user_id, url)
    except ReplyDiscoveryError as exc:
        raise InvalidReplyTargetError(str(exc)) from exc

    target.x_tweet_id = normalize_x_tweet_id(tweet.x_tweet_id)
    target.x_user_id = tweet.x_user_id
    target.author_handle = tweet.author_handle.lstrip("@")
    if tweet.tweet_text.strip():
        target.tweet_text = tweet.tweet_text
    target.conversation_context = _reply_context_metadata(
        reply_allowed=tweet.reply_allowed,
        reply_block_reason=tweet.reply_block_reason,
        reply_settings=tweet.reply_settings,
    )
    target.expires_at = datetime.now(UTC) + timedelta(hours=48)
    await session.commit()
    await session.refresh(target)
    return target


def target_is_publishable(target: ReplyTarget) -> bool:
    return is_valid_x_tweet_id(target.x_tweet_id)


def target_can_reply(target: ReplyTarget) -> bool:
    meta = reply_meta_from_context(target.conversation_context)
    if "reply_allowed" in meta:
        return bool(meta["reply_allowed"])
    return True


def target_reply_block_reason(target: ReplyTarget) -> str | None:
    meta = reply_meta_from_context(target.conversation_context)
    reason = meta.get("reply_block_reason")
    return str(reason) if reason else None


def to_reply_target_response(target: ReplyTarget):
    from xautopilot.schemas.reply_target import ReplyTargetResponse

    return ReplyTargetResponse(
        id=target.id,
        author_handle=target.author_handle,
        tweet_text=target.tweet_text,
        x_tweet_id=target.x_tweet_id,
        x_user_id=target.x_user_id,
        relevance_score=target.relevance_score,
        discovered_at=target.discovered_at,
        expires_at=target.expires_at,
        reply_allowed=target_can_reply(target),
        reply_block_reason=target_reply_block_reason(target),
    )
