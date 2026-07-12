from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from xautopilot.services.auth_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    register_user,
    upgrade_password_hash,
)
from xautopilot.services.token_service import create_access_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    await upgrade_password_hash(db, user, data.password)
    return TokenResponse(access_token=create_access_token(user.id), email=user.email)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
