from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.content import ContentIdea, Draft, DraftVariant
from xautopilot.services.agents.quote_agent import generate_quote_variations
from xautopilot.services.agents.reply_agent import generate_reply_variations
from xautopilot.services.agents.thread_writer import generate_thread_variations
from xautopilot.services.agents.tweet_writer import generate_tweet_variations
from xautopilot.services.content_plan_service import IdeaNotFoundError
from xautopilot.services.reply_target_service import ReplyTargetNotFoundError, get_reply_target
from xautopilot.services.voice_profile_service import get_active_voice_profile


class DraftNotFoundError(Exception):
    pass


class IdeaNotApprovedError(Exception):
    pass


async def _save_variants(
    session: AsyncSession,
    draft: Draft,
    *,
    tweet_variants: list | None = None,
    thread_variants: list | None = None,
    reply_variants: list | None = None,
    quote_variants: list | None = None,
) -> None:
    if tweet_variants is not None:
        for i, variant in enumerate(tweet_variants):
            session.add(
                DraftVariant(
                    draft_id=draft.id,
                    variant_index=i,
                    content_text=variant.text,
                    scores=variant.scores,
                    is_selected=i == 0,
                )
            )
    elif thread_variants is not None:
        for i, variant in enumerate(thread_variants):
            session.add(
                DraftVariant(
                    draft_id=draft.id,
                    variant_index=i,
                    content_text=variant.preview_text,
                    thread_tweets=variant.thread_tweets,
                    scores=variant.scores,
                    is_selected=i == 0,
                )
            )
    elif reply_variants is not None:
        for i, variant in enumerate(reply_variants):
            session.add(
                DraftVariant(
                    draft_id=draft.id,
                    variant_index=i,
                    content_text=variant.text,
                    scores=variant.scores,
                    is_selected=i == 0,
                )
            )
    elif quote_variants is not None:
        for i, variant in enumerate(quote_variants):
            session.add(
                DraftVariant(
                    draft_id=draft.id,
                    variant_index=i,
                    content_text=variant.text,
                    scores=variant.scores,
                    is_selected=i == 0,
                )
            )


async def _maybe_auto_schedule_reply(session: AsyncSession, user_id: UUID, draft: Draft) -> Draft:
    from xautopilot.services.publish_service import schedule_draft
    from xautopilot.services.schedule_service import get_schedule

    schedule = await get_schedule(session, user_id)
    if draft.content_type != "reply" or not schedule.auto_schedule_replies:
        return draft
    if not draft.variants:
        return draft
    best = draft.variants[0]
    draft.selected_variant_id = best.id
    for variant in draft.variants:
        variant.is_selected = variant.id == best.id
    draft.status = "approved"
    await session.flush()
    try:
        await schedule_draft(session, user_id, draft.id)
    except Exception:
        await session.commit()
    return await get_draft(session, user_id, draft.id)


