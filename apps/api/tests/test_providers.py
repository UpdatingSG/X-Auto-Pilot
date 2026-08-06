import pytest

from xautopilot.services.providers import get_provider, list_provider_names
from xautopilot.services.providers.base import Discussion, PublishPayload
from xautopilot.services.providers.mock import MockPlatformProvider, PublishNotApprovedError
from xautopilot.services.providers.registry import register_provider


@pytest.mark.asyncio
async def test_mock_provider_search_filters_by_query():
    provider = MockPlatformProvider()
    results = await provider.search_discussions("browser-first")
    assert len(results) == 1
    assert "browser-first" in results[0].title.lower()


@pytest.mark.asyncio
async def test_mock_provider_refuses_unapproved_publish():
    provider = MockPlatformProvider()
    with pytest.raises(PublishNotApprovedError):
        await provider.publish(PublishPayload(text="hello", approved=False))


@pytest.mark.asyncio
async def test_mock_provider_publishes_when_approved():
    provider = MockPlatformProvider()
    result = await provider.publish(PublishPayload(text="hello", approved=True))
    assert result.external_id.startswith("mock-")


def test_registry_lists_phase1_providers():
    names = list_provider_names()
    for expected in (
        "mock",
        "hacker_news",
        "github_trending",
        "devto",
        "reddit_browser",
        "medium",
        "engineering_blogs",
        "x_browser",
    ):
        assert expected in names


def test_registry_get_provider_unknown():
    with pytest.raises(KeyError, match="Unknown provider"):
        get_provider("does-not-exist")


@pytest.mark.asyncio
async def test_registry_resolves_hacker_news():
    provider = get_provider("hacker_news")
    results = await provider.search_discussions("browser")
    assert results
    assert results[0].provider == "hacker_news"


def test_register_custom_provider():
    register_provider(
        "custom_test",
        lambda: MockPlatformProvider(
            name="custom_test",
            discussions=[
                Discussion(
                    provider="custom_test",
                    external_id="c1",
                    title="Custom",
                    url="https://example.com/c1",
                    excerpt="x",
                )
            ],
        ),
    )
    assert "custom_test" in list_provider_names()
    assert get_provider("custom_test").name == "custom_test"
