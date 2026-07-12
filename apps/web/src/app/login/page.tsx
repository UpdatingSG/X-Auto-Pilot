"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api-client";
import { saveToken, saveUserEmail, warmApiHealth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    warmApiHealth();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setStatus("Signing in…");
    try {
      const { access_token, email: userEmail } = await api.login(email, password);
      saveToken(access_token);
      if (userEmail) saveUserEmail(userEmail);
      setStatus("Opening dashboard…");
      router.push("/dashboard/briefing");
    } catch (err) {
      setStatus(null);
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900 p-8 shadow-xl">
        <h1 className="text-2xl font-semibold text-white">Sign in to X-Autopilot</h1>
        <p className="mt-2 text-sm text-zinc-400">Your AI content team awaits.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="block text-sm text-zinc-300">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-white outline-none focus:border-sky-500"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-300">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-white outline-none focus:border-sky-500"
            />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          {status && !error && <p className="text-sm text-zinc-400">{status}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-sky-500 py-2.5 font-medium text-white hover:bg-sky-400 disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-400">
          No account?{" "}
          <Link href="/register" className="text-sky-400 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
