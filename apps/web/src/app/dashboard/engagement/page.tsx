"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, ReplyTarget } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function EngagementPage() {
  const [targets, setTargets] = useState<ReplyTarget[]>([]);
  const [handle, setHandle] = useState("");
  const [tweetText, setTweetText] = useState("");
  const [tweetId, setTweetId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const list = await api.listReplyTargets(token);
    setTargets(list);
  }

  useEffect(() => { load(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !handle.trim() || !tweetText.trim()) return;
    setError(null);
    setMessage(null);
    try {
      await api.createReplyTarget(token, {
        author_handle: handle.trim(),
        tweet_text: tweetText.trim(),
        x_tweet_id: tweetId.trim() || undefined,
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

  return (
    <AppShell title="Engagement">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Add tweets you want to reply to. The content planner will suggest reply ideas, or draft a reply directly.
      </p>

      <form onSubmit={handleAdd} className="mb-8 max-w-xl space-y-3 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="font-medium">Add reply target</h3>
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
          placeholder="X tweet ID (optional — needed to publish)"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium hover:bg-sky-400">
          Add target
        </button>
      </form>

      {targets.length === 0 && (
        <p className="text-zinc-500">No reply targets yet. Add tweets from your niche to start engaging.</p>
      )}

      <div className="space-y-4">
        {targets.map((target) => (
          <div key={target.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-sky-400">@{target.author_handle}</p>
                <p className="mt-2 text-white">{target.tweet_text}</p>
                {target.x_tweet_id && (
                  <p className="mt-1 text-xs text-zinc-500">Tweet ID: {target.x_tweet_id}</p>
                )}
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => handleDraftReply(target.id)}
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm hover:bg-sky-500"
              >
                Draft reply now
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
