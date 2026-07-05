from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.models.llm_usage import LlmUsageDaily
from xautopilot.services.llm_service import LLMBudgetExceededError, LlmUsage


async def get_daily_spend(session: AsyncSession, user_id: UUID, usage_date: date | None = None) -> float:
    usage_date = usage_date or date.today()
    result = await session.execute(
        select(LlmUsageDaily).where(
            LlmUsageDaily.user_id == user_id,
            LlmUsageDaily.usage_date == usage_date,
        )
    )
    row = result.scalar_one_or_none()
    return row.cost_usd if row else 0.0


async def ensure_llm_budget(session: AsyncSession, user_id: UUID) -> None:
    spent = await get_daily_spend(session, user_id)
    budget = settings.llm_daily_budget_usd
    if spent >= budget:
        raise LLMBudgetExceededError(spent, budget)


async def record_llm_usage(session: AsyncSession, user_id: UUID, usage: LlmUsage) -> None:
    usage_date = date.today()
    result = await session.execute(
        select(LlmUsageDaily).where(
            LlmUsageDaily.user_id == user_id,
            LlmUsageDaily.usage_date == usage_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = LlmUsageDaily(
            user_id=user_id,
            usage_date=usage_date,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.estimated_cost_usd,
            request_count=1,
        )
        session.add(row)
    else:
        row.input_tokens += usage.input_tokens
        row.output_tokens += usage.output_tokens
        row.cost_usd += usage.estimated_cost_usd
        row.request_count += 1
    await session.flush()
