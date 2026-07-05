from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.agents.prompts import (
    PROMPT_VERSION,
    planner_system_prompt,
    planner_user_prompt,
)
from xautopilot.services.llm_cost_service import ensure_llm_budget, record_llm_usage
from xautopilot.services.llm_service import LLMError, complete_json


@dataclass
class PlannedIdea:
    content_type: str
    category: str
    title: str
    hook_idea: str
    rationale: str
    reply_target_id: UUID | None = None


def thread_plan_days(threads_per_week: int) -> list[int]:
    """Spread thread days evenly across the week (Mon=0 .. Sun=6)."""
    if threads_per_week <= 0:
        return []
    if threads_per_week == 1:
        return [0]
    # e.g. 2/week → Mon+Sun, 3/week → Mon+Thu+Sun
    return sorted({round(i * 6 / (threads_per_week - 1)) for i in range(threads_per_week)})


def thread_day_names(threads_per_week: int) -> list[str]:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [names[d] for d in thread_plan_days(threads_per_week)]


def should_include_thread(plan_date: date, threads_per_week: int) -> bool:
    return plan_date.weekday() in thread_plan_days(threads_per_week)


def plan_slot_counts(
    plan_date: date,
    *,
    tweets_per_day: int,
    threads_per_week: int,
    replies_per_day: int,
    reply_target_count: int,
) -> dict[str, int]:
    thread_count = 1 if should_include_thread(plan_date, threads_per_week) else 0
    reply_count = min(replies_per_day, 3, reply_target_count) if reply_target_count else 0
    tweet_count = max(1, tweets_per_day - thread_count)
    return {
        "tweet_count": tweet_count,
        "thread_count": thread_count,
        "reply_count": reply_count,
        "total": tweet_count + thread_count + reply_count,
    }


def _enforce_plan_composition(
    ideas: list[PlannedIdea],
    *,
    tweet_count: int,
    thread_count: int,
    reply_count: int,
    reply_targets: list[dict],
) -> list[PlannedIdea]:
    """Force content_type by slot so the LLM cannot return all tweets."""
    expected = tweet_count + thread_count + reply_count
    if len(ideas) < expected:
        raise LLMError(f"Expected {expected} ideas, got {len(ideas)}")

    enforced: list[PlannedIdea] = []
    idx = 0

    for _ in range(tweet_count):
        idea = ideas[idx]
        enforced.append(
            PlannedIdea(
                content_type="tweet",
                category=idea.category,
                title=idea.title,
                hook_idea=idea.hook_idea,
                rationale=idea.rationale,
            )
        )
        idx += 1

    for _ in range(thread_count):
        idea = ideas[idx]
        enforced.append(
            PlannedIdea(
                content_type="thread",
                category=idea.category if idea.category != "engagement" else "educational",
                title=idea.title,
                hook_idea=idea.hook_idea,
                rationale=idea.rationale,
            )
        )
        idx += 1

    for i in range(reply_count):
        idea = ideas[idx]
        target = reply_targets[i] if i < len(reply_targets) else None
        enforced.append(
            PlannedIdea(
                content_type="reply",
                category="engagement",
                title=f"Reply to @{target['author_handle']}" if target else idea.title,
                hook_idea=target["tweet_text"][:120] if target else idea.hook_idea,
                rationale=idea.rationale or "Engage with relevant conversation in your niche",
                reply_target_id=UUID(target["id"]) if target and target.get("id") else None,
            )
        )
        idx += 1

    return enforced


