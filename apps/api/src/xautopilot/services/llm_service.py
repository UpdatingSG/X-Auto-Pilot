from dataclasses import dataclass

from xautopilot.config import settings

# USD per token (input, output)
MODEL_RATES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    "gpt-4o": (2.50 / 1_000_000, 10.0 / 1_000_000),
    "gpt-4.1-mini": (0.40 / 1_000_000, 1.60 / 1_000_000),
    "gpt-4.1": (2.00 / 1_000_000, 8.00 / 1_000_000),
}


class LLMNotConfiguredError(Exception):
    pass


class LLMError(Exception):
    pass


class LLMBudgetExceededError(Exception):
    def __init__(self, spent_usd: float, budget_usd: float):
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        super().__init__(f"Daily LLM budget exceeded (${spent_usd:.4f} / ${budget_usd:.2f})")


@dataclass
class LlmUsage:
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    prompt_version: str


@dataclass
class LlmCompletion:
    data: dict
    usage: LlmUsage


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = MODEL_RATES.get(model, MODEL_RATES["gpt-4o-mini"])
    return input_tokens * in_rate + output_tokens * out_rate


async def complete_json(system: str, user: str, *, prompt_version: str) -> LlmCompletion:
    """Call OpenAI chat completions with JSON output."""
    import httpx

    if not settings.openai_api_key:
        raise LLMNotConfiguredError(
            "OPENAI_API_KEY is not configured. Set it in apps/api/.env for live LLM mode."
        )

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.85,
            },
        )

    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("error", {}).get("message", detail)
        except Exception:
            pass
        raise LLMError(f"OpenAI request failed: {detail}")

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError("OpenAI returned an unexpected response shape") from exc

    import json

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("OpenAI returned invalid JSON") from exc

    usage_raw = payload.get("usage", {})
    input_tokens = int(usage_raw.get("prompt_tokens", 0))
    output_tokens = int(usage_raw.get("completion_tokens", 0))
    model = payload.get("model", settings.openai_model)
    cost = estimate_cost(model, input_tokens, output_tokens)

    return LlmCompletion(
        data=data,
        usage=LlmUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            prompt_version=prompt_version,
        ),
    )
