from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.models.x_account import XAccount
from xautopilot.services.crypto_service import decrypt_text, encrypt_text, TokenDecryptionError
from xautopilot.services.x_account_service import XAccountNotFoundError, get_x_account
from xautopilot.services.x_oauth_service import OAuthTokenSet, refresh_access_token

TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


class XAccountNeedsReauthError(Exception):
    pass


class XTokenRefreshError(Exception):
    pass


def token_needs_refresh(account: XAccount, *, now: datetime | None = None) -> bool:
    if account.token_expires_at is None:
        return False
    now = now or datetime.now(UTC)
    expires_at = account.token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return now >= expires_at - TOKEN_REFRESH_BUFFER


async def apply_token_set(session: AsyncSession, account: XAccount, tokens: OAuthTokenSet) -> None:
    account.access_token_enc = encrypt_text(tokens.access_token)
    if tokens.refresh_token:
        account.refresh_token_enc = encrypt_text(tokens.refresh_token)
    if tokens.expires_in:
        account.token_expires_at = datetime.now(UTC) + timedelta(seconds=tokens.expires_in)
    account.needs_reauth = False
    await session.flush()


async def _refresh_account_tokens(session: AsyncSession, account: XAccount) -> None:
    if not account.refresh_token_enc:
        account.needs_reauth = True
        await session.flush()
        raise XAccountNeedsReauthError("No refresh token; reconnect X account")

    try:
        tokens = await refresh_access_token(decrypt_text(account.refresh_token_enc))
    except TokenDecryptionError:
        account.needs_reauth = True
        await session.flush()
        raise XAccountNeedsReauthError("Encryption key changed; reconnect X account") from None
    except Exception as exc:
        account.needs_reauth = True
        await session.flush()
        raise XTokenRefreshError(str(exc)) from exc

    await apply_token_set(session, account, tokens)


async def refresh_token_if_needed(session: AsyncSession, user_id: UUID) -> bool:
    account = await get_x_account(session, user_id)
    if account.needs_reauth:
        raise XAccountNeedsReauthError("X account needs reauthorization")
    if settings.x_api_mode == "mock" and not token_needs_refresh(account):
        return False
    if not token_needs_refresh(account):
        return False
    await _refresh_account_tokens(session, account)
    await session.commit()
    return True


async def get_valid_access_token(session: AsyncSession, user_id: UUID) -> str:
    account = await get_x_account(session, user_id)
    if account.needs_reauth:
        raise XAccountNeedsReauthError("X account needs reauthorization")
    if token_needs_refresh(account):
        await _refresh_account_tokens(session, account)
        await session.commit()
        await session.refresh(account)
    try:
        return decrypt_text(account.access_token_enc)
    except TokenDecryptionError:
        account.needs_reauth = True
        await session.commit()
        raise XAccountNeedsReauthError("Encryption key changed; reconnect X account") from None


async def mark_account_needs_reauth(session: AsyncSession, user_id: UUID) -> None:
    try:
        account = await get_x_account(session, user_id)
    except XAccountNotFoundError:
        return
    account.needs_reauth = True
    await session.commit()
