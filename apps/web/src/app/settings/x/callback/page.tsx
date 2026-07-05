"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { api, ApiError } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

function XOAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Completing X authorization…");
  const completed = useRef(false);

  useEffect(() => {
    if (completed.current) return;
    completed.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const twitterError = searchParams.get("error");
    const token = getToken();

    if (twitterError) {
      router.replace(`/settings/x?error=oauth_denied`);
      return;
    }
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!code || !state) {
      router.replace("/settings/x?error=oauth_failed");
      return;
    }

    api
      .completeXOAuth(token, code, state)
      .then(() => router.replace("/settings/x?connected=1"))
      .catch((err) => {
        const detail = err instanceof ApiError ? err.message : "Authorization failed";
        setMessage(detail);
        setTimeout(
          () => router.replace(`/settings/x?error=oauth_failed&detail=${encodeURIComponent(detail)}`),
          3000,
        );
      });
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 text-center text-zinc-300">
      <p>{message}</p>
    </div>
  );
}

export default function XOAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 text-center text-zinc-300">
          <p>Completing X authorization…</p>
        </div>
      }
    >
      <XOAuthCallbackContent />
    </Suspense>
  );
}
