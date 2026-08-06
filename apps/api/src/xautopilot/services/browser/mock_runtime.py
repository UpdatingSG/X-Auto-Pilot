from xautopilot.services.browser.runtime import PageContent


class MockBrowserRuntime:
    """Records interactions for tests; returns fixture pages."""

    def __init__(self, pages: dict[str, PageContent] | None = None):
        self.calls: list[tuple[str, tuple, dict]] = []
        self._pages = pages or {}
        self._logged_in: set[str] = set()

    def _record(self, method: str, *args, **kwargs) -> None:
        self.calls.append((method, args, kwargs))

    async def open(self, url: str) -> PageContent:
        self._record("open", url)
        if url in self._pages:
            return self._pages[url]
        return PageContent(url=url, title="Mock page", text=f"Fixture content for {url}")

    async def search(self, site: str, query: str) -> list[PageContent]:
        self._record("search", site, query)
        return [
            PageContent(
                # Placeholder only — not a real web URL (UI treats *.example as non-links).
                url=f"https://{site}.example/fixture/search?q={query}",
                title=f"[demo] {site} result for {query}",
                text=f"Fixture discussion about {query} on {site} (not live data).",
            )
        ]

    async def screenshot(self, label: str) -> str:
        self._record("screenshot", label)
        path = f"/tmp/mock-screenshot-{label}.png"
        return path

    async def ensure_logged_in(self, site: str) -> bool:
        self._record("ensure_logged_in", site)
        self._logged_in.add(site)
        return True
