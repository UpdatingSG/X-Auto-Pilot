"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import {
  api,
  ApiError,
  DiscoveredReplyTarget,
  Draft,
  ReplyTarget,
} from "@/lib/api-client";
import { getToken } from "@/lib/auth";

type DeskStatus = "ready" | "copied" | "posted";
type Lane = "manual" | "mentions";

const STATUS_KEY = "xautopilot.engagement.deskStatus.v1";

function xStatusUrl(handle: string, tweetId: string) {
  const h = handle.replace(/^@/, "");
  return `https://x.com/${h}/status/${tweetId}`;
}

function isValidTweetId(id: string) {
  return /^\d{1,19}$/.test(id);
}

function loadStatusMap(): Record<string, DeskStatus> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STATUS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, DeskStatus>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveStatusMap(map: Record<string, DeskStatus>) {
  localStorage.setItem(STATUS_KEY, JSON.stringify(map));
}

function draftText(draft: Draft | undefined): string {
  if (!draft?.variants?.length) return "";
  const selected =
    draft.variants.find((v) => v.id === draft.selected_variant_id) ??
    draft.variants.find((v) => v.is_selected) ??
    draft.variants[0];
  return selected?.content_text?.trim() ?? "";
}

function replyTargetIdFromDraft(draft: Draft): string | null {
  const id = draft.generation_metadata?.reply_target_id;
  return typeof id === "string" ? id : null;
}

