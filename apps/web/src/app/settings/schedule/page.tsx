"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, Schedule } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

const WINDOW_LABELS = ["Morning", "Afternoon", "Evening"];

export default function ScheduleSettingsPage() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [tweetsPerDay, setTweetsPerDay] = useState(3);
  const [jitterMinutes, setJitterMinutes] = useState(15);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.getSchedule(token).then((s) => {
      setSchedule(s);
      setTweetsPerDay(s.tweets_per_day);
      setJitterMinutes(s.jitter_minutes);
    });
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateSchedule(token, {
        tweets_per_day: tweetsPerDay,
        jitter_minutes: jitterMinutes,
      });
      setSchedule(updated);
      setMessage("Schedule settings saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  return (
    <AppShell title="Posting Schedule">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Configure when X-Autopilot may post. Approved drafts are placed into these windows
        with random jitter so posts feel human, not robotic.
      </p>

      {schedule && (
        <div className="mb-8 grid gap-3 sm:grid-cols-3">
          {schedule.posting_windows.map((window, i) => (
            <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
              <p className="text-sm font-medium text-white">{WINDOW_LABELS[i] ?? `Window ${i + 1}`}</p>
              <p className="mt-1 text-lg text-sky-400">
                {window.start} – {window.end}
              </p>
              <p className="mt-1 text-xs text-zinc-500">Every day</p>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="max-w-md space-y-4">
        <label className="block">
          <span className="text-sm text-zinc-400">Tweets per day</span>
          <input
            type="number"
            min={1}
            max={20}
            value={tweetsPerDay}
            onChange={(e) => setTweetsPerDay(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"
          />
        </label>
        <label className="block">
          <span className="text-sm text-zinc-400">Jitter (minutes)</span>
          <input
            type="number"
            min={0}
            max={60}
            value={jitterMinutes}
            onChange={(e) => setJitterMinutes(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"
          />
          <p className="mt-1 text-xs text-zinc-500">
            Random offset so posts land at 9:07 instead of exactly 9:00.
          </p>
        </label>
        <button
          type="submit"
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
        >
          Save schedule
        </button>
      </form>

      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </AppShell>
  );
}
