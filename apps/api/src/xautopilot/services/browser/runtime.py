from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PageContent:
    url: str
    title: str
    text: str
    html: str = ""
    screenshot_path: str | None = None
    metadata: dict = field(default_factory=dict)


class BrowserRuntime(Protocol):
    """Interact with public websites as a human would. No business logic."""

    async def open(self, url: str) -> PageContent: ...

    async def search(self, site: str, query: str) -> list[PageContent]: ...

    async def screenshot(self, label: str) -> str: ...

    async def ensure_logged_in(self, site: str) -> bool: ...
