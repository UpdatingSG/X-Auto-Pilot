import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.models.knowledge import KnowledgeItem, KnowledgeSource
from xautopilot.schemas.knowledge import SourceCreate


@dataclass
class NormalizedItem:
    external_id: str
    title: str
    url: str | None
    author: str | None
    content: str | None
    published_at: datetime | None


class SourceNotFoundError(Exception):
    pass


def make_external_id(url: str | None, title: str) -> str:
    key = url or title
    return hashlib.sha256(key.encode()).hexdigest()


async def fetch_rss_items(url: str) -> list[NormalizedItem]:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        feed = feedparser.parse(response.text)

    items: list[NormalizedItem] = []
    for entry in feed.entries:
        link = entry.get("link")
        title = entry.get("title", "Untitled")
        summary = entry.get("summary") or entry.get("description")
        published = entry.get("published_parsed")
        published_at = None
        if published:
            published_at = datetime(*published[:6])

        items.append(
            NormalizedItem(
                external_id=make_external_id(link, title),
                title=title,
                url=link,
                author=entry.get("author"),
                content=summary,
                published_at=published_at,
            )
        )
    return items


async def list_sources(session: AsyncSession, user_id: UUID) -> list[KnowledgeSource]:
    result = await session.execute(
        select(KnowledgeSource)
        .where(KnowledgeSource.user_id == user_id)
        .order_by(KnowledgeSource.created_at.desc())
    )
    return list(result.scalars().all())


async def create_source(
    session: AsyncSession, user_id: UUID, data: SourceCreate
) -> KnowledgeSource:
    source = KnowledgeSource(
        user_id=user_id,
        source_type=data.source_type,
        name=data.name,
        config=data.config,
        fetch_interval_minutes=data.fetch_interval_minutes,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def get_source(session: AsyncSession, user_id: UUID, source_id: UUID) -> KnowledgeSource:
    result = await session.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.user_id == user_id,
        )
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise SourceNotFoundError
    return source


async def ingest_from_source(session: AsyncSession, user_id: UUID, source_id: UUID) -> dict:
    source = await get_source(session, user_id, source_id)

    if source.source_type == "rss":
        url = source.config.get("url")
        if not url:
            return {"items_ingested": 0, "items_skipped": 0}
        normalized = await fetch_rss_items(url)
    else:
        normalized = []

    ingested = 0
    skipped = 0
    for item in normalized:
        existing = await session.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.user_id == user_id,
                KnowledgeItem.external_id == item.external_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        session.add(
            KnowledgeItem(
                user_id=user_id,
                source_id=source.id,
                external_id=item.external_id,
                title=item.title,
                url=item.url,
                author=item.author,
                content_raw=item.content,
                published_at=item.published_at,
            )
        )
        ingested += 1

    source.last_fetched_at = datetime.now(UTC)
    await session.commit()
    return {"items_ingested": ingested, "items_skipped": skipped}


async def list_knowledge_items(session: AsyncSession, user_id: UUID) -> list[KnowledgeItem]:
    result = await session.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.user_id == user_id)
        .order_by(KnowledgeItem.fetched_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def list_timely_knowledge_items(
    session: AsyncSession, user_id: UUID, *, hours: int = 48, limit: int = 10
) -> list[dict]:
    """Return recent knowledge items with snippets for timely-take planning."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    result = await session.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.user_id == user_id)
        .order_by(KnowledgeItem.published_at.desc().nullslast(), KnowledgeItem.fetched_at.desc())
        .limit(limit * 2)
    )
    items: list[dict] = []
    for item in result.scalars().all():
        published = item.published_at
        if published and published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        fetched = item.fetched_at
        if fetched and fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=UTC)
        ref_time = published or fetched
        if ref_time and ref_time < cutoff:
            continue
        snippet = (item.content_raw or "")[:300].strip()
        items.append(
            {
                "title": item.title,
                "url": item.url,
                "snippet": snippet or item.title,
                "published_at": ref_time.isoformat() if ref_time else None,
            }
        )
        if len(items) >= limit:
            break
    return items
