from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.reply_target import ReplyTarget


class ReplyTargetNotFoundError(Exception):
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
    conversation_context: list | None = None,
) -> ReplyTarget:
    handle = author_handle.lstrip("@")
    tweet_id = x_tweet_id or f"manual-{handle}-{len(tweet_text)}"
    target = ReplyTarget(
        user_id=user_id,
        x_tweet_id=tweet_id,
        x_user_id=x_user_id,
        author_handle=handle,
        tweet_text=tweet_text,
        conversation_context=conversation_context or [],
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


async def delete_reply_target(session: AsyncSession, user_id: UUID, target_id: UUID) -> None:
    target = await get_reply_target(session, user_id, target_id)
    await session.delete(target)
    await session.commit()