def _template_plan(
    profession: str,
    interests: list[str],
    knowledge_titles: list[str],
    tweet_count: int,
    thread_count: int,
    reply_count: int,
    reply_targets: list[dict],
) -> list[PlannedIdea]:
    topics = interests[:3] or ["engineering"]
    ideas: list[PlannedIdea] = []

    for i in range(tweet_count):
        topic = topics[i % len(topics)]
        news = knowledge_titles[i % len(knowledge_titles)] if knowledge_titles else None
        ideas.append(
            PlannedIdea(
                content_type="tweet",
                category=["engineering", "hot_take", "educational"][i % 3],
                title=f"{topic} insight #{i + 1}",
                hook_idea=f"Contrarian take on {topic}",
                rationale=f"Trending: {news}" if news else f"Core expertise: {topic}",
            )
        )

    for i in range(thread_count):
        topic = topics[i % len(topics)]
        ideas.append(
            PlannedIdea(
                content_type="thread",
                category="educational",
                title=f"Deep dive: {topic}",
                hook_idea=f"A thread on what most people get wrong about {topic}",
                rationale="Weekly thread for depth and dwell time",
            )
        )

    for i, target in enumerate(reply_targets[:reply_count]):
        ideas.append(
            PlannedIdea(
                content_type="reply",
                category="engagement",
                title=f"Reply to @{target['author_handle']}",
                hook_idea=target["tweet_text"][:120],
                rationale="Engage with relevant conversation in your niche",
                reply_target_id=UUID(target["id"]) if target.get("id") else None,
            )
        )

    return ideas


def _safe_uuid(value: str | None) -> UUID | None:
    if not value or value in ("null", "none", "None"):
        return None
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _parse_planned_ideas(data: dict, expected_count: int) -> list[PlannedIdea]:
    raw = data.get("ideas", [])
    ideas: list[PlannedIdea] = []
    for item in raw[:expected_count]:
        ideas.append(
            PlannedIdea(
                content_type=item.get("content_type", "tweet"),
                category=item.get("category", "engineering"),
                title=str(item.get("title", "Untitled idea")),
                hook_idea=str(item.get("hook_idea", "")),
                rationale=str(item.get("rationale", "")),
                reply_target_id=_safe_uuid(item.get("reply_target_id")),
            )
        )
    if len(ideas) < expected_count:
        raise LLMError(f"Expected {expected_count} ideas, got {len(ideas)}")
    return ideas


async def plan_daily_content(
    profession: str,
    interests: list[str],
    knowledge_titles: list[str],
    *,
    tweets_per_day: int = 3,
    threads_per_week: int = 2,
    replies_per_day: int = 2,
    plan_date: date | None = None,
    reply_targets: list[dict] | None = None,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
    tone: list[str] | None = None,
    never_discuss: list[str] | None = None,
) -> tuple[list[PlannedIdea], dict]:
    plan_date = plan_date or date.today()
    reply_targets = reply_targets or []

    slots = plan_slot_counts(
        plan_date,
        tweets_per_day=tweets_per_day,
        threads_per_week=threads_per_week,
        replies_per_day=replies_per_day,
        reply_target_count=len(reply_targets),
    )
    tweet_count = slots["tweet_count"]
    thread_count = slots["thread_count"]
    reply_count = slots["reply_count"]
    total = slots["total"]

    base_metadata = {
        "tweet_count": tweet_count,
        "thread_count": thread_count,
        "reply_count": reply_count,
        "is_thread_day": thread_count > 0,
        "thread_days": thread_day_names(threads_per_week),
        "reply_targets_available": len(reply_targets),
        "prompt_version": PROMPT_VERSION,
    }

    if settings.llm_mode == "mock":
        return _template_plan(
            profession,
            interests,
            knowledge_titles,
            tweet_count,
            thread_count,
            reply_count,
            reply_targets,
        ), {**base_metadata, "llm_mode": "mock"}

    if session is None or user_id is None:
        raise LLMError("session and user_id are required for live LLM mode")

    await ensure_llm_budget(session, user_id)
    completion = await complete_json(
        planner_system_prompt(),
        planner_user_prompt(
            profession=profession,
            interests=interests,
            knowledge_titles=knowledge_titles,
            tweet_count=tweet_count,
            thread_count=thread_count,
            reply_count=reply_count,
            reply_targets=reply_targets,
            tone=tone or [],
            never_discuss=never_discuss or [],
        ),
        prompt_version=PROMPT_VERSION,
    )
    ideas = _parse_planned_ideas(completion.data, total)
    ideas = _enforce_plan_composition(
        ideas,
        tweet_count=tweet_count,
        thread_count=thread_count,
        reply_count=reply_count,
        reply_targets=reply_targets,
    )
    await record_llm_usage(session, user_id, completion.usage)

    metadata = {
        **base_metadata,
        "llm_mode": "live",
        "model": completion.usage.model,
    }
    return ideas, metadata
