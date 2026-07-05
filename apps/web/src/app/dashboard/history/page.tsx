"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, PublishedPost } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

function formatWhen(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function PublishHistoryPage() {
  const [posts, setPosts] = useState<PublishedPost[]>([]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.getPublishHistory(token).then(setPosts);
  }, []);

  return (
    <AppShell title="Published Posts">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Tweets that went live on X. Each post is stored with its X tweet ID for analytics in M6.
      </p>

      {posts.length === 0 && (
        <p className="text-zinc-500">No published posts yet. Publish from the queue when ready.</p>
      )}

      <div className="space-y-4">
        {posts.map((post) => (
          <div key={post.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-zinc-500">
              {post.content_type} · {formatWhen(post.published_at)}
            </p>
            <p className="mt-2 text-white">{post.preview_text}</p>
            <p className="mt-2 text-sm text-sky-400">
              X tweet ID: {post.x_tweet_id}
            </p>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
