# Phase 1 vertical slices — Browser-First Content OS

Parent: [docs/19-BROWSER-FIRST-PRD.md](../19-BROWSER-FIRST-PRD.md)

> GitHub CLI auth is currently invalid on this machine (`gh auth refresh` required).
> File these with label `ready-for-agent` after re-auth.

---

## 1. Provider interface + mock registry

- **Type:** AFK
- **Blocked by:** None
- **User stories:** 21, 23, 25

### What to build

Introduce a platform-agnostic provider protocol (search, get discussion, list replies, publish, engagement) with a mock implementation and name-based registry. Orchestration code must be able to obtain a provider without knowing browser vs API.

### Acceptance criteria

- [ ] `PlatformProvider` protocol and shared DTOs exist
- [ ] Mock provider returns deterministic canned discussions
- [ ] Registry resolves `mock` (and stubs for Phase 1 names)
- [ ] Unit tests cover search + registry lookup

### Blocked by

None - can start immediately

---

## 2. Browser runtime mock + X browser provider shell

- **Type:** AFK
- **Blocked by:** 1
- **User stories:** 2, 24, 25

### What to build

Add a `BrowserRuntime` protocol (navigate, content, screenshot, login session hook) with a mock runtime. Implement `x_browser` provider that performs search/read via the runtime only — no ranking or writing logic inside browser calls.

### Acceptance criteria

- [ ] Mock runtime records calls and returns fixture HTML/text
- [ ] `x_browser` provider uses runtime for search/get_discussion
- [ ] Publish method exists but refuses without approval token/flag from caller (provider does not decide approval)
- [ ] Unit tests assert runtime interactions

### Blocked by

Slice 1

---

## 3. Research engine daily pipeline

- **Type:** AFK
- **Blocked by:** 1
- **User stories:** 1, 4, 5, 7, 8, 9

### What to build

Research engine accepts topics + provider list, collects discussions, dedupes by canonical id/url, ranks by relevance/engagement, returns a structured report and markdown body suitable for `research/YYYY-MM-DD.md`.

### Acceptance criteria

- [ ] Multi-provider collect works with mocks
- [ ] Dedupe collapses identical canonical keys
- [ ] Ranking is deterministic for equal fixtures
- [ ] Markdown report includes date, topics, ranked items, insights stubs
- [ ] Unit tests cover dedupe + rank + markdown shape

### Blocked by

Slice 1

---

## 4. Stub providers: HN, GitHub Trending, Dev.to

- **Type:** AFK
- **Blocked by:** 1, 3
- **User stories:** 4, 5, 6

### What to build

Register stub/mock-backed providers for Hacker News, GitHub Trending, and Dev.to that return typed `Discussion` objects. Prefer public HTTP for HN when easy; otherwise mock fixtures behind the same interface.

### Acceptance criteria

- [ ] Providers registered by stable names
- [ ] Research engine can include them in a daily run
- [ ] Tests use fixtures (no live network in CI)

### Blocked by

Slices 1 and 3

---

## 5. Review pipeline (detect → humanize → fact-check)

- **Type:** AFK
- **Blocked by:** None
- **User stories:** 16, 17, 18, 27

### What to build

Composable review pipeline that runs AI detection, humanization, and fact checking in order. Mock mode for CI. Attach a `ReviewResult` to generation metadata (wire into draft generation in a follow-up if needed).

### Acceptance criteria

- [ ] Fixed stage order enforced
- [ ] `passed` false if detection score above threshold or fact-check fails
- [ ] Humanized text returned even when failed (for UI editing)
- [ ] Unit tests for pass/fail paths

### Blocked by

None - can start immediately

---

## 6. Approval gate service

- **Type:** AFK
- **Blocked by:** None
- **User stories:** 19, 27

### What to build

Centralize idea/draft approval rules: when generation is allowed, when schedule is allowed, when publish is allowed. Typed errors for invalid transitions. Align with existing statuses (`proposed`/`approved`/`generated`, `ready`/`approved`/`scheduled`).

### Acceptance criteria

- [ ] Pure functions/service methods cover generate/schedule/publish gates
- [ ] Invalid transitions raise typed errors
- [ ] Unit tests for allowed and denied paths
- [ ] Optional thin wiring from draft/publish services without behavior change

### Blocked by

None - can start immediately

---

## 7. Wire research → knowledge item ingest (tracer)

- **Type:** AFK
- **Blocked by:** 3
- **User stories:** 10, 11, 12

### What to build

End-to-end thin slice: run research for one topic with mock providers, persist top results as knowledge items (or equivalent), expose a simple API or service entrypoint that the planner can later consume.

### Acceptance criteria

- [ ] Service entrypoint runs research and stores N items
- [ ] References/URLs preserved
- [ ] At least one API or authenticated service test proves persistence
- [ ] No live browser required

### Blocked by

Slice 3

---

## 8. Draft generation runs review pipeline

- **Type:** AFK
- **Blocked by:** 5, 6
- **User stories:** 13–19

### What to build

After writers produce variants, run review pipeline on the selected/default variant text; store review metadata; keep human approval required before schedule/publish.

### Acceptance criteria

- [ ] Draft `generation_metadata` includes review summary
- [ ] Approval gate still required to schedule
- [ ] Integration test with mock LLM + mock review

### Blocked by

Slices 5 and 6

---

## 9. Reddit + blogs/Medium provider stubs

- **Type:** AFK
- **Blocked by:** 1, 2
- **User stories:** 3, 6

### What to build

Register `reddit_browser`, `engineering_blogs`, `medium` stubs (mock runtime fixtures). Enough for research engine inclusion; live scraping deferred.

### Acceptance criteria

- [ ] Names registered and discoverable
- [ ] Fixture-backed search returns discussions
- [ ] CI tests offline

### Blocked by

Slices 1 and 2

---

## 10. Dashboard: research report viewer (thin UI)

- **Type:** AFK
- **Blocked by:** 7
- **User stories:** 9, 10

### What to build

Minimal Next.js page listing the latest research run / markdown summary so a human can audit daily research.

### Acceptance criteria

- [ ] Authenticated page shows latest report or empty state
- [ ] Links/references visible
- [ ] No publish actions on this page

### Blocked by

Slice 7
