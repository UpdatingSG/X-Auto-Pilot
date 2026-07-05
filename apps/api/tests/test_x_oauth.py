"""OAuth 2.0 PKCE flow for X account connection."""

import base64
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login
from xautopilot.config import settings
from xautopilot.services.x_oauth_service import OAuthTokenSet, XUserProfile


@pytest.fixture(autouse=True)
def oauth_live_config(monkeypatch):
    monkeypatch.setattr(settings, "x_api_mode", "live")
    monkeypatch.setattr(settings, "x_client_id", "test-client-id")
    monkeypatch.setattr(settings, "x_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "x_redirect_uri", "http://localhost:8000/v1/x/oauth/callback")
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")


async def test_oauth_start_returns_authorization_url(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)

    response = await client.post("/v1/x/oauth/start", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert "twitter.com/i/oauth2/authorize" in body["authorization_url"]
    assert "code_challenge=" in body["authorization_url"]
    assert body["state"]


async def test_basic_auth_header_format():
    from xautopilot.config import settings
    from xautopilot.services.x_oauth_service import _basic_auth_header

    settings.x_client_id = "test-client-id"
    settings.x_client_secret = "test-secret"
    header = _basic_auth_header()
    assert header.startswith("Basic ")
    payload = header.removeprefix("Basic ")
    decoded = base64.b64decode(payload).decode()
    assert decoded == "test-client-id:test-secret"


async def test_oauth_complete_via_frontend_callback(client: AsyncClient, monkeypatch):
    token = await register_and_login(client)
    headers = auth_headers(token)
    start = await client.post("/v1/x/oauth/start", headers=headers)
    state = start.json()["state"]

    async def fake_exchange(code: str, verifier: str) -> OAuthTokenSet:
        return OAuthTokenSet(
            access_token="live-access-token",
            refresh_token="live-refresh-token",
            expires_in=7200,
            scope="tweet.read tweet.write users.read offline.access",
        )

    async def fake_user(access_token: str) -> XUserProfile:
        return XUserProfile(x_user_id="99887766", handle="produser")

    monkeypatch.setattr("xautopilot.services.x_oauth_service._exchange_code", fake_exchange)
    monkeypatch.setattr("xautopilot.services.x_oauth_service._fetch_x_user", fake_user)

    response = await client.post(
        "/v1/x/oauth/complete",
        json={"code": "auth-code-xyz", "state": state},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["handle"] == "produser"
    assert response.json()["x_user_id"] == "99887766"


async def test_oauth_callback_stores_connected_account(client: AsyncClient, monkeypatch):
    token = await register_and_login(client)
    headers = auth_headers(token)
    start = await client.post("/v1/x/oauth/start", headers=headers)
    state = start.json()["state"]

    async def fake_exchange(code: str, verifier: str) -> OAuthTokenSet:
        assert code == "auth-code-xyz"
        return OAuthTokenSet(
            access_token="live-access-token",
            refresh_token="live-refresh-token",
            expires_in=7200,
            scope="tweet.read tweet.write users.read offline.access",
        )

    async def fake_user(access_token: str) -> XUserProfile:
        assert access_token == "live-access-token"
        return XUserProfile(x_user_id="99887766", handle="produser")

    monkeypatch.setattr(
        "xautopilot.services.x_oauth_service._exchange_code",
        fake_exchange,
    )
    monkeypatch.setattr(
        "xautopilot.services.x_oauth_service._fetch_x_user",
        fake_user,
    )

    response = await client.get(
        f"/v1/x/oauth/callback?state={state}&code=auth-code-xyz",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:3000/settings/x?connected=1"

    account = await client.get("/v1/x/account", headers=headers)
    assert account.status_code == 200
    assert account.json()["handle"] == "produser"
    assert account.json()["x_user_id"] == "99887766"


async def test_mock_connect_blocked_in_live_mode(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/x/account/connect",
        json={"handle": "testuser"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "oauth/start" in response.json()["detail"].lower()