export default function EngagementPage() {
  const [targets, setTargets] = useState<ReplyTarget[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [discovered, setDiscovered] = useState<DiscoveredReplyTarget[]>([]);
  const [selectedDiscover, setSelectedDiscover] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftEdits, setDraftEdits] = useState<Record<string, string>>({});
  const [statusMap, setStatusMap] = useState<Record<string, DeskStatus>>({});
  const [lane, setLane] = useState<Lane>("manual");
  const [tweetUrl, setTweetUrl] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [importing, setImporting] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [showTools, setShowTools] = useState(false);

  const draftsByTarget = useMemo(() => {
    const map = new Map<string, Draft>();
    for (const draft of drafts) {
      if (draft.content_type !== "reply") continue;
      if (draft.status === "rejected" || draft.status === "published") continue;
      const tid = replyTargetIdFromDraft(draft);
      if (!tid) continue;
      const existing = map.get(tid);
      if (!existing) {
        map.set(tid, draft);
        continue;
      }
      // Prefer newest non-scheduled ready/approved draft
      map.set(tid, draft);
    }
    return map;
  }, [drafts]);

  const activeTargets = useMemo(() => {
    if (lane === "mentions") return [];
    return targets.filter((t) => statusMap[t.id] !== "posted");
  }, [targets, statusMap, lane]);

  const postedTargets = useMemo(
    () => targets.filter((t) => statusMap[t.id] === "posted"),
    [targets, statusMap],
  );

  const selected = activeTargets.find((t) => t.id === selectedId) ?? activeTargets[0] ?? null;
  const linkedDraft = selected ? draftsByTarget.get(selected.id) : undefined;
  const draft =
    selected && (draftEdits[selected.id] !== undefined
      ? draftEdits[selected.id]
      : draftText(linkedDraft));

  const setStatus = useCallback((targetId: string, status: DeskStatus) => {
    setStatusMap((prev) => {
      const next = { ...prev, [targetId]: status };
      saveStatusMap(next);
      return next;
    });
  }, []);

  async function load() {
    const token = getToken();
    if (!token) return;
    const [list, draftList] = await Promise.all([
      api.listReplyTargets(token),
      api.listDrafts(token),
    ]);
    setTargets(list);
    setDrafts(draftList);
    setStatusMap(loadStatusMap());
  }

  useEffect(() => {
    load().catch(() => setError("Failed to load engagement data"));
  }, []);

  useEffect(() => {
    if (!selectedId && activeTargets[0]) {
      setSelectedId(activeTargets[0].id);
    } else if (selectedId && !activeTargets.some((t) => t.id === selectedId)) {
      setSelectedId(activeTargets[0]?.id ?? null);
    }
  }, [activeTargets, selectedId]);

  async function handleDiscover() {
    const token = getToken();
    if (!token) return;
    setDiscovering(true);
    setError(null);
    try {
      const result = await api.discoverReplyTargets(token, {
        min_followers: 2_000,
        max_followers: 50_000,
        limit: 10,
      });
      setDiscovered(result.targets);
      setSelectedDiscover(new Set(result.targets.map((t) => t.x_tweet_id)));
      setShowTools(true);
      setMessage(
        result.message
          ? `Found ${result.targets.length} opportunities (${result.source}). ${result.message}`
          : `Found ${result.targets.length} reply opportunities from ${result.source}.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Discovery failed");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleDiscoverWatchlist() {
    const token = getToken();
    if (!token) return;
    setDiscovering(true);
    setError(null);
    try {
      const result = await api.discoverWatchlistTargets(token);
      setDiscovered(result.targets);
      setSelectedDiscover(new Set(result.targets.map((t) => t.x_tweet_id)));
      setShowTools(true);
      setMessage(result.message ?? `Found ${result.targets.length} posts from your watchlist.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Watchlist discovery failed");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleImportSelected() {
    const token = getToken();
    if (!token) return;
    const toImport = discovered.filter((t) => selectedDiscover.has(t.x_tweet_id));
    if (toImport.length === 0) return;
    setImporting(true);
    setError(null);
    try {
      const result = await api.importReplyTargets(token, toImport);
      setMessage(`Imported ${result.imported} targets into your reply workspace.`);
      setDiscovered([]);
      setSelectedDiscover(new Set());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  async function handleImportUrl(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !tweetUrl.trim()) return;
    setError(null);
    setImporting(true);
    try {
      const target = await api.importReplyTargetFromUrl(token, tweetUrl.trim());
      setTweetUrl("");
      setMessage(
        target.reply_block_confirmed
          ? `Imported, but X will block replies: ${target.reply_block_reason ?? "author restricts replies"}.`
          : "Target added to workspace.",
      );
      setSelectedId(target.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not import URL");
    } finally {
      setImporting(false);
    }
  }

  async function handleGenerate() {
    const token = getToken();
    if (!token || !selected) return;
    if (!isValidTweetId(selected.x_tweet_id)) {
      setError("This target needs a valid tweet ID. Paste the post URL under Tools.");
      setShowTools(true);
      return;
    }
    if (selected.reply_block_confirmed) {
      setError(selected.reply_block_reason ?? "X blocks replies to this post.");
      return;
    }
    setGeneratingId(selected.id);
    setError(null);
    setMessage(null);
    try {
      const draft = await api.generateReplyDraft(token, selected.id);
      setMessage("Reply drafted — edit if needed, then copy and post on X.");
      const text = draftText(draft);
      setDraftEdits((prev) => {
        const next = { ...prev };
        if (text) next[selected.id] = text;
        else delete next[selected.id];
        return next;
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Draft generation failed");
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleCopy() {
    if (!selected || !draft.trim()) return;
    await navigator.clipboard.writeText(draft.trim());
    setStatus(selected.id, "copied");
    setMessage("Copied — paste as a reply on X.");
  }

  function handleOpenOnX() {
    if (!selected || !isValidTweetId(selected.x_tweet_id)) return;
    window.open(xStatusUrl(selected.author_handle, selected.x_tweet_id), "_blank", "noopener,noreferrer");
  }

  async function handleCopyAndOpen() {
    await handleCopy();
    handleOpenOnX();
  }

  function handleMarkPosted() {
    if (!selected) return;
    setStatus(selected.id, "posted");
    setMessage("Marked posted. Keep going with the next target.");
  }

  async function handleRemove(targetId: string) {
    const token = getToken();
    if (!token) return;
    await api.deleteReplyTarget(token, targetId);
    setStatusMap((prev) => {
      const next = { ...prev };
      delete next[targetId];
      saveStatusMap(next);
      return next;
    });
    setMessage("Target removed");
    await load();
  }

  function toggleDiscover(tweetId: string) {
    setSelectedDiscover((prev) => {
      const next = new Set(prev);
      if (next.has(tweetId)) next.delete(tweetId);
      else next.add(tweetId);
      return next;
    });
  }

  const deskStatus = selected ? statusMap[selected.id] ?? "ready" : "ready";

  return (
    <AppShell title="Engagement">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-xl">
          <h3 className="text-xl font-semibold text-white">Reply workspace</h3>
          <p className="mt-1 text-sm text-zinc-400">
            X blocks most auto-replies via API. Draft here, then post the native reply yourself on X.
          </p>
        </div>
        <div className="flex rounded-lg border border-zinc-700 p-1 text-sm">
          <button
            type="button"
            onClick={() => setLane("manual")}
            className={`rounded-md px-3 py-1.5 ${lane === "manual" ? "bg-zinc-700 text-white" : "text-zinc-400"}`}
          >
            Manual lane
          </button>
          <button
            type="button"
            onClick={() => setLane("mentions")}
            className={`rounded-md px-3 py-1.5 ${lane === "mentions" ? "bg-zinc-700 text-white" : "text-zinc-400"}`}
          >
            Mentions (API)
          </button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleDiscover}
          disabled={discovering}
          className="rounded-lg bg-sky-500 px-3 py-1.5 text-sm font-medium hover:bg-sky-400 disabled:opacity-50"
        >
          {discovering ? "Discovering…" : "Discover replies"}
        </button>
        <button
          type="button"
          onClick={handleDiscoverWatchlist}
          disabled={discovering}
          className="rounded-lg border border-sky-600 px-3 py-1.5 text-sm text-sky-300 hover:bg-sky-950 disabled:opacity-50"
        >
          Watchlist
        </button>
        <button
          type="button"
          onClick={() => setShowTools((v) => !v)}
          className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm hover:bg-zinc-800"
        >
          {showTools ? "Hide tools" : "Paste URL / tools"}
        </button>
      </div>

      {showTools && (
        <div className="mb-6 space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/80 p-4">
          <form onSubmit={handleImportUrl} className="flex flex-wrap gap-2">
            <input
              value={tweetUrl}
              onChange={(e) => setTweetUrl(e.target.value)}
              placeholder="https://x.com/handle/status/1234567890"
              className="min-w-[16rem] flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={importing || !tweetUrl.trim()}
              className="rounded-lg border border-zinc-600 px-4 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
            >
              Import URL
            </button>
          </form>

          {discovered.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-sm font-medium text-zinc-300">Discovered</h4>
                <button
                  type="button"
                  onClick={handleImportSelected}
                  disabled={importing || selectedDiscover.size === 0}
                  className="rounded-lg bg-green-600 px-3 py-1.5 text-sm hover:bg-green-500 disabled:opacity-50"
                >
                  Import selected ({selectedDiscover.size})
                </button>
              </div>
              {discovered.map((item) => (
                <label
                  key={item.x_tweet_id}
                  className="flex cursor-pointer gap-3 rounded-lg border border-zinc-800 bg-zinc-950 p-3"
                >
                  <input
                    type="checkbox"
                    checked={selectedDiscover.has(item.x_tweet_id)}
                    onChange={() => toggleDiscover(item.x_tweet_id)}
                    className="mt-1"
                  />
                  <div>
                    <p className="text-sm text-sky-400">
                      @{item.author_handle} · {item.author_followers.toLocaleString()} followers
                    </p>
                    <p className="mt-1 text-sm text-zinc-200">{item.tweet_text}</p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
      )}

      {lane === "mentions" ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
          <p className="text-lg text-white">Mentions lane</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-zinc-400">
            When someone @mentions you (or you reply to your own posts), the X API can still publish.
            Use Drafts → approve → schedule for those. Stranger outreach stays in Manual lane.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
          <div className="max-h-[70vh] space-y-2 overflow-y-auto pr-1">
            {activeTargets.length === 0 && (
              <p className="rounded-lg border border-dashed border-zinc-700 p-6 text-sm text-zinc-500">
                No active targets. Discover replies or paste a post URL to start.
              </p>
            )}
            {activeTargets.map((item) => {
              const st = statusMap[item.id] ?? "ready";
              const active = item.id === selected?.id;
              const hasDraft = Boolean(draftsByTarget.get(item.id) || draftEdits[item.id]);
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  className={`w-full rounded-lg border px-3 py-3 text-left ${
                    active
                      ? "border-sky-500 bg-sky-950/30"
                      : "border-zinc-800 bg-zinc-900 hover:border-zinc-600"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-sky-400">@{item.author_handle}</span>
                    <span className="flex items-center gap-2 text-[10px] uppercase tracking-wide">
                      {hasDraft && <span className="text-zinc-500">drafted</span>}
                      <span
                        className={
                          st === "copied"
                            ? "text-amber-300"
                            : st === "posted"
                              ? "text-green-400"
                              : "text-zinc-500"
                        }
                      >
                        {st}
                      </span>
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-zinc-300">{item.tweet_text}</p>
                  {item.reply_block_confirmed && (
                    <p className="mt-1 text-xs text-red-300">Replies blocked by author settings</p>
                  )}
                </button>
              );
            })}

            {postedTargets.length > 0 && (
              <div className="pt-4">
                <p className="mb-2 text-xs uppercase tracking-wide text-zinc-600">Posted this session</p>
                {postedTargets.map((item) => (
                  <div
                    key={item.id}
                    className="mb-2 rounded-lg border border-zinc-800/80 bg-zinc-950/50 px-3 py-2 opacity-70"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-zinc-400">@{item.author_handle}</span>
                      <button
                        type="button"
                        className="text-xs text-zinc-500 hover:text-zinc-300"
                        onClick={() => setStatus(item.id, "ready")}
                      >
                        Restore
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {selected ? (
            <div className="sticky top-4 space-y-4 self-start rounded-xl border border-zinc-700 bg-zinc-900 p-5">
              <div>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm text-sky-400">@{selected.author_handle}</p>
                  <span
                    className={`text-[10px] uppercase tracking-wide ${
                      deskStatus === "copied"
                        ? "text-amber-300"
                        : deskStatus === "posted"
                          ? "text-green-400"
                          : "text-zinc-500"
                    }`}
                  >
                    {deskStatus}
                  </span>
                </div>
                <p className="mt-2 text-sm text-zinc-300">{selected.tweet_text}</p>
                {selected.reply_warning && !selected.reply_block_confirmed && (
                  <p className="mt-2 text-xs text-amber-300">{selected.reply_warning}</p>
                )}
                {selected.reply_block_confirmed && (
                  <p className="mt-2 text-xs text-red-300">
                    {selected.reply_block_reason ?? "Author restricts who can reply."}
                  </p>
                )}
                {!isValidTweetId(selected.x_tweet_id) && (
                  <p className="mt-2 text-xs text-amber-300">
                    Missing valid tweet ID — open Tools and import the post URL.
                  </p>
                )}
              </div>

              <label className="block">
                <span className="text-xs uppercase tracking-wide text-zinc-500">Your reply</span>
                <textarea
                  value={draft}
                  onChange={(e) =>
                    setDraftEdits((d) => ({ ...d, [selected.id]: e.target.value }))
                  }
                  rows={6}
                  placeholder={
                    generatingId === selected.id
                      ? "Generating…"
                      : "Generate a draft, or write your own reply…"
                  }
                  className="mt-2 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white"
                />
                <p className="mt-1 text-xs text-zinc-500">{draft.length}/280</p>
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={
                    generatingId === selected.id ||
                    selected.reply_block_confirmed ||
                    !isValidTweetId(selected.x_tweet_id)
                  }
                  className="rounded-lg border border-sky-700 px-3 py-2 text-sm text-sky-300 hover:bg-sky-950 disabled:opacity-50"
                >
                  {generatingId === selected.id
                    ? "Generating…"
                    : linkedDraft
                      ? "Regenerate draft"
                      : "Generate draft"}
                </button>
                <button
                  type="button"
                  onClick={handleCopyAndOpen}
                  disabled={!draft.trim() || !isValidTweetId(selected.x_tweet_id)}
                  className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
                >
                  Copy & open on X
                </button>
                <button
                  type="button"
                  onClick={handleCopy}
                  disabled={!draft.trim()}
                  className="rounded-lg border border-zinc-600 px-3 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
                >
                  Copy reply
                </button>
                <button
                  type="button"
                  onClick={handleOpenOnX}
                  disabled={!isValidTweetId(selected.x_tweet_id)}
                  className="rounded-lg border border-zinc-600 px-3 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
                >
                  Open post on X
                </button>
                <button
                  type="button"
                  onClick={handleMarkPosted}
                  className="rounded-lg border border-green-700/50 px-3 py-2 text-sm text-green-300 hover:bg-green-950/40"
                >
                  Mark posted
                </button>
                <button
                  type="button"
                  onClick={() => handleRemove(selected.id)}
                  className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800"
                >
                  Remove
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-zinc-700 p-8 text-center text-sm text-zinc-500">
              Select a target to draft and post.
            </div>
          )}
        </div>
      )}

      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </AppShell>
  );
}
