"""Slice 1: Creator can read their posting schedule (defaults if not configured)."""

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_get_schedule_returns_defaults(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get("/v1/schedule", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["tweets_per_day"] == 3
    assert body["jitter_minutes"] == 15
    assert len(body["posting_windows"]) == 3
