"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import { clearToken, getToken } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/settings/profile", label: "Voice Profile" },
  { href: "/settings/sources", label: "Sources" },
  { href: "/settings/schedule", label: "Schedule" },
  { href: "/settings/x", label: "X Account" },
  { href: "/dashboard/plan", label: "Content Plan" },
  { href: "/dashboard/engagement", label: "Engagement" },
  { href: "/dashboard/drafts", label: "Drafts" },
  { href: "/dashboard/schedule", label: "Publish Queue" },
  { href: "/dashboard/history", label: "Published" },
  { href: "/dashboard/analytics", label: "Analytics" },
];

export function AppShell({ children, title }: { children: React.ReactNode; title: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api.me(token).then((u) => setEmail(u.email)).catch(() => {
      clearToken();
      router.replace("/login");
    });
  }, [router]);

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="w-64 border-r border-zinc-800 bg-zinc-900 p-6">
        <h1 className="text-lg font-semibold text-white">X-Autopilot</h1>
        <p className="mt-1 text-xs text-zinc-500">Milestone 7</p>
        <nav className="mt-8 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-lg px-3 py-2 text-sm ${
                pathname === item.href
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-800 px-8 py-4">
          <div>
            <h2 className="text-xl font-medium">{title}</h2>
            {email && <p className="text-sm text-zinc-400">{email}</p>}
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
          >
            Log out
          </button>
        </header>
        <div className="flex-1 p-8">{children}</div>
      </main>
    </div>
  );
}
