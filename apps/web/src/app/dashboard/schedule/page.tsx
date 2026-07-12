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
        Scheduled drafts waiting to go live. Overdue posts publish when the API worker runs
        (every minute while the server is awake). On Render&apos;s free tier the API sleeps
        after ~15 min idle — use <strong className="text-zinc-200">Publish now</strong> or set
        up a cron ping to <code className="text-sky-300">POST /v1/worker/tick</code>.
      </p>

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
