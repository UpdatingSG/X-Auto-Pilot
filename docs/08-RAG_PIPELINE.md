# RAG Pipeline

## Overview

Retrieval-Augmented Generation grounds all content in real information — reducing hallucination and enabling timely, relevant tweets.

```
Sources → Ingest → Chunk → Embed → Store (pgvector)
                                        ↓
Content Idea → Query Builder → Retrieve → Rerank → Context Pack → Writer Agent
```

## Ingestion Pipeline

### 1. Fetch

| Source | Fetcher | Normalized Fields |
|--------|---------|-------------------|
| RSS | `feedparser` | title, url, content, published_at, author |
| Hacker News | Firebase API | title, url, score, comments |
| Reddit | PRAW/API | title, selftext, url, score, subreddit |
| Dev.to | REST API | title, body, tags, published_at |
| Manual notes | User input | title, content, tags |

### 2. Normalize

```python
class NormalizedItem(BaseModel):
    external_id: str      # sha256(url) or api id
    title: str
    content: str          # plain text, HTML stripped
    url: str | None
    author: str | None
    published_at: datetime | None
    source_metadata: dict # scores, tags, etc.
```

### 3. Deduplicate

Two-stage:

1. **Exact:** `external_id` unique constraint
2. **Semantic:** embedding cosine similarity > 0.95 to existing item in last 7 days → merge as duplicate, keep higher-scored source

### 4. Summarize

For items > 2000 tokens, generate summary via `gpt-5.5-mini`:

```
Summarize in 3-5 sentences. Extract key facts, statistics, and opinions.
Preserve technical accuracy. Output JSON: {summary, key_facts[], statistics[]}
```

Store summary in `knowledge_items.content_summary`.

### 5. Chunk

```python
CHUNK_CONFIG = {
    "chunk_size": 512,      # tokens
    "chunk_overlap": 64,
    "separator": "\n\n",
}
```

Use `tiktoken` for token counting. Each chunk stores:
- `chunk_index`
- `content`
- `metadata`: `{item_id, title, url, published_at, source_type}`

### 6. Embed

```python
model = "text-embedding-3-small"  # 1536 dimensions
batch_size = 100
```

Batch embed all chunks for an ingestion run. Store in `knowledge_chunks.embedding`.

## Retrieval Pipeline

### Query Construction

Different strategies per content type:

**Tweet/Thread from cluster:**
```python
query = f"{cluster.title} {cluster.summary} {' '.join(cluster.insights[:3])}"
```

**Reply:**
```python
query = f"{target.tweet_text} {target.author_handle} engineering"
```

**Ad-hoc regenerate:**
```python
query = f"{idea.title} {idea.hook_idea} {idea.category}"
```

### Hybrid Search

Combine vector + metadata filtering:

```sql
SELECT kc.id, kc.content, kc.metadata,
       1 - (kc.embedding <=> $1::vector) AS similarity
FROM knowledge_chunks kc
JOIN knowledge_items ki ON ki.id = kc.item_id
WHERE ki.user_id = $2
  AND ki.fetched_at > NOW() - INTERVAL '7 days'
  AND 1 - (kc.embedding <=> $1::vector) > 0.7
ORDER BY similarity DESC
LIMIT 20;
```

### Rerank

Retrieve top 20, rerank to top 5 with cross-encoder or LLM:

```python
async def rerank(query: str, chunks: list[Chunk], top_k: int = 5) -> list[Chunk]:
    # Option A (MVP): LLM rerank via gpt-5.5-mini
    # Option B (scale): Cohere rerank or local cross-encoder
```

Rerank prompt:
```
Given the content idea: "{idea}"
Rank these passages by relevance for writing a {content_type}.
Return top 5 IDs in order.
```

### Context Pack

Final context injected into writer prompt:

```xml
<context>
<chunk id="uuid1" source="Hacker News" date="2026-07-03">
Redis hot key contention causes 40% latency spikes during peak...
</chunk>
<chunk id="uuid2" source="engineering.blog" date="2026-07-02">
Dragonfly migration reduced p99 by 3x but cache warming took 45 min...
</chunk>
</context>
```

Writer must cite `rag_source_ids` — validated post-generation.

## Research Agent RAG

Separate from writer RAG — operates on item-level:

1. Fetch all items from last 48h
2. Embed titles + summaries
3. HDBSCAN clustering (min_cluster_size=2)
4. Per cluster: LLM extracts insights, opinions, stats
5. Store as `research_clusters` with cluster centroid embedding

## Memory RAG (Anti-Repetition)

```sql
-- Before planning, fetch similar past content
SELECT summary, memory_type, metadata
FROM generation_memory
WHERE user_id = $1
  AND 1 - (embedding <=> $2::vector) > 0.8
ORDER BY created_at DESC
LIMIT 10;
```

Inject into planner prompt as "RECENTLY COVERED — DO NOT REPEAT."

## Index Tuning

```sql
-- HNSW params for pgvector
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Query-time
SET hnsw.ef_search = 40;
```

For >1M chunks (SaaS scale): migrate to dedicated Qdrant with same schema.

## Caching

| Cache | Key | TTL |
|-------|-----|-----|
| Embedding | `emb:{sha256(text)}` | 7d |
| Retrieval result | `rag:{user_id}:{idea_hash}` | 1h |
| Cluster summary | `cluster:{cluster_id}` | 24h |

## Quality Metrics

Track in `research_runs` and generation metadata:

- `retrieval_precision@5` — manual eval on golden set
- `citation_rate` — % drafts with valid rag_source_ids
- `hallucination_rate` — % fact-check failures
- `chunk_freshness` — avg age of retrieved chunks

## Data Retention

| Data | Retention |
|------|-----------|
| Raw content | 90 days |
| Chunks + embeddings | 90 days (re-embed on access if needed) |
| Cluster summaries | 30 days |
| Published content snapshots | Indefinite |

Cleanup via weekly Temporal `DataRetentionWorkflow`.
