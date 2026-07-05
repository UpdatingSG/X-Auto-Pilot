from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.x_account import XAccount
from xautopilot.services.crypto_service import encrypt_text


class XAccountNotFoundError(Exception):
    pass


async def get_x_account(session: AsyncSession, user_id: UUID) -> XAccount:
    result = await session.execute(
        select(XAccount).where(XAccount.user_id == user_id, XAccount.is_active.is_(True))
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise XAccountNotFoundError
    return account


async def connect_mock_account(
    session: AsyncSession,
    user_id: UUID,
    handle: str,
    x_user_id: str | None = None,
    token_expires_at: datetime | None = None,
) -> XAccount:
    result = await session.execute(select(XAccount).where(XAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    resolved_x_user_id = x_user_id or f"mock-{handle}"
    default_expiry = datetime.now(UTC) + timedelta(hours=2)
    resolved_expiry = token_expires_at
    if resolved_expiry is not None and resolved_expiry.tzinfo is None:
        resolved_expiry = resolved_expiry.replace(tzinfo=UTC)

    if account is None:
        account = XAccount(
            user_id=user_id,
            x_user_id=resolved_x_user_id,
            handle=handle.lstrip("@"),
            access_token_enc=encrypt_text(f"mock-access-{handle}"),
            refresh_token_enc=encrypt_text(f"mock-refresh-{handle}"),
            token_expires_at=resolved_expiry or default_expiry,
            scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
            needs_reauth=False,
        )
        session.add(account)
    else:
        account.handle = handle.lstrip("@")
        account.x_user_id = resolved_x_user_id
        account.access_token_enc = encrypt_text(f"mock-access-{handle}")
        account.refresh_token_enc = encrypt_text(f"mock-refresh-{handle}")
        account.token_expires_at = resolved_expiry or default_expiry
        account.needs_reauth = False
        account.is_active = True

    await session.commit()
    await session.refresh(account)
    return account


async def upsert_x_account_from_oauth(
    session: AsyncSession,
    user_id: UUID,
    x_user_id: str,
    handle: str,
    access_token_enc: bytes,
    refresh_token_enc: bytes | None,
    token_expires_at: datetime | None,
    scopes: list[str],
) -> XAccount:
    result = await session.execute(select(XAccount).where(XAccount.user_id == user_id))
    account = result.scalar_one_or_none()

    if account is None:
        account = XAccount(
            user_id=user_id,
            x_user_id=x_user_id,
            handle=handle.lstrip("@"),
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            token_expires_at=token_expires_at,
            scopes=scopes,
            needs_reauth=False,
        )
        session.add(account)
    else:
        account.x_user_id = x_user_id
        account.handle = handle.lstrip("@")
        account.access_token_enc = access_token_enc
        account.refresh_token_enc = refresh_token_enc
        account.token_expires_at = token_expires_at
        account.scopes = scopes
        account.is_active = True
        account.needs_reauth = False

    await session.flush()
    return account


async def disconnect_x_account(session: AsyncSession, user_id: UUID) -> None:
    result = await session.execute(select(XAccount).where(XAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    if account is not None:
        await session.delete(account)
        await session.commit()
