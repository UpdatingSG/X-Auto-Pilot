"""Slice 2: A new creator can register with email and password."""

from httpx import AsyncClient


async def test_register_creates_user(client: AsyncClient):
    response = await client.post(
        "/v1/auth/register",
        json={"email": "creator@example.com", "password": "securepass123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "creator@example.com"
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_rejects_duplicate_email(client: AsyncClient):
    payload = {"email": "creator@example.com", "password": "securepass123"}
    await client.post("/v1/auth/register", json=payload)

    response = await client.post("/v1/auth/register", json=payload)

    assert response.status_code == 409
