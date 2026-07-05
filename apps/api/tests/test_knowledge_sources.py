"""Knowledge sources: configure where the AI reads from."""

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login

SAMPLE_RSS_SOURCE = {
    "source_type": "rss",
    "name": "Hacker News Frontpage",
    "config": {"url": "https://hnrss.org/frontpage"},
}


async def test_list_sources_empty(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get("/v1/sources", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == []


async def test_create_rss_source(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.post(
        "/v1/sources",
        json=SAMPLE_RSS_SOURCE,
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Hacker News Frontpage"
    assert body["source_type"] == "rss"
    assert body["is_enabled"] is True
    assert "id" in body


async def test_list_sources_after_create(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/sources", json=SAMPLE_RSS_SOURCE, headers=headers)

    response = await client.get("/v1/sources", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
