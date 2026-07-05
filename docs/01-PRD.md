# Product Requirements Document (PRD)

## 1. Overview

**Product Name:** X-Autopilot  
**Version:** MVP 1.0  
**Author:** Personal use → SaaS evolution  
**Last Updated:** July 2026

### 1.1 Problem Statement

Consistent, high-quality Twitter/X presence requires 2–4 hours daily: researching trends, reading articles, crafting tweets, writing threads, engaging with creators, and analyzing performance. Most AI tools produce generic, detectable content that hurts credibility and growth.

### 1.2 Solution

An AI content team that behaves like a professional Twitter creator. Users configure voice, topics, and posting cadence. The platform autonomously researches, plans, generates, humanizes, schedules, publishes (with approval), and learns from engagement.

### 1.3 Success Metrics (MVP)

| Metric | Target (90 days) |
|--------|------------------|
| Time saved on content creation | ≥ 80% reduction |
| Draft approval rate (first-pass) | ≥ 60% |
| Engagement rate vs. manual baseline | ≥ parity |
| AI detectability score (internal rubric) | < 20% flagged |
| System uptime | 99.5% |
| Draft-to-publish latency | < 5 min after approval |

### 1.4 Non-Goals (MVP)

- Multi-tenant SaaS billing
- Mobile app
- Auto-publish without approval
- DM automation
- Follow/unfollow automation
- Paid promotion management

---

## 2. User Personas

### 2.1 Primary: Technical Creator (You)

- Backend engineer building personal brand
- Posts 3x/day, 2 threads/week, 15 replies/day
- Values authenticity, technical accuracy, no cringe
- Wants approval gate before anything goes live

### 2.2 Future: SaaS Creator

- Non-technical marketer, indie hacker, consultant
- Needs onboarding wizard, templates, team seats
- Pays $29–99/month

---

## 3. Functional Requirements

### 3.1 User Profile (FR-001)

Store and version a **Voice Profile** containing:

- Bio, profession, expertise areas
- Interests and topics (weighted)
- Writing style, tone, personality descriptors
- Vocabulary preferences (use/avoid lists)
- Emoji and hashtag preferences
- Favorite creators (for reply targeting)
- Audience type
- Hard constraints: topics to never discuss

**Acceptance Criteria:**
- Profile editable via UI
- Changes create new version; content generation uses latest
- Export/import as JSON

### 3.2 Knowledge Sources (FR-002)

Ingest from configurable sources:

| Source | MVP | Post-MVP |
|--------|-----|----------|
| RSS feeds | ✅ | |
| Hacker News | ✅ | |
| Reddit (subreddits) | ✅ | |
| Dev.to | ✅ | |
| Personal notes/bookmarks | ✅ | |
| Twitter/X (trends, followed accounts) | | ✅ |
| GitHub Trending | | ✅ |
| Arxiv, TechCrunch, engineering blogs | | ✅ |
| News APIs | | ✅ |

**Acceptance Criteria:**
- Add/remove sources via UI
- Ingestion runs on schedule (default: every 4 hours)
- Deduplication by URL + semantic similarity
- All items stored in knowledge base with embeddings

### 3.3 Research Agent (FR-003)

Every 4 hours (configurable):

1. Collect latest from all sources
2. Cluster similar stories
3. Deduplicate
4. Rank by relevance to user topics + recency + engagement signals
5. Extract: insights, opinions, statistics, controversies, opportunities
6. Store in vector DB with metadata

### 3.4 Content Planner (FR-004)

Daily at configured time (default: 6 AM user timezone):

Generate content plan containing:

- Tweet ideas (N = daily quota)
- Thread ideas (weekly quota distributed)
- Reply opportunities
- Quote tweet opportunities

Each idea tagged with category:

`educational | opinion | story | personal | tutorial | hot_take | news | career | productivity | behind_the_scenes | lessons_learned | engineering`

**Acceptance Criteria:**
- Plan visible in dashboard by 7 AM
- User can approve/reject/edit ideas before generation
- Rejected ideas inform future planning

