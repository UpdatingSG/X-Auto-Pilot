from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.config import settings
from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.x_account import (
    OAuthCompleteRequest,
    OAuthStartResponse,
    TokenRefreshResponse,
    XAccountConnectRequest,
    XAccountResponse,
)
from xautopilot.services.x_account_service import (
    XAccountNotFoundError,
    connect_mock_account,
    disconnect_x_account,
    get_x_account,
)
from xautopilot.services.x_oauth_service import (
    OAuthConfigError,
    OAuthExchangeError,
    OAuthStateError,
    OAuthUserMismatchError,
    complete_oauth,
    oauth_client_type,
    start_oauth,
    verify_oauth_credentials,
)
from xautopilot.services.x_token_service import (
    XAccountNeedsReauthError,
    XTokenRefreshError,
    refresh_token_if_needed,
)

router = APIRouter(prefix="/v1/x", tags=["x-account"])


@router.get("/config")
async def x_connection_config(current_user: User = Depends(get_current_user)):
    cred_error = await verify_oauth_credentials() if settings.x_api_mode == "live" else None
    return {
        "connection_mode": settings.x_api_mode,
        "oauth_client_type": oauth_client_type(),
        "redirect_uri": settings.x_redirect_uri,
        "credentials_ok": cred_error is None,
        "credentials_hint": cred_error,
    }


@router.get("/account", response_model=XAccountResponse)
async def read_x_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        account = await get_x_account(db, current_user.id)
    except XAccountNotFoundError:
        raise HTTPException(status_code=404, detail="X account not connected") from None
    return XAccountResponse.model_validate(account)


@router.post("/oauth/start", response_model=OAuthStartResponse)
async def oauth_start(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if settings.x_api_mode == "mock":
        raise HTTPException(
            status_code=400,
            detail="OAuth is disabled in mock mode. Use POST /v1/x/account/connect or set X_API_MODE=live.",
        )
    try:
        result = await start_oauth(db, current_user.id)
    except OAuthConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return OAuthStartResponse(authorization_url=result.authorization_url, state=result.state)


@router.post("/oauth/complete", response_model=XAccountResponse)
async def oauth_complete(
    data: OAuthCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete OAuth after Twitter redirects to the frontend callback page."""
    if settings.x_api_mode == "mock":
        raise HTTPException(status_code=400, detail="OAuth is disabled in mock mode.")
    try:
        await complete_oauth(db, state=data.state, code=data.code, expected_user_id=current_user.id)
        account = await get_x_account(db, current_user.id)
    except OAuthStateError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state. Try connecting again.") from None
    except OAuthUserMismatchError:
        raise HTTPException(status_code=403, detail="OAuth state does not match current user") from None
    except OAuthExchangeError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"X authorization failed: {exc}") from None
    return XAccountResponse.model_validate(account)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        await complete_oauth(db, state=state, code=code)
    except OAuthStateError:
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings/x?error=invalid_state",
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings/x?error=oauth_failed",
            status_code=302,
        )
    return RedirectResponse(url=f"{settings.frontend_url}/settings/x?connected=1", status_code=302)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await disconnect_x_account(db, current_user.id)


@router.post("/account/connect", response_model=XAccountResponse)
async def connect_x_account(
    data: XAccountConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if settings.x_api_mode != "mock":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /v1/x/oauth/start to connect with X in live mode.",
        )
    account = await connect_mock_account(
        db,
        current_user.id,
        data.handle,
        data.x_user_id,
        token_expires_at=data.token_expires_at,
    )
    return XAccountResponse.model_validate(account)


@router.post("/account/refresh", response_model=TokenRefreshResponse)
async def refresh_x_account_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        refreshed = await refresh_token_if_needed(db, current_user.id)
    except XAccountNotFoundError:
        raise HTTPException(status_code=404, detail="X account not connected") from None
    except XAccountNeedsReauthError:
        raise HTTPException(
            status_code=401,
            detail="X session expired. Reconnect your account in Settings.",
        ) from None
    except XTokenRefreshError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return TokenRefreshResponse(refreshed=refreshed)
