"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, GrowthDashboard } from "@/lib/api-client";
import { getToken, warmApiHealth } from "@/lib/auth";

export default function GrowthPage() {
  const [data, setData] = useState<GrowthDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [learning, setLearning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    warmApiHealth();
    const token = getToken();
    if (!token) return;
    api.getGrowthDashboard(token).then(setData).catch((err) => {
      const msg = err instanceof ApiError ? err.message : "Failed to load";
      setError(
        msg.includes("migrations") || msg.includes("schema") || msg.includes("Redeploy")
          ? `${msg} After redeploying the API on Render, refresh this page.`
          : msg,
      );
    });
  }, []);

  async function runLearning() {
    const token = getToken();
    if (!token) return;
    setLearning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.runLearningCycle(token);
      if (result.applied) {
        setMessage("Learning cycle complete — future plans and briefings will use updated weights.");
      } else if (result.reason === "no_active_profile") {
        setError("Set up your Voice Profile first (Settings → Voice Profile).");
      } else if (result.reason === "insufficient_data") {
        setMessage("Not enough published posts yet. Publish a few more posts, then try again.");
      } else {
        setMessage("Learning cycle finished with no changes.");
      }
      setData(await api.getGrowthDashboard(token));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Learning failed";
      setError(
        msg.includes("ROUTER_EXTERNAL_TARGET") || msg.includes("502") || msg.includes("504")
          ? "API timed out — wait a moment for the server to wake up, then try again."
          : msg,
      );
    } finally {
      setLearning(false);
    }
  }

  if (!data) {
    return (
      <AppShell title="Growth">
        {error ? <p className="text-red-400">{error}</p> : <p className="text-zinc-400">Loading...</p>}
      </AppShell>
    );
  }

  return (
    <AppShell title="Growth Dashboard">
      <div className="mb-6 flex items-center justify-between">
        <p className="max-w-2xl text-zinc-400">
          Leading indicators for account growth — replies sent, content-type performance, and reply streaks.
        </p>
        <button
          onClick={runLearning}
          disabled={learning}
          className="rounded-lg border border-zinc-600 px-4 py-2 text-sm hover:bg-zinc-800 disabled:opacity-50"
        >
          {learning ? "Learning…" : "Run learning cycle"}
        </button>
      </div>

      {message && <p className="mb-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <div className="mb-8 grid gap-4 sm:grid-cols-4">
        <Metric label="Reply streak" value={`${data.streak.reply_days} days`} />
        <Metric
          label="Replies today"
          value={`${data.today_counts.reply ?? 0} / ${data.daily_targets.replies}`}
        />
        <Metric
          label="Tweets today"
          value={`${data.today_counts.tweet ?? 0} / ${data.daily_targets.tweets}`}
        />
        <Metric
          label="Follower Δ (7d)"
          value={data.follower_delta_7d != null ? `${data.follower_delta_7d >= 0 ? "+" : ""}${data.follower_delta_7d}` : "—"}
        />
      </div>

      <section className="mb-8">
        <h3 className="mb-3 text-sm font-medium uppercase text-zinc-500">This week</h3>
        <div className="flex flex-wrap gap-4 text-sm text-zinc-300">
          <span>{data.week_counts.reply ?? 0} replies</span>
          <span>{data.week_counts.tweet ?? 0} tweets</span>
          <span>{data.week_counts.thread ?? 0} threads</span>
          <span>{data.week_counts.quote_tweet ?? 0} quotes</span>
        </div>
      </section>

      <section className="mb-8">
        <h3 className="mb-3 text-sm font-medium uppercase text-zinc-500">Content type performance (30d)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-zinc-500">
              <tr>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Count</th>
                <th className="pb-2 pr-4">Avg impressions</th>
                <th className="pb-2 pr-4">Avg ER</th>
                <th className="pb-2">Avg bookmarks</th>
              </tr>
            </thead>
            <tbody className="text-zinc-300">
              {data.content_breakdown.map((row) => (
                <tr key={row.content_type} className="border-t border-zinc-800">
                  <td className="py-2 pr-4 capitalize">{row.content_type.replace("_", " ")}</td>
                  <td className="py-2 pr-4">{row.count}</td>
                  <td className="py-2 pr-4">{row.avg_impressions}</td>
                  <td className="py-2 pr-4">{(row.avg_engagement_rate * 100).toFixed(2)}%</td>
                  <td className="py-2">{row.avg_bookmarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {data.reply_performance.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-medium uppercase text-zinc-500">Reply performance</h3>
          <div className="space-y-3">
            {data.reply_performance.map((r) => (
              <div key={r.post_id} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-sm text-zinc-300">{r.preview_text}</p>
                <p className="mt-2 text-xs text-zinc-500">
                  {r.impressions} imp · {r.likes} likes · {r.replies} replies · ER{" "}
                  {(r.engagement_rate * 100).toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
