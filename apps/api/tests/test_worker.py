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
    assert body["published_ok"] == 1
    assert body["published_failed"] == 0

    history = await client.get("/v1/publish/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_worker_tick_skips_future_draft(client: AsyncClient):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    response = await client.post("/v1/worker/tick")

    assert response.status_code == 200
    assert response.json()["published_ok"] == 0


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
    body = response.json()
    assert body["metrics_ok"] == 3
    assert body["metrics_failed"] == 0


async def test_worker_status_endpoint(client: AsyncClient):
    response = await client.get("/v1/worker/status")
    assert response.status_code == 200
    body = response.json()
    assert body["tick_interval_seconds"] == 60
    assert "manual_tick_enabled" in body
    assert "cron_tick_configured" in body


async def test_worker_cron_returns_plaintext_ok(client: AsyncClient):
    response = await client.get("/v1/worker/cron")
    assert response.status_code == 200
    assert response.text == "ok"
    assert response.headers["content-type"].startswith("text/plain")


async def test_worker_tick_compact_json_with_cron_secret(client: AsyncClient, monkeypatch):
    from xautopilot.config import settings

    monkeypatch.setattr(settings, "worker_cron_secret", "test-cron-secret")
    response = await client.post(
        "/v1/worker/tick",
        headers={"X-Worker-Secret": "test-cron-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"ok": True, "p": 0, "f": 0, "m": 0}
