from xautopilot.services.providers.base import (
    Discussion,
    EngagementMetrics,
    PublishPayload,
    PublishResult,
    Reply,
)
from xautopilot.services.providers.base import PlatformProvider  # noqa: F401 — typing aid


class PublishNotApprovedError(Exception):
    """Providers must refuse publish when the payload is not marked approved."""


class MockPlatformProvider:
    """Deterministic provider for tests and offline research runs."""

    def __init__(self, name: str = "mock", discussions: list[Discussion] | None = None):
        self.name = name
        self._discussions = discussions or [
            Discussion(
                provider=name,
                external_id="d1",
                title=f"[{name}] Async Python patterns worth stealing",
                url=f"https://example.com/{name}/d1",
                excerpt="Structured concurrency and backpressure in practice.",
                author="alice",
                score=120.0,
                comment_count=42,
            ),
            Discussion(
                provider=name,
                external_id="d2",
                title=f"[{name}] Why browser-first beats brittle APIs",
                url=f"https://example.com/{name}/d2",
                excerpt="Public web interfaces as a durable integration surface.",
                author="bob",
                score=80.0,
                comment_count=15,
            ),
        ]
        self._by_id = {d.external_id: d for d in self._discussions}

    async def search_discussions(self, query: str, *, limit: int = 20) -> list[Discussion]:
        q = query.lower().strip()
        matched = [
            d
            for d in self._discussions
            if not q or q in d.title.lower() or q in d.excerpt.lower()
        ]
        return matched[:limit]

    async def get_discussion(self, external_id: str) -> Discussion:
        if external_id not in self._by_id:
            raise KeyError(f"Unknown discussion: {external_id}")
        return self._by_id[external_id]

    async def list_replies(self, external_id: str, *, limit: int = 50) -> list[Reply]:
        await self.get_discussion(external_id)
        return [
            Reply(
                provider=self.name,
                external_id=f"{external_id}-r1",
                parent_id=external_id,
                author="carol",
                text="Agree — the durable interface is the public web.",
                score=10.0,
            )
        ][:limit]

    async def publish(self, draft: PublishPayload) -> PublishResult:
        if not draft.approved:
            raise PublishNotApprovedError("Human approval required before publish")
        return PublishResult(external_id="mock-published-1", url="https://example.com/p/1")

    async def get_engagement(self, external_id: str) -> EngagementMetrics:
        return EngagementMetrics(impressions=1000, likes=50, replies=8, reposts=3, bookmarks=12)
