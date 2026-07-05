import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xautopilot.config import settings
from xautopilot.database import Base, get_db
from xautopilot.main import app
from xautopilot.models import content, knowledge, llm_usage, metrics_sync_job, oauth_pkce_state, post_metrics, published_post, reply_target, schedule, user, voice_profile, x_account  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def force_mock_x_api_mode(request, monkeypatch):
    """Tests use mock X by default; test_x_oauth.py overrides to live."""
    if "test_x_oauth.py" in str(request.fspath):
        return
    monkeypatch.setattr(settings, "x_api_mode", "mock")


@pytest.fixture(autouse=True)
def force_mock_llm_mode(request, monkeypatch):
    """Tests use mock LLM by default; test_openai_llm.py overrides to live."""
    if "test_openai_llm.py" in str(request.fspath):
        return
    monkeypatch.setattr(settings, "llm_mode", "mock")


@pytest.fixture(autouse=True)
def disable_background_worker(request, monkeypatch):
    """Tests disable APScheduler; test_worker.py manages worker explicitly."""
    if "test_worker.py" in str(request.fspath):
        return
    monkeypatch.setattr(settings, "worker_enabled", False)


@pytest.fixture
async def client():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
