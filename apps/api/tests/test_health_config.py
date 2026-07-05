"""Health config endpoint."""

from httpx import AsyncClient


async def test_health_config_reports_development(client: AsyncClient):
    response = await client.get("/health/config")

    assert response.status_code == 200
    body = response.json()
    assert body["app_env"] == "development"
    assert body["encryption_key_source"] in (
        "token_encryption_key",
        "secret_key_derived_dev_only",
    )
    assert isinstance(body["issues"], list)
    assert isinstance(body["secrets_ok"], bool)
