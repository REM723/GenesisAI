"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Wordmark } from "./wordmark";

const LINKS = [
  { href: "/dashboard", label: "Projects" },
  { href: "/settings/keys", label: "Keys" },
];

export function AppNav() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-line/8 bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-8">
          <Wordmark href="/dashboard" />
          <nav className="flex items-center gap-1">
            {LINKS.map((l) => {
              const active = pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-[13px] transition-colors duration-150 ease-out",
                    active ? "text-ink" : "text-faint hover:text-muted",
                  )}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <Button variant="ghost" size="sm" onClick={logout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
