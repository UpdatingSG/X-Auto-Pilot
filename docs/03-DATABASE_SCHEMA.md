# Database Schema

PostgreSQL 16 + pgvector extension. All timestamps `TIMESTAMPTZ`. UUIDs for primary keys.

## Entity Relationship Overview

```
users ──┬── voice_profiles (versioned)
        ├── x_accounts (OAuth tokens)
        ├── knowledge_sources
        ├── schedules
        ├── content_plans ── content_ideas
        ├── drafts ── draft_variants
        ├── published_posts ── post_metrics (time-series)
        ├── reply_targets
        ├── generation_memory
        └── audit_logs

knowledge_items ── knowledge_chunks (embeddings)
research_runs ── research_clusters ── cluster_items
```

## Core Tables

### users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),          -- null if OAuth-only
    timezone        VARCHAR(64) NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### voice_profiles

Versioned voice configuration. Generation always uses `is_active = true`.

```sql
CREATE TABLE voice_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT false,

    -- Identity
    display_name    VARCHAR(128),
    bio             TEXT,
    profession      VARCHAR(128),

    -- Voice (JSONB for flexibility)
    interests       JSONB NOT NULL DEFAULT '[]',       -- [{topic, weight}]
    expertise       JSONB NOT NULL DEFAULT '[]',
    writing_style   JSONB NOT NULL DEFAULT '{}',       -- {adjectives, sentence_length, ...}
    tone            JSONB NOT NULL DEFAULT '[]',
    personality     JSONB NOT NULL DEFAULT '[]',
    vocabulary      JSONB NOT NULL DEFAULT '{"use": [], "avoid": []}',
    emoji_prefs     JSONB NOT NULL DEFAULT '{"enabled": true, "max_per_tweet": 2, "favorites": []}',
    hashtag_prefs   JSONB NOT NULL DEFAULT '{"max_per_tweet": 2, "favorites": []}',
    favorite_creators JSONB NOT NULL DEFAULT '[]',     -- [{x_user_id, handle, priority}]
    audience_type   VARCHAR(64),
    never_discuss   JSONB NOT NULL DEFAULT '[]',

    -- Learned weights (updated by feedback loop)
    learned_weights JSONB NOT NULL DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, version)
);

CREATE INDEX idx_voice_profiles_active ON voice_profiles(user_id) WHERE is_active = true;
```

### x_accounts

```sql
CREATE TABLE x_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    x_user_id           VARCHAR(32) NOT NULL,
    handle              VARCHAR(64) NOT NULL,
    access_token_enc    BYTEA NOT NULL,          -- AES-256-GCM encrypted
    refresh_token_enc   BYTEA,
    token_expires_at    TIMESTAMPTZ,
    scopes              TEXT[] NOT NULL,
    follower_count      INT,
    last_synced_at      TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, x_user_id)
);
```

### knowledge_sources

```sql
CREATE TYPE source_type AS ENUM (
    'rss', 'hacker_news', 'reddit', 'devto', 'twitter',
    'github_trending', 'arxiv', 'manual_note', 'bookmark'
);

CREATE TABLE knowledge_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type     source_type NOT NULL,
    name            VARCHAR(128) NOT NULL,
    config          JSONB NOT NULL,              -- {url, subreddit, query, ...}
    is_enabled      BOOLEAN NOT NULL DEFAULT true,
    fetch_interval_minutes INT NOT NULL DEFAULT 240,
    last_fetched_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### knowledge_items

```sql
CREATE TABLE knowledge_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_id       UUID REFERENCES knowledge_sources(id),
    external_id     VARCHAR(512),                -- URL hash or API id
    title           TEXT NOT NULL,
    url             TEXT,
    author          VARCHAR(256),
    content_raw     TEXT,
    content_summary TEXT,
    published_at    TIMESTAMPTZ,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    relevance_score FLOAT,
    metadata        JSONB NOT NULL DEFAULT '{}',

    UNIQUE (user_id, external_id)
);

CREATE INDEX idx_knowledge_items_user_fetched ON knowledge_items(user_id, fetched_at DESC);
```

### knowledge_chunks

```sql
CREATE TABLE knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id         UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),              -- text-embedding-3-small
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

### research_runs

```sql
CREATE TABLE research_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(32) NOT NULL,      -- running, completed, failed
    items_processed INT DEFAULT 0,
    clusters_created INT DEFAULT 0,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ
);
```

### research_clusters

```sql
CREATE TABLE research_clusters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    summary         TEXT,
    importance_score FLOAT NOT NULL,
    insights        JSONB NOT NULL DEFAULT '[]',
    opinions        JSONB NOT NULL DEFAULT '[]',
    statistics      JSONB NOT NULL DEFAULT '[]',
    controversies   JSONB NOT NULL DEFAULT '[]',
    opportunities   JSONB NOT NULL DEFAULT '[]',
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### schedules

```sql
CREATE TABLE schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active       BOOLEAN NOT NULL DEFAULT true,

    tweets_per_day          INT NOT NULL DEFAULT 3,
    threads_per_week        INT NOT NULL DEFAULT 2,
    replies_per_day         INT NOT NULL DEFAULT 15,
    quote_tweets_per_day    INT NOT NULL DEFAULT 1,

    posting_windows JSONB NOT NULL DEFAULT '[]',
    -- [{start: "09:00", end: "09:45", days: [1,2,3,4,5]}]

    jitter_minutes  INT NOT NULL DEFAULT 15,
    require_approval BOOLEAN NOT NULL DEFAULT true,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### content_plans

