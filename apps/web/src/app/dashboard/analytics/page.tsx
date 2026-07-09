"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, AnalyticsInsights, AnalyticsOverview, PostAnalyticsItem } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

function pct(rate: number) {
  return `${(rate * 100).toFixed(1)}%`;
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [posts, setPosts] = useState<PostAnalyticsItem[]>([]);
  const [insights, setInsights] = useState<AnalyticsInsights | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const [ov, po, ins] = await Promise.all([
      api.getAnalyticsOverview(token),
      api.getAnalyticsPosts(token),
      api.getAnalyticsInsights(token),
    ]);
    setOverview(ov);
    setPosts(po);
    setInsights(ins);
  }

  useEffect(() => { load(); }, []);

  async function handleSync(postId: string) {
    const token = getToken();
    if (!token) return;
    setSyncing(postId);
    try {
      await api.syncPostMetrics(token, postId);
      await load();
    } finally {
      setSyncing(null);
    }
  }

  return (
    <AppShell title="Analytics">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Track how your posts perform on X. Low impressions on new accounts are normal — X rarely
        pushes standalone tweets to strangers. Growth comes from replies, questions, and threads.
      </p>

      <div className="mb-8 rounded-xl border border-amber-800/40 bg-amber-950/20 p-5 text-sm text-amber-100/90">
        <h3 className="font-medium text-amber-200">Why reach feels low</h3>
        <ul className="mt-3 list-inside list-disc space-y-1 text-amber-100/80">
          <li>Under ~500 followers, most impressions come from your existing network only</li>
          <li>Generic educational posts + double hashtags rarely get algorithmic boost</li>
          <li>Your best posts asked questions — replies signal X to show you to more people</li>
          <li>Use Engagement → add reply targets on larger accounts in your niche</li>
        </ul>
      </div>

      {overview && (
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Posts (7d)" value={String(overview.posts_published)} />
          <StatCard label="Impressions" value={overview.total_impressions.toLocaleString()} />
          <StatCard label="Avg engagement" value={pct(overview.avg_engagement_rate)} />
          <StatCard
            label="Top post ER"
            value={overview.top_post ? pct(overview.top_post.engagement_rate) : "—"}
          />
        </div>
      )}

      {insights && insights.what_worked.length > 0 && (
        <div className="mb-8 rounded-xl border border-sky-800/40 bg-sky-950/20 p-5">
          <h3 className="text-sm font-medium text-sky-300">Weekly insights</h3>
          <ul className="mt-3 space-y-2 text-sm text-zinc-300">
            {insights.what_worked.map((item) => (
              <li key={item}>✓ {item}</li>
            ))}
          </ul>
          {insights.best_category && (
            <p className="mt-3 text-xs text-zinc-500">
              Best category: {insights.best_category}
              {insights.best_posting_hour != null && ` · best hour: ${insights.best_posting_hour}:00 UTC`}
            </p>
          )}
        </div>
      )}

      <h3 className="mb-4 text-lg font-medium">Post performance</h3>
      {posts.length === 0 && (
        <p className="text-zinc-500">Publish posts first, then sync metrics here.</p>
      )}

      <div className="space-y-4">
        {posts.map((post) => (
          <div key={post.post_id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-zinc-500">{post.category} · {post.x_tweet_id}</p>
            <p className="mt-2 text-white">{post.preview_text}</p>
            {post.metrics ? (
              <div className="mt-4 flex flex-wrap gap-4 text-sm text-zinc-400">
                <span>{post.metrics.impressions.toLocaleString()} impressions</span>
                <span>{post.metrics.likes} likes</span>
                <span>{pct(post.metrics.engagement_rate)} ER</span>
              </div>
            ) : (
              <button
                onClick={() => handleSync(post.post_id)}
                disabled={syncing === post.post_id}
                className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm hover:bg-sky-500 disabled:opacity-50"
              >
                {syncing === post.post_id ? "Syncing…" : "Sync metrics"}
              </button>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}
