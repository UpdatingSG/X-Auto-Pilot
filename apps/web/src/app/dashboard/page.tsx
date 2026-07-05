"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api } from "@/lib/api-client";
import { clearToken, getToken } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const [hasProfile, setHasProfile] = useState(false);
  const [sourceCount, setSourceCount] = useState(0);
  const [itemCount, setItemCount] = useState(0);
  const [ideaCount, setIdeaCount] = useState(0);
  const [draftCount, setDraftCount] = useState(0);
  const [queueCount, setQueueCount] = useState(0);

  useEffect(() => {
    const token = getToken();
    if (!token) { router.replace("/login"); return; }
    Promise.allSettled([
      api.getVoiceProfile(token),
      api.listSources(token),
      api.listKnowledgeItems(token),
      api.getTodayPlan(token),
      api.listDrafts(token, "ready"),
      api.getPublishQueue(token),
    ]).then(([profile, sources, items, plan, drafts, queue]) => {
      setHasProfile(profile.status === "fulfilled");
      if (sources.status === "fulfilled") setSourceCount(sources.value.length);
      if (items.status === "fulfilled") setItemCount(items.value.length);
      if (plan.status === "fulfilled") setIdeaCount(plan.value.ideas.length);
      if (drafts.status === "fulfilled") setDraftCount(drafts.value.length);
      if (queue.status === "fulfilled") setQueueCount(queue.value.length);
    });
  }, [router]);

  return (
    <AppShell title="Dashboard">
      <div className="max-w-2xl">
        <p className="text-zinc-400">Your AI content team at a glance.</p>
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <StatCard label="Voice Profile" value={hasProfile ? "✅ Set" : "Not set"} href="/settings/profile" warn={!hasProfile} />
          <StatCard label="Sources" value={String(sourceCount)} href="/settings/sources" />
          <StatCard label="Articles" value={String(itemCount)} href="/settings/sources" />
          <StatCard label="Today's ideas" value={ideaCount ? String(ideaCount) : "—"} href="/dashboard/plan" />
          <StatCard label="Ready drafts" value={draftCount ? String(draftCount) : "—"} href="/dashboard/drafts" />
          <StatCard label="Scheduled" value={queueCount ? String(queueCount) : "—"} href="/dashboard/schedule" />
        </div>
        {!hasProfile && (
          <div className="mt-6 rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 text-sm text-amber-200">
            Start by setting up your{" "}
            <Link href="/settings/profile" className="underline">voice profile</Link>
            {" "}— the AI needs to know how you write.
          </div>
        )}
      </div>
    </AppShell>
  );
}

function StatCard({
  label, value, href, warn,
}: { label: string; value: string; href: string; warn?: boolean }) {
  return (
    <Link
      href={href}
      className={`rounded-xl border p-4 transition hover:bg-zinc-900 ${
        warn ? "border-amber-800" : "border-zinc-800"
      }`}
    >
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </Link>
  );
}