### 3.5 Tweet Generator (FR-005)

- Generate 3–5 variations per approved idea
- Score each on: hook strength, authenticity, technical accuracy, voice match, novelty
- Select best; present top 2 for user choice
- Hard limits: 280 chars (or X Premium limit if configured)

### 3.6 Thread Generator (FR-006)

- 6–15 tweets per thread
- Structure: hook → context → body (examples, code) → takeaways → CTA
- Each tweet standalone-readable
- Numbered implicitly through narrative, not "1/12" unless style prefers

### 3.7 Reply Generator (FR-007)

- Monitor tweets from favorite creators
- Understand thread context (parent + top replies)
- Generate substantive replies (min 50 chars, max 280)
- Blocklist generic patterns ("Great post!", "This!", "+1")

### 3.8 Quote Tweet Generator (FR-008)

- Find high-value tweets in user's niche
- Generate unique angle, not paraphrase
- Max 1/day default (configurable)

### 3.9 Scheduler (FR-009)

Configurable quotas:

```
tweets_per_day: 3
threads_per_week: 2
replies_per_day: 15
quote_tweets_per_day: 1
```

Posting windows (randomized within):

```
09:00–09:45, 13:00–13:45, 19:00–19:45
```

**Humanization:** ±0–15 min jitter, skip exact round minutes, vary day-to-day.

### 3.10 Draft Approval (FR-010)

**MVP requires approval before publish.**

States: `planned → generating → draft → approved → scheduled → published → failed`

- Push/email notification when drafts ready
- Bulk approve/reject
- Inline edit with re-score
- Auto-expire drafts after 48h

### 3.11 Analytics (FR-011)

Track per post and aggregate:

- Impressions, likes, replies, reposts, bookmarks
- Follower delta (24h, 7d)
- Engagement rate
- Best topic, time, content type

### 3.12 Learning Loop (FR-012)

Weekly job:

- Analyze top/bottom 20% by engagement
- Extract patterns (topic, hook type, length, tone)
- Update generation weights in Voice Profile metadata
- Store learnings as structured memory

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | API response time (p95) | < 500ms (non-AI endpoints) |
| NFR-002 | Tweet generation latency | < 30s |
| NFR-003 | Thread generation latency | < 90s |
| NFR-004 | Data retention | Indefinite (user content), 90d (raw ingest) |
| NFR-005 | Encryption at rest | AES-256 |
| NFR-006 | Encryption in transit | TLS 1.3 |
| NFR-007 | X API rate limit compliance | 100% — never exceed |
| NFR-008 | Audit log | All publish actions logged |

---

## 5. User Stories (MVP)

1. **As a creator**, I configure my voice profile once so all content sounds like me.
2. **As a creator**, I review daily content plan each morning and approve ideas I like.
3. **As a creator**, I receive draft tweets/threads and approve/edit before they post.
4. **As a creator**, I see which topics and times perform best weekly.
5. **As a creator**, I add RSS feeds and HN as sources without code.
6. **As a creator**, I connect my X account via OAuth and posts publish automatically after approval.

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| X API policy changes | High | Abstract publisher; support manual copy-paste fallback |
| AI-detectable content | High | Humanization layer + quality reviewer + user feedback |
| Hallucinated technical claims | High | Fact checker agent + RAG grounding + user approval |
| Account suspension | Critical | Rate limits, human-like timing, no spam patterns |
| Cost overrun (LLM) | Medium | Caching, smaller models for scoring, batch embeddings |

---

## 7. MVP Definition of Done

- [ ] Voice profile CRUD
- [ ] 3+ knowledge sources ingesting
- [ ] Daily content plan generated
- [ ] Tweet + thread generation with 3 variations
- [ ] Draft approval UI
- [ ] Scheduler with randomized windows
- [ ] X OAuth + publish tweet/thread
- [ ] Analytics sync (24h post-publish)
- [ ] Weekly learning report
- [ ] Docker Compose local dev environment
