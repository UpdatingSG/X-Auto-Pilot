"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError, XAccount } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

function XAccountContent() {
  const searchParams = useSearchParams();
  const [account, setAccount] = useState<XAccount | null>(null);
  const [connectionMode, setConnectionMode] = useState<"mock" | "live">("mock");
  const [handle, setHandle] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    if (searchParams.get("connected") === "1") {
      setMessage("X account connected successfully.");
    }
    const oauthError = searchParams.get("error");
    if (oauthError === "invalid_state") {
      setError("OAuth session expired. Please try connecting again.");
    } else if (oauthError === "oauth_denied") {
      setError("You declined authorization on X. Click Connect with X to try again.");
    } else if (oauthError === "oauth_failed") {
      const detail = searchParams.get("detail");
      setError(
        detail
          ? decodeURIComponent(detail)
          : "X authorization failed. Check callback URL in X Developer Portal.",
      );
    }

    Promise.all([
      api.getXAccount(token).catch(() => null),
      api.getXConfig(token),
    ])
      .then(([acc, config]) => {
        if (acc) setAccount(acc);
        setConnectionMode(config.connection_mode === "live" ? "live" : "mock");
      })
      .finally(() => setLoading(false));
  }, [searchParams]);

  async function handleMockConnect(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !handle.trim()) return;
    setError(null);
    setMessage(null);
    try {
      const linked = await api.connectXAccount(token, handle.trim());
      setAccount(linked);
      setMessage(`Connected as @${linked.handle} (mock)`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connect failed");
    }
  }

  async function handleDisconnect() {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    await api.disconnectXAccount(token);
    setAccount(null);
    setMessage("Disconnected. Connect again with X.");
  }

  async function handleOAuthConnect() {
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      const { authorization_url } = await api.startXOAuth(token);
      window.location.href = authorization_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start OAuth");
    }
  }

  return (
    <AppShell title="X Account">
      <p className="mb-6 max-w-2xl text-zinc-400">
        Link your X account so approved drafts can be published.
        {connectionMode === "mock"
          ? " Dev mode uses a mock connect — set X_API_MODE=live in the API .env for real OAuth."
          : " Production mode — you will be redirected to X to authorize."}
      </p>

      {loading && <p className="text-zinc-500">Loading…</p>}

      {!loading && account && (
        <div
          className={`rounded-xl border p-5 ${
            account.needs_reauth
              ? "border-amber-800/50 bg-amber-950/20"
              : "border-green-800/50 bg-green-950/20"
          }`}
        >
          {account.needs_reauth ? (
            <>
              <p className="text-sm text-amber-400">Session expired</p>
              <p className="mt-1 text-xl font-medium text-white">@{account.handle}</p>
              <p className="mt-2 text-sm text-amber-200/90">
                Your X authorization expired or was revoked. Reconnect to publish and sync metrics.
              </p>
              {connectionMode === "live" ? (
                <button
                  onClick={handleOAuthConnect}
                  className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
                >
                  Reconnect with X
                </button>
              ) : (
                <button
                  onClick={handleDisconnect}
                  className="mt-4 rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
                >
                  Disconnect and reconnect
                </button>
              )}
            </>
          ) : (
            <>
              <p className="text-sm text-green-400">Connected</p>
              <p className="mt-1 text-xl font-medium text-white">@{account.handle}</p>
              <p className="mt-1 text-xs text-zinc-500">X user ID: {account.x_user_id}</p>
              {account.x_user_id.startsWith("mock-") && connectionMode === "live" && (
                <p className="mt-3 text-sm text-amber-300">
                  This is a mock connection from dev mode. Disconnect and use Connect with X for real OAuth.
                </p>
              )}
              <button
                onClick={handleDisconnect}
                className="mt-4 rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
              >
                Disconnect
              </button>
            </>
          )}
        </div>
      )}

      {!loading && !account && connectionMode === "live" && (
        <button
          onClick={handleOAuthConnect}
          className="rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-medium hover:bg-sky-500"
        >
          Connect with X
        </button>
      )}

      {!loading && !account && connectionMode === "mock" && (
        <form onSubmit={handleMockConnect} className="max-w-md space-y-4">
          <label className="block">
            <span className="text-sm text-zinc-400">Your X handle (mock)</span>
            <input
              type="text"
              placeholder="yourhandle"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
          >
            Connect (mock)
          </button>
        </form>
      )}

      {message && <p className="mt-4 text-sm text-green-400">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
    </AppShell>
  );
}

export default function XAccountPage() {
  return (
    <Suspense fallback={
      <AppShell title="X Account">
        <p className="text-zinc-500">Loading…</p>
      </AppShell>
    }>
      <XAccountContent />
    </Suspense>
  );
}
