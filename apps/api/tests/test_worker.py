"""Step 5: background publish + metrics sync workers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient

from tests.helpers_publishing import connect_x_account, create_published_post, create_scheduled_draft
from tests.helpers_scheduling import create_approved_draft


async def _schedule_in_past(client: AsyncClient, headers: dict, draft_id: str) -> None:
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    response = await client.post(
        f"/v1/drafts/{draft_id}/schedule",
        json={"scheduled_at": past},
        headers=headers,
    )
    assert response.status_code == 200


async def test_worker_tick_auto_publishes_overdue_draft(client: AsyncClient):
    headers, draft_id = await create_approved_draft(client)
    await connect_x_account(client, headers)
    await _schedule_in_past(client, headers, draft_id)

    response = await client.post("/v1/worker/tick")

    assert response.status_code == 200
    body = response.json()
    assert len(body["published"]) == 1
    assert body["published"][0]["success"] is True
    assert body["published"][0]["x_tweet_id"]

    history = await client.get("/v1/publish/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_worker_tick_skips_future_draft(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    response = await client.post("/v1/worker/tick")

    assert response.status_code == 200
    assert response.json()["published"] == []


async def test_metrics_sync_tick_runs_due_jobs(client: AsyncClient, monkeypatch):
    headers, published = await create_published_post(client)

    async def all_pending(session, now=None):
        from sqlalchemy import select

        from xautopilot.models.metrics_sync_job import MetricsSyncJob

        result = await session.execute(
            select(MetricsSyncJob).where(
                MetricsSyncJob.post_id == UUID(published["id"]),
                MetricsSyncJob.status == "pending",
            )
        )
        return list(result.scalars().all())

    monkeypatch.setattr(
        "xautopilot.services.worker_service.list_due_metrics_sync_jobs",
        all_pending,
    )

    response = await client.post("/v1/worker/tick")
    assert response.status_code == 200
    synced = response.json()["metrics_synced"]
    assert len(synced) == 3
    assert all(s["success"] for s in synced)


async def test_worker_status_endpoint(client: AsyncClient):
    response = await client.get("/v1/worker/status")
    assert response.status_code == 200
    body = response.json()
    assert body["tick_interval_seconds"] == 60
    assert "manual_tick_enabled" in body
