from datetime import date

import pytest

from xautopilot.services.providers.base import Discussion
from xautopilot.services.providers.mock import MockPlatformProvider
from xautopilot.services.research_engine import (
    dedupe_discussions,
    rank_discussions,
    run_daily_research,
)


def test_dedupe_keeps_higher_score():
    a = Discussion(
        provider="mock",
        external_id="1",
        title="A",
        url="https://example.com/1",
        excerpt="",
        score=10,
        comment_count=1,
        canonical_key="same",
    )
    b = Discussion(
        provider="mock",
        external_id="2",
        title="B",
        url="https://example.com/2",
        excerpt="",
        score=50,
        comment_count=1,
        canonical_key="same",
    )
    result = dedupe_discussions([a, b])
    assert len(result) == 1
    assert result[0].title == "B"


def test_rank_is_deterministic():
    items = [
        Discussion(
            provider="mock",
            external_id="a",
            title="a",
            url="https://example.com/a",
            excerpt="",
            score=10,
            comment_count=5,
        ),
        Discussion(
            provider="mock",
            external_id="b",
            title="b",
            url="https://example.com/b",
            excerpt="",
            score=10,
            comment_count=9,
        ),
    ]
    ranked = rank_discussions(items)
    assert ranked[0].external_id == "b"
    assert rank_discussions(list(reversed(items)))[0].external_id == "b"


@pytest.mark.asyncio
async def test_run_daily_research_markdown_shape():
    providers = [
        MockPlatformProvider(name="mock"),
        MockPlatformProvider(
            name="hacker_news",
            discussions=[
                Discussion(
                    provider="hacker_news",
                    external_id="hn-99",
                    title="HN special",
                    url="https://news.ycombinator.com/item?id=99",
                    excerpt="signal",
                    score=999,
                    comment_count=1,
                )
            ],
        ),
    ]
    report = await run_daily_research(
        topics=["python"],
        providers=providers,
        run_date=date(2026, 8, 6),
    )

    assert report.run_date == date(2026, 8, 6)
    assert report.topics == ["python"]
    assert report.discussions
    assert "# Research — 2026-08-06" in report.markdown
    assert "## Topics" in report.markdown
    assert "## Ranked discussions" in report.markdown
    assert "## Insights" in report.markdown
    assert report.insights
