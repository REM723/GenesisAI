"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, type ApiKey } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const PROVIDERS = [
  "openai",
  "grok",
  "groq",
  "gemini",
  "deepseek",
  "mistral",
  "openrouter",
  "ollama",
];

export default function KeysPage() {
  const { token } = useAuth();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [provider, setProvider] = useState(PROVIDERS[0]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .listKeys(token)
      .then(setKeys)
      .catch((e) => setError(e.message));
  }, [token]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.addKey(token, provider, value.trim());
      setKeys((prev) => [...(prev ?? []).filter((k) => k.provider !== provider), created]);
      setValue("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the key.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="settle mx-auto max-w-xl">
      <h1 className="font-serif text-3xl tracking-tight text-ink">Provider keys</h1>
      <p className="mt-1.5 text-sm text-muted">
        Bring your own keys. They are encrypted at rest and never shown again.
      </p>

      <Card className="mt-8 p-6">
        <form onSubmit={add} className="space-y-4">
          <Field label="Provider">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="h-10 w-full rounded-[10px] border border-line/12 bg-surface/70 px-3 text-sm text-ink transition-colors duration-150 ease-out hover:border-line/20 focus:border-accent/50"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p} className="bg-surface">
                  {p}
                </option>
              ))}
            </select>
          </Field>
          <Field label="API key">
            <Input
              type="password"
              required
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="sk-..."
            />
          </Field>
          {error ? <p className="text-[13px] text-err">{error}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Save key"}
          </Button>
        </form>
      </Card>

      <div className="mt-8">
        <h2 className="text-[13px] font-medium uppercase tracking-[0.14em] text-faint">Saved</h2>
        <div className="mt-3">
          {keys === null ? (
            <div className="flex items-center gap-3 py-6 text-sm text-muted">
              <Spinner /> Loading
            </div>
          ) : keys.length === 0 ? (
            <p className="py-6 text-sm text-faint">No keys yet. Add one to run the agents.</p>
          ) : (
            <Card className="divide-y divide-line/8">
              {keys.map((k) => (
                <div key={k.id} className="flex items-center justify-between px-5 py-3.5">
                  <span className="text-sm text-ink">{k.provider}</span>
                  <span className="font-mono text-xs text-faint">•••• encrypted</span>
                </div>
              ))}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
