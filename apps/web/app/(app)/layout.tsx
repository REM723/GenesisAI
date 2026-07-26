"use client";

import { AppNav } from "@/components/app-nav";
import { Spinner } from "@/components/ui/spinner";
import { useRequireAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, ready } = useRequireAuth();

  if (!ready || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AppNav />
      <div className="mx-auto max-w-5xl px-6 py-10">{children}</div>
    </div>
  );
}
