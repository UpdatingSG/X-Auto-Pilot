from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.agents.prompts import (
    PROMPT_VERSION,
    reply_writer_system_prompt,
    reply_writer_user_prompt,
)
from xautopilot.services.llm_cost_service import ensure_llm_budget, record_llm_usage
from xautopilot.services.llm_service import LLMError, complete_json


@dataclass
class ReplyVariant:
    text: str
    hook_type: str
    scores: dict[str, float]


def _template_replies(author_handle: str, target_tweet: str, profession: str, count: int) -> list[ReplyVariant]:
    snippets = [
        f"Seen this on prod too — the fix for us was tracing the actual bottleneck first, not adding cache.",
        f"Curious: did you measure before/after? In my experience the obvious fix here often isn't the right one.",
        f"I'd add one nuance: context matters. What worked for our {profession.lower()} team was simplifying first.",
    ]
    variants: list[ReplyVariant] = []
    for i in range(count):
        text = snippets[i % len(snippets)]
        if author_handle.lower() in target_tweet.lower():
            text = f"@{author_handle.lstrip('@')} {text}"
        variants.append(
            ReplyVariant(
                text=text[:280],
                hook_type=["insight", "question", "story"][i % 3],
                scores={
                    "hook_strength": 0.82 - i * 0.03,
                    "voice_match": 0.9,
                    "authenticity": 0.88,
                    "overall": 0.86 - i * 0.02,
                },
            )
        )
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


def _parse_variants(data: dict, count: int) -> list[ReplyVariant]:
    raw = data.get("variants", [])
    variants: list[ReplyVariant] = []
    for item in raw[:count]:
        scores = item.get("scores", {})
        variants.append(
            ReplyVariant(
                text=str(item.get("text", ""))[:280],
                hook_type=str(item.get("hook_type", "insight")),
                scores={
                    "hook_strength": float(scores.get("hook_strength", 0.8)),
                    "voice_match": float(scores.get("voice_match", 0.8)),
                    "authenticity": float(scores.get("authenticity", 0.8)),
                    "overall": float(scores.get("overall", 0.8)),
                },
            )
        )
    if len(variants) < count:
        raise LLMError(f"Expected {count} reply variants, got {len(variants)}")
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


async def generate_reply_variations(
    author_handle: str,
    target_tweet: str,
    profession: str,
    vocabulary_avoid: list[str],
    count: int = 3,
    *,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
    tone: list[str] | None = None,
) -> tuple[list[ReplyVariant], dict]:
    if settings.llm_mode == "mock":
        return _template_replies(author_handle, target_tweet, profession, count), {
            "llm_mode": "mock",
            "prompt_version": PROMPT_VERSION,
        }

    if session is None or user_id is None:
        raise LLMError("session and user_id are required for live LLM mode")

    await ensure_llm_budget(session, user_id)
    completion = await complete_json(
        reply_writer_system_prompt(),
        reply_writer_user_prompt(
            author_handle=author_handle,
            target_tweet=target_tweet,
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
