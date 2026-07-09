"""Slice 2-5: Scheduling approved drafts into human-like posting windows."""

from datetime import UTC, datetime

from httpx import AsyncClient

from tests.helpers_scheduling import create_approved_draft


async def test_update_schedule(client: AsyncClient):
    headers, _ = await create_approved_draft(client)

    response = await client.put(
        "/v1/schedule",
        json={"tweets_per_day": 5, "jitter_minutes": 10},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["tweets_per_day"] == 5
    assert response.json()["jitter_minutes"] == 10


async def test_schedule_approved_draft(client: AsyncClient):
    headers, draft_id = await create_approved_draft(client)

    response = await client.post(f"/v1/drafts/{draft_id}/schedule", json={}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["scheduled_at"] is not None
    scheduled = datetime.fromisoformat(body["scheduled_at"].replace("Z", "+00:00"))
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=UTC)
    assert scheduled > datetime.now(UTC)


async def test_publish_queue_lists_scheduled_draft(client: AsyncClient):
    headers, draft_id = await create_approved_draft(client)
    await client.post(f"/v1/drafts/{draft_id}/schedule", json={}, headers=headers)

    response = await client.get("/v1/publish/queue", headers=headers)

    assert response.status_code == 200
    queue = response.json()
    assert len(queue) == 1
    assert queue[0]["draft_id"] == draft_id
    assert queue[0]["preview_text"]


async def test_cancel_schedule_reverts_to_approved(client: AsyncClient):
    headers, draft_id = await create_approved_draft(client)
    await client.post(f"/v1/drafts/{draft_id}/schedule", json={}, headers=headers)

    response = await client.delete(f"/v1/drafts/{draft_id}/schedule", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["scheduled_at"] is None


async def test_two_scheduled_drafts_use_different_windows(client: AsyncClient):
    headers, draft_id_1 = await create_approved_draft(client)
    await client.put(
        "/v1/schedule",
        json={"growth_mode": False, "tweets_per_day": 5},
        headers=headers,
    )
    resp1 = await client.post(f"/v1/drafts/{draft_id_1}/schedule", json={}, headers=headers)

    plan = (await client.get("/v1/plans/today", headers=headers)).json()
    idea_id = next(i["id"] for i in plan["ideas"] if i["status"] == "proposed")
    await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{idea_id}",
        json={"status": "approved"},
        headers=headers,
    )
    draft_2 = (
        await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)
    ).json()
    await client.patch(
        f"/v1/drafts/{draft_2['id']}",
        json={"status": "approved", "selected_variant_id": draft_2["variants"][0]["id"]},
        headers=headers,
    )
    resp2 = await client.post(f"/v1/drafts/{draft_2['id']}/schedule", json={}, headers=headers)

    def parse_dt(s: str) -> datetime:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt

    t1 = parse_dt(resp1.json()["scheduled_at"])
    t2 = parse_dt(resp2.json()["scheduled_at"])
    assert abs((t2 - t1).total_seconds()) >= 20 * 60

    def window_bucket(dt: datetime) -> str:
        hour = dt.hour
        if 9 <= hour < 10:
            return "morning"
        if 13 <= hour < 14:
            return "afternoon"
        if 19 <= hour < 20:
            return "evening"
        return "other"

    assert window_bucket(t1) != window_bucket(t2)