async def generate_draft_from_idea(
    session: AsyncSession, user_id: UUID, idea_id: UUID
) -> Draft:
    result = await session.execute(
        select(ContentIdea).where(ContentIdea.id == idea_id, ContentIdea.user_id == user_id)
    )
    idea = result.scalar_one_or_none()
    if idea is None:
        raise IdeaNotFoundError
    if idea.status != "approved":
        raise IdeaNotApprovedError

    voice = await get_active_voice_profile(session, user_id)
    avoid = voice.vocabulary.get("avoid", []) if voice else []
    profession = voice.profession if voice else "Creator"
    tone = voice.tone if voice else []
    hashtag_prefs = voice.hashtag_prefs if voice else {"max_per_tweet": 1, "favorites": []}
    max_hashtags = min(int(hashtag_prefs.get("max_per_tweet", 1)), 2)
    favorite_hashtags = list(hashtag_prefs.get("favorites", []))

    draft = Draft(
        user_id=user_id,
        idea_id=idea.id,
        content_type=idea.content_type,
        category=idea.category,
        status="generating",
    )
    session.add(draft)
    await session.flush()

    if idea.content_type == "thread":
        from xautopilot.services.analytics_service import build_bookmark_hints

        bookmark_hints = await build_bookmark_hints(session, user_id)
        variations, metadata = await generate_thread_variations(
            title=idea.title,
            hook_idea=idea.hook_idea or "",
            profession=profession,
            vocabulary_avoid=avoid,
            session=session,
            user_id=user_id,
            category=idea.category,
            tone=tone,
            max_hashtags=max_hashtags,
            favorite_hashtags=favorite_hashtags,
            bookmark_hints=bookmark_hints,
        )
        await _save_variants(session, draft, thread_variants=variations)
    elif idea.content_type == "reply":
        if not idea.reply_target_id:
            raise IdeaNotFoundError
        target = await get_reply_target(session, user_id, idea.reply_target_id)
        variations, metadata = await generate_reply_variations(
            author_handle=target.author_handle,
            target_tweet=target.tweet_text,
            profession=profession,
            vocabulary_avoid=avoid,
            session=session,
            user_id=user_id,
            tone=tone,
        )
        metadata["reply_target_id"] = str(target.id)
        metadata["x_tweet_id"] = target.x_tweet_id
        await _save_variants(session, draft, reply_variants=variations)
    elif idea.content_type == "quote_tweet":
        if not idea.reply_target_id:
            raise IdeaNotFoundError
        target = await get_reply_target(session, user_id, idea.reply_target_id)
        variations, metadata = await generate_quote_variations(
            author_handle=target.author_handle,
            target_tweet=target.tweet_text,
            profession=profession,
            vocabulary_avoid=avoid,
            session=session,
            user_id=user_id,
            tone=tone,
        )
        metadata["reply_target_id"] = str(target.id)
        metadata["quote_tweet_id"] = target.x_tweet_id
        await _save_variants(session, draft, quote_variants=variations)
    else:
        variations, metadata = await generate_tweet_variations(
            title=idea.title,
            hook_idea=idea.hook_idea or "",
            profession=profession,
            vocabulary_avoid=avoid,
            session=session,
            user_id=user_id,
            category=idea.category,
            tone=tone,
            max_hashtags=max_hashtags,
            favorite_hashtags=favorite_hashtags,
        )
        await _save_variants(session, draft, tweet_variants=variations)

    draft.generation_metadata = metadata
    draft.status = "ready"
    idea.status = "generated"
    await session.commit()

    return await get_draft(session, user_id, draft.id)


async def generate_reply_draft_from_target(
    session: AsyncSession, user_id: UUID, target_id: UUID
) -> Draft:
    try:
        target = await get_reply_target(session, user_id, target_id)
    except ReplyTargetNotFoundError as exc:
        raise IdeaNotFoundError from exc

    voice = await get_active_voice_profile(session, user_id)
    avoid = voice.vocabulary.get("avoid", []) if voice else []
    profession = voice.profession if voice else "Creator"
    tone = voice.tone if voice else []

    draft = Draft(
        user_id=user_id,
        content_type="reply",
        category="engagement",
        status="generating",
    )
    session.add(draft)
    await session.flush()

    variations, metadata = await generate_reply_variations(
        author_handle=target.author_handle,
        target_tweet=target.tweet_text,
        profession=profession,
        vocabulary_avoid=avoid,
        session=session,
        user_id=user_id,
        tone=tone,
    )
    metadata["reply_target_id"] = str(target.id)
    metadata["x_tweet_id"] = target.x_tweet_id
    draft.generation_metadata = metadata
    await _save_variants(session, draft, reply_variants=variations)

    draft.status = "ready"
    await session.commit()
    draft = await get_draft(session, user_id, draft.id)
    return await _maybe_auto_schedule_reply(session, user_id, draft)


async def get_draft(session: AsyncSession, user_id: UUID, draft_id: UUID) -> Draft:
    result = await session.execute(
        select(Draft)
        .options(selectinload(Draft.variants))
        .where(Draft.id == draft_id, Draft.user_id == user_id)
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise DraftNotFoundError
    return draft


async def list_drafts(
    session: AsyncSession, user_id: UUID, status: str | None = None
) -> list[Draft]:
    query = (
        select(Draft)
        .options(selectinload(Draft.variants))
        .where(Draft.user_id == user_id)
        .order_by(Draft.created_at.desc())
    )
    if status:
        query = query.where(Draft.status == status)
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_draft(
    session: AsyncSession,
    user_id: UUID,
    draft_id: UUID,
    status: str | None,
    selected_variant_id: UUID | None,
) -> Draft:
    draft = await get_draft(session, user_id, draft_id)

    if selected_variant_id:
        draft.selected_variant_id = selected_variant_id
        for v in draft.variants:
            v.is_selected = v.id == selected_variant_id

    if status:
        draft.status = status

    await session.commit()
    await session.refresh(draft)
    return draft
