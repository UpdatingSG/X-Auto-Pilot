from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.services.agents.prompts import (
    PROMPT_VERSION,
    writer_system_prompt,
    writer_user_prompt,
)
from xautopilot.services.llm_cost_service import ensure_llm_budget, record_llm_usage
from xautopilot.services.llm_service import LLMError, complete_json


@dataclass
class TweetVariant:
    text: str
    hook_type: str
    scores: dict[str, float]


def _template_variations(
    title: str,
    hook_idea: str,
    profession: str,
    vocabulary_avoid: list[str],
    count: int,
    category: str = "engineering",
) -> list[TweetVariant]:
    hooks = ["question", "contrarian", "story"][:count]
    variants: list[TweetVariant] = []

    templates = {
        "question": f"Why does everyone overcomplicate {title.lower()}? Here's what I've seen as a {profession}. #buildinpublic",
        "contrarian": f"Unpopular opinion: most {title.lower()} advice is wrong. {hook_idea}. #{category}",
        "story": f"Last week I debugged a production issue related to {title.lower()}. Lesson learned. #tech",
    }

    for i, hook_type in enumerate(hooks):
        text = templates[hook_type]
        for word in vocabulary_avoid:
            text = text.replace(word, "")

        variants.append(
            TweetVariant(
                text=text[:280],
                hook_type=hook_type,
                scores={
                    "hook_strength": 0.85 - i * 0.05,
                    "voice_match": 0.88,
                    "authenticity": 0.82 + i * 0.02,
                    "overall": 0.87 - i * 0.04,
                },
            )
        )

    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


def _parse_variants(data: dict, count: int) -> list[TweetVariant]:
    raw = data.get("variants", [])
    variants: list[TweetVariant] = []
    for item in raw[:count]:
        scores = item.get("scores", {})
        variants.append(
            TweetVariant(
                text=str(item.get("text", ""))[:280],
                hook_type=str(item.get("hook_type", "question")),
                scores={
                    "hook_strength": float(scores.get("hook_strength", 0.8)),
                    "voice_match": float(scores.get("voice_match", 0.8)),
                    "authenticity": float(scores.get("authenticity", 0.8)),
                    "overall": float(scores.get("overall", 0.8)),
                },
            )
        )
    if len(variants) < count:
        raise LLMError(f"Expected {count} variants, got {len(variants)}")
    variants.sort(key=lambda v: v.scores["overall"], reverse=True)
    return variants


async def generate_tweet_variations(
    title: str,
    hook_idea: str,
    profession: str,
    vocabulary_avoid: list[str],
    count: int = 3,
    *,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
    category: str = "engineering",
    tone: list[str] | None = None,
    max_hashtags: int = 2,
    favorite_hashtags: list[str] | None = None,
) -> tuple[list[TweetVariant], dict]:
    if settings.llm_mode == "mock":
        return _template_variations(
            title, hook_idea, profession, vocabulary_avoid, count, category
        ), {
            "llm_mode": "mock",
            "prompt_version": PROMPT_VERSION,
        }

    if session is None or user_id is None:
        raise LLMError("session and user_id are required for live LLM mode")

    await ensure_llm_budget(session, user_id)
    completion = await complete_json(
        writer_system_prompt(max_hashtags=max_hashtags),
        writer_user_prompt(
            title=title,
            hook_idea=hook_idea,
            category=category,
            profession=profession,
            tone=tone or [],
            vocabulary_avoid=vocabulary_avoid,
            count=count,
            max_hashtags=max_hashtags,
            favorite_hashtags=favorite_hashtags,
        ),
        prompt_version=PROMPT_VERSION,
    )
    variants = _parse_variants(completion.data, count)
    await record_llm_usage(session, user_id, completion.usage)

    metadata = {
        "llm_mode": "live",
        "model": completion.usage.model,
        "prompt_version": completion.usage.prompt_version,
        "input_tokens": completion.usage.input_tokens,
        "output_tokens": completion.usage.output_tokens,
        "estimated_cost_usd": completion.usage.estimated_cost_usd,
    }
    return variants, metadata
