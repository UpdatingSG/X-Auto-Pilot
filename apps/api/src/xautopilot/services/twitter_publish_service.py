from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.config import settings
from xautopilot.models.content import Draft, DraftVariant
from xautopilot.models.published_post import PublishedPost
from xautopilot.services.draft_service import DraftNotFoundError, get_draft
from xautopilot.services.reply_target_service import (
    ReplyTargetNotFoundError,
    get_reply_target,
    target_can_reply,
    target_is_publishable,
    target_reply_block_reason,
)
from xautopilot.services.reply_eligibility_service import humanize_x_reply_error
from xautopilot.services.metrics_sync_service import schedule_metrics_sync_jobs
from xautopilot.services.x_account_service import XAccountNotFoundError, get_x_account
from xautopilot.services.x_client import (
    XApiError,
    XApiRateLimitError,
    XApiUnauthorizedError,
    XClient,
    get_x_client,
)
from xautopilot.services.x_tweet_id import is_valid_x_tweet_id
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
    def __init__(self, message: str = "Draft cannot be published"):
        super().__init__(message)


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
    if draft.content_type == "quote_tweet":
        metadata = draft.generation_metadata or {}
        if metadata.get("quote_tweet_id"):
            snapshot["quote_tweet_id"] = metadata["quote_tweet_id"]
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
            raise XPublishForbiddenError(humanize_x_reply_error(str(exc))) from exc
        raise XPublishError(humanize_x_reply_error(str(exc))) from exc


async def _ensure_reply_allowed(
    session: AsyncSession,
    user_id: UUID,
    *,
    in_reply_to: str,
    reply_target=None,
) -> None:
    if settings.x_api_mode == "mock":
        return

    if reply_target is not None and not target_can_reply(reply_target):
        reason = target_reply_block_reason(reply_target)
        raise DraftNotPublishableError(
            reason
            or "X will block this reply because of the author's reply settings. Try a quote-tweet instead."
        )

    account = await get_x_account(session, user_id)
    client = get_x_client()
    access_token = await get_valid_access_token(session, user_id)
    tweet = await client.lookup_tweet(
        access_token, in_reply_to, viewer_x_user_id=account.x_user_id
    )
    if not tweet.reply_allowed:
        raise DraftNotPublishableError(
            tweet.reply_block_reason
            or "X will block this reply because of the author's reply settings. Try a quote-tweet instead."
        )


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
        metadata = draft.generation_metadata or {}
        in_reply_to = metadata.get("x_tweet_id")
        reply_target_id = metadata.get("reply_target_id")
        reply_target = None
        if reply_target_id:
            try:
                reply_target = await get_reply_target(session, user_id, UUID(str(reply_target_id)))
                if target_is_publishable(reply_target):
                    in_reply_to = reply_target.x_tweet_id
                    metadata["x_tweet_id"] = reply_target.x_tweet_id
                    draft.generation_metadata = metadata
                    await session.flush()
            except (ReplyTargetNotFoundError, ValueError):
                reply_target = None
        if not is_valid_x_tweet_id(str(in_reply_to or "")):
            raise DraftNotPublishableError(
                "Reply target is missing a valid numeric X tweet ID. "
                "Re-import the post via URL on the Engagement page, or add the tweet ID from the post URL."
            )

        await _ensure_reply_allowed(
            session, user_id, in_reply_to=str(in_reply_to), reply_target=reply_target
        )

        async def _post_reply(access_token: str):
            return await client.post_reply(
                access_token, text, in_reply_to_tweet_id=str(in_reply_to)
            )

        result = await _publish_with_client(session, user_id, client, _post_reply)
        root_tweet_id = result.x_tweet_id
    elif draft.content_type == "quote_tweet":
        text = preview
        if not text or len(text) > 280:
            raise DraftNotPublishableError
        metadata = draft.generation_metadata or {}
        quote_id = metadata.get("quote_tweet_id") or metadata.get("x_tweet_id")
        reply_target_id = metadata.get("reply_target_id")
        if reply_target_id and not is_valid_x_tweet_id(str(quote_id or "")):
            try:
                target = await get_reply_target(session, user_id, UUID(str(reply_target_id)))
                quote_id = target.x_tweet_id
            except (ReplyTargetNotFoundError, ValueError):
                pass
        if not is_valid_x_tweet_id(str(quote_id or "")):
            raise DraftNotPublishableError("Quote target is missing a valid numeric X tweet ID.")

        async def _post_quote(access_token: str):
            return await client.post_quote_tweet(
                access_token, text, quote_tweet_id=str(quote_id)
            )

        result = await _publish_with_client(session, user_id, client, _post_quote)
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
