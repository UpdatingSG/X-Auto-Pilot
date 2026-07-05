"""Reusable flow: creator with a scheduled draft ready to publish."""

from httpx import AsyncClient

from tests.helpers_scheduling import create_approved_draft


async def create_scheduled_draft(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers, draft_id = await create_approved_draft(client)
    await client.post(f"/v1/drafts/{draft_id}/schedule", json={}, headers=headers)
    return headers, draft_id


async def connect_x_account(client: AsyncClient, headers: dict[str, str], handle: str = "testcreator") -> None:
    response = await client.post(
        "/v1/x/account/connect",
        json={"handle": handle},
        headers=headers,
    )
    assert response.status_code == 200


async def create_published_post(client: AsyncClient) -> tuple[dict[str, str], dict]:
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)
    response = await client.post(f"/v1/publish/{draft_id}", headers=headers)
    assert response.status_code == 200
    return headers, response.json()
