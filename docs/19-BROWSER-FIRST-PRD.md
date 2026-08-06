# Browser-First Content OS — PRD v2

**Parent product:** X-Autopilot  
**Status:** ready-for-agent  
**Last updated:** August 2026

## Problem Statement

Consistent technical presence on X, Reddit, and the wider eng web still costs hours daily. The current product can plan and draft well, but publish/research are coupled to the X Developer API. That blocks growth when API access is limited, expensive, or unavailable, and it keeps research stuck on a single platform.

Creators need an editorial system that discovers discussions across public web sources, builds long-term knowledge, generates and humanizes content, and only publishes after human approval — without treating any one API as a hard dependency.

## Solution

Evolve X-Autopilot into a browser-first Content Operating System. External platforms sit behind provider interfaces. Phase 1 uses browser automation (and public HTML/feeds where appropriate) to research and optionally publish. Official APIs remain optional adapters behind the same interfaces.

An autonomous editorial loop continuously researches → learns → writes → reviews → awaits approval → publishes → feeds analytics back into knowledge.

## User Stories

1. As a technical creator, I want research that does not require an X API key, so that I can keep discovering topics when API access is unavailable.
2. As a technical creator, I want the system to search X via the public web (browser), so that discovery matches how I browse manually.
3. As a technical creator, I want Reddit discussions collected via browser, so that I can learn from eng communities without the Reddit API.
4. As a technical creator, I want Hacker News stories ingested daily, so that high-signal tech discourse feeds my content plan.
5. As a technical creator, I want GitHub Trending scanned, so that popular repos and languages inform what I write about.
6. As a technical creator, I want engineering blogs, Dev.to, and Medium posts discovered, so that long-form sources enrich my knowledge base.
7. As a technical creator, I want duplicates removed across providers, so that I do not review the same discussion twice.
8. As a technical creator, I want discussions ranked by relevance and engagement, so that I focus on the best material first.
9. As a technical creator, I want a dated research markdown artifact each day, so that I can audit what the system learned.
10. As a technical creator, I want insights merged into a long-term knowledge base, so that future drafts reuse durable notes instead of raw scrapes.
11. As a technical creator, I want related concepts linked with original references preserved, so that claims stay traceable.
12. As a technical creator, I want story angles extracted from knowledge, so that planning starts from narratives not raw links.
13. As a technical creator, I want tweet ideas generated from stories, so that daily posting stays concrete.
14. As a technical creator, I want threads generated from approved ideas, so that deep topics become publishable sequences.
15. As a technical creator, I want reply drafts generated for discovered discussions, so that engagement is prepared before I approve.
16. As a technical creator, I want every draft run through AI detection, so that I know how machine-like it looks before I post.
17. As a technical creator, I want humanization applied after detection, so that voice stays natural and on-brand.
18. As a technical creator, I want fact checking against knowledge references, so that I do not publish unsupported claims.
19. As a technical creator, I want a draft queue that requires my approval, so that nothing goes live without me.
20. As a technical creator, I want browser-assisted publishing after approval, so that I can post without an official API when needed.
21. As a technical creator, I want the existing X API publish path to remain available as an optional provider, so that I can switch transports without rewriting workflows.
22. As a technical creator, I want engagement metrics collected after publish, so that learning improves future drafts.
23. As a technical creator, I want orchestration to be unaware of browser vs API, so that new platforms plug in without rewriting agents.
24. As an operator, I want retries, failure handling, and screenshots in the browser layer, so that flaky pages are debuggable.
25. As an operator, I want business logic kept out of browser scripts, so that providers stay testable.
26. As an operator, I want prompts version-controlled as files, so that editorial changes are reviewable in git.
27. As an operator, I want structured logs and an audit trail for AI outputs, so that I can reconstruct how a draft was produced.
28. As an operator, I want LLM providers (OpenAI, Anthropic, Gemini, Ollama) selectable by config, so that models change without code edits.
29. As a technical creator, I want Phase 1 limited to research, knowledge, generation, review, and manual publish assist, so that the system ships before analytics/RAG expansions.
30. As a future user, I want LinkedIn/YouTube/official APIs addable later, so that the architecture does not paint us into a corner.

