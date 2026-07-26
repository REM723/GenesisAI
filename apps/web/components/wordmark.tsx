import Link from "next/link";

import { cn } from "@/lib/utils";

// Editorial wordmark: serif "Genesis", light "AI" in brass. The mark carries the tone.
export function Wordmark({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      className={cn("group inline-flex items-baseline gap-[3px] tracking-tightest", className)}
    >
      <span className="font-serif text-[19px] italic text-ink">Genesis</span>
      <span className="text-[19px] font-medium text-accent">AI</span>
    </Link>
  );
}
