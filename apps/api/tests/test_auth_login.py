"""Slice 3: A registered creator can log in and receive a JWT."""

from httpx import AsyncClient


async def test_login_returns_access_token(client: AsyncClient):
    await client.post(
        "/v1/auth/register",
        json={"email": "creator@example.com", "password": "securepass123"},
    )

    response = await client.post(
        "/v1/auth/login",
        json={"email": "creator@example.com", "password": "securepass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["email"] == "creator@example.com"


async def test_login_rejects_wrong_password(client: AsyncClient):
    await client.post(
        "/v1/auth/register",
        json={"email": "creator@example.com", "password": "securepass123"},
    )

    response = await client.post(
        "/v1/auth/login",
        json={"email": "creator@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
