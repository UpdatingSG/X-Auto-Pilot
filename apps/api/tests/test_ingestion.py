"""Slice 6: Fetching a source ingests items into the knowledge base."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login
from tests.test_knowledge_sources import SAMPLE_RSS_SOURCE
from xautopilot.services.ingestion_service import NormalizedItem

MOCK_RSS_ITEMS = [
    NormalizedItem(
        external_id="abc123",
        title="Redis vs Dragonfly benchmarks",
        url="https://example.com/redis-dragonfly",
        author="jane",
        content="A deep dive into cache performance...",
        published_at=None,
    )
]


async def test_fetch_source_ingests_items(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    create_resp = await client.post("/v1/sources", json=SAMPLE_RSS_SOURCE, headers=headers)
    source_id = create_resp.json()["id"]

    with patch(
        "xautopilot.services.ingestion_service.fetch_rss_items",
        new=AsyncMock(return_value=MOCK_RSS_ITEMS),
    ):
        response = await client.post(f"/v1/sources/{source_id}/fetch", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items_ingested"] == 1

    items_resp = await client.get("/v1/knowledge/items", headers=headers)
    items = items_resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "Redis vs Dragonfly benchmarks"


async def test_fetch_source_deduplicates(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)
    create_resp = await client.post("/v1/sources", json=SAMPLE_RSS_SOURCE, headers=headers)
    source_id = create_resp.json()["id"]

    with patch(
        "xautopilot.services.ingestion_service.fetch_rss_items",
        new=AsyncMock(return_value=MOCK_RSS_ITEMS),
    ):
        await client.post(f"/v1/sources/{source_id}/fetch", headers=headers)
        response = await client.post(f"/v1/sources/{source_id}/fetch", headers=headers)

    assert response.json()["items_ingested"] == 0
    items_resp = await client.get("/v1/knowledge/items", headers=headers)
    assert len(items_resp.json()) == 1
