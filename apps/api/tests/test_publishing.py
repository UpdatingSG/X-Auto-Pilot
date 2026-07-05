"""Slice 1-5: Publishing scheduled drafts to X."""

from httpx import AsyncClient

from tests.helpers_publishing import connect_x_account, create_scheduled_draft


async def test_publish_requires_connected_x_account(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)

    response = await client.post(f"/v1/publish/{draft_id}", headers=headers)

    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


async def test_publish_scheduled_draft(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    response = await client.post(f"/v1/publish/{draft_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["x_tweet_id"]
    assert body["preview_text"]


async def test_published_post_appears_in_history(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)
    await client.post(f"/v1/publish/{draft_id}", headers=headers)

    response = await client.get("/v1/publish/history", headers=headers)

    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["draft_id"] == draft_id
    assert history[0]["x_tweet_id"]


async def test_publish_same_draft_twice_is_idempotent(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    first = await client.post(f"/v1/publish/{draft_id}", headers=headers)
    second = await client.post(f"/v1/publish/{draft_id}", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
from xautopilot.services.x_client import XApiError


async def test_publish_returns_x_api_error_not_500(client: AsyncClient, monkeypatch):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    class ForbiddenClient:
        async def post_tweet(self, access_token: str, text: str):
            raise XApiError(
                "You are not permitted to create a Tweet with this app tier.",
                status_code=403,
            )

    monkeypatch.setattr(
        "xautopilot.services.twitter_publish_service.get_x_client",
        lambda: ForbiddenClient(),
    )

    response = await client.post(f"/v1/publish/{draft_id}", headers=headers)

    assert response.status_code == 403
    assert "not permitted" in response.json()["detail"].lower()
