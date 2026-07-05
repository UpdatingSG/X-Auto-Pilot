"""Reusable flow: creator with an approved draft ready to schedule."""

from httpx import AsyncClient

from tests.fixtures.voice_profile import SAMPLE_VOICE_PROFILE
from tests.helpers import auth_headers, register_and_login


async def create_approved_draft(client: AsyncClient) -> tuple[dict[str, str], str]:
    token = await register_and_login(client)
    headers = auth_headers(token)
    await client.post("/v1/profile/voice", json=SAMPLE_VOICE_PROFILE, headers=headers)
    plan = (await client.post("/v1/plans/generate", headers=headers)).json()
    idea_id = plan["ideas"][0]["id"]
    await client.patch(
        f"/v1/plans/{plan['id']}/ideas/{idea_id}",
        json={"status": "approved"},
        headers=headers,
    )
    draft = (
        await client.post("/v1/drafts/generate", json={"idea_id": idea_id}, headers=headers)
    ).json()
    variant_id = draft["variants"][0]["id"]
    await client.patch(
        f"/v1/drafts/{draft['id']}",
        json={"status": "approved", "selected_variant_id": variant_id},
        headers=headers,
    )
    return headers, draft["id"]
