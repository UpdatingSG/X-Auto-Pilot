"""Tests for daily content plans and idea approval."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login
from xautopilot.config import settings


async def _setup_creator(client: AsyncClient) -> tuple[str, dict[str, str]]:
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    return token, headers


async def test_get_today_plan_returns_404_when_none(client: AsyncClient):
    token = await register_and_login(client)
    response = await client.get("/v1/plans/today", headers=auth_headers(token))
    assert response.status_code == 404


async def test_generate_plan_creates_mixed_ideas(client: AsyncClient):
    _, headers = await _setup_creator(client)

    response = await client.post("/v1/plans/generate", headers=headers)

    assert response.status_code == 201
    body = response.json()
    types = {i["content_type"] for i in body["ideas"]}
    assert types <= {"tweet", "thread", "reply", "quote_tweet"}
    assert any(i["content_type"] == "tweet" for i in body["ideas"])
    assert all(i["status"] == "proposed" for i in body["ideas"])


async def test_get_today_plan_after_generate(client: AsyncClient):
    _, headers = await _setup_creator(client)
    await client.post("/v1/plans/generate", headers=headers)

    response = await client.get("/v1/plans/today", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["ideas"]) >= 1


async def test_regenerate_plan_replaces_cached_ideas(client: AsyncClient, monkeypatch):
    from xautopilot.services.agents.content_planner import PlannedIdea

    _, headers = await _setup_creator(client)
    first = await client.post("/v1/plans/generate", headers=headers)
    assert first.status_code == 201
    assert "insight #1" in first.json()["ideas"][0]["title"]

    async def fake_plan(*args, **kwargs):
        return (
            [
                PlannedIdea(
                    content_type="tweet",
                    category="engineering",
                    title="Fresh Groq idea",
                    hook_idea="New hook",
                    rationale="Regenerated",
                )
            ]
            * 3,
            {"llm_mode": "live"},
        )

    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr("xautopilot.services.content_plan_service.plan_daily_content", fake_plan)

    second = await client.post("/v1/plans/generate?force=true", headers=headers)
    assert second.status_code == 201
    assert second.json()["ideas"][0]["title"] == "Fresh Groq idea"


async def test_approve_idea(client: AsyncClient):
    _, headers = await _setup_creator(client)
    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    idea_id = plan["ideas"][0]["id"]

    response = await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{idea_id}",
        json={"status": "approved"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
