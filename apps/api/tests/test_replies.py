"""Tests for reply targets, reply drafts, and publishing."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login
from tests.helpers_publishing import connect_x_account


async def _setup_creator(client: AsyncClient) -> dict[str, str]:
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    await client.put(
        "/v1/schedule",
        json={"auto_schedule_replies": False},
        headers=headers,
    )
    return headers


async def test_create_reply_target(client: AsyncClient):
    headers = await _setup_creator(client)

    response = await client.post(
        "/v1/reply-targets",
        json={
            "author_handle": "sama",
            "tweet_text": "AI will change how we build software.",
            "x_tweet_id": "1234567890",
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["author_handle"] == "sama"
    assert body["x_tweet_id"] == "1234567890"


async def test_plan_includes_reply_when_targets_exist(client: AsyncClient):
    headers = await _setup_creator(client)
    await client.post(
        "/v1/reply-targets",
        json={
            "author_handle": "naval",
            "tweet_text": "Specific knowledge is found by pursuing your curiosity.",
            "x_tweet_id": "9876543210",
        },
        headers=headers,
    )

    plan = (await client.post("/v1/plans/generate?force=true", headers=headers)).json()
    reply_ideas = [i for i in plan["ideas"] if i["content_type"] == "reply"]

    assert len(reply_ideas) >= 1
    assert reply_ideas[0]["reply_target_id"]


async def test_generate_reply_draft_from_target(client: AsyncClient):
    headers = await _setup_creator(client)
    target = (
        await client.post(
            "/v1/reply-targets",
            json={
                "author_handle": "paulg",
                "tweet_text": "The best startup ideas come from problems you have yourself.",
                "x_tweet_id": "5555555555",
            },
            headers=headers,
        )
    ).json()

    response = await client.post(
        "/v1/drafts/generate",
        json={"reply_target_id": target["id"]},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "reply"
    assert body["variants"][0]["content_text"]


async def test_discover_reply_targets(client: AsyncClient):
    headers = await _setup_creator(client)

    response = await client.post(
        "/v1/reply-targets/discover",
        json={"min_followers": 10000, "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["targets"]) >= 1
    assert body["targets"][0]["x_tweet_id"]
    assert body["targets"][0]["author_followers"] >= 10000


async def test_import_discovered_reply_targets(client: AsyncClient):
    headers = await _setup_creator(client)
    discovered = (
        await client.post(
            "/v1/reply-targets/discover",
            json={"limit": 2},
            headers=headers,
        )
    ).json()

    response = await client.post(
        "/v1/reply-targets/discover/import",
        json={"targets": discovered["targets"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2


async def test_import_reply_target_from_url(client: AsyncClient):
    headers = await _setup_creator(client)

    response = await client.post(
        "/v1/reply-targets/from-url/import",
        json={"url": "https://x.com/rakyll/status/1234567890123456789"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["author_handle"] == "rakyll"


async def test_create_reply_target_rejects_invalid_tweet_id(client: AsyncClient):
    headers = await _setup_creator(client)

    response = await client.post(
        "/v1/reply-targets",
        json={
            "author_handle": "Vivek4real_",
            "tweet_text": "Some tweet",
            "x_tweet_id": "manual-Vivek4real_-77",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "numeric" in response.json()["detail"].lower()


async def test_publish_reply_draft(client: AsyncClient):
    headers = await _setup_creator(client)
    target = (
        await client.post(
            "/v1/reply-targets",
            json={
                "author_handle": "levelsio",
                "tweet_text": "Ship fast, iterate faster.",
                "x_tweet_id": "1111222233",
            },
            headers=headers,
        )
    ).json()
    draft = (
        await client.post(
            "/v1/drafts/generate",
            json={"reply_target_id": target["id"]},
            headers=headers,
        )
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
    assert response.json()["content_type"] == "reply"
