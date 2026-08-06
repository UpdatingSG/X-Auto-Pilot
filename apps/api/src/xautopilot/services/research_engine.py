from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from xautopilot.services.providers.base import Discussion, PlatformProvider


@dataclass(frozen=True)
class ResearchInsight:
    summary: str
    source_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResearchReport:
    run_date: date
    topics: list[str]
    discussions: list[Discussion]
    insights: list[ResearchInsight]
    markdown: str


def _rank_key(discussion: Discussion) -> tuple[float, int, str]:
    # Higher score/comments first; stable tie-break on canonical_key
    return (-discussion.score, -discussion.comment_count, discussion.canonical_key)


def dedupe_discussions(discussions: list[Discussion]) -> list[Discussion]:
    """Collapse by canonical_key, keeping the higher-ranked copy."""
    best: dict[str, Discussion] = {}
    for d in discussions:
        key = d.canonical_key or f"{d.provider}:{d.url}"
        existing = best.get(key)
        if existing is None or _rank_key(d) < _rank_key(existing):
            best[key] = d
    return sorted(best.values(), key=_rank_key)


def rank_discussions(discussions: list[Discussion]) -> list[Discussion]:
    return sorted(discussions, key=_rank_key)


def render_research_markdown(report_date: date, topics: list[str], discussions: list[Discussion], insights: list[ResearchInsight]) -> str:
    lines = [
        f"# Research — {report_date.isoformat()}",
        "",
        "## Topics",
        "",
    ]
    for topic in topics:
        lines.append(f"- {topic}")
    lines.extend(["", "## Ranked discussions", ""])
    for i, d in enumerate(discussions, start=1):
        lines.append(
            f"{i}. [{d.title}]({d.url}) — score={d.score:g}, comments={d.comment_count} (`{d.canonical_key}`)"
        )
        if d.excerpt:
            lines.append(f"   - {d.excerpt}")
    lines.extend(["", "## Insights", ""])
    if not insights:
        lines.append("- (none)")
    else:
        for insight in insights:
            refs = ", ".join(insight.source_keys) if insight.source_keys else "n/a"
            lines.append(f"- {insight.summary} [{refs}]")
    lines.append("")
    return "\n".join(lines)


def _stub_insights(discussions: list[Discussion]) -> list[ResearchInsight]:
    if not discussions:
        return []
    top = discussions[0]
    return [
        ResearchInsight(
            summary=f"Top signal: {top.title}",
            source_keys=[top.canonical_key],
        )
    ]


async def run_daily_research(
    topics: list[str],
    providers: list[PlatformProvider],
    *,
    run_date: date | None = None,
    limit_per_query: int = 10,
) -> ResearchReport:
    """Collect → dedupe → rank → insights → markdown. No browser logic here."""
    day = run_date or date.today()
    collected: list[Discussion] = []
    for topic in topics:
        for provider in providers:
            found = await provider.search_discussions(topic, limit=limit_per_query)
            collected.extend(found)

    unique = dedupe_discussions(collected)
    ranked = rank_discussions(unique)
    insights = _stub_insights(ranked)
    markdown = render_research_markdown(day, topics, ranked, insights)
    return ResearchReport(
        run_date=day,
        topics=list(topics),
        discussions=ranked,
        insights=insights,
        markdown=markdown,
    )
