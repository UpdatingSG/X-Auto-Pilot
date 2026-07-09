from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.agents.prompts import (
    PROMPT_VERSION,
    quote_writer_system_prompt,
    quote_writer_user_prompt,
)
from xautopilot.services.llm_cost_service import ensure_llm_budget, record_llm_usage
from xautopilot.services.llm_service import LLMError, complete_json


@dataclass
class QuoteVariant:
    text: str
    hook_type: str
    scores: dict[str, float]


def _template_quotes(author_handle: str, target_tweet: str, profession: str, count: int) -> list[QuoteVariant]:
    snippets = [
        f"Strong take — I'd add: the bottleneck is rarely where teams look first.",
        f"Disagree on one point here. In production {profession.lower()} work, simplicity beat scale every time.",
        f"This matches what I've seen, with one caveat: measure before you optimize.",
    ]
    variants: list[QuoteVariant] = []
    for i in range(count):
        variants.append(
            QuoteVariant(
                text=snippets[i % len(snippets)][:250],
                hook_type=["contrarian", "insight", "story"][i % 3],
                scores={
                    "hook_strength": 0.85 - i * 0.03,
                    "voice_match": 0.9,
                    "authenticity": 0.87,
                    "overall": 0.87 - i * 0.02,
                },
            )
        )
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


def _parse_variants(data: dict, count: int) -> list[QuoteVariant]:
    raw = data.get("variants", [])
    variants: list[QuoteVariant] = []
    for item in raw[:count]:
        scores = item.get("scores", {})
        variants.append(
            QuoteVariant(
                text=str(item.get("text", ""))[:250],
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
        raise LLMError(f"Expected {count} quote variants, got {len(variants)}")
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


async def generate_quote_variations(
    author_handle: str,
    target_tweet: str,
    profession: str,
    vocabulary_avoid: list[str],
    count: int = 3,
    *,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
    tone: list[str] | None = None,
) -> tuple[list[QuoteVariant], dict]:
    if settings.llm_mode == "mock":
        return _template_quotes(author_handle, target_tweet, profession, count), {
            "llm_mode": "mock",
            "prompt_version": PROMPT_VERSION,
        }

    if session is None or user_id is None:
        raise LLMError("session and user_id are required for live LLM mode")

    await ensure_llm_budget(session, user_id)
    completion = await complete_json(
        quote_writer_system_prompt(),
        quote_writer_user_prompt(
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
