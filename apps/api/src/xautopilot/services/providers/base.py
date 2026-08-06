from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Discussion:
    provider: str
    external_id: str
    title: str
    url: str
    excerpt: str
    author: str | None = None
    score: float = 0.0
    comment_count: int = 0
    canonical_key: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.canonical_key:
            object.__setattr__(self, "canonical_key", f"{self.provider}:{self.external_id}")


@dataclass(frozen=True)
class Reply:
    provider: str
    external_id: str
    parent_id: str
    author: str | None
    text: str
    score: float = 0.0


@dataclass(frozen=True)
class EngagementMetrics:
    impressions: int = 0
    likes: int = 0
    replies: int = 0
    reposts: int = 0
    bookmarks: int = 0


@dataclass(frozen=True)
class PublishPayload:
    text: str
    content_type: str = "tweet"
    thread_tweets: list[str] | None = None
    in_reply_to_id: str | None = None
    approved: bool = False


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    url: str | None = None


class PlatformProvider(Protocol):
    """Orchestration depends only on this interface — never on browser vs API."""

    name: str

    async def search_discussions(self, query: str, *, limit: int = 20) -> list[Discussion]: ...

    async def get_discussion(self, external_id: str) -> Discussion: ...

    async def list_replies(self, external_id: str, *, limit: int = 50) -> list[Reply]: ...

    async def publish(self, draft: PublishPayload) -> PublishResult: ...

    async def get_engagement(self, external_id: str) -> EngagementMetrics: ...
