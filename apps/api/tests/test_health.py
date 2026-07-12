"""Slice 1: API is alive and reports its status."""

from httpx import ASGITransport, AsyncClient

from xautopilot.main import app


async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "xautopilot-api"}


async def test_ping_returns_plaintext_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert response.text == "ok"
