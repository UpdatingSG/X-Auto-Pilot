"""Slice 1: Creator can check whether their X account is connected."""

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_get_x_account_returns_not_connected(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get("/v1/x/account", headers=auth_headers(token))

    assert response.status_code == 404
    assert "not connected" in response.json()["detail"].lower()


async def test_connect_x_account(client: AsyncClient):
    token = await register_and_login(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/x/account/connect",
        json={"handle": "testcreator"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handle"] == "testcreator"
    assert body["connected"] is True

    linked = await client.get("/v1/x/account", headers=headers)
    assert linked.status_code == 200
    assert linked.json()["handle"] == "testcreator"
