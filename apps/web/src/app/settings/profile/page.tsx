"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { api, ApiError } from "@/lib/api-client";
import { getToken } from "@/lib/auth";

export default function VoiceProfilePage() {
  const [profession, setProfession] = useState("Backend Engineer");
  const [bio, setBio] = useState("");
  const [topics, setTopics] = useState("System Design, Distributed Systems, AI");
  const [tone, setTone] = useState("technical, helpful, honest");
  const [avoid, setAvoid] = useState("leverage, synergy, game-changer");
  const [neverDiscuss, setNeverDiscuss] = useState("politics, crypto shilling");
  const [version, setVersion] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.getVoiceProfile(token).then((p) => {
      setProfession(p.profession ?? "");
      setBio(p.bio ?? "");
      setTopics(p.interests.map((i) => i.topic).join(", "));
      setTone(p.tone.join(", "));
      setAvoid(p.vocabulary.avoid.join(", "));
      setNeverDiscuss(p.never_discuss.join(", "));
      setVersion(p.version);
    }).catch(() => {/* no profile yet */});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setError(null);
    setMessage(null);
    try {
      const profile = await api.saveVoiceProfile(token, {
        profession,
        bio,
        interests: topics.split(",").map((t) => ({ topic: t.trim(), weight: 1 })).filter((i) => i.topic),
        tone: tone.split(",").map((t) => t.trim()).filter(Boolean),
        vocabulary: {
          use: [],
          avoid: avoid.split(",").map((t) => t.trim()).filter(Boolean),
        },
        never_discuss: neverDiscuss.split(",").map((t) => t.trim()).filter(Boolean),
        writing_style: { formality: "casual-professional" },
      });
      setVersion(profile.version);
      setMessage(`Voice profile saved (v${profile.version})`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  return (
    <AppShell title="Voice Profile">
      <p className="mb-6 max-w-2xl text-zinc-400">
        This is your AI&apos;s personality. Every tweet and thread will sound like this voice.
        {version && <span className="ml-2 text-sky-400">Active version: {version}</span>}
      </p>
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-5">
        <Field label="Profession" value={profession} onChange={setProfession} />
        <Field label="Bio" value={bio} onChange={setBio} multiline />
        <Field label="Topics (comma-separated)" value={topics} onChange={setTopics} />
        <Field label="Tone (comma-separated)" value={tone} onChange={setTone} />
        <Field label="Words to avoid" value={avoid} onChange={setAvoid} />
        <Field label="Never discuss" value={neverDiscuss} onChange={setNeverDiscuss} />
        {error && <p className="text-sm text-red-400">{error}</p>}
        {message && <p className="text-sm text-green-400">{message}</p>}
        <button type="submit" className="rounded-lg bg-sky-500 px-6 py-2.5 font-medium hover:bg-sky-400">
          Save voice profile
        </button>
      </form>
    </AppShell>
  );
}

function Field({
  label, value, onChange, multiline,
}: {
  label: string; value: string; onChange: (v: string) => void; multiline?: boolean;
}) {
  const cls = "mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-white outline-none focus:border-sky-500";
  return (
    <div>
      <label className="block text-sm text-zinc-300">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} className={cls} />
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} className={cls} />
      )}
    </div>
  );
}
