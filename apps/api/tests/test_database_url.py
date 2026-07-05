"""Tests for asyncpg DATABASE_URL normalization."""

from xautopilot.database_url import prepare_asyncpg_url


def test_strips_sslmode_and_sets_ssl_connect_arg():
    raw = (
        "postgresql+asyncpg://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
    )
    url, args = prepare_asyncpg_url(raw)
    assert "sslmode" not in url
    assert args == {"ssl": True}


def test_converts_postgresql_scheme_to_asyncpg():
    raw = "postgresql://user:pass@host/db?sslmode=require"
    url, args = prepare_asyncpg_url(raw)
    assert url.startswith("postgresql+asyncpg://")
    assert args == {"ssl": True}


def test_sqlite_url_unchanged():
    raw = "sqlite+aiosqlite:///:memory:"
    url, args = prepare_asyncpg_url(raw)
    assert url == raw
    assert args == {}
