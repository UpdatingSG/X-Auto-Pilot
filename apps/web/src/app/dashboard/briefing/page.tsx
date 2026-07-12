"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, BriefingResponse } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function BriefingPage() {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    try {
      setBriefing(await api.getDailyBriefing(token));
      setError(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to load briefing";
      setError(msg.includes("migrations") || msg.includes("schema") ? `${msg} — redeploy the API on Render to apply updates.` : msg);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleQuickReplies() {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.runQuickReplies(token);
      setMessage(result.message);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Quick replies failed");
    } finally {
      setBusy(false);
    }
  }

  if (!briefing && !error) {
    return (
      <AppShell title="Daily Briefing">
        <p className="text-zinc-400">Loading...</p>
      </AppShell>
    );
  }

  if (!briefing && error) {
    return (
      <AppShell title="Daily Briefing">
        <p className="text-red-400">{error}</p>
      </AppShell>
    );
  }

  if (!briefing) return null;

  const { targets } = briefing;
  const replyPct = targets.replies_goal
    ? Math.min(100, Math.round((targets.replies_sent / targets.replies_goal) * 100))
    : 0;

  return (
    <AppShell title="Daily Briefing">
      <div className="mb-8 rounded-xl border border-sky-800/40 bg-sky-950/20 p-6">
        <h3 className="text-lg font-medium text-white">Your 3-step growth workflow</h3>
        <ol className="mt-3 list-inside list-decimal space-y-1 text-sm text-zinc-300">
          <li>Click <strong>Find & draft replies</strong> below (discovers posts + writes reply drafts)</li>
          <li>Go to <Link href="/dashboard/drafts" className="text-sky-400 hover:underline">Drafts</Link> → approve the ones you like</li>
          <li>They auto-schedule (or publish from <Link href="/dashboard/schedule" className="text-sky-400 hover:underline">Publish Queue</Link>)</li>
        </ol>
        <button
          disabled={busy}
          onClick={handleQuickReplies}
          className="mt-4 rounded-lg bg-sky-500 px-6 py-2.5 font-medium hover:bg-sky-400 disabled:opacity-50"
        >
          {busy ? "Working…" : "Find & draft replies"}
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {message && <p className="mb-4 text-sm text-green-400">{message}</p>}

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Replies today"
          value={`${targets.replies_sent} / ${targets.replies_goal}`}
          sub={`${replyPct}% of daily target`}
        />
        <StatCard
          label="Original tweets"
          value={`${targets.tweets_sent} / ${targets.tweets_goal}`}
          sub="Keep it to your best idea"
        />
        <StatCard
          label="Threads today"
          value={`${targets.threads_sent} / ${targets.threads_goal}`}
          sub="Depth over volume"
        />
      </div>

      {briefing.actions.length > 0 && (
        <section className="mb-8">
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">Next up</h3>
          <ul className="space-y-2">
            {briefing.actions.map((a, i) => (
              <li
                key={i}
                className={`rounded-lg border px-4 py-3 text-sm ${
                  a.priority === "high"
                    ? "border-amber-500/40 bg-amber-500/10 text-amber-100"
                    : "border-zinc-700 bg-zinc-900 text-zinc-300"
                }`}
              >
                {a.detail}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mb-8">
        <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">
          Fresh opportunities ({briefing.fresh_opportunities.length})
        </h3>
        {briefing.discovery_message && (
          <p className="mb-3 text-xs text-zinc-500">{briefing.discovery_message}</p>
        )}
        <div className="space-y-3">
          {briefing.fresh_opportunities.slice(0, 5).map((t) => (
            <TargetCard key={t.x_tweet_id} target={t} />
          ))}
          {briefing.fresh_opportunities.length === 0 && (
            <p className="text-sm text-zinc-500">No fresh posts — add creators to your watchlist in Voice Profile.</p>
          )}
        </div>
        <Link href="/dashboard/engagement" className="mt-3 inline-block text-sm text-sky-400 hover:underline">
          More discovery options →
        </Link>
      </section>

      <Link href="/dashboard/growth" className="text-sm text-zinc-500 hover:text-zinc-300">
        View detailed growth stats →
      </Link>
    </AppShell>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-zinc-500">{sub}</p>
    </div>
  );
}

function TargetCard({
  target,
}: {
  target: {
    author_handle: string;
    tweet_text: string;
    author_followers: number;
    likes: number;
    relevance_score: number;
    source: string;
  };
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-sky-400">@{target.author_handle}</p>
        <span className="text-xs text-zinc-500">{target.source}</span>
      </div>
      <p className="mt-2 text-sm text-zinc-300">{target.tweet_text}</p>
      <p className="mt-2 text-xs text-zinc-500">
        {target.author_followers.toLocaleString()} followers · {target.likes} likes
      </p>
    </div>
  );
}
