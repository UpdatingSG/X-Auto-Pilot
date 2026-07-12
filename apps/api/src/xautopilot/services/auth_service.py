import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.user import User
from xautopilot.schemas.auth import RegisterRequest

# 10 rounds is the usual production default; keeps verify fast without weakening security much.
BCRYPT_ROUNDS = 10


class EmailAlreadyRegisteredError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def password_needs_rehash(password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) < 3:
        return True
    try:
        rounds = int(parts[2])
    except ValueError:
        return True
    return rounds > BCRYPT_ROUNDS


async def upgrade_password_hash(session: AsyncSession, user: User, password: str) -> None:
    if not password_needs_rehash(user.password_hash):
        return
    user.password_hash = hash_password(password)
    await session.commit()


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    user = User(email=data.email.lower(), password_hash=hash_password(data.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise EmailAlreadyRegisteredError from None
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
