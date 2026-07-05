"""Tests for tweet draft generation and approval."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login


async def _plan_with_approved_idea(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    idea_id = plan["ideas"][0]["id"]
    await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{idea_id}",
        json={"status": "approved"},
        headers=headers,
    )
    return headers, idea_id


async def test_generate_draft_requires_approved_idea(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    idea_id = plan["ideas"][0]["id"]

    response = await client.post(
        "/v1/drafts/generate",
        json={"idea_id": idea_id},
        headers=headers,
    )

    assert response.status_code == 400


async def test_generate_draft_creates_variants(client: AsyncClient):
    headers, idea_id = await _plan_with_approved_idea(client)

    response = await client.post(
        "/v1/drafts/generate",
        json={"idea_id": idea_id},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["variants"]) == 3
    assert body["variants"][0]["scores"]["overall"] >= body["variants"][1]["scores"]["overall"]
    assert all(v["content_text"] for v in body["variants"])


async def test_list_ready_drafts(client: AsyncClient):
    headers, idea_id = await _plan_with_approved_idea(client)
    await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)

    response = await client.get("/v1/drafts?status=ready", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_approve_draft(client: AsyncClient):
    headers, idea_id = await _plan_with_approved_idea(client)
    draft = (
        await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)
    ).json()
    best_variant = draft["variants"][0]["id"]

    response = await client.patch(
        f"/v1/drafts/{draft['id']}",
        json={"status": "approved", "selected_variant_id": best_variant},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["selected_variant_id"] == best_variant


async def test_reject_draft_hides_from_ready_list(client: AsyncClient):
    headers, idea_id = await _plan_with_approved_idea(client)
    draft = (
        await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)
    ).json()

    reject = await client.patch(
        f"/v1/drafts/{draft['id']}",
        json={"status": "rejected"},
        headers=headers,
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    ready = await client.get("/v1/drafts?status=ready", headers=headers)
    assert ready.status_code == 200
    assert all(d["id"] != draft["id"] for d in ready.json())
