"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, DiscoveredReplyTarget, ReplyTarget } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function EngagementPage() {
  const [targets, setTargets] = useState<ReplyTarget[]>([]);
  const [discovered, setDiscovered] = useState<DiscoveredReplyTarget[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tweetUrl, setTweetUrl] = useState("");
  const [handle, setHandle] = useState("");
  const [tweetText, setTweetText] = useState("");
  const [tweetId, setTweetId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [fixUrl, setFixUrl] = useState("");
  const [fixingId, setFixingId] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  async function load() {
    const token = getToken();
    if (!token) return;
    const list = await api.listReplyTargets(token);
    setTargets(list);
  }

  useEffect(() => { load(); }, []);

  async function handleDiscoverWatchlist() {
    const token = getToken();
    if (!token) return;
    setDiscovering(true);
    setError(null);
    try {
      const result = await api.discoverWatchlistTargets(token);
      setDiscovered(result.targets);
      setSelected(new Set(result.targets.map((t) => t.x_tweet_id)));
      setMessage(result.message ?? `Found ${result.targets.length} posts from your watchlist.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Watchlist discovery failed");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleDiscoverQuotes() {
    const token = getToken();
    if (!token) return;
    setDiscovering(true);
    setError(null);
    try {
      const result = await api.discoverQuoteOpportunities(token);
      setDiscovered(result.targets);
      setSelected(new Set(result.targets.map((t) => t.x_tweet_id)));
      setMessage(result.message ?? `Found ${result.targets.length} quote opportunities.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Quote discovery failed");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleFixTarget(targetId: string) {
    const token = getToken();
    if (!token || !fixUrl.trim()) return;
    setFixingId(targetId);
    setError(null);
    try {
      await api.fixReplyTargetFromUrl(token, targetId, fixUrl.trim());
      setMessage("Tweet ID fixed — you can draft and publish this reply now.");
      setFixUrl("");
      setFixingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Fix failed");
      setFixingId(null);
    }
  }

  function isValidTweetId(id: string) {
    return /^\d{1,19}$/.test(id);
  }

  async function handleDiscover() {
    const token = getToken();
    if (!token) return;
    setDiscovering(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.discoverReplyTargets(token, {
        min_followers: 10_000,
        limit: 10,
      });
      setDiscovered(result.targets);
      setSelected(new Set(result.targets.map((t) => t.x_tweet_id)));
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

  async function handleImportSelected() {
    const token = getToken();
    if (!token) return;
    const toImport = discovered.filter((t) => selected.has(t.x_tweet_id));
    if (toImport.length === 0) return;
    setImporting(true);
    setError(null);
    try {
      const result = await api.importReplyTargets(token, toImport);
      setMessage(`Imported ${result.imported} reply targets — regenerate your content plan next.`);
      setDiscovered([]);
      setSelected(new Set());
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
    setMessage(null);
    setImporting(true);
    try {
      const target = await api.importReplyTargetFromUrl(token, tweetUrl.trim());
      setTweetUrl("");
      setMessage(
        target.reply_allowed === false
          ? `Imported, but X will block replies: ${target.reply_block_reason ?? "author restricts replies"}. Follow them or use a quote-tweet.`
          : "Reply target added from URL.",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not import URL");
    } finally {
      setImporting(false);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !handle.trim() || !tweetText.trim() || !tweetId.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await api.createReplyTarget(token, {
        author_handle: handle.trim(),
        tweet_text: tweetText.trim(),
        x_tweet_id: tweetId.trim(),
      });
      setHandle("");
      setTweetText("");
      setTweetId("");
      setMessage("Reply target added — regenerate your content plan to include reply ideas.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add target");
    }
  }

  async function handleDelete(targetId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    await api.deleteReplyTarget(token, targetId);
    setMessage("Reply target removed");
    await load();
  }

  async function handleDraftReply(targetId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      await api.generateReplyDraft(token, targetId);
      setMessage("Reply draft generated — check the Drafts page.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Draft generation failed");
    }
  }

  function toggleSelected(tweetId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tweetId)) next.delete(tweetId);
      else next.add(tweetId);
      return next;
    });
  }

  return (
    <AppShell title="Engagement">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Paste an X post URL to reply to it. Use <strong className="text-zinc-200">Daily Briefing</strong> for
        the one-click workflow — this page is for manual fixes and discovery.
      </p>

      <div className="mb-8 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleDiscover}
          disabled={discovering}
          className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium hover:bg-sky-400 disabled:opacity-50"
        >
          {discovering ? "Discovering…" : "Discover replies"}
        </button>
        <button
          type="button"
          onClick={handleDiscoverWatchlist}
          disabled={discovering}
          className="rounded-lg border border-sky-600 px-4 py-2 text-sm text-sky-300 hover:bg-sky-950 disabled:opacity-50"
        >
          Watchlist
        </button>
        <button
          type="button"
          onClick={handleDiscoverQuotes}
          disabled={discovering}
          className="rounded-lg border border-zinc-600 px-4 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
        >
          Quote opportunities
        </button>
        {discovered.length > 0 && (
          <button
            type="button"
            onClick={handleImportSelected}
            disabled={importing || selected.size === 0}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium hover:bg-green-500 disabled:opacity-50"
          >
            {importing ? "Importing…" : `Import selected (${selected.size})`}
          </button>
        )}
      </div>

      <form onSubmit={handleImportUrl} className="mb-8 max-w-xl space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="font-medium">Paste X post URL</h3>
        <input
          value={tweetUrl}
          onChange={(e) => setTweetUrl(e.target.value)}
          placeholder="https://x.com/handle/status/1234567890"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={importing || !tweetUrl.trim()}
          className="rounded-lg border border-zinc-600 px-4 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
        >
          Import from URL
        </button>
      </form>

      {discovered.length > 0 && (
        <div className="mb-8 space-y-3">
          <h3 className="text-sm font-medium text-zinc-300">Discovered opportunities</h3>
          {discovered.map((item) => (
            <label
              key={item.x_tweet_id}
              className="flex cursor-pointer gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4"
            >
              <input
                type="checkbox"
                checked={selected.has(item.x_tweet_id)}
                onChange={() => toggleSelected(item.x_tweet_id)}
                className="mt-1"
              />
              <div>
                <p className="text-sm text-sky-400">
                  @{item.author_handle} · {item.author_followers.toLocaleString()} followers · {item.likes} likes
                </p>
                <p className="mt-2 text-white">{item.tweet_text}</p>
                <p className="mt-1 text-xs text-zinc-500">Tweet ID: {item.x_tweet_id}</p>
              </div>
            </label>
          ))}
        </div>
      )}

      <form onSubmit={handleAdd} className="mb-8 max-w-xl space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="font-medium">Add manually (optional)</h3>
        <input
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          placeholder="@handle"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
        />
        <textarea
          value={tweetText}
          onChange={(e) => setTweetText(e.target.value)}
          placeholder="Paste the tweet you want to reply to..."
          rows={3}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
        />
        <input
          value={tweetId}
          onChange={(e) => setTweetId(e.target.value)}
          placeholder="X tweet ID (required — from post URL)"
          required
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded-lg bg-zinc-700 px-4 py-2 text-sm font-medium hover:bg-zinc-600">
          Add target
        </button>
      </form>

      {targets.length === 0 && (
        <p className="text-zinc-500">No reply targets yet. Click discover or paste a post URL to start.</p>
      )}

      <div className="space-y-4">
        {targets.map((target) => (
          <div key={target.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-sky-400">@{target.author_handle}</p>
                <p className="mt-2 text-white">{target.tweet_text}</p>
                {target.x_tweet_id && (
                  <p className={`mt-1 text-xs ${isValidTweetId(target.x_tweet_id) ? "text-zinc-500" : "text-amber-400"}`}>
                    Tweet ID: {target.x_tweet_id}
                    {!isValidTweetId(target.x_tweet_id) && " — invalid, fix with URL below"}
                  </p>
                )}
                {target.reply_allowed === false && (
                  <p className="mt-2 text-sm text-amber-300">
                    Replies blocked: {target.reply_block_reason ?? "Author restricts who can reply."}
                    {" "}Follow them on X first, or use Quote opportunities instead.
                  </p>
                )}
              </div>
            </div>
            {!isValidTweetId(target.x_tweet_id) && (
              <div className="mt-3 flex gap-2">
                <input
                  value={fixingId === target.id ? fixUrl : ""}
                  onChange={(e) => {
                    setFixingId(target.id);
                    setFixUrl(e.target.value);
                  }}
                  placeholder="Paste X post URL to fix ID"
                  className="flex-1 rounded-lg border border-amber-700/50 bg-zinc-950 px-3 py-2 text-sm"
                />
                <button
                  onClick={() => handleFixTarget(target.id)}
                  disabled={fixingId === target.id && !fixUrl.trim()}
                  className="rounded-lg bg-amber-600 px-3 py-2 text-sm hover:bg-amber-500 disabled:opacity-50"
                >
                  Fix ID
                </button>
              </div>
            )}
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => handleDraftReply(target.id)}
                disabled={!isValidTweetId(target.x_tweet_id) || target.reply_allowed === false}
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm hover:bg-sky-500 disabled:opacity-50"
              >
                {target.reply_allowed === false ? "Reply blocked by X" : "Draft reply now"}
              </button>
              <button
                onClick={() => handleDelete(target.id)}
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm hover:bg-zinc-800"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </AppShell>
  );
}
