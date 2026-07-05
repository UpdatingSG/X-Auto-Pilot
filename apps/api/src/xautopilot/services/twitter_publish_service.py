from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.content import Draft, DraftVariant
from xautopilot.models.published_post import PublishedPost
from xautopilot.services.draft_service import DraftNotFoundError, get_draft
from xautopilot.services.metrics_sync_service import schedule_metrics_sync_jobs
from xautopilot.services.x_account_service import XAccountNotFoundError, get_x_account
from xautopilot.services.x_client import (
    XApiError,
    XApiRateLimitError,
    XApiUnauthorizedError,
    XClient,
    get_x_client,
)
from xautopilot.services.x_token_service import (
    XAccountNeedsReauthError,
    XTokenRefreshError,
    get_valid_access_token,
    mark_account_needs_reauth,
)


class XRateLimitError(Exception):
    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("X API rate limit exceeded")


class XAccountNotConnectedError(Exception):
    pass


class DraftNotPublishableError(Exception):
    pass


class XPublishError(Exception):
    """X API rejected the publish request (non-auth)."""


class XPublishForbiddenError(XPublishError):
    pass


def _selected_variant(draft: Draft) -> DraftVariant | None:
    if not draft.variants:
        return None
    if draft.selected_variant_id:
        for variant in draft.variants:
            if variant.id == draft.selected_variant_id:
                return variant
    return draft.variants[0]


def _preview_text(draft: Draft) -> str | None:
    variant = _selected_variant(draft)
    return variant.content_text if variant else None


def _thread_tweets(draft: Draft) -> list[str]:
    variant = _selected_variant(draft)
    if variant is None or not variant.thread_tweets:
        return []
    tweets = sorted(variant.thread_tweets, key=lambda t: t.get("index", 0))
    return [str(t.get("text", "")).strip() for t in tweets if str(t.get("text", "")).strip()]


def _content_snapshot(draft: Draft) -> dict:
    variant = _selected_variant(draft)
    preview = _preview_text(draft)
    snapshot: dict = {
        "content_type": draft.content_type,
        "category": draft.category,
        "text": preview,
        "selected_variant_id": str(draft.selected_variant_id) if draft.selected_variant_id else None,
    }
    if draft.content_type == "thread" and variant and variant.thread_tweets:
        snapshot["thread_tweets"] = variant.thread_tweets
    if draft.content_type == "reply":
        metadata = draft.generation_metadata or {}
        if metadata.get("x_tweet_id"):
            snapshot["in_reply_to_tweet_id"] = metadata["x_tweet_id"]
    return snapshot


async def _publish_with_client(
    session: AsyncSession,
    user_id: UUID,
    client: XClient,
    publish_fn,
):
    try:
        access_token = await get_valid_access_token(session, user_id)
        return await publish_fn(access_token)
    except XAccountNeedsReauthError:
        raise
    except XTokenRefreshError:
        await mark_account_needs_reauth(session, user_id)
        raise XAccountNeedsReauthError from None
    except XApiUnauthorizedError:
        await mark_account_needs_reauth(session, user_id)
        raise XAccountNeedsReauthError from None
    except XApiRateLimitError as exc:
        raise XRateLimitError(exc.retry_after_seconds) from exc
    except XApiError as exc:
        if exc.status_code == 403:
            raise XPublishForbiddenError(str(exc)) from exc
        raise XPublishError(str(exc)) from exc


async def get_published_post_for_draft(
    session: AsyncSession, user_id: UUID, draft_id: UUID
) -> PublishedPost | None:
    result = await session.execute(
        select(PublishedPost).where(
            PublishedPost.user_id == user_id,
            PublishedPost.draft_id == draft_id,
        )
    )
    return result.scalar_one_or_none()


async def publish_draft(
    session: AsyncSession,
    user_id: UUID,
    draft_id: UUID,
    x_client: XClient | None = None,
) -> PublishedPost:
    existing = await get_published_post_for_draft(session, user_id, draft_id)
    if existing is not None:
        return existing

    try:
        await get_x_account(session, user_id)
    except XAccountNotFoundError as exc:
        raise XAccountNotConnectedError from exc

    draft = await get_draft(session, user_id, draft_id)
    if draft.status not in ("scheduled", "approved"):
        raise DraftNotPublishableError

    client = x_client or get_x_client()
    preview = _preview_text(draft)
    root_tweet_id: str
    thread_ids: list[str] | None = None

    if draft.content_type == "thread":
        tweets = _thread_tweets(draft)
        if len(tweets) < 2:
            raise DraftNotPublishableError
        if any(len(t) > 280 for t in tweets):
            raise DraftNotPublishableError
        preview = tweets[0]

        async def _post_thread(access_token: str):
            return await client.post_thread(access_token, tweets)

        result = await _publish_with_client(session, user_id, client, _post_thread)
        root_tweet_id = result.x_tweet_id
        thread_ids = result.thread_ids
    elif draft.content_type == "reply":
        text = preview
        if not text or len(text) > 280:
            raise DraftNotPublishableError
        in_reply_to = (draft.generation_metadata or {}).get("x_tweet_id")
        if not in_reply_to:
            raise DraftNotPublishableError

        async def _post_reply(access_token: str):
            return await client.post_reply(
                access_token, text, in_reply_to_tweet_id=str(in_reply_to)
            )

        result = await _publish_with_client(session, user_id, client, _post_reply)
        root_tweet_id = result.x_tweet_id
    else:
        text = preview
        if not text or len(text) > 280:
            raise DraftNotPublishableError

        async def _post_tweet(access_token: str):
            return await client.post_tweet(access_token, text)

        result = await _publish_with_client(session, user_id, client, _post_tweet)
        root_tweet_id = result.x_tweet_id

    snapshot = _content_snapshot(draft)
    if thread_ids:
        snapshot["thread_ids"] = thread_ids

    post = PublishedPost(
        user_id=user_id,
        draft_id=draft_id,
        x_tweet_id=root_tweet_id,
        content_type=draft.content_type,
        content_snapshot=snapshot,
        preview_text=preview,
    )
    draft.status = "published"
    session.add(post)
    await session.flush()
    await schedule_metrics_sync_jobs(session, post)
    await session.commit()
    await session.refresh(post)
    return post


async def list_published_posts(session: AsyncSession, user_id: UUID) -> list[PublishedPost]:
    result = await session.execute(
        select(PublishedPost)
        .where(PublishedPost.user_id == user_id)
        .order_by(PublishedPost.published_at.desc())
    )
    return list(result.scalars().all())
