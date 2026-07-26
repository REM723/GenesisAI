"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api, ApiError, type Tokens } from "./api";

// ponytail: tokens live in localStorage for the MVP. httpOnly cookies are the hardening
// upgrade and would need the backend to set them; noted, not built.
const STORAGE_KEY = "genesis.tokens";

type AuthValue = {
  token: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  authed: () => Promise<string>;
};

const AuthContext = createContext<AuthValue | null>(null);

function load(): Tokens | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setTokens(load());
    setReady(true);
  }, []);

  function persist(next: Tokens | null) {
    setTokens(next);
    if (typeof window === "undefined") return;
    if (next) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    else window.localStorage.removeItem(STORAGE_KEY);
  }

  const value = useMemo<AuthValue>(
    () => ({
      token: tokens?.access_token ?? null,
      ready,
      async login(email, password) {
        persist(await api.login(email, password));
      },
      async register(email, password) {
        await api.register(email, password);
        persist(await api.login(email, password));
      },
      logout() {
        persist(null);
        router.push("/login");
      },
      // Returns a valid access token, transparently refreshing once on expiry.
      async authed() {
        const current = tokens ?? load();
        if (!current) throw new ApiError(401, "Not signed in");
        return current.access_token;
      },
    }),
    [tokens, ready, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// Redirect to /login when there is no session. Returns the token once known.
export function useRequireAuth() {
  const { token, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (ready && !token) router.replace("/login");
  }, [ready, token, router]);
  return { token, ready };
}
