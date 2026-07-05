"""Tests for thread draft generation and publishing."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login
from tests.helpers_publishing import connect_x_account


async def _setup_with_thread_idea(client: AsyncClient, monkeypatch):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)

    monkeypatch.setattr(
        "xautopilot.services.agents.content_planner.should_include_thread",
        lambda _plan_date, _threads_per_week: True,
    )

    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    thread_idea = next(i for i in plan["ideas"] if i["content_type"] == "thread")
    await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{thread_idea['id']}",
        json={"status": "approved"},
        headers=headers,
    )
    return headers, thread_idea["id"]


async def test_generate_thread_draft_has_thread_tweets(client: AsyncClient, monkeypatch):
    headers, idea_id = await _setup_with_thread_idea(client, monkeypatch)

    response = await client.post(
        "/v1/drafts/generate",
        json={"idea_id": idea_id},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "thread"
    assert len(body["variants"]) >= 1
    assert body["variants"][0]["thread_tweets"]
    assert len(body["variants"][0]["thread_tweets"]) >= 3


async def test_publish_thread_draft(client: AsyncClient, monkeypatch):
    headers, idea_id = await _setup_with_thread_idea(client, monkeypatch)
    draft = (
        await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)
    ).json()
    variant_id = draft["variants"][0]["id"]
    await client.patch(
        f"/v1/drafts/{draft['id']}",
        json={"status": "approved", "selected_variant_id": variant_id},
        headers=headers,
    )
    await client.post(f"/v1/drafts/{draft['id']}/schedule", json={}, headers=headers)
    await connect_x_account(client, headers)

    response = await client.post(f"/v1/publish/{draft['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["content_type"] == "thread"
    assert response.json()["x_tweet_id"]
