"""Shared auth helpers for integration tests."""

from httpx import AsyncClient

REGISTER_PAYLOAD = {"email": "creator@example.com", "password": "securepass123"}


async def register_and_login(client: AsyncClient) -> str:
    await client.post("/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post("/v1/auth/login", json=REGISTER_PAYLOAD)
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
