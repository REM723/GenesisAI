"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NewProject() {
  const { token } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const project = await api.createProject(token, name.trim(), idea.trim());
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
      setBusy(false);
    }
  }

  return (
    <div className="settle mx-auto max-w-xl">
      <h1 className="font-serif text-3xl tracking-tight text-ink">A new idea</h1>
      <p className="mt-1.5 text-sm text-muted">
        Give it a name and describe what you want to build, in your own words.
      </p>

      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Project name">
          <Input
            required
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Habit tracker"
          />
        </Field>
        <Field label="The idea" hint="One clear paragraph works best.">
          <Textarea
            required
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="A mobile-first habit tracker with streaks and weekly email summaries."
          />
        </Field>

        {error ? (
          <p className="rounded-[10px] border border-err/25 bg-err/10 px-3.5 py-2.5 text-[13px] text-err">
            {error}
          </p>
        ) : null}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Create project"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
