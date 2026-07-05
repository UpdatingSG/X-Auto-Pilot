"""Slice 1-3: X token refresh and re-auth handling."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login
from tests.helpers_publishing import connect_x_account, create_scheduled_draft
from xautopilot.models.x_account import XAccount
from xautopilot.services.x_oauth_service import OAuthTokenSet
from xautopilot.services.x_token_service import token_needs_refresh
from xautopilot.services.x_client import XApiUnauthorizedError


def test_token_needs_refresh_when_expiring_within_five_minutes():
    account = XAccount(
        user_id=uuid4(),
        x_user_id="123",
        handle="user",
        access_token_enc=b"x",
        scopes=[],
        token_expires_at=datetime.now(UTC) + timedelta(minutes=3),
    )
    assert token_needs_refresh(account) is True


def test_token_needs_refresh_false_when_expiry_far():
    account = XAccount(
        user_id=uuid4(),
        x_user_id="123",
        handle="user",
        access_token_enc=b"x",
        scopes=[],
        token_expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    assert token_needs_refresh(account) is False


async def test_get_valid_access_token_refreshes_when_expiring(client: AsyncClient, monkeypatch):
    token = await register_and_login(client)
    headers = auth_headers(token)
    near_expiry = (datetime.now(UTC) + timedelta(minutes=2)).isoformat()
    await client.post(
        "/v1/x/account/connect",
        json={"handle": "refreshuser", "token_expires_at": near_expiry},
        headers=headers,
    )

    refreshed = OAuthTokenSet(
        access_token="refreshed-access-token",
        refresh_token="refreshed-refresh-token",
        expires_in=7200,
        scope="tweet.read tweet.write",
    )

    async def fake_refresh(_refresh_token: str) -> OAuthTokenSet:
        return refreshed

    monkeypatch.setattr(
        "xautopilot.services.x_token_service.refresh_access_token",
        fake_refresh,
    )

    response = await client.post("/v1/x/account/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["refreshed"] is True


async def test_publish_marks_needs_reauth_when_x_returns_401(client: AsyncClient, monkeypatch):
    headers, draft_id = await create_scheduled_draft(client)
    await connect_x_account(client, headers)

    class FailingClient:
        async def post_tweet(self, access_token: str, text: str):
            raise XApiUnauthorizedError("token revoked")

    monkeypatch.setattr(
        "xautopilot.services.twitter_publish_service.get_x_client",
        lambda: FailingClient(),
    )

    response = await client.post(f"/v1/publish/{draft_id}", headers=headers)

    assert response.status_code == 401
    assert "reconnect" in response.json()["detail"].lower()

    account = await client.get("/v1/x/account", headers=headers)
    assert account.status_code == 200
    assert account.json()["needs_reauth"] is True
