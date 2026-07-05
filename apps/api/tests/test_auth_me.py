"""Slice 4: Authenticated creators can fetch their own profile."""

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/v1/auth/register",
        json={"email": "creator@example.com", "password": "securepass123"},
    )
    response = await client.post(
        "/v1/auth/login",
        json={"email": "creator@example.com", "password": "securepass123"},
    )
    return response.json()["access_token"]


async def test_me_returns_current_user(client: AsyncClient):
    token = await _register_and_login(client)

    response = await client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "creator@example.com"


async def test_me_rejects_missing_token(client: AsyncClient):
    response = await client.get("/v1/auth/me")

    assert response.status_code == 401
