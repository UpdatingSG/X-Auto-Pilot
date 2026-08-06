"""X (browser) provider — uses BrowserRuntime only for I/O."""

from xautopilot.services.browser.runtime import BrowserRuntime
from xautopilot.services.providers.base import (
    Discussion,
    EngagementMetrics,
    PublishPayload,
    PublishResult,
    Reply,
)
from xautopilot.services.providers.mock import PublishNotApprovedError


class XBrowserProvider:
    name = "x_browser"

    def __init__(self, runtime: BrowserRuntime):
        self._runtime = runtime

    async def search_discussions(self, query: str, *, limit: int = 20) -> list[Discussion]:
        pages = await self._runtime.search("x", query)
        discussions: list[Discussion] = []
        for i, page in enumerate(pages[:limit]):
            discussions.append(
                Discussion(
                    provider=self.name,
                    external_id=f"x-search-{i}",
                    title=page.title,
                    url=page.url,
                    excerpt=page.text[:280],
                    score=float(max(limit - i, 1)),
                )
            )
        return discussions

    async def get_discussion(self, external_id: str) -> Discussion:
        page = await self._runtime.open(f"https://x.com/i/status/{external_id}")
        return Discussion(
            provider=self.name,
            external_id=external_id,
            title=page.title,
            url=page.url,
            excerpt=page.text[:280],
        )

    async def list_replies(self, external_id: str, *, limit: int = 50) -> list[Reply]:
        await self._runtime.open(f"https://x.com/i/status/{external_id}")
        return [
            Reply(
                provider=self.name,
                external_id=f"{external_id}-reply-0",
                parent_id=external_id,
                author=None,
                text="Mock reply extracted via browser runtime",
            )
        ][:limit]

    async def publish(self, draft: PublishPayload) -> PublishResult:
        if not draft.approved:
            raise PublishNotApprovedError("Human approval required before browser publish")
        await self._runtime.ensure_logged_in("x")
        await self._runtime.open("https://x.com/compose/post")
        return PublishResult(external_id="x-browser-published", url=None)

    async def get_engagement(self, external_id: str) -> EngagementMetrics:
        await self._runtime.open(f"https://x.com/i/status/{external_id}")
        return EngagementMetrics()
