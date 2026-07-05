"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, ContentPlan } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function ContentPlanPage() {
  const [plan, setPlan] = useState<ContentPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const p = await api.getTodayPlan(token);
      setPlan(p);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setPlan(null);
      else setError(err instanceof ApiError ? err.message : "Failed to load plan");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleGenerate(regenerate = false) {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      const p = await api.generatePlan(token, regenerate);
      setPlan(p);
      setMessage(regenerate ? "Plan regenerated with fresh AI ideas" : "Daily plan generated");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    }
  }

  async function handleApprove(ideaId: string) {
    const token = getToken();
    if (!token || !plan) return;
    await api.updateIdeaStatus(token, plan.id, ideaId, "approved");
    await load();
    setMessage("Idea approved — ready for draft generation");
  }

  async function handleGenerateDraft(ideaId: string) {
    const token = getToken();
    if (!token) return;
    await api.generateDraft(token, ideaId);
    setMessage("Draft generated! Check the Drafts page.");
    await load();
  }

  const mix = plan
    ? {
        tweet: plan.composition?.tweets ?? 0,
        thread: plan.composition?.threads ?? 0,
        reply: plan.composition?.replies ?? 0,
      }
    : null;

  const totalIdeas = plan?.ideas.length ?? 0;
  const pct = (type: string) =>
    totalIdeas && mix ? Math.round(((mix[type as keyof typeof mix] ?? 0) / totalIdeas) * 100) : 0;

  return (
    <AppShell title="Content Plan">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Your AI content planner suggests tweets, threads, and replies based on your voice profile and engagement targets.
      </p>

      {!plan && !loading && (
        <button onClick={() => handleGenerate(false)} className="rounded-lg bg-sky-500 px-6 py-2.5 font-medium hover:bg-sky-400">
          Generate today&apos;s plan
        </button>
      )}

      {plan && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-500">{plan.ideas.length} ideas for {plan.plan_date}</p>
              {mix && (
                <p className="mt-1 text-xs text-zinc-500">
                  Mix: {mix.tweet} tweets ({pct("tweet")}%) · {mix.thread} threads ({pct("thread")}%) · {mix.reply} replies ({pct("reply")}%)
                  <span className="ml-2 text-zinc-600">· target ~60/25/15</span>
                </p>
              )}
              {plan.composition?.hints && plan.composition.hints.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-amber-400/90">
                  {plan.composition.hints.map((hint) => (
                    <li key={hint}>• {hint}</li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={() => handleGenerate(true)}
              className="rounded-lg border border-zinc-600 px-4 py-2 text-sm hover:bg-zinc-800"
            >
              Regenerate plan
            </button>
          </div>
          {plan.ideas.map((idea) => (
            <div key={idea.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{idea.category}</span>
                    <span className={`rounded px-2 py-0.5 text-xs ${
                      idea.content_type === "thread"
                        ? "bg-purple-900/50 text-purple-300"
                        : idea.content_type === "reply"
                          ? "bg-amber-900/50 text-amber-300"
                          : "bg-sky-900/50 text-sky-300"
                    }`}>
                      {idea.content_type}
                    </span>
                  </div>
                  <h3 className="mt-2 font-medium">{idea.title}</h3>
                  <p className="mt-1 text-sm text-zinc-400">{idea.hook_idea}</p>
                  <p className="mt-1 text-xs text-zinc-500">{idea.rationale}</p>
                </div>
                <span className={`text-xs ${idea.status === "approved" ? "text-green-400" : idea.status === "generated" ? "text-sky-400" : "text-zinc-500"}`}>
                  {idea.status}
                </span>
              </div>
              <div className="mt-4 flex gap-2">
                {idea.status === "proposed" && (
                  <button onClick={() => handleApprove(idea.id)} className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm hover:bg-zinc-800">
                    Approve
                  </button>
                )}
                {idea.status === "approved" && (
                  <button onClick={() => handleGenerateDraft(idea.id)} className="rounded-lg bg-sky-500 px-3 py-1.5 text-sm hover:bg-sky-400">
                    Generate draft
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
    </AppShell>
  );
}
