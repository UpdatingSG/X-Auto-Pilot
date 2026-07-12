"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, QueueItem, XAccount } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

function formatWhen(iso: string) {
  const dt = new Date(iso);
  return dt.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function PublishQueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [account, setAccount] = useState<XAccount | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const [items, xAccount] = await Promise.allSettled([
      api.getPublishQueue(token),
      api.getXAccount(token),
    ]);
    if (items.status === "fulfilled") setQueue(items.value);
    if (xAccount.status === "fulfilled") setAccount(xAccount.value);
    else setAccount(null);
  }

  useEffect(() => {
    setNowMs(Date.now());
    load();
  }, []);

  async function handleCancel(draftId: string) {
    const token = getToken();
    if (!token) return;
    await api.cancelSchedule(token, draftId);
    await load();
  }

  async function handlePublishNow(draftId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      const post = await api.publishDraft(token, draftId);
      setMessage(
        post.content_type === "quote_tweet"
          ? `Published with link to original post (${post.x_tweet_id}). X blocks API replies for many accounts, so we posted as a linked quote instead.`
          : `Published to X (tweet ${post.x_tweet_id})`,
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Publish failed");
    }
  }

  return (
    <AppShell title="Publish Queue">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Scheduled drafts waiting to go live. Overdue posts publish when the API worker runs.
        On Render&apos;s <strong className="text-zinc-200">free tier</strong> the API sleeps after
        ~15 minutes with no traffic — browsing this site keeps it awake; when you close the tab,
        scheduled jobs fail unless you set up external cron.
      </p>

      <div className="mb-6 rounded-xl border border-sky-800/50 bg-sky-950/30 p-4 text-sm text-sky-100">
        <p className="font-medium text-sky-200">Render free tier: use two cron-job.org jobs</p>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sky-100/90">
          <li>
            <strong>Keep-alive</strong> — GET{" "}
            <code className="text-sky-300">https://xautopilot-api.onrender.com/ping</code> every{" "}
            <strong>5 minutes</strong> (prevents sleep; response is just <code>ok</code>)
          </li>
          <li>
            <strong>Publish worker</strong> — GET{" "}
            <code className="text-sky-300">https://xautopilot-api.onrender.com/v1/worker/cron?secret=YOUR_SECRET</code>{" "}
            every <strong>15 minutes</strong> (or POST <code>/v1/worker/tick</code> with header{" "}
            <code>X-Worker-Secret</code>)
          </li>
        </ol>
        <p className="mt-2 text-sky-200/80">
          Set <code className="text-sky-300">WORKER_CRON_SECRET</code> on Render to match your secret.
          Without the 5-minute keep-alive, cron fails with &quot;output too large&quot; when Render wakes from sleep.
        </p>
      </div>

      {!account && (
        <div className="mb-6 rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 text-sm text-amber-200">
          Connect your X account in Settings → X Account before publishing.
        </div>
      )}

      {queue.length === 0 && (
        <p className="text-zinc-500">
          Nothing scheduled yet. Approve a draft and click Schedule on the Drafts page.
        </p>
      )}

      <div className="space-y-4">
        {queue.map((item, index) => (
          <div
            key={item.draft_id}
            className="flex flex-col gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-5 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="text-xs text-zinc-500">
                #{index + 1} · {item.category} · {item.content_type}
              </p>
              <p className="mt-2 text-white">{item.preview_text}</p>
              <p className="mt-2 text-sm text-sky-400">
                {formatWhen(item.scheduled_at)}
                {nowMs !== null && new Date(item.scheduled_at).getTime() < nowMs && (
                  <span className="ml-2 text-amber-400">· Overdue</span>
                )}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                onClick={() => handlePublishNow(item.draft_id)}
                disabled={!account}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium hover:bg-green-500 disabled:opacity-40"
              >
                Publish now
              </button>
              <button
                onClick={() => handleCancel(item.draft_id)}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
              >
                Cancel
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
