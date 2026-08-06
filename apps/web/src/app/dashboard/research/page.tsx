"use client";

import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, ResearchReport } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

const DEFAULT_PROVIDERS = [
  "hacker_news",
  "github_trending",
  "devto",
  "reddit_browser",
  "x_browser",
];

/** Phase 1 returns demo/fixture URLs (e.g. x.example) — don't open those as real links. */
function isRealExternalUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
    const host = parsed.hostname.toLowerCase();
    if (host === "example" || host.endsWith(".example") || host === "example.com") {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export default function ResearchPage() {
  const [topics, setTopics] = useState("fastapi, browser automation, python");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ResearchReport | null>(null);

  async function handleRun() {
    const token = getToken();
    if (!token) return;
    const parsed = topics
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (!parsed.length) {
      setError("Enter at least one topic");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.runResearch(token, {
        topics: parsed,
        providers: DEFAULT_PROVIDERS,
      });
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Research failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Research">
      <div className="max-w-3xl space-y-6">
        <p className="text-zinc-400">
          Scouts topics across providers, then ranks what to write about. Phase 1
          uses <span className="text-zinc-300">demo fixture data</span> (not live
          X/Reddit scrapes) — titles labeled demo won&apos;t open a real page yet.
        </p>

        <div className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <label className="block text-sm text-zinc-400">
            Topics (comma-separated)
            <input
              value={topics}
              onChange={(e) => setTopics(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-zinc-100"
            />
          </label>
          <p className="text-xs text-zinc-500">
            Providers: {DEFAULT_PROVIDERS.join(", ")}
          </p>
          <button
            type="button"
            onClick={handleRun}
            disabled={busy}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
          >
            {busy ? "Running…" : "Run research"}
          </button>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </div>

        {report && (
          <div className="space-y-4">
            <div className="rounded-xl border border-zinc-800 p-4">
              <h3 className="text-sm font-medium text-zinc-300">
                {report.run_date} · {report.discussions.length} discussions ·{" "}
                {report.providers_used.join(", ")}
              </h3>
              <ul className="mt-3 space-y-2">
                {report.discussions.slice(0, 12).map((d) => {
                  const realLink = isRealExternalUrl(d.url);
                  return (
                    <li key={d.canonical_key} className="text-sm">
                      {realLink ? (
                        <a
                          href={d.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sky-400 hover:underline"
                        >
                          {d.title}
                        </a>
                      ) : (
                        <span className="text-zinc-200">{d.title}</span>
                      )}
                      <span className="ml-2 text-zinc-500">
                        {d.provider} · score {d.score}
                      </span>
                      {!realLink && (
                        <span className="ml-2 rounded bg-amber-950/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-300">
                          demo fixture
                        </span>
                      )}
                      {d.excerpt && (
                        <p className="text-zinc-500">{d.excerpt}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>

            {report.insights.length > 0 && (
              <div className="rounded-xl border border-zinc-800 p-4">
                <h3 className="text-sm font-medium text-zinc-300">Insights</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-zinc-400">
                  {report.insights.map((insight) => (
                    <li key={insight.summary}>{insight.summary}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-xl border border-zinc-800 p-4">
              <h3 className="mb-2 text-sm font-medium text-zinc-300">
                Markdown artifact
              </h3>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-zinc-950 p-3 text-xs text-zinc-400">
                {report.markdown}
              </pre>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
