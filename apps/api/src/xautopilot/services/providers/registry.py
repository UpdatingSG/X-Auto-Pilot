from collections.abc import Callable

from xautopilot.services.providers.base import Discussion, PlatformProvider
from xautopilot.services.providers.mock import MockPlatformProvider

ProviderFactory = Callable[[], PlatformProvider]

_REGISTRY: dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory) -> None:
    _REGISTRY[name] = factory


def get_provider(name: str) -> PlatformProvider:
    try:
        factory = _REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown provider '{name}'. Known: {known}") from exc
    return factory()


def list_provider_names() -> list[str]:
    return sorted(_REGISTRY)


def _hn_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="hacker_news",
        discussions=[
            Discussion(
                provider="hacker_news",
                external_id="hn-1",
                title="Show HN: Browser-first content research",
                url="https://news.ycombinator.com/item?id=1",
                excerpt="Collect discussions without official social APIs.",
                author="hn_user",
                score=400.0,
                comment_count=120,
            )
        ],
    )


def _github_trending_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="github_trending",
        discussions=[
            Discussion(
                provider="github_trending",
                external_id="gh-1",
                title="trending/playwright-helpers",
                url="https://github.com/example/playwright-helpers",
                excerpt="Utilities for resilient public-web scraping sessions.",
                author="example",
                score=900.0,
                comment_count=0,
            )
        ],
    )


def _devto_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="devto",
        discussions=[
            Discussion(
                provider="devto",
                external_id="dev-1",
                title="Humanizing AI drafts for technical audiences",
                url="https://dev.to/example/humanizing-ai-drafts",
                excerpt="A practical checklist before you hit publish.",
                author="dev_author",
                score=55.0,
                comment_count=9,
            )
        ],
    )


def _reddit_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="reddit_browser",
        discussions=[
            Discussion(
                provider="reddit_browser",
                external_id="r-1",
                title="r/experienceddevs: What changed in your writing process?",
                url="https://reddit.com/r/experienceddevs/comments/1",
                excerpt="Engineers discussing research → draft → review loops.",
                author="u/dev",
                score=210.0,
                comment_count=88,
            )
        ],
    )


def _medium_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="medium",
        discussions=[
            Discussion(
                provider="medium",
                external_id="m-1",
                title="Building a personal knowledge OS for creators",
                url="https://medium.com/@example/knowledge-os",
                excerpt="From daily research notes to reusable story angles.",
                author="example",
                score=33.0,
                comment_count=4,
            )
        ],
    )


def _engineering_blogs_fixture() -> MockPlatformProvider:
    return MockPlatformProvider(
        name="engineering_blogs",
        discussions=[
            Discussion(
                provider="engineering_blogs",
                external_id="blog-1",
                title="How we debug flaky browser automation",
                url="https://engineering.example.com/flaky-browsers",
                excerpt="Screenshots, retries, and isolating business logic.",
                author="eng-blog",
                score=70.0,
                comment_count=0,
            )
        ],
    )


def _x_browser_factory() -> PlatformProvider:
    from xautopilot.services.browser.mock_runtime import MockBrowserRuntime
    from xautopilot.services.providers.x_browser import XBrowserProvider

    return XBrowserProvider(MockBrowserRuntime())


def ensure_default_providers() -> None:
    """Idempotent registration of Phase 1 provider names."""
    defaults: dict[str, ProviderFactory] = {
        "mock": lambda: MockPlatformProvider(),
        "hacker_news": _hn_fixture,
        "github_trending": _github_trending_fixture,
        "devto": _devto_fixture,
        "reddit_browser": _reddit_fixture,
        "medium": _medium_fixture,
        "engineering_blogs": _engineering_blogs_fixture,
        "x_browser": _x_browser_factory,
    }
    for name, factory in defaults.items():
        if name not in _REGISTRY:
            register_provider(name, factory)


ensure_default_providers()