## Implementation Decisions

### Modules

- **Provider** — common interface: search discussions, read thread/replies, publish draft, collect engagement. Orchestration depends only on this interface.
- **Browser Runtime** — open pages, user-authorized login, navigate, extract, draft/publish actions, screenshots, retries. No ranking, writing, or approval logic.
- **Research Engine** — run selected providers for configured topics, dedupe, rank, persist structured research + daily markdown.
- **Knowledge Engine** — merge insights, cluster topics, link concepts, keep references; primary context for generation.
- **Story / Content Writers** — existing planner + tweet/thread/reply writers consume knowledge/research outputs.
- **Review Pipeline** — ordered AI detection → humanizer → fact checker; produces review metadata on drafts before `ready`.
- **Approval Gate** — centralized rules for idea/draft status transitions; schedule/publish refuse unapproved content.
- **Workflow Orchestrator** — HTTP + APScheduler (current); Temporal remains future. Pipelines are service-level compositions.
- **LLM Gateway** — extend config-driven provider selection beyond OpenAI mock/live.

### Provider interface (decision shape)

```python
class PlatformProvider(Protocol):
    name: str
    async def search_discussions(self, query: str, *, limit: int = 20) -> list[Discussion]: ...
    async def get_discussion(self, external_id: str) -> Discussion: ...
    async def list_replies(self, external_id: str, *, limit: int = 50) -> list[Reply]: ...
    async def publish(self, draft: PublishPayload) -> PublishResult: ...
    async def get_engagement(self, external_id: str) -> EngagementMetrics: ...
```

Phase 1 providers: `x_browser`, `reddit_browser`, `hacker_news`, `github_trending`, `engineering_blogs`, `devto`, `medium`.  
Optional later: `x_api` (wrap existing `XClient`), LinkedIn, Reddit API, YouTube, Medium API.

### Compatibility with current product

- Keep Voice Profile, plans, drafts, schedule, analytics, and X API path.
- Introduce providers beside `XClient`; adapt `XClient` as `x_api` provider over time.
- Approval already exists as status checks; extract `approval_service` as the single gate API.
- Review pipeline is new and runs after writers, before draft `ready` (or attaches review metadata while leaving status flow intact).

### Storage

- PostgreSQL remains system of record.
- Research artifacts also written under `research/YYYY-MM-DD.md` (repo or configured data dir).
- Vector store: continue pgvector; Qdrant optional later.

### Testing focus (confirmed)

Unit/behavior tests for **Provider**, **Research Engine**, **Review Pipeline**, and **Approval Gate**. Browser Runtime tested via a mock runtime; live Playwright is opt-in / manual.

## Testing Decisions

- Prefer testing external behavior of modules (inputs → outputs, status transitions, ranking/dedupe results), not Playwright internals or private helpers.
- **Provider:** mock provider returns canned discussions; registry resolves by name; browser-backed providers call runtime methods (assert interactions via mock runtime).
- **Research Engine:** multi-provider merge dedupes by canonical URL/id, ranks stably, produces report with insights list and markdown body.
- **Review Pipeline:** mock detectors/humanizer/fact-checker; pipeline order fixed; `passed` reflects combined gates.
- **Approval Gate:** idea must be `approved` to generate; draft must be `approved` to schedule; publish accepts only `scheduled` or `approved`; invalid transitions raise typed errors.
- Prior art: `tests/test_x_client.py` (pure unit), integration style in `conftest.py` + helpers for HTTP flows.

## Out of Scope

- Auto-publish without human approval
- DM / follow-unfollow automation
- Team collaboration and billing (Phase 3)
- Full Temporal migration
- Live Playwright CI against real X/Reddit (flaky; use mocks in CI)
- A/B testing and autonomous editorial planning (Phase 3)
- Replacing the existing Next.js dashboard in Phase 1

## Further Notes

- Design principle: browser-first, API-optional.
- Existing milestones M1–M6 remain valuable; this PRD is an evolutionary pivot of transport and research breadth, not a greenfield rewrite.
- Issue slices live in `docs/issues/v2-browser-first-slices.md` until GitHub auth can publish them with the `ready-for-agent` label.