```sql
CREATE TABLE content_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_date       DATE NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, plan_date)
);
```

### content_ideas

```sql
CREATE TYPE content_type AS ENUM ('tweet', 'thread', 'reply', 'quote_tweet');
CREATE TYPE content_category AS ENUM (
    'educational', 'opinion', 'story', 'personal', 'tutorial',
    'hot_take', 'news', 'career', 'productivity', 'behind_the_scenes',
    'lessons_learned', 'engineering'
);
CREATE TYPE idea_status AS ENUM ('proposed', 'approved', 'rejected', 'generated', 'skipped');

CREATE TABLE content_ideas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id         UUID NOT NULL REFERENCES content_plans(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type    content_type NOT NULL,
    category        content_category NOT NULL,
    status          idea_status NOT NULL DEFAULT 'proposed',

    title           TEXT NOT NULL,             -- internal working title
    hook_idea       TEXT,
    source_cluster_id UUID REFERENCES research_clusters(id),
    reply_target_id UUID REFERENCES reply_targets(id),
    rationale       TEXT,                      -- why this idea now

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### reply_targets

```sql
CREATE TABLE reply_targets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    x_tweet_id      VARCHAR(32) NOT NULL,
    x_user_id       VARCHAR(32) NOT NULL,
    author_handle   VARCHAR(64) NOT NULL,
    tweet_text      TEXT NOT NULL,
    conversation_context JSONB NOT NULL DEFAULT '[]',
    relevance_score FLOAT,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,      -- replies stale after 24h

    UNIQUE (user_id, x_tweet_id)
);
```

### drafts

```sql
CREATE TYPE draft_status AS ENUM (
    'generating', 'ready', 'approved', 'rejected',
    'scheduled', 'published', 'failed', 'expired'
);

CREATE TABLE drafts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    idea_id         UUID REFERENCES content_ideas(id),
    content_type    content_type NOT NULL,
    category        content_category,
    status          draft_status NOT NULL DEFAULT 'generating',

    selected_variant_id UUID,
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    x_tweet_id      VARCHAR(32),               -- root tweet id
    idempotency_key VARCHAR(64) UNIQUE,

    generation_metadata JSONB NOT NULL DEFAULT '{}',
    -- {model, tokens, rag_sources, scores, fact_check}

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drafts_user_status ON drafts(user_id, status);
CREATE INDEX idx_drafts_scheduled ON drafts(scheduled_at) WHERE status = 'scheduled';
```

### draft_variants

```sql
CREATE TABLE draft_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id        UUID NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    variant_index   INT NOT NULL,

    -- For tweets/replies/quotes: single text
  content_text    TEXT,

    -- For threads: ordered tweets
    thread_tweets   JSONB,                     -- [{index, text}]

    scores          JSONB NOT NULL DEFAULT '{}',
    -- {hook: 0.9, authenticity: 0.85, voice_match: 0.88, overall: 0.87}

    is_selected     BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### published_posts

```sql
CREATE TABLE published_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES drafts(id),
    x_tweet_id      VARCHAR(32) NOT NULL UNIQUE,
    content_type    content_type NOT NULL,
    content_snapshot JSONB NOT NULL,           -- frozen copy at publish time
    published_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### post_metrics

Time-series engagement snapshots.

```sql
CREATE TABLE post_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id         UUID NOT NULL REFERENCES published_posts(id) ON DELETE CASCADE,
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    impressions     INT,
    likes           INT,
    replies         INT,
    reposts         INT,
    bookmarks       INT,
    quotes          INT,
    engagement_rate FLOAT,

    follower_count  INT                        -- snapshot at capture time
);

CREATE INDEX idx_post_metrics_post_time ON post_metrics(post_id, captured_at DESC);
```

### generation_memory

Prevents repetition; stores what worked.

```sql
CREATE TABLE generation_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type     VARCHAR(32) NOT NULL,      -- topic_used, hook_pattern, failure, success
    content_hash    VARCHAR(64),
    summary         TEXT NOT NULL,
    embedding       vector(1536),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ
);

CREATE INDEX idx_generation_memory_embedding ON generation_memory
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_generation_memory_user_type ON generation_memory(user_id, memory_type);
```

### audit_logs

```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(64) NOT NULL,
    resource_type   VARCHAR(64) NOT NULL,
    resource_id     UUID,
    details         JSONB NOT NULL DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_user_time ON audit_logs(user_id, created_at DESC);
```

## Redis Key Schema

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `ratelimit:x:{user_id}:{endpoint}` | String (counter) | X API rate limit | per reset header |
| `schedule:queue:{user_id}` | Sorted Set | Scheduled publish times | — |
| `draft:notify:{user_id}` | Pub/Sub channel | Real-time notifications | — |
| `gen:cache:{content_hash}` | String (JSON) | Generation result cache | 24h |
| `session:{token}` | Hash | User session | 7d |
| `workflow:lock:{draft_id}` | String | Publish idempotency | 1h |

## Migrations Strategy

- Alembic for Python/FastAPI
- One migration per feature branch
- Seed script for dev user + sample voice profile
- pgvector extension enabled in migration `0001_enable_extensions`
