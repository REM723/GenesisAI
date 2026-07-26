"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "./ui/button";
import { Field, Input } from "./ui/input";
import { Spinner } from "./ui/spinner";
import { Wordmark } from "./wordmark";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { login, register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const signup = mode === "signup";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (signup) await register(email, password);
      else await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  }

  return (
    <main className="grain flex min-h-screen items-center justify-center px-6">
      <div className="settle w-full max-w-sm">
        <div className="mb-9 flex justify-center">
          <Wordmark />
        </div>
        <h1 className="text-center font-serif text-2xl tracking-tight text-ink">
          {signup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="mt-2 text-center text-sm text-muted">
          {signup ? "Start turning ideas into software." : "Sign in to continue."}
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <Field label="Email">
            <Input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </Field>
          <Field label="Password" hint={signup ? "At least 8 characters." : undefined}>
            <Input
              type="password"
              autoComplete={signup ? "new-password" : "current-password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </Field>

          {error ? (
            <p className="rounded-[10px] border border-err/25 bg-err/10 px-3.5 py-2.5 text-[13px] text-err">
              {error}
            </p>
          ) : null}

          <Button type="submit" size="lg" className="w-full" disabled={busy}>
            {busy ? <Spinner /> : signup ? "Create account" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          {signup ? "Already have an account? " : "New here? "}
          <Link
            href={signup ? "/login" : "/signup"}
            className="text-ink underline-offset-4 hover:underline"
          >
            {signup ? "Sign in" : "Create one"}
          </Link>
        </p>
      </div>
    </main>
  );
}
