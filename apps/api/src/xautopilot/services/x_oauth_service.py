import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.models.oauth_pkce_state import OAuthPkceState
from xautopilot.services.crypto_service import encrypt_text
from xautopilot.services.x_account_service import upsert_x_account_from_oauth


def oauth_client_type(client_id: str | None = None) -> str:
    """Decode X OAuth client id suffix: :ci = confidential, :na = public (native)."""
    client_id = client_id or settings.x_client_id
    try:
        padded = client_id + "=" * (-len(client_id) % 4)
        decoded = base64.b64decode(padded).decode("ascii")
        if decoded.endswith(":na"):
            return "public"
        if decoded.endswith(":ci"):
            return "confidential"
    except Exception:
        pass
    return "confidential" if settings.x_client_secret else "public"


class OAuthConfigError(Exception):
    pass


class OAuthStateError(Exception):
    pass


class OAuthUserMismatchError(Exception):
    pass


class OAuthExchangeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class OAuthStartResult:
    authorization_url: str
    state: str


@dataclass
class OAuthTokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    scope: str | None


@dataclass
class XUserProfile:
    x_user_id: str
    handle: str


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "scope": settings.x_oauth_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{settings.x_oauth_authorize_url}?{urlencode(params)}"


async def start_oauth(session: AsyncSession, user_id: UUID) -> OAuthStartResult:
    if not settings.x_client_id:
        raise OAuthConfigError("X_CLIENT_ID is not configured")

    state = secrets.token_urlsafe(32)
    verifier = _generate_code_verifier()
    challenge = _code_challenge(verifier)
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    session.add(
        OAuthPkceState(
            user_id=user_id,
            state=state,
            code_verifier=verifier,
            expires_at=expires_at,
        )
    )
    await session.commit()

    return OAuthStartResult(
        authorization_url=build_authorization_url(state, challenge),
        state=state,
    )


def _basic_auth_header() -> str:
    """Confidential clients: Base64(urlencode(client_id):urlencode(client_secret))."""
    if not settings.x_client_secret:
        raise OAuthExchangeError(
            "X_CLIENT_SECRET is missing. Regenerate OAuth 2.0 Client Secret in the X Developer Portal."
        )
    cid = quote(settings.x_client_id, safe="")
    secret = quote(settings.x_client_secret, safe="")
    credentials = f"{cid}:{secret}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


async def verify_oauth_credentials() -> str | None:
    """Return None if credentials look valid, else an error hint."""
    if not settings.x_client_id:
        return "X_CLIENT_ID is not set"
    client_type = oauth_client_type()
    data = {
        "grant_type": "authorization_code",
        "code": "credential-check",
        "redirect_uri": settings.x_redirect_uri,
        "code_verifier": "credential-check",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if client_type == "confidential":
        headers["Authorization"] = _basic_auth_header()
    else:
        data["client_id"] = settings.x_client_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(settings.x_oauth_token_url, data=data, headers=headers)
    if response.status_code == 401:
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if "authorization header" in str(body).lower():
            return (
                "X rejected your OAuth 2.0 Client ID/Secret. In Developer Portal → Keys and tokens, "
                "regenerate OAuth 2.0 Client Secret (not API Key/Secret) and update apps/api/.env. "
                f"App type detected: {client_type}."
            )
    return None


async def _exchange_code(code: str, code_verifier: str) -> OAuthTokenSet:
    client_type = oauth_client_type()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.x_redirect_uri,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    if client_type == "public":
        data["client_id"] = settings.x_client_id
    else:
        headers["Authorization"] = _basic_auth_header()
        data["client_id"] = settings.x_client_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.x_oauth_token_url,
            data=data,
            headers=headers,
        )
        if response.status_code >= 400:
            try:
                detail = response.json()
                error = detail.get("error_description") or detail.get("error") or response.text
            except Exception:
                error = response.text
            raise OAuthExchangeError(f"X token exchange failed: {error}")
        payload = response.json()

    return OAuthTokenSet(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
        scope=payload.get("scope"),
    )


async def refresh_access_token(refresh_token: str) -> OAuthTokenSet:
    client_type = oauth_client_type()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.x_client_id,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    if client_type == "confidential":
        headers["Authorization"] = _basic_auth_header()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.x_oauth_token_url,
            data=data,
            headers=headers,
        )
        if response.status_code >= 400:
            try:
                detail = response.json()
                error = detail.get("error_description") or detail.get("error") or response.text
            except Exception:
                error = response.text
            raise OAuthExchangeError(f"X token refresh failed: {error}")
        payload = response.json()

    return OAuthTokenSet(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
        scope=payload.get("scope"),
    )


async def _fetch_x_user(access_token: str) -> XUserProfile:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.x_api_base_url}/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"user.fields": "username"},
        )
        response.raise_for_status()
        user = response.json()["data"]
    return XUserProfile(x_user_id=user["id"], handle=user["username"])


async def complete_oauth(
    session: AsyncSession,
    state: str,
    code: str,
    expected_user_id: UUID | None = None,
) -> UUID:
    result = await session.execute(
        select(OAuthPkceState).where(OAuthPkceState.state == state)
    )
    pkce = result.scalar_one_or_none()
    if pkce is None:
        raise OAuthStateError
    expires_at = pkce.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise OAuthStateError
    if expected_user_id is not None and pkce.user_id != expected_user_id:
        raise OAuthUserMismatchError

    tokens = await _exchange_code(code, pkce.code_verifier)
    profile = await _fetch_x_user(tokens.access_token)

    scopes = (tokens.scope or settings.x_oauth_scopes).split()
    expires_at = None
    if tokens.expires_in:
        expires_at = datetime.now(UTC) + timedelta(seconds=tokens.expires_in)

    await upsert_x_account_from_oauth(
        session,
        user_id=pkce.user_id,
        x_user_id=profile.x_user_id,
        handle=profile.handle,
        access_token_enc=encrypt_text(tokens.access_token),
        refresh_token_enc=encrypt_text(tokens.refresh_token) if tokens.refresh_token else None,
        token_expires_at=expires_at,
        scopes=scopes,
    )

    await session.execute(delete(OAuthPkceState).where(OAuthPkceState.id == pkce.id))
    await session.commit()
    return pkce.user_id
