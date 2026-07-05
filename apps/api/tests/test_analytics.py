"""Slice 1: Analytics overview for creators with no published posts yet."""

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login
from tests.helpers_publishing import create_published_post


async def test_analytics_overview_empty(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get("/v1/analytics/overview?period=7d", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["posts_published"] == 0
    assert body["total_impressions"] == 0
    assert body["avg_engagement_rate"] == 0.0
    assert body["top_post"] is None


async def test_sync_post_metrics(client: AsyncClient):
    headers, published = await create_published_post(client)

    response = await client.post(
        f"/v1/analytics/posts/{published['id']}/sync",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["impressions"] > 0
    assert body["likes"] >= 0
    assert 0 <= body["engagement_rate"] <= 1


async def test_analytics_overview_reflects_synced_metrics(client: AsyncClient):
    headers, published = await create_published_post(client)
    sync = await client.post(f"/v1/analytics/posts/{published['id']}/sync", headers=headers)
    synced_impressions = sync.json()["impressions"]

    response = await client.get("/v1/analytics/overview?period=7d", headers=headers)

    body = response.json()
    assert body["posts_published"] == 1
    assert body["total_impressions"] == synced_impressions
    assert body["avg_engagement_rate"] > 0
    assert body["top_post"]["post_id"] == published["id"]


async def test_analytics_posts_leaderboard(client: AsyncClient):
    headers, published = await create_published_post(client)
    await client.post(f"/v1/analytics/posts/{published['id']}/sync", headers=headers)

    response = await client.get("/v1/analytics/posts?period=30d", headers=headers)

    posts = response.json()
    assert len(posts) == 1
    assert posts[0]["post_id"] == published["id"]
    assert posts[0]["metrics"]["impressions"] > 0


async def test_analytics_insights_when_posts_exist(client: AsyncClient):
    headers, published = await create_published_post(client)
    await client.post(f"/v1/analytics/posts/{published['id']}/sync", headers=headers)

    response = await client.get("/v1/analytics/insights", headers=headers)

    body = response.json()
    assert body["period"] == "7d"
    assert body["best_category"] is not None
    assert isinstance(body["what_worked"], list)

