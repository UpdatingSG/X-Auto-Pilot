from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xautopilot.models.content import ContentIdea, ContentPlan
from xautopilot.services.agents.content_planner import (
    plan_daily_content,
    plan_slot_counts,
    thread_day_names,
)
from xautopilot.services.ingestion_service import list_knowledge_items
from xautopilot.services.reply_target_service import list_active_reply_targets
from xautopilot.services.schedule_service import get_schedule
from xautopilot.services.voice_profile_service import get_active_voice_profile


class PlanNotFoundError(Exception):
    pass


class IdeaNotFoundError(Exception):
    pass


async def get_plan_composition(
    session: AsyncSession,
    user_id: UUID,
    plan: ContentPlan,
) -> dict:
    schedule = await get_schedule(session, user_id)
    targets = await list_active_reply_targets(session, user_id)
    slots = plan_slot_counts(
        plan.plan_date,
        tweets_per_day=schedule.tweets_per_day,
        threads_per_week=schedule.threads_per_week,
        replies_per_day=min(schedule.replies_per_day, 3),
        reply_target_count=len(targets),
    )

    counts = {"tweet": 0, "thread": 0, "reply": 0}
    for idea in plan.ideas:
        if idea.content_type in counts:
            counts[idea.content_type] += 1

    hints: list[str] = []
    if slots["thread_count"] == 0 and schedule.threads_per_week > 0:
        days = ", ".join(thread_day_names(schedule.threads_per_week))
        hints.append(f"No thread today — thread days are {days}.")
    if slots["reply_count"] == 0:
        if len(targets) == 0:
            hints.append("No replies — add reply targets on the Engagement page.")
        else:
            hints.append("Reply slots full or capped for today.")
    if counts["thread"] == 0 and counts["reply"] == 0 and counts["tweet"] == len(plan.ideas):
        if slots["thread_count"] > 0 or slots["reply_count"] > 0:
            hints.append("Regenerate the plan — this one was created before mixed planning or without reply targets.")
        else:
            hints.append("Today's plan is tweets-only based on your schedule.")

    return {
        "tweets": counts["tweet"],
        "threads": counts["thread"],
        "replies": counts["reply"],
        "thread_days": thread_day_names(schedule.threads_per_week),
        "is_thread_day": slots["thread_count"] > 0,
        "reply_targets_available": len(targets),
        "hints": hints,
    }


async def get_plan_for_date(
    session: AsyncSession, user_id: UUID, plan_date: date
) -> ContentPlan | None:
    result = await session.execute(
        select(ContentPlan)
        .options(selectinload(ContentPlan.ideas))
        .where(ContentPlan.user_id == user_id, ContentPlan.plan_date == plan_date)
    )
    return result.scalar_one_or_none()


async def generate_daily_plan(
    session: AsyncSession,
    user_id: UUID,
    plan_date: date,
    *,
    force: bool = False,
) -> ContentPlan:
    existing = await get_plan_for_date(session, user_id, plan_date)
    if existing:
        if not force:
            return existing
        await session.delete(existing)
        await session.flush()

    voice = await get_active_voice_profile(session, user_id)
    interests = [i["topic"] for i in (voice.interests if voice else [])]
    profession = voice.profession if voice else "Creator"

    items = await list_knowledge_items(session, user_id)
    titles = [item.title for item in items[:10]]
    schedule = await get_schedule(session, user_id)
    targets = await list_active_reply_targets(session, user_id)
    target_payload = [
        {
            "id": str(t.id),
            "author_handle": t.author_handle,
            "tweet_text": t.tweet_text,
        }
        for t in targets
    ]

    planned, _metadata = await plan_daily_content(
        profession,
        interests,
        titles,
        tweets_per_day=schedule.tweets_per_day,
        threads_per_week=schedule.threads_per_week,
        replies_per_day=min(schedule.replies_per_day, 3),
        plan_date=plan_date,
        reply_targets=target_payload,
        session=session,
        user_id=user_id,
        tone=voice.tone if voice else [],
        never_discuss=voice.never_discuss if voice else [],
    )

    plan = ContentPlan(user_id=user_id, plan_date=plan_date, status="ready")
    session.add(plan)
    await session.flush()

    for idea in planned:
        session.add(
            ContentIdea(
                plan_id=plan.id,
                user_id=user_id,
                content_type=idea.content_type,
                category=idea.category,
                title=idea.title,
                hook_idea=idea.hook_idea,
                rationale=idea.rationale,
                reply_target_id=idea.reply_target_id,
            )
        )

    await session.commit()
    result = await session.execute(
        select(ContentPlan)
        .options(selectinload(ContentPlan.ideas))
        .where(ContentPlan.id == plan.id)
    )
    return result.scalar_one()


async def update_idea_status(
    session: AsyncSession, user_id: UUID, plan_id: UUID, idea_id: UUID, status: str
) -> ContentIdea:
    result = await session.execute(
        select(ContentIdea).where(
            ContentIdea.id == idea_id,
            ContentIdea.plan_id == plan_id,
            ContentIdea.user_id == user_id,
        )
    )
    idea = result.scalar_one_or_none()
    if idea is None:
        raise IdeaNotFoundError
    idea.status = status
    await session.commit()
    await session.refresh(idea)
    return idea
