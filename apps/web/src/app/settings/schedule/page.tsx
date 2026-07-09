"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, Schedule } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

const WINDOW_LABELS = ["Morning", "Afternoon", "Evening"];

export default function ScheduleSettingsPage() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [tweetsPerDay, setTweetsPerDay] = useState(1);
  const [repliesPerDay, setRepliesPerDay] = useState(10);
  const [threadsPerWeek, setThreadsPerWeek] = useState(1);
  const [jitterMinutes, setJitterMinutes] = useState(15);
  const [growthMode, setGrowthMode] = useState(true);
  const [autoScheduleReplies, setAutoScheduleReplies] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.getSchedule(token).then((s) => {
      setSchedule(s);
      setTweetsPerDay(s.tweets_per_day);
      setRepliesPerDay(s.replies_per_day);
      setThreadsPerWeek(s.threads_per_week);
      setJitterMinutes(s.jitter_minutes);
      setGrowthMode(s.growth_mode);
      setAutoScheduleReplies(s.auto_schedule_replies);
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
        replies_per_day: repliesPerDay,
        threads_per_week: threadsPerWeek,
        jitter_minutes: jitterMinutes,
        growth_mode: growthMode,
        auto_schedule_replies: autoScheduleReplies,
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
        Growth mode prioritizes replies over broadcasting. Replies use their own daily quota and can
        auto-schedule when drafts are generated from the Engagement or Briefing pages.
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
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={growthMode}
            onChange={(e) => setGrowthMode(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm text-zinc-300">Growth mode (reply-first planning)</span>
        </label>
        <label className="block">
          <span className="text-sm text-zinc-400">Replies per day</span>
          <input
            type="number"
            min={0}
            max={50}
            value={repliesPerDay}
            onChange={(e) => setRepliesPerDay(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"
          />
        </label>
        <label className="block">
          <span className="text-sm text-zinc-400">Original tweets per day</span>
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
          <span className="text-sm text-zinc-400">Threads per week</span>
          <input
            type="number"
            min={0}
            max={14}
            value={threadsPerWeek}
            onChange={(e) => setThreadsPerWeek(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"
          />
        </label>
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={autoScheduleReplies}
            onChange={(e) => setAutoScheduleReplies(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm text-zinc-300">Auto-schedule reply drafts after generation</span>
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
