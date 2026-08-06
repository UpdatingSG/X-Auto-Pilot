"""Browser runtime — transport only; no ranking, writing, or approval logic."""

from xautopilot.services.browser.mock_runtime import MockBrowserRuntime
from xautopilot.services.browser.runtime import BrowserRuntime, PageContent

__all__ = ["BrowserRuntime", "MockBrowserRuntime", "PageContent"]
