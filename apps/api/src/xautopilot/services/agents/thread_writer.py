from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.agents.prompts import (
    PROMPT_VERSION,
    thread_writer_system_prompt,
    thread_writer_user_prompt,
)
from xautopilot.services.llm_cost_service import ensure_llm_budget, record_llm_usage
from xautopilot.services.llm_service import LLMError, complete_json


@dataclass
class ThreadVariant:
    hook_type: str
    thread_tweets: list[dict]
    scores: dict[str, float]
    preview_text: str


def _template_thread(title: str, hook_idea: str, profession: str, count: int) -> list[ThreadVariant]:
    base_tweets = [
        f"Most people misunderstand {title.lower()}. Here's what I've learned as a {profession}:",
        f"First: {hook_idea}",
        "The mistake is optimizing too early before you understand the bottleneck.",
        "Start with observability — htop, logs, and one metric that matters.",
        "Second: simplify before you scale. Complexity is rarely the answer.",
        "I learned this the hard way on a production incident last year.",
        "If this helped, follow for more backend/system design notes.",
    ]
    variants: list[ThreadVariant] = []
    for i in range(count):
        tweets = [{"index": j, "text": t[:280]} for j, t in enumerate(base_tweets)]
        variants.append(
            ThreadVariant(
                hook_type=["story", "educational"][i % 2],
                thread_tweets=tweets,
                preview_text=tweets[0]["text"],
                scores={
                    "hook_strength": 0.88 - i * 0.04,
                    "voice_match": 0.9,
                    "authenticity": 0.87,
                    "overall": 0.89 - i * 0.03,
                },
            )
        )
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


def _parse_variants(data: dict, count: int) -> list[ThreadVariant]:
    raw = data.get("variants", [])
    variants: list[ThreadVariant] = []
    for item in raw[:count]:
        tweets = item.get("thread_tweets", [])
        normalized = [
            {"index": t.get("index", i), "text": str(t.get("text", ""))[:280]}
            for i, t in enumerate(tweets)
        ]
        if len(normalized) < 3:
            raise LLMError("Thread must have at least 3 tweets")
        preview = normalized[0]["text"]
        scores = item.get("scores", {})
        variants.append(
            ThreadVariant(
                hook_type=str(item.get("hook_type", "story")),
                thread_tweets=normalized,
                preview_text=preview,
                scores={
                    "hook_strength": float(scores.get("hook_strength", 0.8)),
                    "voice_match": float(scores.get("voice_match", 0.8)),
                    "authenticity": float(scores.get("authenticity", 0.8)),
                    "overall": float(scores.get("overall", 0.8)),
                },
            )
        )
    if len(variants) < count:
        raise LLMError(f"Expected {count} thread variants, got {len(variants)}")
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


async def generate_thread_variations(
    title: str,
    hook_idea: str,
    profession: str,
    vocabulary_avoid: list[str],
    count: int = 2,
    *,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
    category: str = "educational",
    tone: list[str] | None = None,
) -> tuple[list[ThreadVariant], dict]:
    if settings.llm_mode == "mock":
        return _template_thread(title, hook_idea, profession, count), {
            "llm_mode": "mock",
            "prompt_version": PROMPT_VERSION,
        }

    if session is None or user_id is None:
        raise LLMError("session and user_id are required for live LLM mode")

    await ensure_llm_budget(session, user_id)
    completion = await complete_json(
        thread_writer_system_prompt(),
        thread_writer_user_prompt(
            title=title,
            hook_idea=hook_idea,
            category=category,
            profession=profession,
            tone=tone or [],
            vocabulary_avoid=vocabulary_avoid,
            count=count,
        ),
        prompt_version=PROMPT_VERSION,
    )
    variants = _parse_variants(completion.data, count)
    await record_llm_usage(session, user_id, completion.usage)
    return variants, {
        "llm_mode": "live",
        "model": completion.usage.model,
        "prompt_version": completion.usage.prompt_version,
    }
