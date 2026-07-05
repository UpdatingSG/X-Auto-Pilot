"""Step 4: OpenAI LLM integration tests."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login
from xautopilot.config import settings
from xautopilot.services.llm_service import LlmCompletion, LlmUsage


async def _setup_creator(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    return headers


def _fake_plan_completion() -> LlmCompletion:
    return LlmCompletion(
        data={
            "ideas": [
                {
                    "content_type": "tweet",
                    "category": "engineering",
                    "title": "Latency budgets matter",
                    "hook_idea": "Most teams ignore p99 until users complain",
                    "rationale": "Matches system design interest",
                },
                {
                    "content_type": "tweet",
                    "category": "hot_take",
                    "title": "Microservices regret",
                    "hook_idea": "Monoliths ship faster for small teams",
                    "rationale": "Contrarian backend take",
                },
                {
                    "content_type": "tweet",
                    "category": "educational",
                    "title": "Idempotency keys",
                    "hook_idea": "A 5-line pattern that prevents duplicate charges",
                    "rationale": "Practical engineering lesson",
                },
            ]
        },
        usage=LlmUsage(
            model="gpt-4o-mini",
            input_tokens=400,
            output_tokens=200,
            estimated_cost_usd=0.0002,
            prompt_version="1.0.0",
        ),
    )


def _fake_writer_completion() -> LlmCompletion:
    return LlmCompletion(
        data={
            "variants": [
                {
                    "text": "Why do teams ignore p99 latency until prod screams?",
                    "hook_type": "question",
                    "scores": {
                        "hook_strength": 0.9,
                        "voice_match": 0.88,
                        "authenticity": 0.86,
                        "overall": 0.89,
                    },
                },
                {
                    "text": "Hot take: most microservice splits are premature.",
                    "hook_type": "contrarian",
                    "scores": {
                        "hook_strength": 0.87,
                        "voice_match": 0.85,
                        "authenticity": 0.84,
                        "overall": 0.86,
                    },
                },
                {
                    "text": "I once fixed duplicate payments with one idempotency key.",
                    "hook_type": "story",
                    "scores": {
                        "hook_strength": 0.84,
                        "voice_match": 0.83,
                        "authenticity": 0.9,
                        "overall": 0.85,
                    },
                },
            ]
        },
        usage=LlmUsage(
            model="gpt-4o-mini",
            input_tokens=350,
            output_tokens=180,
            estimated_cost_usd=0.00016,
            prompt_version="1.0.0",
        ),
    )


async def test_live_plan_generation_uses_openai(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    async def fake_complete(*args, **kwargs):
        return _fake_plan_completion()

    monkeypatch.setattr(
        "xautopilot.services.agents.content_planner.complete_json",
        fake_complete,
    )

    headers = await _setup_creator(client)
    response = await client.post("/v1/plans/generate", headers=headers)

    assert response.status_code == 201
    ideas = response.json()["ideas"]
    assert len(ideas) == 3
    assert ideas[0]["title"] == "Latency budgets matter"


async def test_live_draft_generation_stores_metadata(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")

    call_count = {"n": 0}

    async def fake_complete(system, user, *, prompt_version):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_plan_completion()
        return _fake_writer_completion()

    monkeypatch.setattr(
        "xautopilot.services.agents.content_planner.complete_json",
        fake_complete,
    )
    monkeypatch.setattr(
        "xautopilot.services.agents.tweet_writer.complete_json",
        fake_complete,
    )

    headers = await _setup_creator(client)
    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    idea_id = plan["ideas"][0]["id"]
    await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{idea_id}",
        json={"status": "approved"},
        headers=headers,
    )

    response = await client.post(
        "/v1/drafts/generate",
        json={"idea_id": idea_id},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["variants"][0]["content_text"].startswith("Why do teams")
    assert len(body["variants"]) == 3
    assert body["generation_metadata"]["llm_mode"] == "live"
    assert body["generation_metadata"]["prompt_version"] == "1.0.0"

    draft = await client.get(f"/v1/drafts/{body['id']}", headers=headers)
    assert draft.status_code == 200


async def test_plan_returns_429_when_daily_budget_exceeded(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_daily_budget_usd", 0.0)

    headers = await _setup_creator(client)
    response = await client.post("/v1/plans/generate", headers=headers)

    assert response.status_code == 429
    assert "budget" in response.json()["detail"].lower()
