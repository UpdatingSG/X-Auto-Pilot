from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from xautopilot.config import settings
from xautopilot.database_url import prepare_asyncpg_url

_db_url, _db_connect_args = prepare_asyncpg_url(settings.database_url)
engine = create_async_engine(_db_url, echo=False, connect_args=_db_connect_args)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
