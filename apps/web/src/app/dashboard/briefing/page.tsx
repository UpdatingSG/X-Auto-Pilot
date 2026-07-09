"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, BriefingResponse, DiscoveredReplyTarget } from "@/lib/api-client";
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
      setError(err instanceof ApiError ? err.message : "Failed to load briefing");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function importAndDraft(targets: DiscoveredReplyTarget[]) {
    const token = getToken();
    if (!token || targets.length === 0) return;
    setBusy(true);
    setMessage(null);
    try {
      const imported = await api.importReplyTargets(token, targets.slice(0, 5));
      for (const target of imported.targets.slice(0, 3)) {
        await api.generateReplyDraft(token, target.id);
      }
      setMessage(`Imported ${imported.imported} targets and drafted replies for top picks.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  if (!briefing) {
    return (
      <AppShell title="Daily Briefing">
        {error ? <p className="text-red-400">{error}</p> : <p className="text-zinc-400">Loading...</p>}
      </AppShell>
    );
  }

  const { targets } = briefing;
  const replyPct = targets.replies_goal
    ? Math.min(100, Math.round((targets.replies_sent / targets.replies_goal) * 100))
    : 0;

  return (
    <AppShell title="Daily Briefing">
      <p className="mb-6 max-w-3xl text-zinc-400">
        Your growth workflow for today — fresh reply opportunities, saved targets, and what to do next.
        {briefing.growth_mode && (
          <span className="ml-2 rounded bg-sky-500/20 px-2 py-0.5 text-xs text-sky-300">Growth mode</span>
        )}
      </p>

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
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">Actions</h3>
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
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium uppercase tracking-wide text-zinc-500">
            Fresh opportunities ({briefing.fresh_opportunities.length})
          </h3>
          <button
            disabled={busy || briefing.fresh_opportunities.length === 0}
            onClick={() =>
              importAndDraft(
                briefing.fresh_opportunities.map((t) => ({
                  x_tweet_id: t.x_tweet_id,
                  x_user_id: "0",
                  author_handle: t.author_handle,
                  tweet_text: t.tweet_text,
                  author_followers: t.author_followers,
                  likes: t.likes,
                  relevance_score: t.relevance_score,
                })),
              )
            }
            className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium hover:bg-sky-400 disabled:opacity-50"
          >
            Import top 5 & draft replies
          </button>
        </div>
        {briefing.discovery_message && (
          <p className="mb-3 text-xs text-zinc-500">{briefing.discovery_message}</p>
        )}
        <div className="space-y-3">
          {briefing.fresh_opportunities.map((t) => (
            <TargetCard key={t.x_tweet_id} target={t} />
          ))}
          {briefing.fresh_opportunities.length === 0 && (
            <p className="text-sm text-zinc-500">No fresh posts right now — check Engagement or add watchlist creators.</p>
          )}
        </div>
      </section>

      <section className="mb-8">
        <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">Saved targets</h3>
        <div className="space-y-3">
          {briefing.saved_targets.map((t) => (
            <TargetCard key={t.reply_target_id ?? t.x_tweet_id} target={t} />
          ))}
        </div>
        <Link href="/dashboard/engagement" className="mt-3 inline-block text-sm text-sky-400 hover:underline">
          Manage all targets →
        </Link>
      </section>

      {briefing.hints.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500">Growth hints</h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-zinc-400">
            {briefing.hints.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </section>
      )}
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
    has_draft?: boolean;
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
        {target.author_followers.toLocaleString()} followers · {target.likes} likes · score{" "}
        {target.relevance_score.toFixed(2)}
        {target.has_draft && <span className="ml-2 text-green-400">· draft ready</span>}
      </p>
    </div>
  );
}
