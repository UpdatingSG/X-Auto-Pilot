"""Apply analytics insights to voice profile learned_weights."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.voice_profile import VoiceProfile
from xautopilot.services.analytics_service import get_insights, list_post_analytics


LEARNING_RATE = 0.3


def _merge_weights(current: dict, adjustments: dict[str, dict[str, float]]) -> dict:
    updated: dict = dict(current or {})
    for key, new_weights in adjustments.items():
        bucket = dict(updated.get(key, {}))
        for k, v in new_weights.items():
            old = float(bucket.get(k, 1.0))
            bucket[k] = round(old * (1 - LEARNING_RATE) + float(v) * LEARNING_RATE, 3)
        updated[key] = bucket
    return updated


def _weights_from_insights(insights, posts) -> dict[str, dict[str, float]]:
    adjustments: dict[str, dict[str, float]] = {
        "category_weights": {},
        "content_type_weights": {},
        "hook_weights": {},
    }

    increase = insights.recommended_adjustments.get("increase_weight", [])
    decrease = insights.recommended_adjustments.get("decrease_weight", [])
    for cat in increase:
        adjustments["category_weights"][cat] = 1.25
    for cat in decrease:
        adjustments["category_weights"][cat] = 0.75

    by_type: dict[str, list[float]] = {}
    for post in posts:
        if not post.metrics:
            continue
        ctype = post.content_type if hasattr(post, "content_type") else "tweet"
        by_type.setdefault(ctype, []).append(post.metrics.engagement_rate)

    if by_type:
        avg_all = sum(sum(v) / len(v) for v in by_type.values()) / len(by_type)
        for ctype, rates in by_type.items():
            avg = sum(rates) / len(rates)
            if avg > avg_all * 1.1:
                adjustments["content_type_weights"][ctype] = 1.2
            elif avg < avg_all * 0.8:
                adjustments["content_type_weights"][ctype] = 0.85

    for post in posts:
        if not post.metrics or not post.preview_text:
            continue
        if "?" in post.preview_text and post.metrics.engagement_rate > 0.03:
            adjustments["hook_weights"]["question"] = 1.15
        if post.metrics.bookmarks > post.metrics.likes // 2 and post.metrics.bookmarks > 0:
            adjustments["hook_weights"]["bookmark_thread"] = 1.2

    return {k: v for k, v in adjustments.items() if v}


async def apply_learned_weights(session: AsyncSession, user_id: UUID) -> dict:
    """Run learning cycle and persist weights on the active voice profile."""
    result = await session.execute(
        select(VoiceProfile).where(
            VoiceProfile.user_id == user_id,
            VoiceProfile.is_active.is_(True),
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return {"applied": False, "reason": "no_active_profile"}

    insights = await get_insights(session, user_id)
    posts = await list_post_analytics(session, user_id, "30d")
    adjustments = _weights_from_insights(insights, posts)
    if not adjustments:
        return {"applied": False, "reason": "insufficient_data"}

    merged = _merge_weights(profile.learned_weights, adjustments)
    profile.learned_weights = merged
    await session.commit()
    return {"applied": True, "learned_weights": merged, "adjustments": adjustments}


def get_weight_multiplier(weights: dict, bucket: str, key: str) -> float:
    return float((weights or {}).get(bucket, {}).get(key, 1.0))


def build_weight_hints(weights: dict) -> list[str]:
    hints: list[str] = []
    for cat, mult in (weights or {}).get("category_weights", {}).items():
        if mult >= 1.15:
            hints.append(f"Lean into {cat} content — it outperforms your average.")
        elif mult <= 0.8:
            hints.append(f"Reduce {cat} content — it underperforms for your account.")
    for ctype, mult in (weights or {}).get("content_type_weights", {}).items():
        if mult >= 1.15:
            hints.append(f"Prioritize {ctype}s — they earn more engagement per impression.")
    if (weights or {}).get("hook_weights", {}).get("bookmark_thread", 1.0) >= 1.15:
        hints.append("Threads with save-worthy frameworks are working — add a 'bookmark this' CTA.")
    return hints[:5]
