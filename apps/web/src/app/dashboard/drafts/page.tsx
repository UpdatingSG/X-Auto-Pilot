"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, Draft } from "@/lib/api-client";
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

function contentTypeBadge(type: string) {
  if (type === "thread") return "bg-purple-900/50 text-purple-300";
  if (type === "reply") return "bg-amber-900/50 text-amber-300";
  return "bg-sky-900/50 text-sky-300";
}

function contentTypeLabel(type: string) {
  if (type === "thread") return "Thread — multiple connected tweets";
  if (type === "reply") return "Reply — engages under someone else's tweet";
  return "Tweet — single post";
}

function defaultVariantId(draft: Draft): string | null {
  if (draft.selected_variant_id) return draft.selected_variant_id;
  const selected = draft.variants.find((v) => v.is_selected);
  return selected?.id ?? draft.variants[0]?.id ?? null;
}

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const visibleDrafts = useMemo(
    () => drafts.filter((d) => d.status !== "rejected"),
    [drafts],
  );

  async function load() {
    const token = getToken();
    if (!token) return;
    const list = await api.listDrafts(token);
    setDrafts(list);
    setSelectedVariants((prev) => {
      const next = { ...prev };
      for (const draft of list) {
        if (draft.status === "rejected") continue;
        const id = defaultVariantId(draft);
        if (id) next[draft.id] = id;
      }
      return next;
    });
  }

  useEffect(() => { load(); }, []);

  function handleSelectVariant(draftId: string, variantId: string) {
    setSelectedVariants((prev) => ({ ...prev, [draftId]: variantId }));
  }

  async function handleApprove(draft: Draft) {
    const token = getToken();
    const variantId = selectedVariants[draft.id] ?? defaultVariantId(draft);
    if (!token || !variantId) return;
    setError(null);
    setMessage(null);
    try {
      await api.approveDraft(token, draft.id, variantId);
      setMessage("Draft approved — you can now schedule it.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approve failed");
    }
  }

  async function handleReject(draftId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      await api.rejectDraft(token, draftId);
      setMessage("Draft rejected and hidden from this list.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reject failed");
    }
  }

  async function handleSchedule(draftId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    const variantId = selectedVariants[draftId];
    try {
      if (variantId) {
        await api.selectDraftVariant(token, draftId, variantId);
      }
      const updated = await api.scheduleDraft(token, draftId);
      setMessage(
        updated.scheduled_at
          ? `Scheduled for ${formatWhen(updated.scheduled_at)}`
          : "Draft scheduled",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Schedule failed");
    }
  }

  async function handleCancelSchedule(draftId: string) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    await api.cancelSchedule(token, draftId);
    setMessage("Schedule cancelled — draft is approved again.");
    await load();
  }

  return (
    <AppShell title="Drafts">
      <p className="mb-4 max-w-2xl text-zinc-400">
        Review AI-generated variations. Click a variant to select it, then approve or reject.
      </p>
      <div className="mb-6 flex flex-wrap gap-3 text-xs text-zinc-500">
        <span className="rounded bg-sky-900/40 px-2 py-1 text-sky-300">tweet</span> single post
        <span className="rounded bg-purple-900/40 px-2 py-1 text-purple-300">thread</span> numbered multi-tweet chain
        <span className="rounded bg-amber-900/40 px-2 py-1 text-amber-300">reply</span> comment on another tweet
      </div>

      {visibleDrafts.length === 0 && (
        <p className="text-zinc-500">No drafts yet. Approve ideas on the Content Plan page first.</p>
      )}

      <div className="space-y-6">
        {visibleDrafts.map((draft) => {
          const activeVariantId = selectedVariants[draft.id] ?? defaultVariantId(draft);
          const canSelect = draft.status === "ready" || draft.status === "approved";

          return (
            <div key={draft.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-zinc-400">{draft.category}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${contentTypeBadge(draft.content_type)}`}>
                    {draft.content_type}
                  </span>
                  <span className="text-xs text-zinc-500">{contentTypeLabel(draft.content_type)}</span>
                </div>
                <span
                  className={`text-xs ${
                    draft.status === "approved"
                      ? "text-green-400"
                      : draft.status === "scheduled"
                        ? "text-sky-400"
                        : "text-amber-400"
                  }`}
                >
                  {draft.status}
                  {draft.scheduled_at && ` · ${formatWhen(draft.scheduled_at)}`}
                </span>
              </div>
              <div className="space-y-3">
                {draft.variants.map((v) => {
                  const isSelected = activeVariantId === v.id;
                  const isTopScored = v.variant_index === 0;

                  return (
                    <button
                      key={v.id}
                      type="button"
                      disabled={!canSelect}
                      onClick={() => canSelect && handleSelectVariant(draft.id, v.id)}
                      className={`w-full rounded-lg border p-4 text-left transition ${
                        isSelected
                          ? "border-sky-500 bg-sky-950/40 ring-1 ring-sky-500/50"
                          : "border-zinc-700 hover:border-zinc-600"
                      } ${canSelect ? "cursor-pointer" : "cursor-default"}`}
                    >
                      {draft.content_type === "thread" && v.thread_tweets && v.thread_tweets.length > 0 ? (
                        <div className="space-y-2">
                          <p className="text-xs text-purple-300">
                            Thread · {v.thread_tweets.length} tweets
                          </p>
                          {v.thread_tweets.map((tweet) => (
                            <p key={tweet.index} className="text-white">
                              <span className="mr-2 text-xs text-zinc-500">{tweet.index + 1}.</span>
                              {tweet.text}
                            </p>
                          ))}
                        </div>
                      ) : (
                        <p className="text-white">{v.content_text}</p>
                      )}
                      <p className="mt-2 text-xs text-zinc-500">
                        Score: {(v.scores.overall * 100).toFixed(0)}% · hook {(v.scores.hook_strength * 100).toFixed(0)}% · voice {(v.scores.voice_match * 100).toFixed(0)}%
                        {isTopScored && <span className="ml-2 text-zinc-400">highest score</span>}
                        {isSelected && <span className="ml-2 text-sky-400">★ selected</span>}
                      </p>
                    </button>
                  );
                })}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {draft.status === "ready" && (
                  <>
                    <button
                      onClick={() => handleApprove(draft)}
                      className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium hover:bg-green-500"
                    >
                      Approve selected
                    </button>
                    <button
                      onClick={() => handleReject(draft.id)}
                      className="rounded-lg border border-red-800 px-4 py-2 text-sm text-red-300 hover:bg-red-950/40"
                    >
                      Reject
                    </button>
                  </>
                )}
                {draft.status === "approved" && (
                  <>
                    <button
                      onClick={() => handleSchedule(draft.id)}
                      className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
                    >
                      Schedule
                    </button>
                    <button
                      onClick={() => handleReject(draft.id)}
                      className="rounded-lg border border-red-800 px-4 py-2 text-sm text-red-300 hover:bg-red-950/40"
                    >
                      Reject
                    </button>
                  </>
                )}
                {draft.status === "scheduled" && (
                  <button
                    onClick={() => handleCancelSchedule(draft.id)}
                    className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
                  >
                    Cancel schedule
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </AppShell>
  );
}
