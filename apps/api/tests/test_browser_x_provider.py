import pytest

from xautopilot.services.browser import MockBrowserRuntime
from xautopilot.services.providers.base import PublishPayload
from xautopilot.services.providers.mock import PublishNotApprovedError
from xautopilot.services.providers.x_browser import XBrowserProvider


@pytest.mark.asyncio
async def test_x_browser_search_uses_runtime():
    runtime = MockBrowserRuntime()
    provider = XBrowserProvider(runtime)

    results = await provider.search_discussions("fastapi", limit=5)

    assert results
    assert results[0].provider == "x_browser"
    assert any(call[0] == "search" for call in runtime.calls)
    assert runtime.calls[0][1][:2] == ("x", "fastapi")


@pytest.mark.asyncio
async def test_x_browser_get_discussion_opens_status_url():
    runtime = MockBrowserRuntime()
    provider = XBrowserProvider(runtime)

    discussion = await provider.get_discussion("12345")

    assert discussion.external_id == "12345"
    open_calls = [c for c in runtime.calls if c[0] == "open"]
    assert open_calls
    assert "12345" in open_calls[0][1][0]


@pytest.mark.asyncio
async def test_x_browser_publish_requires_approval_and_login():
    runtime = MockBrowserRuntime()
    provider = XBrowserProvider(runtime)

    with pytest.raises(PublishNotApprovedError):
        await provider.publish(PublishPayload(text="hi", approved=False))

    result = await provider.publish(PublishPayload(text="hi", approved=True))
    assert result.external_id == "x-browser-published"
    assert any(c[0] == "ensure_logged_in" for c in runtime.calls)
