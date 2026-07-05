"""Slice 1: Creator can read their active voice profile (or get told none exists)."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login


async def test_get_voice_profile_returns_404_when_none(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get("/v1/profile/voice", headers=auth_headers(token))

    assert response.status_code == 404


async def test_create_voice_profile_returns_version_one(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.post(
        "/v1/profile/voice",
        json=SAMPLE_VOICE_PROFILE,
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["is_active"] is True
    assert body["profession"] == "Backend Engineer"
    assert body["interests"][0]["topic"] == "System Design"


async def test_get_voice_profile_after_create(client: AsyncClient):
    token = await register_and_login(client)
    await client.post(
        "/v1/profile/voice",
        json=SAMPLE_VOICE_PROFILE,
        headers=auth_headers(token),
    )

    response = await client.get("/v1/profile/voice", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["profession"] == "Backend Engineer"


async def test_new_voice_profile_increments_version_and_deactivates_old(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)

    updated = {**SAMPLE_VOICE_PROFILE, "profession": "Staff Engineer"}
    response = await client.post("/v1/profile/voice", json=updated, headers=headers)

    assert response.status_code == 201
    assert response.json()["version"] == 2
    assert response.json()["profession"] == "Staff Engineer"

    get_response = await client.get("/v1/profile/voice", headers=headers)
    assert get_response.json()["version"] == 2

