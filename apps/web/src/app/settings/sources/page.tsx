"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, KnowledgeItem, KnowledgeSource } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function SourcesPage() {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [name, setName] = useState("Hacker News");
  const [url, setUrl] = useState("https://hnrss.org/frontpage");
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const [s, i] = await Promise.all([
      api.listSources(token),
      api.listKnowledgeItems(token),
    ]);
    setSources(s);
    setItems(i);
  }

  useEffect(() => { load(); }, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setError(null);
    try {
      await api.createSource(token, {
        source_type: "rss",
        name,
        config: { url },
      });
      setMessage("Source added");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add source");
    }
  }

  async function handleFetch(sourceId: string) {
    const token = getToken();
    if (!token) return;
    setLoading(sourceId);
    setError(null);
    try {
      const result = await api.fetchSource(token, sourceId);
      setMessage(`Fetched ${result.items_ingested} new items (${result.items_skipped} duplicates skipped)`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Fetch failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <AppShell title="Knowledge Sources">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Add RSS feeds and other sources. The AI reads these to generate timely, relevant content.
      </p>

      <form onSubmit={handleAdd} className="mb-8 max-w-2xl space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="font-medium">Add RSS feed</h3>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2"
        />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2"
        />
        <button type="submit" className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium hover:bg-sky-400">
          Add source
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {message && <p className="mb-4 text-sm text-green-400">{message}</p>}

      <h3 className="mb-3 font-medium">Your sources</h3>
      <div className="mb-8 space-y-2">
        {sources.length === 0 && <p className="text-zinc-500">No sources yet.</p>}
        {sources.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
            <div>
              <p className="font-medium">{s.name}</p>
              <p className="text-xs text-zinc-500">{s.config.url}</p>
            </div>
            <button
              onClick={() => handleFetch(s.id)}
              disabled={loading === s.id}
              className="rounded-lg border border-zinc-600 px-3 py-1.5 text-sm hover:bg-zinc-800 disabled:opacity-50"
            >
              {loading === s.id ? "Fetching…" : "Fetch now"}
            </button>
          </div>
        ))}
      </div>

      <h3 className="mb-3 font-medium">Ingested articles ({items.length})</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
            <p className="font-medium">{item.title}</p>
            {item.url && (
              <a href={item.url} target="_blank" rel="noreferrer" className="text-xs text-sky-400 hover:underline">
                {item.url}
              </a>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
